"""Secure import of Garmin wellness ZIP archives and sleep summary CSV files."""

from __future__ import annotations

import csv
import hashlib
import io
import re
import tempfile
import zipfile
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import fitfile

from .health_store import HealthStore


BEIJING = ZoneInfo("Asia/Shanghai")
MAX_ARCHIVE_FILES = 100
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
MAX_ARCHIVE_ENTRY_BYTES = 25 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200


class HealthImportError(ValueError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _date_hint(filename: str) -> str | None:
    match = re.search(r"(?<!\d)(20\d{2}-\d{2}-\d{2})(?!\d)", filename)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1)).isoformat()
    except ValueError:
        return None


FIT_KIND_NAMES = {
    "monitoring_b": "daily_monitoring",
    "metrics": "metrics",
    "hrv_status": "hrv_status",
    "sleep": "sleep",
    "activity": "activity",
}
HRV_STATUS_NAMES = {0: "unknown", 2: "poor", 3: "low", 4: "balanced"}


def _utc_datetime(value: datetime) -> datetime:
    """把 FIT 时间戳统一成 tz-aware UTC。

    **naive 值一律按 UTC 解释**，这不是省事而是 FIT 规范：`date_time` 基类型定义
    为"seconds since UTC 1989-12-31"，fitfile 只是在 `utc=False` 时不给它挂 tzinfo。
    真正的本地墙钟字段是 `local_date_time`（例如 `monitoring_info.local_timestamp`），
    那种值**不能**走这里——它需要显式 `replace(tzinfo=BEIJING)`。目前没有任何调用
    方传本地墙钟值进来；要加的话请另写一个函数，别扩展这个的语义。见
    `_STRESS_TIME_FIELDS` 的说明（BUG-15）。
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# ── 睡眠会话字段（2026-08-24 实测确证，改前先读这段）──────────────────────
#
# Garmin 把睡眠汇总塞在**没有官方名字**的消息里，fitfile 只能给出
# `unknown_<msg>` / `unknown_<field>`。照 `_STRESS_TIME_FIELDS` 的先例，把位置
# 集中写在这里，并让每个值都过范围闸门：上游换固件重排字段时，宁可没有值，也
# 不要悄悄写错值。
#
# 证据：`data/health-imports/` 里 17 份日包，配 5 份睡眠 CSV 真值
# （2026-08-10 / 19 / 20 / 21 / 22）。下面每一条都是 5/5 或 17/17 精确吻合。
#
#   METRICS 的 `unknown_384` 一条消息就自带全部所需：
#       unknown_9   躺床开始（裸 FIT 时间戳，要加 _GARMIN_EPOCH_OFFSET）
#       unknown_11  躺床结束（同上）
#       unknown_24  清醒分钟
#       unknown_2   睡眠分数
#     其 9/11 与 SLEEP_DATA 的 event(event=sleep) start/stop **完全相等**（5/5），
#     两个文件互为佐证。
#   SLEEP_DATA 另有：`unknown_521.unknown_1`、`unknown_346.unknown_6` = 睡眠分数
#     （与 METRICS 的两处共 4 处，17/17 天全部一致）；
#     `unknown_382.unknown_1` = 不安稳状态（5/5）。
#
# **睡眠时长 = 躺床时长 − 清醒分钟**，5/5 天与 CSV 精确吻合。
# 例：2026-08-21 躺床 544 − 清醒 67 = 477 = CSV 的「7 时 57 分」。
#
# ⚠️ 已确认**不在 FIT 里**：深 / 浅 / REM 分期时长、夜间平均心率、静息心率、
# SpO2、呼吸频率、HRV、平均压力——原值/×60/×2/÷2/占比 都试过，找不到五天一致的
# 字段。分期时长是 Garmin 云端重算的：文件里那条 `sleep_level` 时间线一晚只有
# 15~33 条记录，累加出来与 Connect 的分期差 -181~+50 分钟，**绝不能当作睡眠
# 时长**（这正是本次修掉的错，见 health_store.get_sleep 的说明）。
_GARMIN_EPOCH_OFFSET = 631065600  # FIT date_time 基准：1989-12-31T00:00:00Z
_SLEEP_SESSION_MESSAGE = "unknown_384"
_SLEEP_SESSION_BED_START = "unknown_9"
_SLEEP_SESSION_BED_END = "unknown_11"
_SLEEP_SESSION_AWAKE_MIN = "unknown_24"
_SLEEP_SESSION_SCORE = "unknown_2"
_SLEEP_SCORE_FALLBACKS = (
    ("unknown_521", "unknown_1"),
    ("unknown_346", "unknown_6"),
    ("unknown_330", "unknown_2"),
)
_SLEEP_RESTLESSNESS_FIELD = ("unknown_382", "unknown_1")
_SLEEP_SCORE_RANGE = (0, 100)
_SLEEP_RESTLESSNESS_RANGE = (0, 10000)
_SLEEP_MAX_MINUTES = 24 * 60
# 时间戳合理区间：2010-01-01 ~ 2050-01-01（UTC 秒），挡掉 0 与明显越界的脏值
_SLEEP_TS_RANGE = (1262304000, 2524608000)


def _gated_int(value: Any, low: float, high: float) -> int | None:
    """只接受落在 [low, high] 的数值，其余一律当"没有这个值"。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not low <= value <= high:
        return None
    return int(value)


# ── HRV 状态字段（DATA-18，2026-08-27 实测确证，改前先读这段）──────────────
#
# 又一次"上游字段名不可信"，成因与 `_STRESS_TIME_FIELDS` 完全相同：fitfile 给
# 这条消息的字段起的名字**按位置整体偏了一位**（从字段 1 起），而旧实现照抄了
# 那些名字。照那条先例，把「SDK 语义 ← fitfile 名字」的对应集中写在这里。
#
# FIT SDK 里 `hrv_status_summary` 的字段序是：
#     0 weekly_average          1 last_night_average
#     2 last_night_5_min_high   3 baseline_low_upper
#     4 baseline_balanced_lower 5 baseline_balanced_upper
#     6 status
# fitfile 把 1..5 分别叫成了 last_night / last_night_average / baseline_low /
# baseline_high / baseline_balanced_low——**字段 0 没有偏**，所以只有 1..5 需要
# 重命名（原清单标题写"七个字段整体错位"并不准确）。
#
# 证据（`data/health-imports/` 全部 22 份 HRV_STATUS.fit，20 个不同日期）：
#   1) fitfile 的 `last_night` 才是昨夜平均。用同一份文件里 `hrv_value` 采样
#      自算的均值钉住，20/20 天都落在 ±2 ms 内（例：44 对 44.6、47 对 45.9、
#      35 对 34.2）；而 fitfile 的 `last_night_average` 恒为 53~88，系统性高出
#      10~38 ms，是**昨夜 5 分钟峰值**而不是平均。
#   2) 重映射后三条基线严格单调：low_upper 35 < balanced_lower 37~38 <
#      balanced_upper 48~50，且 `weekly_average`（41~46）**20/20 天都落在
#      [balanced_lower, balanced_upper] 内**，与设备自报的 status=balanced 一致。
#      按旧名字读则得出"昨夜 64 ms 远高于基线上限 37 ms"，与设备自身结论矛盾。
#
# ⚠️ `baseline_balanced_high`（fitfile 名，SDK 未定义该位置）**语义未知**：全量
# 实测取值在 28299 / 31278 / 32768 / 34257 / 35498 / 37236 / 38229 / 40960 /
# 43194 之间变化，**不是常量哨兵**，且 /128 得 221~337 ms 不像任何 HRV 量。既然
# 拿不出对照证据，就不猜语义、不套 ms 闸门、也不当 HRV 指标暴露，只按原值留一
# 份诊断字段等将来有真值再定——"宁可没有值，也不要悄悄写错值"同样适用于
# "宁可留着不解释，也不要悄悄丢掉"。
_HRV_SCALE = 128.0
# 每个字段按语义单独定闸门（原清单建议的统一 5~200 只适用于下面这些真·毫秒量）。
_HRV_MS_RANGE = (5.0, 200.0)
# SDK 语义键 ← fitfile 实际给出的名字
_HRV_STATUS_FIELDS: tuple[tuple[str, str], ...] = (
    ("weekly_average_ms", "weekly_average"),
    ("last_night_average_ms", "last_night"),
    ("last_night_5min_high_ms", "last_night_average"),
    ("baseline_low_upper_ms", "baseline_low"),
    ("baseline_balanced_lower_ms", "baseline_high"),
    ("baseline_balanced_upper_ms", "baseline_balanced_low"),
)
# 语义未知、原值直存、不参与任何范围判断的字段
_HRV_UNMAPPED_FIELD = "baseline_balanced_high"


def _hrv_ms(value: Any) -> tuple[float | None, bool]:
    """原值 → 毫秒，并报告是否**因越界被拒**（缺字段不算被拒）。

    返回 `(毫秒或 None, 是否被拒)`。区分这两者是为了让越界值能进 warnings，
    而不是像旧实现那样和"没这个字段"一样静默消失。
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None, False
    ms = float(value) / _HRV_SCALE
    if not _HRV_MS_RANGE[0] <= ms <= _HRV_MS_RANGE[1]:
        return None, True
    return round(ms, 2), False


def _garmin_timestamp(value: Any) -> datetime | None:
    """把 `unknown_*` 里的裸 FIT 时间戳转成 tz-aware UTC。

    这些字段没有类型信息，fitfile 原样给出 int/float，所以要自己加基准偏移。
    已经是 datetime 的（有类型的字段）直接走 `_utc_datetime`，不重复加偏移。
    """
    if isinstance(value, datetime):
        return _utc_datetime(value)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    epoch = float(value) + _GARMIN_EPOCH_OFFSET
    if not _SLEEP_TS_RANGE[0] <= epoch <= _SLEEP_TS_RANGE[1]:
        return None
    return datetime.fromtimestamp(epoch, timezone.utc)


def _first_field(fit: Any, message_name: str, field_name: str) -> Any:
    for message in fit.messages:
        if message.type.name == message_name:
            value = message.fields.get(field_name)
            if value is not None:
                return value
    return None


def _sleep_score(fit: Any) -> int | None:
    """按 `_SLEEP_SCORE_FALLBACKS` 的顺序取第一个通过闸门的睡眠分数。

    四处存的是同一个值（17/17 天实测一致），任取其一即可；多写几处是为了某份
    文件缺消息时还能拿到。
    """
    for message_name, field_name in _SLEEP_SCORE_FALLBACKS:
        score = _gated_int(_first_field(fit, message_name, field_name), *_SLEEP_SCORE_RANGE)
        if score is not None:
            return score
    return None


def _sleep_bed_window(fit: Any) -> tuple[datetime, datetime] | None:
    """躺床起止。优先用 SLEEP_DATA 里类型明确的 `event` 消息。

    DATA-28：原实现只取 stop 事件、把 start 丢了，于是第一条 `sleep_level` 记录
    之前的那段（实测 1~14 分钟）凭空消失。start 事件在文件里是明写的，没有理由
    不用。METRICS 那条 `unknown_384` 的 9/11 与这两个事件完全相等（5/5 天），
    所以两条路取到的窗口是同一个。
    """
    starts: list[datetime] = []
    stops: list[datetime] = []
    for message in fit.messages:
        if message.type.name != "event":
            continue
        if _enum_name(message.fields.get("event")) != "sleep":
            continue
        stamp = message.fields.get("timestamp")
        if not isinstance(stamp, datetime):
            continue
        kind = _enum_name(message.fields.get("event_type"))
        if kind == "start":
            starts.append(_utc_datetime(stamp))
        elif kind == "stop":
            stops.append(_utc_datetime(stamp))
    if starts and stops:
        start, end = min(starts), max(stops)
        if end > start:
            return start, end
    # 退路：METRICS 没有 event 消息，用 `unknown_384` 的裸时间戳
    start = _garmin_timestamp(_first_field(fit, _SLEEP_SESSION_MESSAGE, _SLEEP_SESSION_BED_START))
    end = _garmin_timestamp(_first_field(fit, _SLEEP_SESSION_MESSAGE, _SLEEP_SESSION_BED_END))
    if start is not None and end is not None and end > start:
        return start, end
    return None


def _sleep_session(fit: Any) -> dict[str, Any] | None:
    """从一份 METRICS / SLEEP_DATA 里取出一条睡眠会话汇总。

    两种文件都可能只提供一部分字段（清醒分钟只有 METRICS 有，不安稳只有
    SLEEP_DATA 有），缺的留 None，由 `health_store` 按 sleep_date 合并。
    """
    window = _sleep_bed_window(fit)
    if window is None:
        return None
    start, end = window
    minutes = int((end - start).total_seconds() // 60)
    if not 0 < minutes <= _SLEEP_MAX_MINUTES:
        return None
    awake = _gated_int(
        _first_field(fit, _SLEEP_SESSION_MESSAGE, _SLEEP_SESSION_AWAKE_MIN), 0, minutes
    )
    restless = _gated_int(
        _first_field(fit, *_SLEEP_RESTLESSNESS_FIELD), *_SLEEP_RESTLESSNESS_RANGE
    )
    return {
        # 睡眠日期 = 醒来时刻的本地日期。17/17 天与导出包标注的日期一致，跨零点
        # 的夜晚也对（08-20 23:03 入睡、08-21 08:07 醒 → 记 08-21）。
        "sleep_date": end.astimezone(BEIJING).date().isoformat(),
        "bed_start_utc": start.isoformat(),
        "bed_end_utc": end.isoformat(),
        "bed_start_local": start.astimezone(BEIJING).isoformat(),
        "bed_end_local": end.astimezone(BEIJING).isoformat(),
        "time_in_bed_min": minutes,
        "awake_min": awake,
        "score": _sleep_score(fit),
        "restlessness": restless,
    }


# ── BUG-15：stress_level 的时间戳字段名与语义 ──────────────────────────────
#
# fitfile 把 stress_level 字段 1 命名为 `local_timestamp` 并标了 `utc=False`
# （于是返回 naive datetime）。**那是 fitfile 自己标错了**：FIT 规范里该字段是
# `stress_level_time`，基类型 `date_time`，即 UTC 基准。
#
# 已用三份真实 wellness ZIP 逐分钟核对：把这个 naive 值当 UTC 解释，得到的跨度与
# **同一份文件里** monitoring 心率的 `timestamp`（utc=True，语义确定）完全重合
# （偏差 0.0h）；当成本地墙钟解释则整体差 8.0h。同一批文件里
# `monitoring_info.local_timestamp` 与其 `timestamp` 之差确实是 +8h——说明
# fitfile 的 utc=False 在**那个**字段上是对的，只是被错用到了 stress 上。
#
# 结论：现有的时区解释是对的，但**是碰巧对的**——代码里原先没有任何地方记下
# 「这里为什么可以把 naive 当 UTC」。需求清单给出的修法
# （`local_ts.replace(tzinfo=BEIJING)`）正是照着"是本地墙钟"那种解释写的，
# 采纳它会把全部压力数据提前 8 小时。所以这里把契约写死，并用测试钉住。
#
# 候选字段名按「规范名 → 通用名 → fitfile 当前的错名」排序。上游哪天改对了名字
# （它自己就认为这个名字是错的），压力数据不会因此**静默全部消失**——原实现直接
# `values.get("local_timestamp")`，取不到就是 None，随后 isinstance 检查失败，
# 1440 条/天的压力样本一条不剩地被跳过，而且不留任何痕迹。
_STRESS_TIME_FIELDS = ("stress_level_time", "timestamp", "local_timestamp")


def _stress_timestamp(values: Any) -> datetime | None:
    for field_name in _STRESS_TIME_FIELDS:
        value = values.get(field_name)
        if isinstance(value, datetime):
            return value
    return None


# ── 设备算出来的日级指标 ────────────────────────────────────────────────────
#
# 这些值以前一条都没入库，但它们都在包里躺着：
#
# * `monitoring_info.resting_metabolic_rate` —— 手表算的静息代谢率（kcal/天）。
#   `daily_health_summary` 早就有 `resting_calories` / `total_calories` 两列，却
#   **16 天全是空**：读取方去 `monitoring` 里找 `resting_calories`/`bmr_calories`，
#   而这个数其实在 `monitoring_info` 里，而 `monitoring_info` 整条消息从未被处理。
#   实测该值随体重变化重算（08-07~08-13 是 2257，08-14 起 2230）。
#
# * `unknown_211` 的两个字段 —— **逆向推断为静息心率**。证据：`unknown_1` 在
#   2026-08-14 取到 56，与那天睡眠 CSV 的「静息心率 56 bpm」精确一致；跨 15 天
#   它稳定落在 55–63，而当日睡眠时段最低心率是 52–58（静息心率是一段均值而非
#   最小值，所以略高是对的）。`unknown_0` 15 天里几乎恒为 57–59，更像 7 日基线，
#   所以存成 `resting_heart_rate_baseline`，**名字上不声称它一定是什么**。
#   fitfile 没给这个消息命名，只能按 `unknown_211` / `unknown_0` / `unknown_1`
#   读——这是逆向出来的，上游一旦命名就会失配，所以取不到时只是没有值，不报错。
#
# * UTC 偏移 —— `monitoring_info`、`local_time`、`start` 这几条消息同时带
#   `timestamp`（UTC）与 `local_timestamp`（**真正的本地墙钟**，见 BUG-15 里
#   `_utc_datetime` 的说明），两者之差就是设备当时的时区偏移。实测 15 份包全是
#   +480 分钟，所以存下来只是让它可见、可核对，不改变现有的本地日期计算。
_RESTING_HR_MESSAGE = "unknown_211"
_RESTING_HR_FIELDS = {"resting_heart_rate": "unknown_1", "resting_heart_rate_baseline": "unknown_0"}
#: 静息心率的合理区间。逆向字段必须带范围闸门——猜错了字段也不会把垃圾写进库。
_RESTING_HR_RANGE = (25, 120)
#: 带本地墙钟的消息类型。**不能**把它们的 `local_timestamp` 交给 `_utc_datetime`。
_LOCAL_CLOCK_MESSAGES = ("monitoring_info", "local_time", "start")


def _utc_offset_minutes(values: Any) -> int | None:
    """从同一条消息里的 UTC 与本地墙钟时间戳推出设备时区偏移（分钟）。"""
    utc = values.get("timestamp")
    local = values.get("local_timestamp")
    if not isinstance(utc, datetime) or not isinstance(local, datetime):
        return None
    if local.tzinfo is not None:  # 上游哪天给它挂上时区，差值就该按 aware 算
        offset = local - _utc_datetime(utc)
    else:
        offset = local.replace(tzinfo=timezone.utc) - _utc_datetime(utc)
    minutes = round(offset.total_seconds() / 60)
    # ±14 小时是 IANA 的实际上限；超出说明解读错了，宁可不给值
    return minutes if -840 <= minutes <= 840 else None


def _resting_heart_rates(values: Any) -> dict[str, int]:
    result: dict[str, int] = {}
    low, high = _RESTING_HR_RANGE
    for column, field_name in _RESTING_HR_FIELDS.items():
        value = values.get(field_name)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            bpm = int(round(value))
            if low <= bpm <= high:
                result[column] = bpm
    return result


def _seconds(value: Any) -> float | None:
    if isinstance(value, time):
        return value.hour * 3600 + value.minute * 60 + value.second + value.microsecond / 1_000_000
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _enum_name(value: Any) -> str:
    return str(getattr(value, "name", value))


def _timed_value(timestamp: datetime, value: float, **extra: Any) -> dict[str, Any]:
    timestamp_utc = _utc_datetime(timestamp)
    timestamp_local = timestamp_utc.astimezone(BEIJING)
    return {
        "timestamp_utc": timestamp_utc.isoformat(),
        "timestamp_local": timestamp_local.isoformat(),
        "local_date": timestamp_local.date().isoformat(),
        "value": value,
        **extra,
    }


def _parse_fit_source(filename: str, content: bytes) -> dict[str, Any]:
    source_id = str(uuid4())
    source: dict[str, Any] = {
        "id": source_id,
        "filename": filename,
        "kind": "fit_unknown",
        "sha256": _sha256(content),
        "earliest_utc": None,
        "latest_utc": None,
        "device_serial": None,
        "record_count": 0,
        "message_counts": {},
        "data_types": [],
        "heart_rates": [],
        "metric_samples": [],
        "activity_observations": [],
        "device_metrics": [],
        "intensity_observations": [],
        "hrv_statuses": [],
        "sleep_stages": [],
        "sleep_sessions": [],
        "warnings": [],
    }
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        fit = fitfile.file.File(str(temp_path))
    except Exception as exc:  # noqa: BLE001
        source["warnings"].append(f"FIT 解析失败：{exc}")
        return source
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    file_type = _enum_name(fit.type)
    source["kind"] = FIT_KIND_NAMES.get(file_type, file_type or "fit_unknown")
    source["device_serial"] = str(fit.serial_number) if fit.serial_number is not None else None
    source["record_count"] = len(fit.messages)
    counts = Counter(message.type.name for message in fit.messages)
    source["message_counts"] = dict(sorted(counts.items()))
    timestamps = [
        _utc_datetime(value)
        for message in fit.messages
        for value in (message.fields.get("timestamp"),)
        if isinstance(value, datetime)
    ]
    invalid_hr = 0
    missing_stress_time = 0
    for message in fit.messages:
        name = message.type.name
        values = message.fields
        timestamp = values.get("timestamp")

        if name == "monitoring" and isinstance(timestamp, datetime):
            heart_rate = values.get("heart_rate")
            if isinstance(heart_rate, (int, float)):
                bpm = int(round(heart_rate))
                if 25 <= bpm <= 240:
                    sample = _timed_value(timestamp, bpm)
                    sample["bpm"] = sample.pop("value")
                    source["heart_rates"].append(sample)
                else:
                    invalid_hr += 1
            activity_values = {
                "steps": values.get("steps"),
                "distance_m": values.get("distance"),
                "active_calories": values.get("active_calories"),
                "resting_calories": values.get("resting_calories") or values.get("bmr_calories"),
                "total_calories": values.get("total_calories"),
                "active_time_s": _seconds(values.get("cum_active_time")),
            }
            if any(value is not None for value in activity_values.values()):
                activity_timestamp = timestamp
                if _utc_datetime(timestamp).astimezone(BEIJING).time() == time.min:
                    activity_timestamp = timestamp - timedelta(seconds=1)
                activity = _timed_value(
                    activity_timestamp,
                    0,
                    activity_type=_enum_name(values.get("activity_type", "unknown")),
                    **activity_values,
                )
                activity.pop("value", None)
                source["activity_observations"].append(activity)

            # 强度分钟（Garmin/WHO 的活动量指标）。**这两个字段是区间增量而不是
            # 累计值**——实测同一天里出现 60s / 180s / 60s / 240s，累计量不可能
            # 回落，所以汇总时必须 SUM 而不是 MAX。
            # 它们也**不与任何活动字段同现**（steps/active_calories 全为空），所以
            # 挂不到 `daily_activity_observations` 上：那张表只在有活动字段时建行。
            moderate = _seconds(values.get("moderate_activity_time"))
            vigorous = _seconds(values.get("vigorous_activity_time"))
            intensity = values.get("intensity")
            if moderate is not None or vigorous is not None or intensity is not None:
                entry = _timed_value(timestamp, 0)
                entry.pop("value", None)
                entry["moderate_activity_s"] = moderate
                entry["vigorous_activity_s"] = vigorous
                entry["intensity_level"] = (
                    int(round(intensity))
                    if isinstance(intensity, (int, float)) and not isinstance(intensity, bool)
                    else None
                )
                source["intensity_observations"].append(entry)

        if name == "monitoring_info" and isinstance(timestamp, datetime):
            rate = values.get("resting_metabolic_rate")
            entry = _timed_value(timestamp, 0)
            entry.pop("value", None)
            entry["resting_metabolic_rate"] = (
                float(rate) if isinstance(rate, (int, float)) and 500 <= rate <= 6000 else None
            )
            entry["utc_offset_minutes"] = _utc_offset_minutes(values)
            if any(entry.get(key) is not None
                   for key in ("resting_metabolic_rate", "utc_offset_minutes")):
                source["device_metrics"].append(entry)

        if name == _RESTING_HR_MESSAGE and isinstance(timestamp, datetime):
            rates = _resting_heart_rates(values)
            if rates:
                entry = _timed_value(timestamp, 0)
                entry.pop("value", None)
                entry.update(rates)
                source["device_metrics"].append(entry)

        if name in _LOCAL_CLOCK_MESSAGES and name != "monitoring_info" and isinstance(timestamp, datetime):
            # METRICS 文件只有 `local_time` 一条能给出偏移；不带 RMR 也要收下，
            # 否则那几个文件依旧一行数据都不产出。
            offset = _utc_offset_minutes(values)
            if offset is not None:
                entry = _timed_value(timestamp, 0)
                entry.pop("value", None)
                entry["utc_offset_minutes"] = offset
                source["device_metrics"].append(entry)

        metric: str | None = None
        metric_value: float | None = None
        # BUG-15：**不再就地覆盖 `timestamp`**。原实现在 stress 分支里把这个变量
        # 换成另一个字段，而它同时是下面 `_timed_value(...)` 与 hrv_status 分支
        # 读的那一个；分支目前互斥所以没出事，但那是运气，不是设计。
        metric_time: datetime | None = timestamp if isinstance(timestamp, datetime) else None
        if name == "stress_level":
            raw = values.get("stress_level")
            if isinstance(raw, (int, float)) and 0 <= raw <= 100:
                metric_time = _stress_timestamp(values)
                if metric_time is None:
                    missing_stress_time += 1
                else:
                    metric, metric_value = "stress", float(raw)
        elif name == "respiration":
            raw = values.get("respiration_rate")
            if isinstance(raw, (int, float)) and 4 <= raw <= 60:
                metric, metric_value = "respiration", float(raw)
        elif name == "pulse_ox":
            raw = values.get("pulse_ox")
            if isinstance(raw, (int, float)) and 50 <= raw <= 100:
                metric, metric_value = "spo2", float(raw)
        elif name == "hrv_value":
            raw = values.get("hrv_value")
            if isinstance(raw, (int, float)) and raw > 0:
                metric, metric_value = "hrv", float(raw) / 128.0
        if metric and metric_value is not None and metric_time is not None:
            source["metric_samples"].append(_timed_value(metric_time, metric_value, metric=metric))

        if name == "hrv_status_summary" and isinstance(timestamp, datetime):
            # DATA-18：`scaled` 保留的是 fitfile 原始命名，只为兼容旧列（旧数据里
            # 已经是这个口径，原地改语义比现状更糟）。真正给人和 Agent 看的是下面
            # 按 `_HRV_STATUS_FIELDS` 重映射出来的 `*_ms`，见该常量上方的论证。
            scaled = lambda key: float(values[key]) / _HRV_SCALE if values.get(key) else None
            remapped: dict[str, Any] = {}
            for semantic_key, fit_key in _HRV_STATUS_FIELDS:
                ms, rejected = _hrv_ms(values.get(fit_key))
                remapped[semantic_key] = ms
                if rejected:
                    source["warnings"].append(
                        f"HRV {semantic_key} 原值 {values.get(fit_key)} 换算后越界"
                        f"（{_HRV_MS_RANGE[0]:g}~{_HRV_MS_RANGE[1]:g} ms），已丢弃"
                    )
            raw_unmapped = values.get(_HRV_UNMAPPED_FIELD)
            status_sample = _timed_value(
                timestamp,
                0,
                weekly_average=scaled("weekly_average"),
                last_night=scaled("last_night"),
                last_night_average=scaled("last_night_average"),
                baseline_low=scaled("baseline_low"),
                baseline_high=scaled("baseline_high"),
                **remapped,
                unmapped_balanced_high_raw=(
                    float(raw_unmapped)
                    if isinstance(raw_unmapped, (int, float))
                    and not isinstance(raw_unmapped, bool)
                    else None
                ),
                status=HRV_STATUS_NAMES.get(
                    int(values["status"]), str(int(values["status"]))
                ) if isinstance(values.get("status"), (int, float)) else None,
                reading_count=values.get("reading_count"),
            )
            status_sample.pop("value", None)
            source["hrv_statuses"].append(status_sample)

    if source["kind"] == "sleep":
        # 躺床窗口改由 `_sleep_bed_window` 给出（含 start 事件），不再让第一条
        # sleep_level 记录充当起点——DATA-28。
        window = _sleep_bed_window(fit)
        levels = [
            (message.fields.get("timestamp"), _enum_name(message.fields.get("sleep_level")))
            for message in fit.messages
            if message.type.name == "sleep_level"
            and isinstance(message.fields.get("timestamp"), datetime)
        ]
        levels.sort(key=lambda item: item[0])
        if levels:
            sleep_end = window[1] if window else _utc_datetime(levels[-1][0])
            sleep_date = sleep_end.astimezone(BEIJING).date().isoformat()
            for index, (stage_start, stage) in enumerate(levels):
                stage_end = (
                    _utc_datetime(levels[index + 1][0]) if index + 1 < len(levels) else sleep_end
                )
                duration_s = max(0, int((stage_end - _utc_datetime(stage_start)).total_seconds()))
                if duration_s:
                    entry = _timed_value(stage_start, duration_s, sleep_date=sleep_date, stage=stage)
                    entry["duration_s"] = entry.pop("value")
                    source["sleep_stages"].append(entry)

    if source["kind"] in {"sleep", "metrics"}:
        # METRICS 终于产出数据了（DATA-36）：它的 `unknown_384` 自带躺床起止、
        # 清醒分钟与睡眠分数，是"睡眠时长"唯一可靠的来源。
        session = _sleep_session(fit)
        if session is not None:
            source["sleep_sessions"].append(session)

    if timestamps:
        source["earliest_utc"] = min(timestamps).isoformat()
        source["latest_utc"] = max(timestamps).isoformat()
    if invalid_hr:
        source["warnings"].append(f"忽略 {invalid_hr} 个无效心率值")
    if missing_stress_time:
        # 出声而不是静默跳过：这批样本会整批消失，用户看到的只会是"压力数据没有"。
        source["warnings"].append(
            f"{missing_stress_time} 条压力读数没有可识别的时间字段"
            f"（已尝试 {'/'.join(_STRESS_TIME_FIELDS)}），已跳过；"
            "这通常说明 fitfile 版本更换了字段名"
        )
    # Coalesce records emitted by different FIT message types at the same
    # timestamp.  This preserves RMR and resting-HR fields instead of letting
    # the storage UNIQUE constraint discard one of them.
    merged_metrics: dict[str, dict[str, Any]] = {}
    for item in source["device_metrics"]:
        key = item.get("timestamp_utc")
        target = merged_metrics.setdefault(key, dict(item))
        for field in ("resting_metabolic_rate", "resting_heart_rate", "resting_heart_rate_baseline", "utc_offset_minutes"):
            if target.get(field) is None and item.get(field) is not None:
                target[field] = item[field]
    source["device_metrics"] = list(merged_metrics.values())
    merged_intensity: dict[str, dict[str, Any]] = {}
    for item in source["intensity_observations"]:
        key = item.get("timestamp_utc")
        target = merged_intensity.get(key)
        if target is None:
            merged_intensity[key] = {
                field: item.get(field)
                for field in (
                    "timestamp_utc",
                    "timestamp_local",
                    "local_date",
                    "moderate_activity_s",
                    "vigorous_activity_s",
                    "intensity_level",
                )
            }
            continue
        for field in ("moderate_activity_s", "vigorous_activity_s"):
            value = item.get(field)
            if value is not None:
                target[field] = (target.get(field) or 0) + value
        target["intensity_level"] = max(target.get("intensity_level") or 0, item.get("intensity_level") or 0) or None
    source["intensity_observations"] = list(merged_intensity.values())

    data_types = []
    if source["heart_rates"]:
        data_types.append("heart_rate")
    data_types.extend(sorted({sample["metric"] for sample in source["metric_samples"]}))
    if source["activity_observations"]:
        data_types.append("daily_activity")
    if source["intensity_observations"]:
        data_types.append("intensity")
    if any(item.get("resting_metabolic_rate") is not None for item in source["device_metrics"]):
        data_types.append("resting_metabolic_rate")
    if any(item.get("resting_heart_rate") is not None for item in source["device_metrics"]):
        data_types.append("resting_heart_rate")
    if source["hrv_statuses"]:
        data_types.append("hrv_status")
    if source["sleep_stages"]:
        data_types.append("sleep_stage")
    if source["sleep_sessions"]:
        data_types.append("sleep_session")
    if source["kind"] == "metrics" and not data_types:
        # DATA-36：原来这里无条件 append "metrics_snapshot"，于是 90 个 metrics
        # source 全都宣称提供数据、实际只有一行 utc_offset。现在按实际产出判断，
        # 与其余数据类型一致；真的什么都没解析出来时就不要声称有。
        source["warnings"].append("METRICS 文件未解析出任何指标")
    source["data_types"] = sorted(set(data_types))
    return source


def inspect_fit_source(filename: str, content: bytes) -> dict[str, Any]:
    """Parse one FIT file and classify it from its file_id and message contents."""
    return _parse_fit_source(Path(filename).name, content)


def parse_health_fit(filename: str, content: bytes) -> dict[str, Any]:
    source = inspect_fit_source(filename, content)
    warnings = list(source.get("warnings", []))
    return {
        "kind": "health_fit",
        "date_hint": _date_hint(filename),
        "sources": [source],
        "sleep": None,
        "data_types": source.get("data_types", []),
        "warnings": warnings,
        "status": "partial" if warnings else "imported",
    }


def _safe_archive_entries(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    entries = [entry for entry in archive.infolist() if not entry.is_dir()]
    if len(entries) > MAX_ARCHIVE_FILES:
        raise HealthImportError(f"压缩包文件数不能超过 {MAX_ARCHIVE_FILES}", 413)
    total_size = 0
    for entry in entries:
        path = PurePosixPath(entry.filename.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise HealthImportError(f"压缩包包含不安全路径：{entry.filename}")
        if entry.file_size > MAX_ARCHIVE_ENTRY_BYTES:
            raise HealthImportError(f"压缩包内文件过大：{entry.filename}", 413)
        total_size += entry.file_size
        if total_size > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
            raise HealthImportError("压缩包解压后不能超过 250 MiB", 413)
        if entry.file_size > 1024 * 1024:
            ratio = entry.file_size / max(entry.compress_size, 1)
            if ratio > MAX_COMPRESSION_RATIO:
                raise HealthImportError(f"压缩比异常：{entry.filename}", 413)
    return entries


def parse_wellness_zip(filename: str, content: bytes) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    warnings: list[str] = []
    skipped_files: list[dict[str, str]] = []
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = _safe_archive_entries(archive)
            fit_entries = [entry for entry in entries if entry.filename.lower().endswith(".fit")]
            for entry in entries:
                if not entry.filename.lower().endswith(".fit"):
                    skipped_files.append({
                        "filename": entry.filename,
                        "reason": "不属于可处理的 FIT 数据",
                    })
            if skipped_files:
                warnings.append(f"跳过 {len(skipped_files)} 个不支持的文件")
            for entry in fit_entries:
                try:
                    source = _parse_fit_source(entry.filename, archive.read(entry))
                except Exception as exc:  # noqa: BLE001
                    source = {
                        "id": str(uuid4()),
                        "filename": entry.filename,
                        "kind": "fit_unknown",
                        "sha256": "",
                        "record_count": 0,
                        "message_counts": {},
                        "data_types": [],
                        "heart_rates": [],
                        "metric_samples": [],
                        "activity_observations": [],
                        "hrv_statuses": [],
                        "sleep_stages": [],
                        "sleep_sessions": [],
                        "warnings": [f"读取失败：{exc}"],
                    }
                sources.append(source)
                source_warnings = [str(item) for item in source.get("warnings", [])]
                if any("失败" in item for item in source_warnings):
                    skipped_files.append({
                        "filename": entry.filename,
                        "reason": next(item for item in source_warnings if "失败" in item),
                    })
                elif source.get("kind") != "activity" and not source.get("data_types"):
                    skipped_files.append({
                        "filename": entry.filename,
                        "reason": "未提取到系统可保存的数据",
                    })
    except zipfile.BadZipFile as exc:
        raise HealthImportError("ZIP 文件损坏或格式无效") from exc

    heart_rate_count = sum(len(source.get("heart_rates", [])) for source in sources)
    failed = [source for source in sources if any("失败" in item for item in source.get("warnings", []))]
    if failed:
        warnings.append(f"{len(failed)} 个 FIT 文件未能完整解析")
    if heart_rate_count == 0 and any(source.get("kind") != "activity" for source in sources):
        warnings.append("未提取到有效的全天心率样本")
    if not sources:
        warnings.append("压缩包中没有可处理的 FIT 数据")
    return {
        "kind": "wellness_zip",
        "date_hint": _date_hint(filename),
        "sources": sources,
        "data_types": sorted(
            {data_type for source in sources for data_type in source.get("data_types", [])}
        ),
        "sleep": None,
        "warnings": warnings,
        "skipped_files": skipped_files,
        "status": "partial" if warnings or failed else "imported",
    }


def extract_activity_fits(content: bytes) -> list[tuple[str, bytes]]:
    """Find activity FIT files embedded in a ZIP after applying archive safety checks."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            activities: list[tuple[str, bytes]] = []
            for entry in _safe_archive_entries(archive):
                if not entry.filename.lower().endswith(".fit"):
                    continue
                item = archive.read(entry)
                if inspect_fit_source(entry.filename, item).get("kind") == "activity":
                    activities.append((entry.filename, item))
            return activities
    except zipfile.BadZipFile as exc:
        raise HealthImportError("ZIP 文件损坏或格式无效") from exc


def extract_activity_fit(content: bytes, selected_name: str) -> bytes:
    """Extract one exact, previously listed activity FIT from a ZIP archive."""
    for filename, item in extract_activity_fits(content):
        if filename == selected_name:
            return item
    raise HealthImportError("未找到指定的活动 FIT 文件")


def _decode_csv(content: bytes) -> str:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HealthImportError("睡眠 CSV 编码必须是 UTF-8 或 GB18030")


def _number(value: str) -> float | None:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value.replace("'", ""))
    return float(match.group(0)) if match else None


def _integer(value: str) -> int | None:
    number = _number(value)
    return int(round(number)) if number is not None else None


def _duration_minutes(value: str) -> int | None:
    hour = re.search(r"(\d+)\s*(?:时|小时)", value)
    minute = re.search(r"(\d+)\s*分", value)
    if not hour and not minute:
        return None
    return (int(hour.group(1)) * 60 if hour else 0) + (int(minute.group(1)) if minute else 0)


def parse_sleep_csv(filename: str, content: bytes) -> dict[str, Any]:
    text = _decode_csv(content)
    metrics: dict[str, str] = {}
    rows = list(csv.reader(io.StringIO(text)))
    for row in rows:
        if len(row) < 2:
            continue
        key = row[0].strip()
        value = row[1].strip()
        if key and value:
            metrics[key] = value
    sleep_date = metrics.get("日期", "")
    try:
        sleep_date = date.fromisoformat(sleep_date).isoformat()
    except ValueError as exc:
        raise HealthImportError("睡眠 CSV 缺少有效的日期字段") from exc

    sleep = {
        "id": str(uuid4()),
        "sleep_date": sleep_date,
        "duration_min": _duration_minutes(metrics.get("睡眠时长", "")),
        "score": _integer(metrics.get("睡眠分数", "")),
        "quality": metrics.get("质量") or None,
        "stress_avg": _integer(metrics.get("压力 平均", "")),
        "deep_sleep_min": _duration_minutes(metrics.get("深度睡眠持续时间", "")),
        "light_sleep_min": _duration_minutes(metrics.get("轻度睡眠持续时间", "")),
        "rem_sleep_min": _duration_minutes(metrics.get("快速眼动持续时间", "")),
        "awake_min": _duration_minutes(metrics.get("清醒时间", "")),
        "restlessness": _integer(metrics.get("不安稳状态", "")),
        "night_avg_hr": _integer(metrics.get("夜间平均心率", "")),
        "resting_hr": _integer(metrics.get("静息心率", "")),
        "body_battery_change": _integer(metrics.get("身体电量变化", "")),
        "spo2_avg": _number(metrics.get("平均 SpO₂", "")),
        "spo2_min": _number(metrics.get("最低 SpO2", "")),
        "respiration_avg": _number(metrics.get("平均呼吸频率", "")),
        "respiration_min": _number(metrics.get("最低呼吸频率", "")),
        "hrv_avg_ms": _number(metrics.get("平均夜间 HRV", "")),
        "hrv_7d_status": metrics.get("7 天平均 HRV") or None,
        "raw": metrics,
    }
    warnings: list[str] = []
    stages = [sleep["deep_sleep_min"], sleep["light_sleep_min"], sleep["rem_sleep_min"]]
    if sleep["duration_min"] is not None and all(value is not None for value in stages):
        stage_total = sum(stages)
        if stage_total != sleep["duration_min"]:
            warnings.append(
                f"睡眠阶段合计 {stage_total} 分钟，与睡眠时长 {sleep['duration_min']} 分钟不一致"
            )
    return {
        "kind": "sleep_csv",
        "date_hint": sleep_date,
        "sources": [],
        "sleep": sleep,
        "data_types": ["sleep_summary"],
        "warnings": warnings,
        "status": "partial" if warnings else "imported",
    }


class HealthImportService:
    def __init__(self, store: HealthStore) -> None:
        self.store = store

    @staticmethod
    def supported(filename: str) -> bool:
        return Path(filename).suffix.lower() in {".fit", ".zip", ".csv"}

    def import_file(self, filename: str, content: bytes) -> dict[str, Any]:
        safe_name = Path(filename).name
        suffix = Path(safe_name).suffix.lower()
        if suffix not in {".fit", ".zip", ".csv"}:
            raise HealthImportError("健康数据只支持 .fit、.zip 或 .csv")
        digest = _sha256(content)
        with self.store.exclusive_access():
            duplicate = self.store.find_import_by_hash(digest)
            if duplicate:
                skipped_files: list[dict[str, str]] = []
                if suffix == ".zip":
                    skipped_files = list(parse_wellness_zip(safe_name, content).get("skipped_files") or [])
                return {**duplicate, "duplicate": True, "skipped_files": skipped_files}

            stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(safe_name).stem).strip("._") or "health"
            raw_name = stem + suffix
            raw_path = self.store.raw_dir / f"{digest[:16]}-{raw_name}"
            raw_path.write_bytes(content)

            if suffix == ".zip":
                parsed = parse_wellness_zip(safe_name, content)
            elif suffix == ".fit":
                parsed = parse_health_fit(safe_name, content)
            else:
                parsed = parse_sleep_csv(safe_name, content)
            record = {
                **parsed,
                "id": str(uuid4()),
                "sha256": digest,
                "filename": safe_name,
                "raw_path": raw_path.name,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            saved = self.store.save_import(record)
        return {
            **saved,
            "duplicate": False,
            "skipped_files": list(parsed.get("skipped_files") or []),
        }
