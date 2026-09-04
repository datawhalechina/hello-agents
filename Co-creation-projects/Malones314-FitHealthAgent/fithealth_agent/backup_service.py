"""backup_service.py

可移植的本地备份导出与带校验的恢复。

DATA-11：备份原先只装 4 个 JSON + `health.db`，**漏掉了唯一可重新解析的数据源**
`data/health-imports/`。恢复之后库里每条 import 的 `raw_path` 都指向不存在的
文件，而且永远无法从备份重建。同时 manifest 只有 format/version/created_at/files，
**没有每文件校验和**，"结构合法但内容被替换"检测不到。

DATA-12：`restore()` 用 `os.replace` 换 JSON 却**不持有 `JsonFileLock`**，并发的
`add_record` 拿着恢复前读到的内存列表在恢复后写回，直接覆盖恢复结果；换
`health.db` 更危险——任何在飞连接持有它时删掉 `-wal`/`-shm`，那条连接会把旧
WAL 写回新库，Windows 上覆盖被打开的库还会直接 `PermissionError`。

备份内容清单（v2）
------------------
    manifest.json
    daily_records.json / user_profile.json / training_plans.json / info_store.json
    pending_workout.json            仅在存在时（"没有待确认训练"本身是有意义的状态）
    external_model_settings.json    仅在存在时
    health.db                       仅在存在时，用 sqlite backup API 取一致快照
    health-imports/<文件名>          原始导入文件，唯一可重新解析的数据源
    hr_streams/<文件名>              已保存训练的 1Hz 心率流（DATA-05 旁挂存储）

关于 `raw_path`：库里存的已经是**裸文件名**（DATA-02），而 `HealthStore.
resolve_raw_file()` 也只信任文件名部分，所以恢复时不需要改写 DB——老备份里
那些绝对路径同样能被重新对上。这里刻意不加改写逻辑，避免多一处会腐坏的代码。

DATA-14：恢复点（recovery point）
--------------------------------
`/data/reset` 会把六个 store 依次清空，这是全仓库唯一**不可逆**的批量删除。
原实现在第 3 步失败时前 2 步已经永久删掉了，而响应里连"删掉了多少"都没有。
所以清空之前必须先在 `data/recovery-points/` 落一份完整快照——它和普通备份
是同一种 zip，因此不需要任何新的恢复代码路径，用户下载后走 `/data/backup/
import` 就能还原。**快照写不出来就一个字节都不删**，这是这条修法的全部要点。

DATA-23：流式落盘
----------------
原实现把每个成员 `read_bytes()` 拼成一个 `{名字: 字节}` 字典，再在
`io.BytesIO` 里压一份，导出峰值内存约为数据量的两倍（`health.db` 一项就
25 MB 起，且随分钟级心率样本线性增长）。现在两侧都按成员流式处理：
导出边读边写、边算 sha256（`_collect_members` 只返回**磁盘路径**），
恢复先把成员解压到临时目录再按文件搬（`_BackupMembers` 惰性读回）。
`export_bytes`/`validate`/`restore` 的签名与返回形状刻意保持不变。
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import re
import shutil
import sqlite3
import tempfile
import weakref
import zipfile
from collections.abc import Mapping
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from fithealth_agent.atomic_json import temp_write_path
from fithealth_agent.json_file_lock import JsonFileLock


logger = logging.getLogger(__name__)

BACKUP_VERSION = 2
#: v1 备份仍然可以恢复（没有校验和、没有目录），否则用户手上的老备份直接作废。
SUPPORTED_VERSIONS = frozenset({1, 2})

#: 必须存在的 JSON 及其"文件缺失时写入备份的空值"。
JSON_FILES: dict[str, bytes] = {
    "daily_records.json": b"[]",
    "user_profile.json": b"{}",
    "training_plans.json": b"[]",
    "info_store.json": b"[]",
}
#: DATA-11 新增：这两个原先完全没进备份。只在存在时打包——"没有待确认训练"
#: 与"备份里没记这件事"必须能区分开。
OPTIONAL_JSON_FILES = (
    "pending_workout.json", "external_model_settings.json", "muscle_soreness.json",
)
HEALTH_DB_NAME = "health.db"
#: DATA-11 新增：整目录打包。health-imports 是唯一可重新解析的数据源，
#: hr_streams 则被 daily_records.json 里的摘要按记录 id 引用着。
BACKUP_DIRECTORIES = ("health-imports", "hr_streams", "workout-quarantine")

MAX_BACKUP_BYTES = 1024 * 1024 * 1024
#: 解压后的总上限。现在会展开整个目录，没有这道闸门一个高压缩比的 zip
#: 就能把内存吃光。
MAX_UNCOMPRESSED_BYTES = 3 * 1024 * 1024 * 1024

#: 恢复点（DATA-14）存放目录名，以及该目录允许的顶层文件名形状。
RECOVERY_POINT_DIR = "recovery-points"
_RECOVERY_POINT_NAME = re.compile(r"^pre-(?:reset|restore)-(\d{14})\.zip$")
#: 保留多少个恢复点。一个恢复点等于一份完整数据（含 health-imports），
#: 无上限地攒下去会把磁盘吃掉；留几份足够覆盖"删错了想找回来"的窗口。
RECOVERY_POINT_KEEP = 3

_ALLOWED_TOP_LEVEL = frozenset(
    {"manifest.json", *JSON_FILES, *OPTIONAL_JSON_FILES, HEALTH_DB_NAME}
)

#: 流式读写的块大小（DATA-23）。1 MiB 足够摊薄系统调用开销，又不会让峰值
#: 内存跟着成员大小走。
_STREAM_CHUNK_BYTES = 1024 * 1024


def _stream_into(reader: Any, writer: Any) -> tuple[str, int]:
    """按块从 `reader` 抄到 `writer`，顺手算出 sha256 与字节数。

    导出与恢复共用这一段：校验和是"边搬边算"出来的，因此不需要为了填
    manifest 或比对 manifest 再把成员整份读进内存一次。
    """
    hasher = hashlib.sha256()
    size = 0
    while True:
        chunk = reader.read(_STREAM_CHUNK_BYTES)
        if not chunk:
            break
        hasher.update(chunk)
        size += len(chunk)
        writer.write(chunk)
    return hasher.hexdigest(), size


class _BackupMembers(Mapping[str, bytes]):
    """已解压到磁盘的备份成员，按名字**惰性**读回（DATA-23）。

    对外仍然是"成员名 → 字节"的映射：`/data/backup/inspect` 只用
    `sorted(files)` 与 `in`，恢复走 `path()` 直接搬文件，测试里那几处
    `files[name]` 取到的还是原来的 bytes——只是不再有"整份备份同时摊在
    内存里"的那一刻。

    临时目录跟着对象一起消失（`weakref.finalize`），所以 `validate()` 的
    调用方不需要知道这里有磁盘状态；恢复路径出错时会显式 `release()`。
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._paths: dict[str, Path] = {}
        self._finalizer = weakref.finalize(self, shutil.rmtree, root, True)

    def reserve(self, name: str) -> Path:
        """登记一个成员并返回它在临时目录里的落盘位置。"""
        target = self._root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        self._paths[name] = target
        return target

    def path(self, name: str) -> Path:
        return self._paths[name]

    def release(self) -> None:
        self._paths = {}
        self._finalizer()

    def __getitem__(self, name: str) -> bytes:
        return self._paths[name].read_bytes()

    def __iter__(self) -> Iterator[str]:
        return iter(self._paths)

    def __len__(self) -> int:
        return len(self._paths)


def _is_safe_member_name(name: str) -> bool:
    """只接受白名单顶层文件，以及 `<备份目录>/<单层文件名>`。

    顺手挡掉路径穿越：`..`、绝对路径、反斜杠、多层嵌套一概拒绝——备份文件
    是用户从外部传进来的，不能假设它没被改过。
    """
    if not name or name != name.strip() or "\\" in name or name.startswith("/"):
        return False
    parts = name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return False
    if len(parts) == 1:
        return name in _ALLOWED_TOP_LEVEL
    return len(parts) == 2 and parts[0] in BACKUP_DIRECTORIES


class LocalBackupService:
    """导出/校验/恢复个人数据。

    `gate` 与 `database` 是可选协作者（DATA-12）：
    * `gate` —— `MaintenanceGate`，恢复期间拒绝新请求并等在飞请求排空；
    * `database` —— `HealthStore`，提供 `exclusive_access()` 与 `reopen()`，
      保证换库瞬间没有任何连接开着，换完之后重新校验 schema。

    两者都缺省为 None，这样单测可以只拿一个数据目录构造服务。
    """

    def __init__(
        self,
        data_dir: Path,
        *,
        gate: Any = None,
        database: Any = None,
        on_restored: list[Callable[[], Any]] | None = None,
    ) -> None:
        self.data_dir = data_dir
        self._gate = gate
        self._database = database
        self._on_restored = tuple(on_restored or ())

    # ------------------------------------------------------------------
    # 加锁顺序
    # ------------------------------------------------------------------

    @contextmanager
    def _locked_json_targets(self) -> Iterator[None]:
        """按**固定顺序**拿下所有 JSON 的文件锁。

        顺序固定是防死锁的全部要点：导出与恢复都走这里，普通写请求一次只拿
        一把，因此不可能出现反向等待。恢复额外持有的 HealthStore 访问锁一律
        排在这些文件锁**之后**，同样是为了单向依赖。
        """
        with ExitStack() as stack:
            for name in sorted((*JSON_FILES, *OPTIONAL_JSON_FILES)):
                stack.enter_context(JsonFileLock(self.data_dir / name))
            yield

    # ------------------------------------------------------------------
    # 导出
    # ------------------------------------------------------------------

    def _collect_members(self, workspace: Path) -> dict[str, Path]:
        """产出"成员名 → 磁盘上的来源路径"，不把任何内容读进内存（DATA-23）。

        `workspace` 用来放两类需要临时落盘的成员：必备/可选 JSON 的拷贝，
        以及 sqlite 一致快照。目录成员（health-imports 等）直接用原路径。

        ARCH-08 修法 2：JSON 文件锁**只**罩住那几个 JSON 的拷贝——它们小、
        而且正好是文件锁保护的对象；sqlite 快照与后续压缩一律在锁外，否则
        导出会按住 7 把锁做完整个快照 + 压缩，并发的一次保存计划就会撞上
        锁超时。
        """
        sources: dict[str, Path] = {}
        staging = workspace / "json"
        staging.mkdir(parents=True, exist_ok=True)
        with self._locked_json_targets():
            for name, empty in JSON_FILES.items():
                path = self.data_dir / name
                staged = staging / name
                if path.is_file():
                    shutil.copyfile(path, staged)
                else:
                    staged.write_bytes(empty)
                sources[name] = staged
            for name in OPTIONAL_JSON_FILES:
                path = self.data_dir / name
                if path.is_file():
                    staged = staging / name
                    shutil.copyfile(path, staged)
                    sources[name] = staged
        for directory in BACKUP_DIRECTORIES:
            base = self.data_dir / directory
            if not base.is_dir():
                children = []
            else:
                children = sorted(base.iterdir())
            if directory == "workout-quarantine":
                children += sorted(self.data_dir.glob("pending_workout.corrupt-*.json*"))
            for child in children:
                # 只收直接子文件：备份格式刻意保持单层，恢复时才不需要
                # 在解压阶段做任意深度的路径校验。
                if child.is_file():
                    sources[f"{directory}/{child.name}"] = child
        database = self.data_dir / HEALTH_DB_NAME
        if database.exists():
            snapshot = workspace / HEALTH_DB_NAME
            self._snapshot_database(database, snapshot)
            sources[HEALTH_DB_NAME] = snapshot
        return sources

    def _estimated_uncompressed_bytes(self) -> int:
        """Estimate source bytes before loading backup members into memory."""
        total = 0
        for name, empty in JSON_FILES.items():
            path = self.data_dir / name
            total += path.stat().st_size if path.is_file() else len(empty)
        for name in OPTIONAL_JSON_FILES:
            path = self.data_dir / name
            if path.is_file():
                total += path.stat().st_size
        for directory in BACKUP_DIRECTORIES:
            base = self.data_dir / directory
            children = list(base.iterdir()) if base.is_dir() else []
            if directory == "workout-quarantine":
                children += list(self.data_dir.glob("pending_workout.corrupt-*.json*"))
            total += sum(child.stat().st_size for child in children if child.is_file())
        database = self.data_dir / HEALTH_DB_NAME
        if database.is_file():
            total += database.stat().st_size
        return total

    @staticmethod
    def _snapshot_database(database: Path, destination: Path) -> None:
        """用 sqlite backup API 把一致快照落到 `destination`，而不是直接读文件。

        直接 `read_bytes()` 会漏掉还在 `-wal` 里的已提交事务。DATA-23：快照
        直接写到临时文件，不再经过一个 25 MB 起步的 bytes 中转。
        """
        source = sqlite3.connect(database)
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

    def export_bytes(self) -> bytes:
        """导出一份备份。

        对外仍然返回 bytes（`/data/backup/export` 与恢复点都按这个契约用），
        但内部走 `_write_archive` 流式落盘，峰值内存是**压缩后**的体积而不是
        原来的两倍数据量（DATA-23）。
        """
        with tempfile.TemporaryDirectory(prefix="fithealth-export-") as workspace:
            archive_path = Path(workspace) / "backup.zip"
            self._write_archive(archive_path)
            return archive_path.read_bytes()

    def _write_archive(self, destination: Path) -> dict[str, Any]:
        """按成员流式写出备份 zip，返回 manifest。"""
        with tempfile.TemporaryDirectory(prefix="fithealth-backup-") as raw_workspace:
            workspace = Path(raw_workspace)
            with ExitStack() as stack:
                if self._database is not None:
                    stack.enter_context(self._database.exclusive_access())
                if self._estimated_uncompressed_bytes() > MAX_UNCOMPRESSED_BYTES:
                    raise ValueError("数据超过备份解压上限（3 GiB），请先归档历史原始导入文件")
                sources = self._collect_members(workspace)
            # 压缩与校验和计算都在所有锁之外（ARCH-08）。
            members: dict[str, dict[str, Any]] = {}
            total_bytes = 0
            with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name in sorted(sources):
                    source = sources[name]
                    if not source.is_file():
                        # 目录成员是在锁外列出来的，中途被删掉不该让整次导出失败；
                        # manifest 最后才写，漏掉的成员不会造成"登记了但没有"。
                        logger.warning("导出时 %s 已消失，跳过", name)
                        continue
                    with source.open("rb") as reader, archive.open(name, "w") as writer:
                        digest, size = _stream_into(reader, writer)
                    total_bytes += size
                    if total_bytes > MAX_UNCOMPRESSED_BYTES:
                        raise ValueError("数据超过备份解压上限（3 GiB），请先归档历史原始导入文件")
                    # DATA-11：每成员 sha256 + 字节数。少了这个，"结构合法但内容被
                    # 替换"的备份能一路通过校验。
                    members[name] = {"sha256": digest, "bytes": size}
                manifest = {
                    "format": "fithealth-agent-backup",
                    "version": BACKUP_VERSION,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    # `files` 保留 v1 的字段名与含义，方便老工具粗读。
                    "files": sorted(members),
                    "members": dict(sorted(members.items())),
                }
                # manifest 放在最后写：校验和是边搬边算出来的，而 zip 按名字查表，
                # 成员顺序对 `_read_archive` 没有影响。
                archive.writestr(
                    "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2)
                )
        if destination.stat().st_size > MAX_BACKUP_BYTES:
            raise ValueError("压缩备份超过 1 GiB，请先归档历史原始导入文件")
        return manifest

    # ------------------------------------------------------------------
    # 校验
    # ------------------------------------------------------------------

    def _read_archive(self, content: bytes) -> tuple[dict[str, Any], _BackupMembers]:
        if not content or len(content) > MAX_BACKUP_BYTES:
            raise ValueError("备份文件为空或超过 1 GiB")
        try:
            archive = zipfile.ZipFile(io.BytesIO(content))
        except zipfile.BadZipFile as exc:
            raise ValueError("备份文件不是有效 ZIP") from exc
        with archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("备份文件包含重复条目")
            unsafe = [name for name in names if not _is_safe_member_name(name)]
            if unsafe:
                raise ValueError(f"备份文件包含不支持的内容：{unsafe[0]}")
            if sum(info.file_size for info in archive.infolist()) > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("备份文件解压后超过 3 GiB")
            if "manifest.json" not in names:
                raise ValueError("备份文件缺少 manifest")
            try:
                manifest = json.loads(archive.read("manifest.json"))
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError("备份文件的 manifest 无法解析") from exc
            if not isinstance(manifest, dict) or manifest.get("format") != "fithealth-agent-backup":
                raise ValueError("备份文件格式不匹配")
            if manifest.get("version") not in SUPPORTED_VERSIONS:
                raise ValueError("备份文件版本不受支持")
            expected = self._expected_members(manifest, names)
            # DATA-23：成员逐个解压到临时目录，不再攒成 {名字: 字节}。
            files = _BackupMembers(Path(tempfile.mkdtemp(prefix="fithealth-restore-")))
            try:
                extracted_bytes = 0
                for name in names:
                    if name == "manifest.json":
                        continue
                    target = files.reserve(name)
                    with archive.open(name) as reader, target.open("wb") as writer:
                        digest, size = _stream_into(reader, writer)
                    extracted_bytes += size
                    # 上面那道闸门信的是 zip 头里的 file_size；这里数的是真的
                    # 写出去多少，头字段撒谎也拦得住。
                    if extracted_bytes > MAX_UNCOMPRESSED_BYTES:
                        raise ValueError("备份文件解压后超过 3 GiB")
                    self._verify_member(name, digest, size, expected)
                self._verify_payloads(files)
            except BaseException:
                files.release()
                raise
        return manifest, files

    @staticmethod
    def _expected_members(
        manifest: dict[str, Any], names: list[str]
    ) -> dict[str, dict[str, Any]] | None:
        """取出 manifest 里登记的校验和；v1 没有这一段，返回 None 表示跳过。"""
        if manifest.get("version") == 1:
            return None
        members = manifest.get("members")
        if not isinstance(members, dict):
            raise ValueError("备份文件缺少成员校验和")
        present = {name for name in names if name != "manifest.json"}
        missing = sorted(set(members) - present)
        if missing:
            raise ValueError(f"manifest 登记了 {missing[0]} 但备份里没有这个文件")
        return members

    @staticmethod
    def _verify_member(
        name: str, digest: str, size: int, expected: dict[str, dict[str, Any]] | None
    ) -> None:
        """比对 manifest 登记的校验和。

        `digest`/`size` 是解压时边写边算出来的（DATA-23），所以这里不需要
        再把成员读回内存一次。
        """
        if expected is None:
            return
        entry = expected.get(name)
        if not isinstance(entry, dict):
            raise ValueError(f"manifest 未登记 {name}，无法校验其内容")
        if entry.get("bytes") != size:
            raise ValueError(f"{name} 的字节数与 manifest 不一致，备份可能已被改动")
        if entry.get("sha256") != digest:
            raise ValueError(f"{name} 的校验和与 manifest 不一致，备份可能已被改动")

    def _verify_payloads(self, files: _BackupMembers) -> None:
        for name in JSON_FILES:
            if name not in files:
                raise ValueError(f"备份文件缺少 {name}")
        for name in (*JSON_FILES, *OPTIONAL_JSON_FILES):
            if name not in files:
                continue
            try:
                parsed = json.loads(files[name].decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError(f"{name} 不是合法 JSON") from exc
            if name in {"user_profile.json", "pending_workout.json", "external_model_settings.json"}:
                if not isinstance(parsed, dict):
                    raise ValueError(f"{name} 格式无效")
            elif not isinstance(parsed, list):
                raise ValueError(f"{name} 格式无效")
        if HEALTH_DB_NAME in files:
            with tempfile.TemporaryDirectory() as workspace:
                candidate = Path(workspace) / HEALTH_DB_NAME
                # 刻意校验一份副本而不是解压出来的那个文件：`sqlite3.connect`
                # 打开 WAL 模式的库再关掉会做 checkpoint，把待恢复的字节改掉，
                # 那就和刚校验过的 manifest 对不上了。
                shutil.copyfile(files.path(HEALTH_DB_NAME), candidate)
                self._validate_database(candidate)

    def validate(self, content: bytes) -> Mapping[str, bytes]:
        """校验一份备份，返回"成员名 → 字节"的映射（惰性读盘，见 `_BackupMembers`）。"""
        return self._read_archive(content)[1]

    # ------------------------------------------------------------------
    # 恢复
    # ------------------------------------------------------------------

    def restore(self, content: bytes) -> dict[str, Any]:
        """把整份备份作为一次可回滚的事务恢复回去。

        单个文件系统没法原子地替换多个文件，所以每个目标先做快照，任何一步
        失败就按相反顺序全部退回，再把错误抛给调用方。

        DATA-12：整个过程在"维护开关 + JSON 文件锁 + HealthStore 独占"三重
        隔离下进行。加锁顺序固定为 gate → JSON 锁 → 数据库，并且 gate 会先
        把在飞请求排空，所以不存在与普通请求循环等待的可能。
        """
        manifest, files = self._read_archive(content)
        version = int(manifest.get("version") or 1)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        try:
            with ExitStack() as maintenance_stack:
                if self._gate is not None:
                    maintenance_stack.enter_context(self._gate.exclusive("恢复备份"))
                # The recovery point must be inside the maintenance window so no
                # accepted write can fall between the snapshot and restore.
                recovery_point = self.write_recovery_point(prefix="pre-restore")
                with ExitStack() as data_stack:
                    data_stack.enter_context(self._locked_json_targets())
                    if self._database is not None:
                        data_stack.enter_context(self._database.exclusive_access())
                    result = self._apply(files, version=version)
                    if self._database is not None:
                        # 仍在独占期内 reopen：换库与重新校验 schema 之间不能有别人插进来。
                        self._database.reopen()
                # JsonFileLock 不可重入；钩子（如 InfoStore.revalidate）会自行拿锁，
                # 所以先释放文件锁，但继续保持维护模式，阻止普通请求插入这个窗口。
                callback_results = [callback() for callback in self._on_restored]
        finally:
            # 解压出来的成员已经搬进数据目录，临时目录不必等到 GC 才清（DATA-23）。
            files.release()
        return {
            **result,
            "recovery_point": recovery_point,
            "restore_callbacks": callback_results,
        }

    def _apply(self, files: _BackupMembers, *, version: int) -> dict[str, Any]:
        file_targets = {name: files.path(name) for name in files if "/" not in name}
        directory_members: dict[str, dict[str, Path]] = {}
        for name in files:
            if "/" in name:
                directory, child = name.split("/", 1)
                directory_members.setdefault(directory, {})[child] = files.path(name)
        if version >= 2:
            # An absent member means the backed-up directory was empty. Restore
            # that empty state too; otherwise old quarantine/orphan files leak
            # through a nominally complete restore.
            for directory in BACKUP_DIRECTORIES:
                directory_members.setdefault(directory, {})

        transaction_dir = Path(tempfile.mkdtemp(prefix=".restore-", dir=self.data_dir))
        staged_dir = transaction_dir / "staged"
        rollback_dir = transaction_dir / "rollback"
        staged_dir.mkdir()
        rollback_dir.mkdir()
        undo: list[Callable[[], None]] = []

        try:
            for name, source in file_targets.items():
                staged = staged_dir / name
                # DATA-23：从解压目录按文件复制，不经过内存。
                shutil.copyfile(source, staged)
                if name == HEALTH_DB_NAME:
                    self._validate_database(staged)
            for directory, children in directory_members.items():
                staged = staged_dir / directory
                staged.mkdir()
                for child, source in children.items():
                    shutil.copyfile(source, staged / child)

            # v2 备份里没有的可选 JSON，说明导出时它就不存在——恢复后也不该存在。
            # v1 备份从来不带这两个文件，无法区分"没有"和"没记"，所以不动。
            obsolete = (
                [
                    name
                    for name in OPTIONAL_JSON_FILES
                    if name not in file_targets and (self.data_dir / name).exists()
                ]
                if version >= 2
                else []
            )

            for name in sorted(file_targets):
                target = self.data_dir / name
                undo.append(self._snapshot(target, rollback_dir))
                os.replace(staged_dir / name, target)
            for name in obsolete:
                target = self.data_dir / name
                undo.append(self._snapshot(target, rollback_dir))
                target.unlink(missing_ok=True)
            for directory in sorted(directory_members):
                undo.append(self._move_aside(self.data_dir / directory, transaction_dir))
                os.replace(staged_dir / directory, self.data_dir / directory)
            if HEALTH_DB_NAME in file_targets:
                # 边车文件只在**独占期内**删除：有连接开着时删掉 -wal，
                # 那条连接会把旧 WAL 写回新库（DATA-12）。
                for suffix in ("-wal", "-shm"):
                    sidecar = self.data_dir / f"{HEALTH_DB_NAME}{suffix}"
                    undo.append(self._snapshot(sidecar, rollback_dir))
                    sidecar.unlink(missing_ok=True)
        except Exception as exc:
            rollback_errors: list[Exception] = []
            for step in reversed(undo):
                try:
                    step()
                except OSError as rollback_error:
                    rollback_errors.append(rollback_error)
            if rollback_errors:
                logger.error("备份恢复回滚不完整：%s", rollback_errors)
                raise OSError("备份恢复失败且自动回滚不完整") from exc
            raise OSError("备份恢复失败，已回滚到恢复前的数据") from exc
        finally:
            shutil.rmtree(transaction_dir, ignore_errors=True)

        return {
            "restored_files": len(file_targets),
            "has_health_database": HEALTH_DB_NAME in file_targets,
            "restored_directories": sorted(directory_members),
            "restored_directory_files": sum(len(items) for items in directory_members.values()),
            "removed_files": obsolete,
        }

    @staticmethod
    def _snapshot(target: Path, rollback_dir: Path) -> Callable[[], None]:
        """先给 `target` 留一份回滚副本，返回"把它放回去"的动作。

        必须在动手之前调用：返回的动作会在任何一步失败时按相反顺序执行。
        """
        if not target.exists():
            return lambda: target.unlink(missing_ok=True)
        snapshot = rollback_dir / target.name
        shutil.copy2(target, snapshot)
        return lambda: os.replace(snapshot, target)

    @staticmethod
    def _move_aside(target: Path, transaction_dir: Path) -> Callable[[], None]:
        """把整个目录挪到事务目录里，返回"把它挪回来"的动作。

        目录不能像文件那样直接 `os.replace` 覆盖（Windows 与非空目录都会失败），
        所以先整体挪走再把暂存目录换进来——同一文件系统内两步都是 rename。
        """
        if not target.exists():
            return lambda: shutil.rmtree(target, ignore_errors=True)
        aside = transaction_dir / f"old-{target.name}"
        os.replace(target, aside)

        def undo() -> None:
            shutil.rmtree(target, ignore_errors=True)
            os.replace(aside, target)

        return undo

    @staticmethod
    def _validate_database(path: Path) -> None:
        connection = sqlite3.connect(path)
        try:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("健康数据库完整性校验失败")
        finally:
            connection.close()

    # ------------------------------------------------------------------
    # 恢复点（DATA-14）
    # ------------------------------------------------------------------

    @property
    def recovery_dir(self) -> Path:
        return self.data_dir / RECOVERY_POINT_DIR

    def _recovery_point_path(self, name: str) -> Path:
        """把外部传进来的名字解析成恢复点路径，形状不对就拒绝。

        名字会经由 HTTP 路径参数传进来，所以按外部输入处理：只接受
        `pre-reset-<14 位时间戳>.zip`，`..`／子目录／绝对路径一律落不进
        这个正则。`_is_safe_member_name` 管的是备份 zip 内部的成员名，
        两者是不同的入口，不能互相顶替。
        """
        if not _RECOVERY_POINT_NAME.match(name):
            raise ValueError("恢复点名称无效")
        return self.recovery_dir / name

    def write_recovery_point(self, *, prefix: str = "pre-reset") -> dict[str, Any]:
        """在清空数据之前落一份完整快照，返回它的描述。

        任何一步失败都会**抛出**而不是返回失败标记：调用方必须因此中止删除。
        写法与 JSON 落盘同构（临时文件 → fsync → replace），否则"快照已生成"
        可能只是页缓存里的一句空话，正好在断电时和数据一起消失。

        DATA-23：直接把 zip 流式写进临时文件，不再经过一份完整的 bytes。
        """
        if prefix not in {"pre-reset", "pre-restore"}:
            raise ValueError("恢复点前缀无效")
        self.recovery_dir.mkdir(parents=True, exist_ok=True)
        target = self._next_recovery_point_path(datetime.now(), prefix=prefix)
        temp_path = temp_write_path(target)
        try:
            self._write_archive(temp_path)
            with temp_path.open("rb+") as handle:
                handle.flush()
                os.fsync(handle.fileno())
            temp_path.replace(target)
        finally:
            temp_path.unlink(missing_ok=True)
        self._prune_recovery_points(keep=target.name)
        return self._describe_recovery_point(target)

    def _next_recovery_point_path(self, now: datetime, *, prefix: str = "pre-reset") -> Path:
        """分配一个**严格晚于已有全部恢复点**的文件名。

        时间戳只到秒，同一秒内重置两次（第一次半失败、用户立刻重试）会撞名，
        而后一次快照拍的是已经被清空的数据——直接覆盖等于把唯一一份真数据的
        恢复点弄丢。

        修法不是"找个空位"：`_prune_recovery_points` 删掉的是时间戳最小的那份，
        腾出的空位正好在**过去**。填进去会让新快照拿到一个比现存快照更旧的
        名字，于是紧接着的 prune 又把它当成最老的一份删掉——实测就是这样
        把刚写好的快照删没了。所以两种前缀共享一条时间线，取
        `max(now, 现存最大时间戳 + 1s)`，新快照不可能被 prune 选中。
        """
        stamp = now.strftime("%Y%m%d%H%M%S")
        existing = self.list_recovery_points()
        if existing:
            latest = str(existing[0]["stamp"])
            if latest >= stamp:
                stamp = (
                    datetime.strptime(latest, "%Y%m%d%H%M%S") + timedelta(seconds=1)
                ).strftime("%Y%m%d%H%M%S")
        return self.recovery_dir / f"{prefix}-{stamp}.zip"

    def _prune_recovery_points(self, *, keep: str) -> None:
        """只保留最近 RECOVERY_POINT_KEEP 份，`keep` 无论如何都不删。

        显式排除刚写好的那一份：整条修法的前提是"写成功就一定有一份可用的
        恢复点"，把它交给命名顺序去隐式保证太脆。

        清理本身是 best-effort——删不掉旧快照不该让一次**已经写成功**的新快照
        变成失败，那会把调用方推向"没有快照，于是不敢删"的死角。
        """
        points = self.list_recovery_points()
        for item in points[RECOVERY_POINT_KEEP:]:
            if item["name"] == keep:
                continue
            try:
                (self.recovery_dir / item["name"]).unlink()
            except OSError as exc:
                logger.warning("清理旧恢复点 %s 失败：%s", item["name"], exc)

    def _describe_recovery_point(self, path: Path) -> dict[str, Any]:
        stat = path.stat()
        match = _RECOVERY_POINT_NAME.fullmatch(path.name)
        if match is None:
            raise ValueError("恢复点文件名无效")
        return {
            "name": path.name,
            "stamp": match.group(1),
            "bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        }

    def list_recovery_points(self) -> list[dict[str, Any]]:
        """按时间倒序列出恢复点（最新在前）。"""
        if not self.recovery_dir.is_dir():
            return []
        items = [
            self._describe_recovery_point(child)
            for child in self.recovery_dir.iterdir()
            if child.is_file() and _RECOVERY_POINT_NAME.match(child.name)
        ]
        # 两种前缀不参与排序；只比较定宽时间戳。mtime 可能在复制或同步后改变。
        return sorted(items, key=lambda item: (item["stamp"], item["name"]), reverse=True)

    def read_recovery_point(self, name: str) -> bytes:
        path = self._recovery_point_path(name)
        if not path.is_file():
            raise FileNotFoundError("未找到该恢复点")
        return path.read_bytes()

    def delete_recovery_point(self, name: str) -> bool:
        path = self._recovery_point_path(name)
        if not path.is_file():
            return False
        path.unlink()
        return True


