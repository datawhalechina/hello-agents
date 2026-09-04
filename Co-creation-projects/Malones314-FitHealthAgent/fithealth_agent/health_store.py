"""SQLite persistence for imported Garmin wellness and sleep data."""

from __future__ import annotations

import json
import logging
import sqlite3
import tempfile
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from threading import RLock
from typing import Any
from zoneinfo import ZoneInfo

from fithealth_agent.settings import data_path


BEIJING = ZoneInfo("Asia/Shanghai")
logger = logging.getLogger(__name__)

#: 崩溃后**没有**回滚能力的 journal 模式（DATA-09）。
#: MEMORY 把回滚日志只放在内存里，OFF 干脆不写日志——进程崩溃或断电都会留下
#: 结构性损坏的 health.db，而用户毫不知情。原实现在 WAL 失败时正是静默切到
#: MEMORY，异常还被 `pass` 吞掉。
UNSAFE_JOURNAL_MODES = frozenset({"memory", "off"})

#: 按优先级尝试的安全模式。DELETE 是 SQLite 默认模式，同样具备崩溃恢复能力，
#: 只是并发读写不如 WAL；在网络盘/某些容器挂载上 WAL 会被拒绝，那时退到
#: DELETE 是正确的降级方向。
SAFE_JOURNAL_MODES = ("WAL", "DELETE")


# ── BUG-16：按 timestamp_utc 去重的唯一口径 ────────────────────────────────
#
# 同一个 `timestamp_utc` 会有多行：Garmin 官网按天导出的 ZIP 经常互相重叠（同一份
# WELLNESS.fit 出现在相邻两天的包里），而整包 sha256 不同，导入侧的去重拦不住。
# 实测真实库：heart_rate_samples 16220 行 / 去重 15005（重复 7.5%）、
# health_metric_samples 50684 行 / 去重 46971（重复 7.3%），2026-08-15 整日的
# 每个指标恰好翻倍。
#
# **刻意不在写入侧去重**：每行都记着自己的 source_file_id，`delete_import` 靠它精确
# 回退某一次导入。加 UNIQUE 约束会让两次导入共享同一行，删掉任一个都会连带抹掉
# 另一个的数据。所以去重放在读取侧。
#
# 但读取侧必须只有**一份**口径：原先 `_rebuild_daily_summary` 与
# `query_heart_rate_window` 各自做了去重，而 `get_metric_trend(period="day")` 直扫
# 原始表，于是同一天的日汇总卡片是对的、小时曲线的 samples 却翻倍，两处数字对不上
# （实测 68 组里 11 组不一致，最严重的一天 2424 vs 1212）。把 SQL 抽成常量，让
# "同一口径"是结构上的而不是注释上的。
#
# `MIN(timestamp_local)` 而不是任取一个：重复行理论上可能带不同的本地时间字符串，
# 取 MIN 让小时分桶确定，且与日汇总的 coverage_start 用同一个值。
DEDUPED_HEART_RATE_SQL = """
    SELECT timestamp_utc, ROUND(AVG(bpm)) AS bpm, MIN(timestamp_local) AS timestamp_local
    FROM heart_rate_samples
    WHERE local_date = ?
    GROUP BY timestamp_utc
"""

DEDUPED_METRIC_SQL = """
    SELECT metric, timestamp_utc, AVG(value) AS value,
           MIN(timestamp_local) AS timestamp_local
    FROM health_metric_samples
    WHERE local_date = ?
    GROUP BY metric, timestamp_utc
"""

#: 强度分钟同样要先按 timestamp_utc 去重再求和——重叠导入会让它直接翻倍。
#: **必须 SUM 而不是 MAX**：`moderate_activity_time` / `vigorous_activity_time` 是
#: 区间增量，实测同一天出现 60s / 180s / 60s / 240s，累计量不可能回落。
DEDUPED_INTENSITY_SQL = """
    SELECT timestamp_utc,
           MAX(moderate_activity_s) AS moderate_activity_s,
           MAX(vigorous_activity_s) AS vigorous_activity_s,
           MAX(intensity_level) AS intensity_level
    FROM intensity_observations
    WHERE local_date = ?
    GROUP BY timestamp_utc
"""

#: 日累计型指标：值是**当天累计到某一刻的总量**，而不是采样均值。聚合方式与上面
#: 五个采样型指标完全不同，所以单独列出来而不是硬塞进 `metric_fields`：
#: 周/月直接读日汇总那一列；日视图给的是**日内累计曲线**，不是逐小时瞬时值——
#: 静息代谢没有小时粒度，硬拆成瞬时值只是在编数字。
DAILY_TOTAL_METRICS = ("total_calories",)

#: 计入"活动消耗"的活动类型。与 `_rebuild_daily_summary` 逐字一致：手表还会记
#: `generic` 这类聚合行（实测 2026-08-21 的 generic 累计到 277，而当天活动消耗
#: 是 walking 的 187），把它算进来会重复计数。
COUNTED_ACTIVITY_TYPES = ("walking", "running", "cycling")

#: DATA-25：给 SQL 用的同一份类型清单。原先 `_rebuild_daily_summary` 里手写了五遍
#: `IN ('walking','running','cycling')` 字面量，靠上面那句注释"逐字一致"来维持——
#: 改成插值后"同一口径"就是结构上的了，加一种活动类型不会再漏改某一处。
#: 值全部来自本模块常量，不含外部输入，插值安全。
_COUNTED_ACTIVITY_TYPES_SQL = ", ".join(f"'{name}'" for name in COUNTED_ACTIVITY_TYPES)


#: `monitoring_info`、静息心率来自 `unknown_211`），一行里通常只有一列有值，所以
#: 不能整行取最新。另外每天开头往往还留着**前一天**的静息心率（实测 08-21 00:07
#: 是 61，当天真实值是之后稳定的 55），按 local_date 取当天最后一条正好避开它。
_DEVICE_METRIC_COLUMNS = (
    "resting_metabolic_rate",
    "resting_heart_rate",
    "resting_heart_rate_baseline",
    "utc_offset_minutes",
)

#: DATA-24 修法 (3)：**静息心率类**指标要求本地时刻晚于这个阈值。
#: 上面那句"取当天最后一条正好避开前一天的值"只在**当天有正常读数**时成立；某天
#: 若只有跨零点的残留行（一份包的 16:00Z 样本落到次日本地 00:00），"最后一条"就
#: 必然是前一天的值——实测默认健康概览因此显示 2026-08-23 静息心率 61，那其实是
#: 08-22 的。单条 00:0x 的静息心率按语义属于前一天，直接不采纳。
#:
#: 闸门**只加在静息心率上**，不加在 `resting_metabolic_rate` / `utc_offset_minutes`
#: 上：那两个是"设备对当天的陈述"（日代谢率、时区偏移），00:0x 给出完全正常，按
#: 时刻把它们判掉会凭空丢数据。范围校验按字段语义分别制定，不做一刀切。
#: 用 `substr(timestamp_local, 12, 5)` 取本地墙钟的 HH:MM，**不要**用 sqlite 的
#: `time()`：那个函数会把带偏移量的 ISO 串换算成 UTC，本地 09:00 会变成 01:00 而被
#: 这道闸门误挡。同文件 `coverage_end` 取小时用的也是下标切片，口径一致。
_DEVICE_METRIC_EARLIEST_TIME = "04:00"
_TIME_GATED_DEVICE_COLUMNS = frozenset({
    "resting_heart_rate",
    "resting_heart_rate_baseline",
})


class HealthStoreDegradedError(RuntimeError):
    """健康数据库处于只读降级状态时，任何写入都必须显式失败。

    DATA-09：原实现在数据目录不可用时切到系统临时目录后**仍然允许写入**。
    Windows 清理 %TEMP% 时那些新导入的数据直接蒸发，而用户全程看到的是
    "导入成功"。写入必须显式报错，而不是写进一个注定消失的地方。
    """

    def __init__(self, message: str, *, database_path: Path | None = None) -> None:
        super().__init__(message)
        self.database_path = database_path


class HealthStore:
    def __init__(self, db_path: Path | None = None, raw_dir: Path | None = None) -> None:
        self._uses_default_paths = db_path is None and raw_dir is None
        self._configured_db_path = db_path
        self._configured_raw_dir = raw_dir
        self.db_path = db_path or data_path("health.db")
        self.raw_dir = raw_dir or data_path("health-imports")
        # DATA-12：换库时要独占整个 store，所以所有连接都从这把锁下取。
        # RLock 而非 Lock——同一线程里 save_import → _rebuild_daily_summary
        # 这类嵌套是正常的。
        self._access_lock = RLock()
        self._degraded_reason: str | None = None
        self._journal_mode = "unknown"
        self._open()

    def _open(self) -> None:
        """建目录并初始化 schema；数据目录不可用时退到临时目录并转只读。"""
        self._prepare_directories()
        try:
            self._initialize()
        except sqlite3.OperationalError as exc:
            if not self._uses_default_paths or "disk i/o error" not in str(exc).lower():
                raise
            self._use_temporary_storage(str(exc))
            self._initialize()

    def _prepare_directories(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)


    def resolve_raw_file(self, raw_path: object) -> Path | None:
        """把库里存的 raw_path 解析成 raw_dir 内的真实文件路径。

        只信任文件名部分，其余一律丢弃，原因有二：

        1. 历史数据里存的是**绝对路径**，而且常常来自另一个运行环境
           （例如容器内的 ``/opt/project/data/health-imports/...``）。这些
           路径在本机 100% 解析不到，导致删除导入时原始文件永远删不掉、
           不断堆积孤儿文件。只取文件名即可让老数据重新对上。
        2. 更重要的是安全性：raw_path 会随备份一起流转，如果直接拿它
           ``unlink()``，一个被篡改或来自别的机器的备份就能让删除操作
           触及健康数据目录之外的任意文件。

        返回 None 表示"不要动这个路径"（为空、解析越界、或指向目录外的
        符号链接）。
        """
        if not raw_path:
            return None
        # 兼容 Windows 反斜杠分隔的历史值
        name = PurePosixPath(str(raw_path).replace("\\", "/")).name
        if not name or name in {".", ".."}:
            return None
        base = self.raw_dir.resolve()
        candidate = (base / name).resolve()
        # 解析后必须仍然直接位于 raw_dir 之内（符号链接逃逸会在此被拦下）
        if candidate.parent != base:
            return None
        return candidate

    def _delete_raw_file(self, raw_path: object) -> None:
        """删除某条导入的原始文件；越界或缺失时静默跳过并记录。"""
        target = self.resolve_raw_file(raw_path)
        if target is None:
            if raw_path:
                logger.warning(
                    "Refusing to delete raw health file outside of %s: %r",
                    self.raw_dir,
                    raw_path,
                )
            return
        try:
            target.unlink(missing_ok=True)
        except OSError:
            logger.warning("Failed to delete raw health file %s", target, exc_info=True)

    def _use_temporary_storage(self, reason: str = "") -> None:
        fallback_dir = Path(tempfile.gettempdir()) / "fithealth-agent-health"
        self.db_path = fallback_dir / "health.db"
        self.raw_dir = fallback_dir / "health-imports"
        self._prepare_directories()
        # DATA-09：临时目录只用来让读取接口有个能查的空库，**不接受写入**。
        # 原实现允许写，于是 Windows 清理 %TEMP% 时新导入的数据直接蒸发。
        self._degraded_reason = (
            f"数据目录下的 health.db 无法访问（{reason or '磁盘 I/O 错误'}），"
            f"已退到临时存储 {fallback_dir} 并转为只读：读取接口可用，但一切写入都会被拒绝。"
        )
        logger.error(
            "Health database at the project data directory is unavailable (%s); "
            "falling back to READ-ONLY temporary storage at %s. Imports will be rejected.",
            reason or "disk i/o error",
            fallback_dir,
        )

    @property
    def using_temporary_storage(self) -> bool:
        return self._uses_default_paths and "fithealth-agent-health" in self.db_path.parts

    @property
    def writable(self) -> bool:
        return self._degraded_reason is None

    @property
    def journal_mode(self) -> str:
        return self._journal_mode

    def _require_writable(self) -> None:
        if self._degraded_reason is not None:
            raise HealthStoreDegradedError(
                f"健康数据库处于只读降级状态，写入已被拒绝：{self._degraded_reason}",
                database_path=self.db_path,
            )

    def _apply_journal_mode(self, connection: sqlite3.Connection) -> str:
        """把 journal 模式设成第一个能生效的**安全**模式。

        `PRAGMA journal_mode = X` 在被拒绝时不一定抛异常——它会返回当前实际
        生效的模式。所以这里靠**读回返回值**判断是否成功，而不是靠 try/except，
        原实现只 catch OperationalError，静默失败的情况根本抓不到。
        """
        for mode in SAFE_JOURNAL_MODES:
            try:
                row = connection.execute(f"PRAGMA journal_mode = {mode}").fetchone()
            except sqlite3.DatabaseError as exc:
                logger.warning("PRAGMA journal_mode = %s 失败：%s", mode, exc)
                continue
            applied = str(row[0]).lower() if row else ""
            if applied == mode.lower():
                return applied
        # 两种安全模式都设不上：读回真实模式并告警，但**绝不**主动切到 MEMORY。
        try:
            row = connection.execute("PRAGMA journal_mode").fetchone()
            current = str(row[0]).lower() if row else "unknown"
        except sqlite3.DatabaseError:
            current = "unknown"
        if current in UNSAFE_JOURNAL_MODES:
            logger.error(
                "health.db 的 journal 模式是 %s，崩溃或断电会留下结构性损坏的数据库；"
                "WAL 与 DELETE 都无法启用，请检查数据目录所在的文件系统。",
                current,
            )
        return current

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        self._journal_mode = self._apply_journal_mode(connection)
        return connection

    @contextmanager
    def _connection(self):
        # DATA-12：持锁期间外部无法换库，换库期间也不会有连接开着。
        with self._access_lock:
            connection = self._connect()
            try:
                with connection:
                    yield connection
            finally:
                connection.close()

    # ------------------------------------------------------------------
    # 降级状态与维护（DATA-09 / DATA-12）
    # ------------------------------------------------------------------

    def storage_status(self) -> dict[str, Any]:
        return {
            "available": self._degraded_reason is None,
            "writable": self.writable,
            "degraded_reason": self._degraded_reason,
            "database_path": str(self.db_path),
            "using_temporary_storage": self.using_temporary_storage,
            "journal_mode": self._journal_mode,
            "journal_mode_safe": self._journal_mode not in UNSAFE_JOURNAL_MODES,
        }

    def revalidate(self) -> bool:
        """重新尝试打开配置的数据目录，成功则解除只读降级。

        与 `InfoStore.revalidate()` 同一思路：用户修好权限之后不该被迫重启。
        """
        if self._degraded_reason is None:
            return True
        with self._access_lock:
            previous = (self.db_path, self.raw_dir, self._degraded_reason)
            self.db_path = self._configured_db_path or data_path("health.db")
            self.raw_dir = self._configured_raw_dir or data_path("health-imports")
            self._degraded_reason = None
            try:
                self._prepare_directories()
                self._initialize()
            except (OSError, sqlite3.DatabaseError) as exc:
                self.db_path, self.raw_dir, self._degraded_reason = previous
                logger.warning("健康数据库重新校验失败，继续保持只读降级：%s", exc)
                return False
            logger.info("健康数据库已恢复可写：%s", self.db_path)
            return True

    @contextmanager
    def exclusive_access(self):
        """独占整个 store，期间不会有任何连接开着——换库/删边车文件的前提。

        DATA-12：任何在飞连接持有 health.db 时删掉 `-wal`/`-shm`，那条连接会
        把旧 WAL 内容写回新库；Windows 上覆盖被打开的 health.db 还会直接
        `PermissionError`。
        """
        with self._access_lock:
            yield self

    def reopen(self) -> None:
        """换库之后重新建目录并校验 schema。"""
        with self._access_lock:
            self._journal_mode = "unknown"
            self._open()


    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS health_imports (
                    id TEXT PRIMARY KEY,
                    sha256 TEXT NOT NULL UNIQUE,
                    filename TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    date_hint TEXT,
                    warnings_json TEXT NOT NULL DEFAULT '[]',
                    raw_path TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS health_source_files (
                    id TEXT PRIMARY KEY,
                    import_id TEXT NOT NULL REFERENCES health_imports(id) ON DELETE CASCADE,
                    filename TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    earliest_utc TEXT,
                    latest_utc TEXT,
                    device_serial TEXT,
                    record_count INTEGER NOT NULL DEFAULT 0,
                    message_counts_json TEXT NOT NULL DEFAULT '{}',
                    data_types_json TEXT NOT NULL DEFAULT '[]',
                    warnings_json TEXT NOT NULL DEFAULT '[]'
                );

                CREATE TABLE IF NOT EXISTS heart_rate_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file_id TEXT NOT NULL REFERENCES health_source_files(id) ON DELETE CASCADE,
                    timestamp_utc TEXT NOT NULL,
                    timestamp_local TEXT NOT NULL,
                    local_date TEXT NOT NULL,
                    bpm INTEGER NOT NULL,
                    UNIQUE(source_file_id, timestamp_utc, bpm)
                );

                CREATE INDEX IF NOT EXISTS idx_hr_local_date
                    ON heart_rate_samples(local_date, timestamp_utc);
                CREATE INDEX IF NOT EXISTS idx_hr_utc
                    ON heart_rate_samples(timestamp_utc);

                CREATE TABLE IF NOT EXISTS health_metric_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file_id TEXT NOT NULL REFERENCES health_source_files(id) ON DELETE CASCADE,
                    timestamp_utc TEXT NOT NULL,
                    timestamp_local TEXT NOT NULL,
                    local_date TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    UNIQUE(source_file_id, timestamp_utc, metric)
                );

                CREATE INDEX IF NOT EXISTS idx_metric_date
                    ON health_metric_samples(local_date, metric, timestamp_utc);

                CREATE TABLE IF NOT EXISTS daily_activity_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file_id TEXT NOT NULL REFERENCES health_source_files(id) ON DELETE CASCADE,
                    timestamp_utc TEXT NOT NULL,
                    timestamp_local TEXT NOT NULL,
                    local_date TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    steps INTEGER,
                    distance_m REAL,
                    active_calories REAL,
                    resting_calories REAL,
                    total_calories REAL,
                    active_time_s REAL,
                    UNIQUE(source_file_id, timestamp_utc, activity_type)
                );

                CREATE TABLE IF NOT EXISTS device_daily_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file_id TEXT NOT NULL REFERENCES health_source_files(id) ON DELETE CASCADE,
                    timestamp_utc TEXT NOT NULL,
                    timestamp_local TEXT NOT NULL,
                    local_date TEXT NOT NULL,
                    resting_metabolic_rate REAL,
                    resting_heart_rate INTEGER,
                    resting_heart_rate_baseline INTEGER,
                    utc_offset_minutes INTEGER,
                    UNIQUE(source_file_id, timestamp_utc)
                );

                CREATE INDEX IF NOT EXISTS idx_device_metrics_date
                    ON device_daily_metrics(local_date, timestamp_utc);

                CREATE TABLE IF NOT EXISTS intensity_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file_id TEXT NOT NULL REFERENCES health_source_files(id) ON DELETE CASCADE,
                    timestamp_utc TEXT NOT NULL,
                    timestamp_local TEXT NOT NULL,
                    local_date TEXT NOT NULL,
                    intensity_level INTEGER,
                    moderate_activity_s REAL,
                    vigorous_activity_s REAL,
                    UNIQUE(source_file_id, timestamp_utc)
                );

                CREATE INDEX IF NOT EXISTS idx_intensity_date
                    ON intensity_observations(local_date, timestamp_utc);

                CREATE TABLE IF NOT EXISTS hrv_status_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file_id TEXT NOT NULL REFERENCES health_source_files(id) ON DELETE CASCADE,
                    timestamp_utc TEXT NOT NULL,
                    timestamp_local TEXT NOT NULL,
                    local_date TEXT NOT NULL,
                    -- 下面五列是 fitfile 的原始命名，语义是错的，只为兼容旧数据保留
                    -- （DATA-18：原地改语义会让同一列名在新旧数据里含义不同）。
                    weekly_average REAL,
                    last_night REAL,
                    last_night_average REAL,
                    baseline_low REAL,
                    baseline_high REAL,
                    -- 按 FIT SDK 语义重映射后的列，新代码只读这些
                    weekly_average_ms REAL,
                    last_night_average_ms REAL,
                    last_night_5min_high_ms REAL,
                    baseline_low_upper_ms REAL,
                    baseline_balanced_lower_ms REAL,
                    baseline_balanced_upper_ms REAL,
                    -- 语义未知，原值直存，不参与任何判断
                    unmapped_balanced_high_raw REAL,
                    status TEXT,
                    reading_count INTEGER,
                    UNIQUE(source_file_id, timestamp_utc)
                );

                CREATE TABLE IF NOT EXISTS sleep_stage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file_id TEXT NOT NULL REFERENCES health_source_files(id) ON DELETE CASCADE,
                    sleep_date TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    timestamp_local TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    duration_s INTEGER NOT NULL,
                    UNIQUE(source_file_id, timestamp_utc, stage)
                );

                CREATE INDEX IF NOT EXISTS idx_sleep_stage_date
                    ON sleep_stage_events(sleep_date, timestamp_utc);

                CREATE TABLE IF NOT EXISTS daily_health_summary (
                    date TEXT PRIMARY KEY,
                    heart_rate_min INTEGER,
                    heart_rate_max INTEGER,
                    heart_rate_avg REAL,
                    heart_rate_samples INTEGER NOT NULL DEFAULT 0,
                    coverage_start TEXT,
                    coverage_end TEXT,
                    stress_min REAL,
                    stress_max REAL,
                    stress_avg REAL,
                    stress_samples INTEGER NOT NULL DEFAULT 0,
                    respiration_min REAL,
                    respiration_max REAL,
                    respiration_avg REAL,
                    respiration_samples INTEGER NOT NULL DEFAULT 0,
                    spo2_min REAL,
                    spo2_max REAL,
                    spo2_avg REAL,
                    spo2_samples INTEGER NOT NULL DEFAULT 0,
                    hrv_min REAL,
                    hrv_max REAL,
                    hrv_avg REAL,
                    hrv_samples INTEGER NOT NULL DEFAULT 0,
                    steps INTEGER,
                    distance_m REAL,
                    active_calories REAL,
                    active_time_min REAL,
                    hrv_weekly_average REAL,
                    hrv_last_night REAL,
                    hrv_last_night_average REAL,
                    hrv_baseline_low REAL,
                    hrv_baseline_high REAL,
                    hrv_last_night_average_ms REAL,
                    hrv_last_night_5min_high_ms REAL,
                    hrv_baseline_low_upper_ms REAL,
                    hrv_baseline_balanced_lower_ms REAL,
                    hrv_baseline_balanced_upper_ms REAL,
                    hrv_weekly_average_ms REAL,
                    hrv_status TEXT,
                    hrv_reading_count INTEGER,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sleep_summaries (
                    id TEXT PRIMARY KEY,
                    import_id TEXT NOT NULL REFERENCES health_imports(id) ON DELETE CASCADE,
                    sleep_date TEXT NOT NULL,
                    duration_min INTEGER,
                    score INTEGER,
                    quality TEXT,
                    stress_avg INTEGER,
                    deep_sleep_min INTEGER,
                    light_sleep_min INTEGER,
                    rem_sleep_min INTEGER,
                    awake_min INTEGER,
                    restlessness INTEGER,
                    night_avg_hr INTEGER,
                    resting_hr INTEGER,
                    body_battery_change INTEGER,
                    spo2_avg REAL,
                    spo2_min REAL,
                    respiration_avg REAL,
                    respiration_min REAL,
                    hrv_avg_ms REAL,
                    hrv_7d_status TEXT,
                    raw_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(import_id, sleep_date)
                );

                CREATE INDEX IF NOT EXISTS idx_sleep_date
                    ON sleep_summaries(sleep_date, created_at);

                -- 睡眠会话（来自 FIT，2026-08-24 新增）。
                -- 与 sleep_summaries 的区别：那张表只由睡眠 CSV 填，这张表由
                -- METRICS / SLEEP_DATA 填，是"睡眠时长"唯一可靠的来源。
                -- 一天可能由两份文件各写一行（清醒分钟只有 METRICS 有、不安稳只有
                -- SLEEP_DATA 有），读取时按 sleep_date 合并，缺的字段取非空值。
                CREATE TABLE IF NOT EXISTS sleep_sessions (
                    source_file_id TEXT NOT NULL
                        REFERENCES health_source_files(id) ON DELETE CASCADE,
                    sleep_date TEXT NOT NULL,
                    bed_start_utc TEXT NOT NULL,
                    bed_end_utc TEXT NOT NULL,
                    bed_start_local TEXT NOT NULL,
                    bed_end_local TEXT NOT NULL,
                    time_in_bed_min INTEGER NOT NULL,
                    awake_min INTEGER,
                    score INTEGER,
                    restlessness INTEGER,
                    PRIMARY KEY (source_file_id, sleep_date)
                );

                CREATE INDEX IF NOT EXISTS idx_sleep_session_date
                    ON sleep_sessions(sleep_date);
                """
            )
            source_columns = {
                "message_counts_json": "TEXT NOT NULL DEFAULT '{}'",
                "data_types_json": "TEXT NOT NULL DEFAULT '[]'",
            }
            for name, definition in source_columns.items():
                self._ensure_column(connection, "health_source_files", name, definition)
            activity_columns = {
                "resting_calories": "REAL",
                "total_calories": "REAL",
            }
            for name, definition in activity_columns.items():
                self._ensure_column(connection, "daily_activity_observations", name, definition)
            # DATA-18：SDK 语义列走加列、旧的 fitfile 命名列原样保留。
            hrv_status_columns = {
                "weekly_average_ms": "REAL",
                "last_night_average_ms": "REAL",
                "last_night_5min_high_ms": "REAL",
                "baseline_low_upper_ms": "REAL",
                "baseline_balanced_lower_ms": "REAL",
                "baseline_balanced_upper_ms": "REAL",
                "unmapped_balanced_high_raw": "REAL",
            }
            for name, definition in hrv_status_columns.items():
                self._ensure_column(connection, "hrv_status_summaries", name, definition)
            summary_columns = {
                "stress_min": "REAL", "stress_max": "REAL", "stress_avg": "REAL",
                "stress_samples": "INTEGER NOT NULL DEFAULT 0",
                "respiration_min": "REAL", "respiration_max": "REAL", "respiration_avg": "REAL",
                "respiration_samples": "INTEGER NOT NULL DEFAULT 0",
                "spo2_min": "REAL", "spo2_max": "REAL", "spo2_avg": "REAL",
                "spo2_samples": "INTEGER NOT NULL DEFAULT 0",
                "hrv_min": "REAL", "hrv_max": "REAL", "hrv_avg": "REAL",
                "hrv_samples": "INTEGER NOT NULL DEFAULT 0",
                "steps": "INTEGER", "distance_m": "REAL", "active_calories": "REAL",
                "resting_calories": "REAL", "total_calories": "REAL",
                "active_time_min": "REAL", "hrv_weekly_average": "REAL",
                "hrv_last_night": "REAL", "hrv_last_night_average": "REAL",
                "hrv_baseline_low": "REAL", "hrv_baseline_high": "REAL",
                "hrv_last_night_average_ms": "REAL", "hrv_last_night_5min_high_ms": "REAL",
                "hrv_baseline_low_upper_ms": "REAL", "hrv_baseline_balanced_lower_ms": "REAL",
                "hrv_baseline_balanced_upper_ms": "REAL", "hrv_weekly_average_ms": "REAL",
                "hrv_status": "TEXT", "hrv_reading_count": "INTEGER",
                # 设备算出来的日级指标（原先一条都没入库）
                "resting_metabolic_rate": "REAL",
                "resting_heart_rate": "INTEGER",
                "resting_heart_rate_baseline": "INTEGER",
                "utc_offset_minutes": "INTEGER",
                # 强度分钟：Garmin 的高强度按双倍计入 intensity_minutes
                "moderate_activity_min": "REAL",
                "vigorous_activity_min": "REAL",
                "intensity_minutes": "REAL",
            }
            for name, definition in summary_columns.items():
                self._ensure_column(connection, "daily_health_summary", name, definition)

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection, table: str, column: str, definition: str
    ) -> None:
        columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    @staticmethod
    def _hrv_col(row: Any, column: str) -> float | None:
        """读 `hrv_status_summaries` 的 SDK 语义列，缺列/缺行都当"没有值"。

        用 `sqlite3.Row` 直接下标取一个不存在的列会抛 IndexError；历史库在
        `_ensure_column` 跑过之后不会缺列，但回灌脚本可能拿到更早的连接，
        所以这里不假设。
        """
        if row is None:
            return None
        try:
            value = row[column]
        except (IndexError, KeyError):
            return None
        return float(value) if isinstance(value, (int, float)) else None

    @staticmethod
    def _loads(value: str | None, fallback: Any) -> Any:
        try:
            return json.loads(value or "")
        except json.JSONDecodeError:
            return fallback

    def find_import_by_hash(self, digest: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM health_imports WHERE sha256 = ?", (digest,)
            ).fetchone()
            return self._import_row(connection, row) if row else None

    def save_import(self, parsed: dict[str, Any]) -> dict[str, Any]:
        self._require_writable()
        affected_dates: set[str] = set()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO health_imports
                    (id, sha256, filename, kind, status, date_hint, warnings_json, raw_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    parsed["id"],
                    parsed["sha256"],
                    parsed["filename"],
                    parsed["kind"],
                    parsed["status"],
                    parsed.get("date_hint"),
                    json.dumps(parsed.get("warnings", []), ensure_ascii=False),
                    parsed.get("raw_path"),
                    parsed["created_at"],
                ),
            )

            for source in parsed.get("sources", []):
                connection.execute(
                    """
                    INSERT INTO health_source_files
                        (id, import_id, filename, kind, sha256, earliest_utc, latest_utc,
                         device_serial, record_count, message_counts_json, data_types_json,
                         warnings_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source["id"],
                        parsed["id"],
                        source["filename"],
                        source["kind"],
                        source["sha256"],
                        source.get("earliest_utc"),
                        source.get("latest_utc"),
                        source.get("device_serial"),
                        source.get("record_count", len(source.get("heart_rates", []))),
                        json.dumps(source.get("message_counts", {}), ensure_ascii=False),
                        json.dumps(source.get("data_types", []), ensure_ascii=False),
                        json.dumps(source.get("warnings", []), ensure_ascii=False),
                    ),
                )
                samples = source.get("heart_rates", [])
                connection.executemany(
                    """
                    INSERT OR IGNORE INTO heart_rate_samples
                        (source_file_id, timestamp_utc, timestamp_local, local_date, bpm)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            source["id"],
                            sample["timestamp_utc"],
                            sample["timestamp_local"],
                            sample["local_date"],
                            sample["bpm"],
                        )
                        for sample in samples
                    ],
                )
                affected_dates.update(sample["local_date"] for sample in samples)

                metric_samples = source.get("metric_samples", [])
                connection.executemany(
                    """
                    INSERT OR IGNORE INTO health_metric_samples
                        (source_file_id, timestamp_utc, timestamp_local, local_date, metric, value)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            source["id"], sample["timestamp_utc"], sample["timestamp_local"],
                            sample["local_date"], sample["metric"], sample["value"],
                        )
                        for sample in metric_samples
                    ],
                )
                affected_dates.update(sample["local_date"] for sample in metric_samples)

                activity = source.get("activity_observations", [])
                connection.executemany(
                    """
                    INSERT OR IGNORE INTO daily_activity_observations
                        (source_file_id, timestamp_utc, timestamp_local, local_date, activity_type,
                         steps, distance_m, active_calories, resting_calories, total_calories, active_time_s)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            source["id"], item["timestamp_utc"], item["timestamp_local"],
                            item["local_date"], item["activity_type"], item.get("steps"),
                            item.get("distance_m"), item.get("active_calories"),
                            item.get("resting_calories"), item.get("total_calories"),
                            item.get("active_time_s"),
                        )
                        for item in activity
                    ],
                )
                affected_dates.update(item["local_date"] for item in activity)

                device_metrics = source.get("device_metrics", [])
                connection.executemany(
                    """
                    INSERT OR IGNORE INTO device_daily_metrics
                        (source_file_id, timestamp_utc, timestamp_local, local_date,
                         resting_metabolic_rate, resting_heart_rate,
                         resting_heart_rate_baseline, utc_offset_minutes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            source["id"], item["timestamp_utc"], item["timestamp_local"],
                            item["local_date"], item.get("resting_metabolic_rate"),
                            item.get("resting_heart_rate"),
                            item.get("resting_heart_rate_baseline"),
                            item.get("utc_offset_minutes"),
                        )
                        for item in device_metrics
                    ],
                )
                affected_dates.update(item["local_date"] for item in device_metrics)

                intensity = source.get("intensity_observations", [])
                connection.executemany(
                    """
                    INSERT OR IGNORE INTO intensity_observations
                        (source_file_id, timestamp_utc, timestamp_local, local_date,
                         intensity_level, moderate_activity_s, vigorous_activity_s)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            source["id"], item["timestamp_utc"], item["timestamp_local"],
                            item["local_date"], item.get("intensity_level"),
                            item.get("moderate_activity_s"), item.get("vigorous_activity_s"),
                        )
                        for item in intensity
                    ],
                )
                affected_dates.update(item["local_date"] for item in intensity)

                statuses = source.get("hrv_statuses", [])
                connection.executemany(
                    """
                    INSERT OR IGNORE INTO hrv_status_summaries
                        (source_file_id, timestamp_utc, timestamp_local, local_date,
                         weekly_average, last_night, last_night_average, baseline_low,
                         baseline_high, weekly_average_ms, last_night_average_ms,
                         last_night_5min_high_ms, baseline_low_upper_ms,
                         baseline_balanced_lower_ms, baseline_balanced_upper_ms,
                         unmapped_balanced_high_raw, status, reading_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            source["id"], item["timestamp_utc"], item["timestamp_local"],
                            item["local_date"], item.get("weekly_average"), item.get("last_night"),
                            item.get("last_night_average"), item.get("baseline_low"),
                            item.get("baseline_high"),
                            item.get("weekly_average_ms"), item.get("last_night_average_ms"),
                            item.get("last_night_5min_high_ms"), item.get("baseline_low_upper_ms"),
                            item.get("baseline_balanced_lower_ms"),
                            item.get("baseline_balanced_upper_ms"),
                            item.get("unmapped_balanced_high_raw"),
                            item.get("status"), item.get("reading_count"),
                        )
                        for item in statuses
                    ],
                )
                affected_dates.update(item["local_date"] for item in statuses)

                stages = source.get("sleep_stages", [])
                connection.executemany(
                    """
                    INSERT OR IGNORE INTO sleep_stage_events
                        (source_file_id, sleep_date, timestamp_utc, timestamp_local, stage, duration_s)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            source["id"], item["sleep_date"], item["timestamp_utc"],
                            item["timestamp_local"], item["stage"], item["duration_s"],
                        )
                        for item in stages
                    ],
                )
                affected_dates.update(item["sleep_date"] for item in stages)

                sessions = source.get("sleep_sessions", [])
                connection.executemany(
                    """
                    INSERT OR REPLACE INTO sleep_sessions
                        (source_file_id, sleep_date, bed_start_utc, bed_end_utc,
                         bed_start_local, bed_end_local, time_in_bed_min,
                         awake_min, score, restlessness)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            source["id"], item["sleep_date"],
                            item["bed_start_utc"], item["bed_end_utc"],
                            item["bed_start_local"], item["bed_end_local"],
                            item["time_in_bed_min"], item.get("awake_min"),
                            item.get("score"), item.get("restlessness"),
                        )
                        for item in sessions
                    ],
                )
                affected_dates.update(item["sleep_date"] for item in sessions)

            sleep = parsed.get("sleep")
            if sleep:
                connection.execute(
                    """
                    INSERT INTO sleep_summaries
                        (id, import_id, sleep_date, duration_min, score, quality, stress_avg,
                         deep_sleep_min, light_sleep_min, rem_sleep_min, awake_min, restlessness,
                         night_avg_hr, resting_hr, body_battery_change, spo2_avg, spo2_min,
                         respiration_avg, respiration_min, hrv_avg_ms, hrv_7d_status,
                         raw_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sleep["id"],
                        parsed["id"],
                        sleep["sleep_date"],
                        sleep.get("duration_min"),
                        sleep.get("score"),
                        sleep.get("quality"),
                        sleep.get("stress_avg"),
                        sleep.get("deep_sleep_min"),
                        sleep.get("light_sleep_min"),
                        sleep.get("rem_sleep_min"),
                        sleep.get("awake_min"),
                        sleep.get("restlessness"),
                        sleep.get("night_avg_hr"),
                        sleep.get("resting_hr"),
                        sleep.get("body_battery_change"),
                        sleep.get("spo2_avg"),
                        sleep.get("spo2_min"),
                        sleep.get("respiration_avg"),
                        sleep.get("respiration_min"),
                        sleep.get("hrv_avg_ms"),
                        sleep.get("hrv_7d_status"),
                        json.dumps(sleep.get("raw", {}), ensure_ascii=False),
                        parsed["created_at"],
                    ),
                )
                affected_dates.add(sleep["sleep_date"])

            for day in affected_dates:
                self._rebuild_daily_summary(connection, day)

            row = connection.execute(
                "SELECT * FROM health_imports WHERE id = ?", (parsed["id"],)
            ).fetchone()
            return self._import_row(connection, row)

    def rebuild_daily_summaries(self, days: Iterable[str] | None = None) -> int:
        """重算 `daily_health_summary`；`days=None` 表示重算全部有观测的日期。

        供回灌脚本用（DATA-18 之后 HRV 语义列变了，历史日期需要重算一遍）。
        只重算派生汇总，不触碰任何原始观测表。
        """
        with self.exclusive_access(), self._connect() as connection:
            if days is None:
                targets = sorted({
                    row["local_date"]
                    for row in connection.execute(
                        """
                        SELECT local_date FROM heart_rate_samples
                        UNION SELECT local_date FROM metric_samples
                        UNION SELECT local_date FROM daily_activity_observations
                        UNION SELECT local_date FROM intensity_observations
                        UNION SELECT local_date FROM device_daily_metrics
                        UNION SELECT local_date FROM hrv_status_summaries
                        UNION SELECT sleep_date AS local_date FROM sleep_stage_events
                        """
                    )
                })
            else:
                targets = sorted({str(day) for day in days if day})
            for day in targets:
                self._rebuild_daily_summary(connection, day)
            return len(targets)

    def _rebuild_daily_summary(self, connection: sqlite3.Connection, day: str) -> None:
        heart_rate = connection.execute(
            f"""
            SELECT MIN(bpm) AS hr_min, MAX(bpm) AS hr_max, AVG(bpm) AS hr_avg,
                   COUNT(*) AS sample_count, MIN(timestamp_local) AS coverage_start,
                   MAX(timestamp_local) AS coverage_end
            FROM ({DEDUPED_HEART_RATE_SQL})
            """,
            (day,),
        ).fetchone()
        metric_rows = connection.execute(
            f"""
            SELECT metric, MIN(value) AS value_min, MAX(value) AS value_max,
                   AVG(value) AS value_avg, COUNT(*) AS sample_count
            FROM ({DEDUPED_METRIC_SQL})
            GROUP BY metric
            """,
            (day,),
        ).fetchall()
        metrics = {row["metric"]: row for row in metric_rows}
        activity = connection.execute(
            f"""
            WITH deduplicated AS (
                SELECT timestamp_utc, activity_type, MAX(steps) AS steps,
                       MAX(distance_m) AS distance_m, MAX(active_calories) AS active_calories,
                       MAX(resting_calories) AS resting_calories, MAX(total_calories) AS total_calories,
                       MAX(active_time_s) AS active_time_s
                FROM daily_activity_observations
                WHERE local_date = ?
                GROUP BY timestamp_utc, activity_type
            ), per_type AS (
                SELECT activity_type, MAX(steps) AS steps, MAX(distance_m) AS distance_m,
                       MAX(active_calories) AS active_calories,
                       MAX(resting_calories) AS resting_calories, MAX(total_calories) AS total_calories,
                       MAX(active_time_s) AS active_time_s
                FROM deduplicated
                GROUP BY activity_type
            )
            SELECT SUM(CASE WHEN activity_type IN ({_COUNTED_ACTIVITY_TYPES_SQL}) THEN COALESCE(steps, 0) ELSE 0 END) AS steps,
                   SUM(CASE WHEN activity_type IN ({_COUNTED_ACTIVITY_TYPES_SQL}) THEN COALESCE(distance_m, 0) ELSE 0 END) AS distance_m,
                   SUM(CASE WHEN activity_type IN ({_COUNTED_ACTIVITY_TYPES_SQL})
                            THEN COALESCE(active_calories, 0) ELSE 0 END) AS active_calories,
                   MAX(resting_calories) AS resting_calories,
                   MAX(total_calories) AS total_calories,
                   SUM(CASE WHEN activity_type IN ({_COUNTED_ACTIVITY_TYPES_SQL})
                            THEN COALESCE(active_time_s, 0) ELSE 0 END) AS active_time_s,
                   COUNT(*) AS activity_types
            FROM per_type
            """,
            (day,),
        ).fetchone()
        hrv_status = connection.execute(
            """
            SELECT * FROM hrv_status_summaries
            WHERE local_date = ?
            ORDER BY timestamp_utc DESC LIMIT 1
            """,
            (day,),
        ).fetchone()
        intensity = connection.execute(
            f"""
            SELECT SUM(COALESCE(moderate_activity_s, 0)) AS moderate_s,
                   SUM(COALESCE(vigorous_activity_s, 0)) AS vigorous_s,
                   COUNT(*) AS observations
            FROM ({DEDUPED_INTENSITY_SQL})
            """,
            (day,),
        ).fetchone()
        device: dict[str, Any] = {}
        for column in _DEVICE_METRIC_COLUMNS:
            time_gate = (
                _DEVICE_METRIC_EARLIEST_TIME
                if column in _TIME_GATED_DEVICE_COLUMNS
                else "00:00"
            )
            row = connection.execute(
                f"""
                SELECT {column} AS value FROM device_daily_metrics
                WHERE local_date = ? AND {column} IS NOT NULL
                  AND substr(timestamp_local, 12, 5) >= ?
                ORDER BY timestamp_utc DESC LIMIT 1
                """,
                (day, time_gate),
            ).fetchone()
            device[column] = row["value"] if row else None
        has_hr = bool(heart_rate and heart_rate["sample_count"] and heart_rate["sample_count"] >= 10)
        has_metrics = bool(metric_rows)
        has_activity = bool(activity and activity["activity_types"])
        has_intensity = bool(intensity and intensity["observations"])
        has_device = any(value is not None for value in device.values())
        if (
            not has_hr and not has_metrics and not has_activity
            and not hrv_status and not has_intensity and not has_device
        ):
            connection.execute("DELETE FROM daily_health_summary WHERE date = ?", (day,))
            return

        active_calories = (
            round(float(activity["active_calories"]), 1) if has_activity else None
        )
        # 静息热量优先用设备报的静息代谢率（monitoring_info.resting_metabolic_rate）。
        # `daily_activity_observations.resting_calories` 恒为空——读取方去 monitoring
        # 里找 resting_calories/bmr_calories，而那个数其实在 monitoring_info 里，而
        # monitoring_info 整条消息以前从未被处理。
        resting_calories = None
        if device["resting_metabolic_rate"] is not None:
            coverage_end = heart_rate["coverage_end"] if has_hr else None
            try:
                hour = int(str(coverage_end)[11:13]) if coverage_end else 23
            except (TypeError, ValueError):
                hour = 23
            resting_calories = float(device["resting_metabolic_rate"]) * (hour + 1) / 24
        if resting_calories is None and has_activity and activity["resting_calories"] is not None:
            resting_calories = float(activity["resting_calories"])
        # 总热量：设备直接报了就用它，否则按"静息 + 活动"推导（Garmin 自己也是
        # 这个定义）。推导出来的值只在两项都有时才给，避免把 None 当 0 用。
        total_calories = (
            float(activity["total_calories"])
            if has_activity and activity["total_calories"] is not None
            else None
        )
        if total_calories is None and resting_calories is not None and active_calories is not None:
            total_calories = resting_calories + active_calories
        # DATA-25：必须用 `is not None` 而不是真值判断。`0` 是 falsy，旧写法把"当天
        # 增量确实为 0"写成 NULL，于是 intensity 整节从 available_sections 消失——
        # 实测 16 天里有 7 天落到这个分支，而那些天各有 420~490 条观测；08-08 走了
        # 8371 步、活动 110.7 分钟却显示"没有强度数据"。0 分钟和没有数据不是一回事。
        moderate_min = (
            round(float(intensity["moderate_s"]) / 60, 1)
            if has_intensity and intensity["moderate_s"] is not None else None
        )
        vigorous_min = (
            round(float(intensity["vigorous_s"]) / 60, 1)
            if has_intensity and intensity["vigorous_s"] is not None else None
        )
        # Garmin 的强度分钟：高强度按双倍计入（WHO 每周 150 分钟目标用的也是这个口径）
        intensity_minutes = None
        if moderate_min is not None or vigorous_min is not None:
            intensity_minutes = round((moderate_min or 0) + (vigorous_min or 0) * 2, 1)

        values: dict[str, Any] = {
            "date": day,
            "heart_rate_min": int(heart_rate["hr_min"]) if has_hr else None,
            "heart_rate_max": int(heart_rate["hr_max"]) if has_hr else None,
            "heart_rate_avg": round(float(heart_rate["hr_avg"]), 1) if has_hr else None,
            "heart_rate_samples": int(heart_rate["sample_count"]) if has_hr else 0,
            "coverage_start": heart_rate["coverage_start"] if has_hr else None,
            "coverage_end": heart_rate["coverage_end"] if has_hr else None,
            "steps": int(activity["steps"]) if has_activity and activity["steps"] is not None else None,
            "distance_m": round(float(activity["distance_m"]), 2) if has_activity and activity["distance_m"] is not None else None,
            "active_calories": active_calories,
            "resting_calories": round(resting_calories, 1) if resting_calories is not None else None,
            "total_calories": round(total_calories, 1) if total_calories is not None else None,
            "active_time_min": round(float(activity["active_time_s"]) / 60, 1) if has_activity else None,
            "resting_metabolic_rate": device["resting_metabolic_rate"],
            "resting_heart_rate": device["resting_heart_rate"],
            "resting_heart_rate_baseline": device["resting_heart_rate_baseline"],
            "utc_offset_minutes": device["utc_offset_minutes"],
            "moderate_activity_min": moderate_min,
            "vigorous_activity_min": vigorous_min,
            "intensity_minutes": intensity_minutes,
            # 旧的 fitfile 命名列（语义是错的，仅为兼容旧数据保留，别给新代码用）
            "hrv_weekly_average": hrv_status["weekly_average"] if hrv_status else None,
            "hrv_last_night": hrv_status["last_night"] if hrv_status else None,
            "hrv_last_night_average": hrv_status["last_night_average"] if hrv_status else None,
            "hrv_baseline_low": hrv_status["baseline_low"] if hrv_status else None,
            "hrv_baseline_high": hrv_status["baseline_high"] if hrv_status else None,
            # DATA-18：SDK 语义列。直接抄 `hrv_status_summaries` 里已经重映射好的
            # 同名列，**不要**在这里再做一次名字搬运——上一版就是在这里手写映射，
            # 结果和导入侧各错一处。映射逻辑只有 `_HRV_STATUS_FIELDS` 一处。
            "hrv_weekly_average_ms": self._hrv_col(hrv_status, "weekly_average_ms"),
            "hrv_last_night_average_ms": self._hrv_col(hrv_status, "last_night_average_ms"),
            "hrv_last_night_5min_high_ms": self._hrv_col(hrv_status, "last_night_5min_high_ms"),
            "hrv_baseline_low_upper_ms": self._hrv_col(hrv_status, "baseline_low_upper_ms"),
            "hrv_baseline_balanced_lower_ms": self._hrv_col(
                hrv_status, "baseline_balanced_lower_ms"
            ),
            "hrv_baseline_balanced_upper_ms": self._hrv_col(
                hrv_status, "baseline_balanced_upper_ms"
            ),
            "hrv_status": hrv_status["status"] if hrv_status else None,
            "hrv_reading_count": hrv_status["reading_count"] if hrv_status else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        for metric in ("stress", "respiration", "spo2", "hrv"):
            row = metrics.get(metric)
            values[f"{metric}_min"] = round(float(row["value_min"]), 1) if row else None
            values[f"{metric}_max"] = round(float(row["value_max"]), 1) if row else None
            values[f"{metric}_avg"] = round(float(row["value_avg"]), 1) if row else None
            values[f"{metric}_samples"] = int(row["sample_count"]) if row else 0

        columns = list(values)
        updates = ", ".join(f"{column}=excluded.{column}" for column in columns if column != "date")
        connection.execute(
            f"""
            INSERT INTO daily_health_summary ({', '.join(columns)})
            VALUES ({', '.join(':' + column for column in columns)})
            ON CONFLICT(date) DO UPDATE SET {updates}
            """,
            values,
        )

    def _import_row(self, connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        counts = connection.execute(
            """
            SELECT COUNT(*) AS source_count,
                   (SELECT COUNT(*) FROM heart_rate_samples hr
                    JOIN health_source_files src ON src.id = hr.source_file_id
                    WHERE src.import_id = ?) AS heart_rate_count,
                   (SELECT COUNT(*) FROM health_metric_samples hm
                    JOIN health_source_files src ON src.id = hm.source_file_id
                    WHERE src.import_id = ?) AS metric_count,
                   (SELECT COUNT(*) FROM sleep_stage_events se
                    JOIN health_source_files src ON src.id = se.source_file_id
                    WHERE src.import_id = ?) AS sleep_stage_count
            FROM health_source_files
            WHERE import_id = ?
            """,
            (row["id"], row["id"], row["id"], row["id"]),
        ).fetchone()
        source_rows = connection.execute(
            "SELECT data_types_json FROM health_source_files WHERE import_id = ?", (row["id"],)
        ).fetchall()
        data_types = sorted(
            {item for source in source_rows for item in self._loads(source["data_types_json"], [])}
        )
        if row["kind"] == "sleep_csv":
            data_types.append("sleep_summary")
        sleep = connection.execute(
            """
            SELECT sleep_date FROM sleep_summaries WHERE import_id = ?
            UNION
            SELECT se.sleep_date FROM sleep_stage_events se
            JOIN health_source_files sf ON sf.id = se.source_file_id
            WHERE sf.import_id = ?
            LIMIT 1
            """,
            (row["id"], row["id"]),
        ).fetchone()
        return {
            "id": row["id"],
            "sha256": row["sha256"],
            "filename": row["filename"],
            "kind": row["kind"],
            "status": row["status"],
            "date_hint": row["date_hint"],
            "warnings": self._loads(row["warnings_json"], []),
            "raw_path": row["raw_path"],
            "created_at": row["created_at"],
            "source_count": int(counts["source_count"] or 0),
            "heart_rate_count": int(counts["heart_rate_count"] or 0),
            "metric_count": int(counts["metric_count"] or 0),
            "sleep_stage_count": int(counts["sleep_stage_count"] or 0),
            "data_types": data_types,
            "sleep_date": sleep["sleep_date"] if sleep else None,
        }

    def list_imports(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM health_imports ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._import_row(connection, row) for row in rows]

    def get_import_detail(self, import_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM health_imports WHERE id = ?", (import_id,)
            ).fetchone()
            if not row:
                return None
            result = self._import_row(connection, row)
            sources = connection.execute(
                "SELECT * FROM health_source_files WHERE import_id = ? ORDER BY filename",
                (import_id,),
            ).fetchall()
            result["sources"] = [
                {
                    "id": source["id"],
                    "filename": source["filename"],
                    "kind": source["kind"],
                    "record_count": source["record_count"],
                    "earliest_utc": source["earliest_utc"],
                    "latest_utc": source["latest_utc"],
                    "data_types": self._loads(source["data_types_json"], []),
                    "message_counts": self._loads(source["message_counts_json"], {}),
                    "warnings": self._loads(source["warnings_json"], []),
                }
                for source in sources
            ]
            return result

    def get_sleep(self, sleep_date: str) -> dict[str, Any] | None:
        date.fromisoformat(sleep_date)
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT ss.*, hi.filename AS source_filename
                FROM sleep_summaries ss
                JOIN health_imports hi ON hi.id = ss.import_id
                WHERE ss.sleep_date = ?
                ORDER BY ss.created_at DESC LIMIT 1
                """,
                (sleep_date,),
            ).fetchone()
            stage_rows = connection.execute(
                """
                WITH deduplicated AS (
                    SELECT timestamp_utc, MIN(timestamp_local) AS timestamp_local, stage,
                           MAX(duration_s) AS duration_s
                    FROM sleep_stage_events WHERE sleep_date = ?
                    GROUP BY timestamp_utc, stage
                )
                SELECT stage, SUM(duration_s) AS duration_s, COUNT(*) AS segments,
                       MIN(timestamp_local) AS coverage_start, MAX(timestamp_local) AS last_stage_start
                FROM deduplicated
                GROUP BY stage
                """,
                (sleep_date,),
            ).fetchall()
            coverage = connection.execute(
                """
                WITH deduplicated AS (
                    SELECT timestamp_utc, MIN(timestamp_local) AS timestamp_local, stage,
                           MAX(duration_s) AS duration_s
                    FROM sleep_stage_events WHERE sleep_date = ?
                    GROUP BY timestamp_utc, stage
                )
                SELECT MIN(timestamp_local) AS coverage_start,
                       SUM(duration_s) AS duration_s, COUNT(*) AS segments
                FROM deduplicated
                """,
                (sleep_date,),
            ).fetchone()
            last_stage = connection.execute(
                """
                SELECT MIN(timestamp_local) AS timestamp_local, MAX(duration_s) AS duration_s
                FROM sleep_stage_events WHERE sleep_date = ?
                GROUP BY timestamp_utc, stage ORDER BY timestamp_utc DESC LIMIT 1
                """,
                (sleep_date,),
            ).fetchone()
            # 一天可能有两行（METRICS 一份、SLEEP_DATA 一份），字段互补，取非空值合并。
            session = connection.execute(
                """
                SELECT MIN(bed_start_utc) AS bed_start_utc, MAX(bed_end_utc) AS bed_end_utc,
                       MIN(bed_start_local) AS bed_start_local, MAX(bed_end_local) AS bed_end_local,
                       MAX(time_in_bed_min) AS time_in_bed_min,
                       MAX(awake_min) AS awake_min, MAX(score) AS score,
                       MAX(restlessness) AS restlessness, COUNT(*) AS rows
                FROM sleep_sessions WHERE sleep_date = ?
                """,
                (sleep_date,),
            ).fetchone()
        fit_summary = None
        if stage_rows or (session and session["rows"]):
            # 睡眠时长的口径（2026-08-24 用 5 份睡眠 CSV 真值重新定过）：
            #
            #   躺床时长 = sleep start 事件 → sleep stop 事件      （5/5 天精确）
            #   睡眠时长 = 躺床时长 − 清醒分钟（METRICS unknown_384.unknown_24）
            #
            # **不要再用「深+浅+REM 累加」当睡眠时长。** 那是上一版的做法，实测
            # 每天都少报：2026-08-10 少 142 分钟、08-19 少 144、08-20 少 79、
            # 08-21 少 96、08-22 少 13。原因不是加法写错，而是 FIT 里那条
            # sleep_level 时间线一晚只有 15~33 条记录，是设备端的粗分期，
            # Garmin Connect 的分期是云端重算的：08-21 深度 53 vs 119、
            # 清醒 156 vs 67。分期时长在 FIT 里根本不存在（原值/×60/÷2/占比都
            # 试过，五天找不到一致字段），所以下面把它单列成 `device_stage_*`
            # 并标 `stage_source`，不再冒充 Garmin 的口径。
            stage_minutes = {
                item["stage"]: round(float(item["duration_s"]) / 60, 1) for item in stage_rows
            } if stage_rows else {}
            has_session = bool(session and session["rows"])
            if has_session:
                time_in_bed = int(session["time_in_bed_min"])
                awake = session["awake_min"]
                asleep = time_in_bed - int(awake) if awake is not None else None
                fit_summary = {
                    "source_type": "fit_sleep_session",
                    "sleep_date": sleep_date,
                    "duration_min": asleep,
                    "time_in_bed_min": time_in_bed,
                    "awake_min": int(awake) if awake is not None else None,
                    "score": session["score"],
                    "restlessness": session["restlessness"],
                    "bed_start_local": session["bed_start_local"],
                    "bed_end_local": session["bed_end_local"],
                    "is_partial": asleep is None,
                }
                if asleep is None:
                    fit_summary["duration_note"] = (
                        "缺少清醒分钟（该日没有 METRICS 文件），只能给出躺床时长"
                    )
            elif stage_rows:
                fit_summary = {
                    "source_type": "fit_sleep_stages_only",
                    "sleep_date": sleep_date,
                    "duration_min": None,
                    "time_in_bed_min": round(float(coverage["duration_s"]) / 60, 1),
                    "is_partial": True,
                    "duration_note": (
                        "该日只有分期时间线、没有睡眠会话汇总，无法给出睡眠时长；"
                        "分期是设备端粗分期，与 Garmin Connect 的分期不是一个口径"
                    ),
                }
            if fit_summary is not None and stage_rows:
                coverage_end = None
                if last_stage:
                    coverage_end = (
                        datetime.fromisoformat(last_stage["timestamp_local"])
                        + timedelta(seconds=last_stage["duration_s"])
                    ).isoformat()
                fit_summary.update({
                    "stage_source": "device_coarse_timeline",
                    "device_stage_deep_min": stage_minutes.get("deep_sleep", 0),
                    "device_stage_light_min": stage_minutes.get("light_sleep", 0),
                    "device_stage_rem_min": stage_minutes.get("rem_sleep", 0),
                    "device_stage_awake_min": stage_minutes.get("awake", 0),
                    "segments": int(coverage["segments"]),
                    "coverage_start": coverage["coverage_start"],
                    "coverage_end": coverage_end,
                })
            if fit_summary is not None:
                # 夜间心率：睡眠窗口内的心率样本（走 BUG-16 那套按 timestamp_utc
                # 去重）。窗口优先用睡眠会话的躺床起止——它来自文件里明写的
                # start/stop 事件，比分期时间线的覆盖范围准（后者会漏掉开头
                # 1~14 分钟）。
                if has_session:
                    window_start = session["bed_start_local"]
                    window_end = session["bed_end_local"]
                else:
                    window_start = coverage["coverage_start"]
                    window_end = fit_summary.get("coverage_end")
                fit_summary.update(self._night_heart_rate(window_start, window_end))
        if not row:
            return fit_summary
        result = dict(row)
        result["raw"] = self._loads(result.pop("raw_json"), {})
        result["source_type"] = "sleep_csv"
        if fit_summary:
            result["fit_stage_summary"] = fit_summary
        return result

    def _night_heart_rate(
        self, coverage_start: str | None, coverage_end: str | None
    ) -> dict[str, Any]:
        """睡眠窗口内的平均/最低心率。

        睡眠**分数**其实在 FIT 里（见 health_importer 的 `_SLEEP_SCORE_FALLBACKS`，
        2026-08-24 用 17 份包确证），只有「质量」那个中文分档是 Connect 的展示层
        文案。夜间心率则一直都能自己算——原料是分钟级心率 + 睡眠窗口。
        按 `timestamp_utc` 去重后再统计，与日汇总同口径（BUG-16）。
        """
        if not coverage_start or not coverage_end:
            return {"night_avg_hr": None, "night_min_hr": None}
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT AVG(bpm) AS avg_bpm, MIN(bpm) AS min_bpm, COUNT(*) AS samples FROM (
                    SELECT timestamp_utc, ROUND(AVG(bpm)) AS bpm
                    FROM heart_rate_samples
                    WHERE timestamp_local >= ? AND timestamp_local <= ?
                    GROUP BY timestamp_utc
                )
                """,
                (coverage_start, coverage_end),
            ).fetchone()
        if not row or not row["samples"]:
            return {"night_avg_hr": None, "night_min_hr": None}
        return {
            "night_avg_hr": round(float(row["avg_bpm"]), 1),
            "night_min_hr": int(row["min_bpm"]),
            "night_hr_samples": int(row["samples"]),
        }

    def get_daily_health(self, day: str) -> dict[str, Any]:
        date.fromisoformat(day)
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM daily_health_summary WHERE date = ?", (day,)
            ).fetchone()
        summary = dict(row) if row else {}

        def metric(name: str) -> dict[str, Any] | None:
            if not summary.get(f"{name}_samples"):
                return None
            return {
                "min": summary.get(f"{name}_min"),
                "max": summary.get(f"{name}_max"),
                "avg": summary.get(f"{name}_avg"),
                "samples": summary.get(f"{name}_samples"),
            }

        heart_rate = None
        if summary.get("heart_rate_samples"):
            heart_rate = {
                "min": summary.get("heart_rate_min"),
                "max": summary.get("heart_rate_max"),
                "avg": summary.get("heart_rate_avg"),
                "samples": summary.get("heart_rate_samples"),
                "coverage_start": summary.get("coverage_start"),
                "coverage_end": summary.get("coverage_end"),
            }
        activity = None
        if any(summary.get(key) is not None for key in ("steps", "distance_m", "active_calories", "resting_calories", "total_calories")):
            activity = {
                "steps": summary.get("steps"),
                "distance_m": summary.get("distance_m"),
                "active_calories": summary.get("active_calories"),
                "resting_calories": summary.get("resting_calories"),
                "total_calories": summary.get("total_calories"),
                "active_time_min": summary.get("active_time_min"),
            }
        # 强度分钟：中等 + 高强度×2，与 Garmin/WHO 的每周 150 分钟目标同口径。
        intensity = None
        if summary.get("intensity_minutes") is not None:
            intensity = {
                "moderate_min": summary.get("moderate_activity_min"),
                "vigorous_min": summary.get("vigorous_activity_min"),
                "intensity_minutes": summary.get("intensity_minutes"),
            }
        # 设备算出来的日级指标。静息心率是逆向推断的字段（见 health_importer 里
        # `_RESTING_HR_MESSAGE` 的证据），所以单独成节而不是混进 heart_rate。
        device = {
            key: summary.get(key)
            for key in (
                "resting_metabolic_rate",
                "resting_heart_rate",
                "resting_heart_rate_baseline",
                "utc_offset_minutes",
            )
        }
        if not any(value is not None for value in device.values()):
            device = None
        hrv = metric("hrv")
        # DATA-18：`*_ms` 是按 FIT SDK 语义重映射后的值，是给前端与 Agent 看的正本。
        # 无后缀的五个键是 fitfile 原始命名，语义错（`last_night_average` 其实是
        # 昨夜 5 分钟峰值、`baseline_high` 其实是平衡区**下限**），只为兼容旧调用
        # 方留一段时间，新代码不要读。
        status_fields = {
            "weekly_average_ms": summary.get("hrv_weekly_average_ms"),
            "last_night_average_ms": summary.get("hrv_last_night_average_ms"),
            "last_night_5min_high_ms": summary.get("hrv_last_night_5min_high_ms"),
            "baseline_low_upper_ms": summary.get("hrv_baseline_low_upper_ms"),
            "baseline_balanced_lower_ms": summary.get("hrv_baseline_balanced_lower_ms"),
            "baseline_balanced_upper_ms": summary.get("hrv_baseline_balanced_upper_ms"),
            "status": summary.get("hrv_status"),
            "reading_count": summary.get("hrv_reading_count"),
            "weekly_average": summary.get("hrv_weekly_average"),
            "last_night": summary.get("hrv_last_night"),
            "last_night_average": summary.get("hrv_last_night_average"),
            "baseline_low": summary.get("hrv_baseline_low"),
            "baseline_high": summary.get("hrv_baseline_high"),
        }

        if any(value is not None for value in status_fields.values()):
            hrv = {**(hrv or {}), **status_fields}
        return {
            "date": day,
            "heart_rate": heart_rate,
            "stress": metric("stress"),
            "respiration": metric("respiration"),
            "spo2": metric("spo2"),
            "hrv": hrv,
            "activity": activity,
            "intensity": intensity,
            "device": device,
            "sleep": self.get_sleep(day),
        }

    def get_daily_overview(self, day: str | None = None) -> dict[str, Any]:
        """Return one calendar day's health overview, defaulting to the latest data day."""
        if day:
            selected_day = date.fromisoformat(day).isoformat()
        else:
            with self._connection() as connection:
                row = connection.execute(
                    """
                    SELECT MAX(day) AS latest_day FROM (
                        SELECT date AS day FROM daily_health_summary
                         WHERE heart_rate_samples >= 10
                            OR steps IS NOT NULL OR stress_samples > 0 OR hrv_reading_count IS NOT NULL
                        UNION ALL SELECT sleep_date AS day FROM sleep_summaries
                        UNION ALL SELECT sleep_date AS day FROM sleep_stage_events
                    )
                    """
                ).fetchone()
            selected_day = row["latest_day"] if row and row["latest_day"] else date.today().isoformat()

        overview = self.get_daily_health(selected_day)
        available_sections = [
            name for name in ("sleep", "heart_rate", "stress", "hrv", "activity", "intensity", "device")
            if overview.get(name)
        ]
        return {
            **overview,
            "available_sections": available_sections,
            "has_data": bool(available_sections),
        }

    def get_health_range(self, start_date: str, end_date: str, max_days: int = 31) -> list[dict[str, Any]]:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        if end < start:
            raise ValueError("结束日期不能早于开始日期")
        if (end - start).days + 1 > max_days:
            raise ValueError(f"查询范围不能超过 {max_days} 天")
        return [
            self.get_daily_health((start + timedelta(days=offset)).isoformat())
            for offset in range((end - start).days + 1)
        ]

    def _cumulative_calories_by_hour(
        self, connection: sqlite3.Connection, day: str
    ) -> list[dict[str, Any]]:
        """当天逐小时的累计总热量（静息 + 活动）。

        静息部分按静息代谢率**匀速摊到全天**：手表只给一个 kcal/天 的日速率，没有
        小时粒度，所以到第 h 小时末算作 `RMR × (h+1)/24`。活动部分是
        `daily_activity_observations.active_calories`，它在每个 activity_type 内是
        **单调累计**的（已在真实数据上逐日核对过），所以取"截至该小时的最大值"再
        按类型求和即可；某个类型在早些小时还没出现就计 0，那正是它当时还没开始。

        整日完整时最后一点必然等于日汇总的 `total_calories`——有测试钉住这条。
        """
        rows = connection.execute(
            f"""
            SELECT substr(timestamp_local, 1, 13) AS bucket, activity_type,
                   MAX(active_calories) AS active_calories
            FROM (
                SELECT timestamp_utc, MIN(timestamp_local) AS timestamp_local,
                       activity_type, MAX(active_calories) AS active_calories
                FROM daily_activity_observations
                WHERE local_date = ? AND active_calories IS NOT NULL
                GROUP BY timestamp_utc, activity_type
            )
            WHERE activity_type IN ({', '.join('?' * len(COUNTED_ACTIVITY_TYPES))})
            GROUP BY bucket, activity_type ORDER BY bucket
            """,
            (day, *COUNTED_ACTIVITY_TYPES),
        ).fetchall()
        summary = connection.execute(
            "SELECT resting_metabolic_rate FROM daily_health_summary WHERE date = ?", (day,)
        ).fetchone()
        resting_rate = summary["resting_metabolic_rate"] if summary else None
        if resting_rate is None:
            # 没有静息代谢率就没有"总热量"可言——静息是主项（2026-08-21 是 2417 里的
            # 2230），只画活动那部分却标成总热量会低报 90% 以上。返回空与周/月视图
            # 一致：`_rebuild_daily_summary` 也只在静息与活动都有时才写 total_calories。
            return []

        # 曲线只画到**当天真正有数据的最后一小时**，不往后补满 24 格：今天才过到
        # 10 点就画出一整天，等于凭空替用户消耗了 14 小时的静息热量。
        last_row = connection.execute(
            """
            SELECT MAX(bucket) AS bucket FROM (
                SELECT substr(timestamp_local, 1, 13) AS bucket FROM heart_rate_samples
                WHERE local_date = ?
                UNION ALL
                SELECT substr(timestamp_local, 1, 13) FROM daily_activity_observations
                WHERE local_date = ?
            )
            """,
            (day, day),
        ).fetchone()
        if not last_row or not last_row["bucket"]:
            return []
        last_hour = int(last_row["bucket"][11:13])

        per_hour: dict[int, dict[str, float]] = {}
        for row in rows:
            hour = int(row["bucket"][11:13])
            per_hour.setdefault(hour, {})[row["activity_type"]] = float(row["active_calories"])

        items: list[dict[str, Any]] = []
        running: dict[str, float] = {}
        for hour in range(last_hour + 1):
            for activity_type, value in per_hour.get(hour, {}).items():
                running[activity_type] = max(running.get(activity_type, 0.0), value)
            active = sum(running.values())
            resting = float(resting_rate) * (hour + 1) / 24
            items.append({
                "label": f"{hour:02d}:00",
                "value": round(resting + active, 1),
                "active_calories": round(active, 1),
                "resting_calories": round(resting, 1),
            })
        return items

    def get_metric_trend(self, metric: str, period: str, end_date: str | None = None) -> dict[str, Any]:
        """Return chart-ready health metric averages for a day, week, or month."""
        metric_fields = {
            "heart_rate": ("heart_rate_avg", "heart_rate_samples"),
            "stress": ("stress_avg", "stress_samples"),
            "respiration": ("respiration_avg", "respiration_samples"),
            "spo2": ("spo2_avg", "spo2_samples"),
            "hrv": ("hrv_avg", "hrv_samples"),
        }
        if metric not in metric_fields and metric not in DAILY_TOTAL_METRICS:
            raise ValueError("Unsupported health metric")
        if period not in {"day", "week", "month"}:
            raise ValueError("Unsupported trend period")
        cumulative = metric in DAILY_TOTAL_METRICS and period == "day"

        with self._connection() as connection:
            if end_date:
                end = date.fromisoformat(end_date)
            else:
                row = connection.execute(
                    "SELECT MAX(date) AS latest_date FROM daily_health_summary"
                ).fetchone()
                end = date.fromisoformat(row["latest_date"]) if row and row["latest_date"] else date.today()

            if metric in DAILY_TOTAL_METRICS and period == "day":
                items = self._cumulative_calories_by_hour(connection, end.isoformat())
                start = end
            elif period == "day":
                # BUG-16：与 _rebuild_daily_summary 共用 DEDUPED_* 口径。原先这里
                # 直扫原始表只按小时分桶，重叠导入让 samples 翻倍、被重复的时段在
                # 该小时均值里拿到双份权重，而同一天的日汇总卡片是对的——两处数字
                # 对不上，用户无从判断哪个可信。
                if metric == "heart_rate":
                    rows = connection.execute(
                        f"""
                        SELECT substr(timestamp_local, 1, 13) AS bucket, ROUND(AVG(bpm), 1) AS value,
                               COUNT(*) AS samples
                        FROM ({DEDUPED_HEART_RATE_SQL})
                        GROUP BY bucket ORDER BY bucket
                        """,
                        (end.isoformat(),),
                    ).fetchall()
                else:
                    # metric 过滤刻意放在**外层**：内层必须与日汇总逐字一致，否则
                    # "同一口径"又变成两份需要各自维护的 SQL。一天的指标行数在
                    # 5 千量级，先整日去重再筛指标的代价可以忽略。
                    rows = connection.execute(
                        f"""
                        SELECT substr(timestamp_local, 1, 13) AS bucket, ROUND(AVG(value), 1) AS value,
                               COUNT(*) AS samples
                        FROM ({DEDUPED_METRIC_SQL})
                        WHERE metric = ?
                        GROUP BY bucket ORDER BY bucket
                        """,
                        (end.isoformat(), metric),
                    ).fetchall()
                items = [
                    {"label": row["bucket"][11:13] + ":00", "value": row["value"], "samples": row["samples"]}
                    for row in rows
                ]
                start = end
            else:
                days = 7 if period == "week" else 30
                start = end - timedelta(days=days - 1)
                if metric in DAILY_TOTAL_METRICS:
                    # 日累计型指标没有"采样数"这个概念，筛选条件也就不能用
                    # `samples > 0`——只能按值是否存在来筛。
                    rows = connection.execute(
                        f"""
                        SELECT date, {metric} AS value
                        FROM daily_health_summary
                        WHERE date >= ? AND date <= ? AND {metric} IS NOT NULL
                        ORDER BY date
                        """,
                        (start.isoformat(), end.isoformat()),
                    ).fetchall()
                    items = [{"label": row["date"], "value": row["value"]} for row in rows]
                else:
                    value_field, sample_field = metric_fields[metric]
                    rows = connection.execute(
                        f"""
                        SELECT date, {value_field} AS value, {sample_field} AS samples
                        FROM daily_health_summary
                        WHERE date >= ? AND date <= ? AND {sample_field} > 0
                        ORDER BY date
                        """,
                        (start.isoformat(), end.isoformat()),
                    ).fetchall()
                    items = [
                        {"label": row["date"], "value": row["value"], "samples": row["samples"]}
                        for row in rows
                    ]

        return {
            "metric": metric,
            "period": period,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            # 日视图下这条曲线是**累计量**：取平均没有意义，前端据此改用"当日累计"。
            "cumulative": cumulative,
            "unit": "kcal" if metric in DAILY_TOTAL_METRICS else None,
            "items": items,
        }

    def query_heart_rate_window(self, start_time: str, end_time: str) -> dict[str, Any]:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
        if start.tzinfo is None:
            start = start.replace(tzinfo=BEIJING)
        if end.tzinfo is None:
            end = end.replace(tzinfo=BEIJING)
        if end <= start:
            raise ValueError("结束时间必须晚于开始时间")
        if end - start > timedelta(days=7):
            raise ValueError("心率窗口不能超过 7 天")
        start_utc = start.astimezone(timezone.utc).isoformat()
        end_utc = end.astimezone(timezone.utc).isoformat()
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT MIN(bpm) AS hr_min, MAX(bpm) AS hr_max, AVG(bpm) AS hr_avg,
                       COUNT(*) AS sample_count
                FROM (
                    SELECT timestamp_utc, ROUND(AVG(bpm)) AS bpm
                    FROM heart_rate_samples
                    WHERE timestamp_utc >= ? AND timestamp_utc <= ?
                    GROUP BY timestamp_utc
                )
                """,
                (start_utc, end_utc),
            ).fetchone()
        return {
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "heart_rate_min": int(row["hr_min"]) if row and row["hr_min"] is not None else None,
            "heart_rate_max": int(row["hr_max"]) if row and row["hr_max"] is not None else None,
            "heart_rate_avg": round(float(row["hr_avg"]), 1) if row and row["hr_avg"] is not None else None,
            "sample_count": int(row["sample_count"] or 0) if row else 0,
        }

    def delete_import(self, import_id: str, *, keep_raw_file: bool = False) -> bool:
        self._require_writable()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT raw_path FROM health_imports WHERE id = ?", (import_id,)
            ).fetchone()
            if not row:
                return False
            affected = {
                item["local_date"]
                for item in connection.execute(
                    """
                    SELECT local_date FROM heart_rate_samples hr
                    JOIN health_source_files sf ON sf.id = hr.source_file_id WHERE sf.import_id = ?
                    UNION
                    SELECT local_date FROM health_metric_samples hm
                    JOIN health_source_files sf ON sf.id = hm.source_file_id WHERE sf.import_id = ?
                    UNION
                    SELECT local_date FROM daily_activity_observations da
                    JOIN health_source_files sf ON sf.id = da.source_file_id WHERE sf.import_id = ?
                    UNION
                    SELECT local_date FROM hrv_status_summaries hs
                    JOIN health_source_files sf ON sf.id = hs.source_file_id WHERE sf.import_id = ?
                    UNION
                    -- 新表也必须列进来：某一天的数据可能**只**来自它们（跨零点那天
                    -- 常常只剩一条静息心率），漏掉的话日汇总行删不掉，界面上会留下
                    -- 一个没有来源的幽灵日期。
                    SELECT local_date FROM device_daily_metrics dm
                    JOIN health_source_files sf ON sf.id = dm.source_file_id WHERE sf.import_id = ?
                    UNION
                    SELECT local_date FROM intensity_observations io
                    JOIN health_source_files sf ON sf.id = io.source_file_id WHERE sf.import_id = ?
                    UNION
                    SELECT sleep_date AS local_date FROM sleep_stage_events se
                    JOIN health_source_files sf ON sf.id = se.source_file_id WHERE sf.import_id = ?
                    """,
                    (import_id,) * 7,
                ).fetchall()
            }
            raw_path = row["raw_path"]
            connection.execute("DELETE FROM health_imports WHERE id = ?", (import_id,))
            for day in affected:
                self._rebuild_daily_summary(connection, day)
        if raw_path and not keep_raw_file:
            self._delete_raw_file(raw_path)
        return True

    def clear(self) -> int:
        self._require_writable()
        imports = self.list_imports(limit=1_000_000)
        with self._connection() as connection:
            connection.execute("DELETE FROM health_imports")
            connection.execute("DELETE FROM daily_health_summary")
        for item in imports:
            if item.get("raw_path"):
                self._delete_raw_file(item["raw_path"])
        return len(imports)

    def audit_raw_files(self) -> dict[str, list[str]]:
        """Compare health-import files on disk with database references."""
        with self._access_lock:
            with self._connection() as connection:
                referenced = {
                    Path(str(row["raw_path"])).name
                    for row in connection.execute(
                        "SELECT raw_path FROM health_imports WHERE raw_path IS NOT NULL AND raw_path != ''"
                    ).fetchall()
                }
            present = {item.name for item in self.raw_dir.iterdir() if item.is_file()}
            return {"orphans": sorted(present - referenced), "missing": sorted(referenced - present)}

    def delete_orphan_raw_file(self, name: str) -> bool:
        safe_name = Path(str(name or "")).name
        if not safe_name or safe_name != str(name or ""):
            raise ValueError("原始文件名无效")
        with self._access_lock:
            if safe_name not in self.audit_raw_files()["orphans"]:
                return False
            target = self.resolve_raw_file(safe_name)
            if target is None or not target.is_file():
                return False
            target.unlink()
            return True
