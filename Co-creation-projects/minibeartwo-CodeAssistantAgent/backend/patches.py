"""Reviewable, optimistic file changes with persistent before/after checkpoints."""
from __future__ import annotations

import difflib
import base64
import binascii
import hashlib
import io
import json
import os
import re
import stat
import tempfile
import warnings
from pathlib import Path

from .store import Store, identifier, now
from .skills import ANNOTATION_SKILL, validate_annotation_change
from .workspace import Conflict, MAX_FILE, Workspace, digest


DOCUMENTATION_SKILL = "analyze-project-zh"
DOCUMENTATION_PATHS = (
    "项目说明.md", "docs/diagrams/README.md", "docs/diagrams/architecture.png",
    "docs/diagrams/workflow.png", "docs/diagrams/sequence.png",
)
PNG_PATHS = frozenset(path for path in DOCUMENTATION_PATHS if path.endswith(".png"))
MAX_DOCUMENTATION_BUNDLE = 1_024_000
MAX_EXISTING_PNG = 8 * 1024 * 1024
MAX_DOCUMENTATION_BACKUP = 24 * 1024 * 1024 + MAX_FILE * 2


def raw_digest(content: bytes | None) -> str:
    return "missing" if content is None else hashlib.sha256(content).hexdigest()


def checked_png(content: str | None, *, optional: bool = False, maximum: int = MAX_FILE) -> bytes | None:
    """Decode bounded, static PNG data; base64 is a checkpoint representation only."""
    if content is None and optional:
        return None
    if not isinstance(content, str) or len(content) > ((maximum + 2) // 3) * 4:
        raise ValueError("PNG 补丁必须提供 256 KB 以内图片的标准 base64 数据。")
    try:
        raw = base64.b64decode(content, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("PNG 补丁的 base64 数据无效。") from exc
    if (len(raw) > maximum or not raw.startswith(b"\x89PNG\r\n\x1a\n")
            or base64.b64encode(raw).decode("ascii") != content):
        raise ValueError("文档图片必须是 256 KB 以内的有效 PNG。")
    from PIL import Image, UnidentifiedImageError
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as picture:
                if (picture.format != "PNG" or not 0 < picture.width <= 4096
                        or not 0 < picture.height <= 4096 or picture.width * picture.height > 12_000_000
                        or getattr(picture, "n_frames", 1) != 1):
                    raise ValueError("PNG 尺寸或帧数超过文档图表的安全范围。")
                picture.verify()
            with Image.open(io.BytesIO(raw)) as picture:
                picture.load()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise ValueError("PNG 补丁图片损坏或无法安全解码。") from exc
    return raw


class AnnotationAlreadyComplete(ValueError):
    """A validated annotation candidate is identical to the current files."""


class EditMatchError(ValueError):
    def __init__(self, message: str, path: str | None = None):
        super().__init__(message)
        self.path = path


class Patches:
    def __init__(self, store: Store):
        self.store = store

    def propose(self, task: dict, changes: list[dict], *, read_baselines: dict[str, str] | None = None,
                diagnostics: list[str] | None = None) -> dict:
        if task.get("skill") == DOCUMENTATION_SKILL:
            raise ValueError("项目解析任务只能通过专用文档交付接口生成说明和设计图，不能提出普通源码补丁。")
        if not isinstance(changes, list):
            raise ValueError("changes 必须是 JSON 数组（列表），每项包含 path、base_hash 及 content 或 edits。")
        if not 1 <= len(changes) <= 5:
            raise ValueError("一次补丁需要包含 1–5 个文件。")
        workspace = Workspace(self.store.one("workspaces", task["workspace_id"])["root"],
                              include_build_sources=task.get("skill") == ANNOTATION_SKILL)
        prepared, seen, unchanged = [], set(), []
        total = 0
        for index, change in enumerate(changes):
            if not isinstance(change, dict):
                raise ValueError(f"changes[{index}] 必须是包含 path、base_hash 及 content 或 edits 的 JSON 对象。")
            if {"encoding", "mime_type", "binary"} & change.keys():
                raise ValueError("普通补丁仅接受文本，PNG 图片只能通过受控文档交付接口生成。")
            if task.get("skill") == ANNOTATION_SKILL and not change.get("path") and read_baselines:
                # Recover only from actual reads in this task, never a summary or
                # an arbitrary workspace scan. Duplicate contents are ambiguous.
                candidates = [name for name, hash_value in read_baselines.items()
                              if hash_value == change.get("base_hash")]
                if len(candidates) == 1 and workspace.read(candidates[0])["hash"] == change.get("base_hash"):
                    change = {**change, "path": candidates[0]}
                    if diagnostics is not None:
                        diagnostics.append(f"changes[{index}] 已按唯一真实读取 hash 补回路径 {candidates[0]}。")
            if not isinstance(change.get("path"), str) or not change["path"].strip():
                raise ValueError(f"changes[{index}].path 缺失或无效：每个文件都必须显式填写工作区相对路径，不能省略或依赖上一轮。")
            if not isinstance(change.get("base_hash"), str) or not change["base_hash"]:
                raise ValueError(f"changes[{index}].base_hash 缺失或无效：请使用 read 返回的真实 hash，新文件用 missing。")
            if ("content" in change) == ("edits" in change):
                raise ValueError("补丁必须提供 content 或 edits，二选一；删除文件使用 content: null。")
            path = workspace.path(change["path"])
            relative = path.relative_to(workspace.root).as_posix()
            if path.suffix.lower() == ".png":
                raise ValueError("PNG 图片只能通过受控文档交付接口生成。")
            if relative.casefold() in seen:
                raise ValueError("补丁中包含重复文件。")
            seen.add(relative.casefold())
            before = workspace.read(relative)["content"] if path.exists() else None
            if change.get("base_hash") != digest(before):
                raise Conflict(f"{relative} 的基线已变化，请重新读取文件。")
            try:
                after = self.apply_edits(before, change["edits"],
                    recover_comments=task.get("skill") == ANNOTATION_SKILL and path.suffix.lower() in {".py", ".pyi"},
                    diagnostics=diagnostics) if "edits" in change else change["content"]
            except EditMatchError as exc:
                raise EditMatchError(f"{relative}：{exc}", relative) from exc
            if after is not None and (not isinstance(after, str) or "\x00" in after):
                raise ValueError("补丁仅接受文本内容或 null（删除文件）。")
            if after == before:
                if task.get("skill") == ANNOTATION_SKILL and path.suffix.lower() in {".py", ".pyi"}:
                    validate_annotation_change(relative, before, after)
                    unchanged.append(relative)
                    continue
                raise ValueError(f"{relative} 没有实际改动。")
            if task.get("skill") == ANNOTATION_SKILL:
                validate_annotation_change(relative, before, after)
            if len(before or "") > 24_000 or len(after or "") > 24_000:
                if task.get("skill") != ANNOTATION_SKILL or "edits" not in change:
                    raise ValueError("整文件编辑限制为 24000 字符；注释长文件请分段 read 后使用 edits 提交局部替换。")
            if len((after or "").encode("utf-8")) > MAX_FILE:
                raise ValueError("注释后的文件超过 256 KB 文本上限，请明确报告该文件尚未覆盖，不能反复提交相同补丁。")
            total += len((after or "").encode("utf-8")) + len((before or "").encode("utf-8"))
            if total > MAX_FILE * 2:
                raise ValueError("补丁过大，请拆分为较小的修改。")
            prepared.append({"path": relative, "before": before, "after": after,
                             "before_hash": digest(before), "after_hash": digest(after),
                             "mode": stat.S_IMODE(path.stat().st_mode) if path.exists() else None})
        if not prepared:
            raise AnnotationAlreadyComplete("、".join(unchanged) + " 与当前文件一致且注释静态检查通过，无需重复应用；请继续处理其余文件。")
        if unchanged and diagnostics is not None:
            diagnostics.append("已跳过静态检查通过且无变化的文件：" + "、".join(unchanged))
        patch_id = identifier()
        self.store.execute("INSERT INTO patches VALUES(?,?,?,?,?,?)", (
            patch_id, task["id"], task["workspace_id"], "proposed", json.dumps(prepared, ensure_ascii=False), now()))
        return self.get(patch_id)

    def propose_documentation(self, task: dict, bundle: list[dict]) -> dict:
        """Prepare exactly two Markdown documents and three locally rendered PNGs."""
        if task.get("skill") != DOCUMENTATION_SKILL:
            raise ValueError("只有项目解析任务可以提交文档交付包。")
        if (not isinstance(bundle, list) or len(bundle) != len(DOCUMENTATION_PATHS)
                or any(not isinstance(change, dict) for change in bundle)):
            raise ValueError("文档交付包必须完整包含说明、图说明及三张设计图。")
        paths = [change.get("path") for change in bundle]
        if any(not isinstance(path, str) for path in paths) or set(paths) != set(DOCUMENTATION_PATHS):
            raise ValueError("文档交付包路径必须精确匹配固定的五个输出文件。")
        workspace = Workspace(self.store.one("workspaces", task["workspace_id"])["root"])
        prepared, total_after, total_before = [], 0, 0
        for change in bundle:
            relative = change["path"]
            path = workspace.path(relative)
            if path.relative_to(workspace.root).as_posix() != relative:
                raise ValueError("文档输出不能通过路径别名或链接改写其他文件。")
            if "base_hash" not in change or not isinstance(change["base_hash"], str):
                raise ValueError("每个文档输出都必须提供当前文件的真实 base_hash。")
            before_limit = MAX_EXISTING_PNG if relative in PNG_PATHS else MAX_FILE
            if path.exists() and (not path.is_file() or path.stat().st_size > before_limit):
                raise ValueError(f"{relative} 不是可替换文件或超过原文件备份上限。")
            before_raw = path.read_bytes() if path.exists() else None
            if raw_digest(before_raw) != change["base_hash"]:
                raise Conflict(f"{relative} 的基线已变化，文档包未写入，请重新核对。")
            if relative in PNG_PATHS:
                if (set(change) != {"path", "base_hash", "content", "encoding", "mime_type"}
                        or change["encoding"] != "base64" or change["mime_type"] != "image/png"):
                    raise ValueError("设计图必须由受控渲染器提供 image/png base64 数据。")
                after_raw = checked_png(change["content"])
                before = base64.b64encode(before_raw).decode("ascii") if before_raw is not None else None
                checked_png(before, optional=True, maximum=MAX_EXISTING_PNG)
                after = change["content"]
                extra = {"encoding": "base64", "mime_type": "image/png"}
            else:
                if set(change) != {"path", "base_hash", "content"}:
                    raise ValueError("说明文档只能包含 path、base_hash 和文本 content。")
                after = change["content"]
                if not isinstance(after, str) or "\x00" in after or len(after) > 24_000:
                    raise ValueError("说明文档必须是 24000 字符以内的 UTF-8 文本，不能删除文件。")
                try:
                    before = before_raw.decode("utf-8") if before_raw is not None else None
                except UnicodeDecodeError as exc:
                    raise ValueError(f"{relative} 当前不是 UTF-8 文本，不能自动替换。") from exc
                if before is not None and ("\x00" in before or len(before) > 24_000):
                    raise ValueError(f"{relative} 当前文档超过文本编辑范围。")
                after_raw, extra = after.encode("utf-8"), {}
                if len(after_raw) > MAX_FILE:
                    raise ValueError("说明文档超过 256 KB。")
            total_after += len(after_raw)
            total_before += len(before_raw or b"")
            prepared.append({"path": relative, "before": before, "after": after,
                "before_hash": raw_digest(before_raw), "after_hash": raw_digest(after_raw),
                "mode": stat.S_IMODE(path.stat().st_mode) if path.exists() else None, **extra})
        if total_after > MAX_DOCUMENTATION_BUNDLE or total_before > MAX_DOCUMENTATION_BACKUP:
            raise ValueError("文档交付包超过检查点总大小限制。")
        self._validate_documentation_records(task, prepared)
        patch_id = identifier()
        self.store.execute("INSERT INTO patches VALUES(?,?,?,?,?,?)", (
            patch_id, task["id"], task["workspace_id"], "proposed", json.dumps(prepared, ensure_ascii=False), now()))
        return self.get(patch_id)

    @staticmethod
    def _validate_documentation_records(task: dict, changes: list[dict]):
        """Recheck persisted binary checkpoints on reads and before every apply/undo."""
        if task.get("skill") != DOCUMENTATION_SKILL:
            if any(isinstance(change, dict) and ({"encoding", "mime_type", "binary"} & change.keys()) for change in changes):
                raise ValueError("普通任务的补丁不能包含二进制文档图表。")
            return
        if (not isinstance(changes, list) or len(changes) != 5
                or any(not isinstance(change, dict) for change in changes)):
            raise ValueError("文档检查点必须包含固定的五个文件。")
        paths = [change.get("path") for change in changes]
        if any(not isinstance(path, str) for path in paths) or set(paths) != set(DOCUMENTATION_PATHS):
            raise ValueError("文档检查点包含未授权或重复的路径。")
        total_before, total_after = 0, 0
        for change in changes:
            if change["path"] in PNG_PATHS:
                if change.get("encoding") != "base64" or change.get("mime_type") != "image/png":
                    raise ValueError("PNG 检查点的编码或格式不正确。")
                before = checked_png(change.get("before"), optional=True, maximum=MAX_EXISTING_PNG)
                after = checked_png(change.get("after"))
            else:
                if {"encoding", "mime_type", "binary"} & change.keys():
                    raise ValueError("Markdown 检查点不能包含二进制内容。")
                before_text, after_text = change.get("before"), change.get("after")
                if (before_text is not None and not isinstance(before_text, str)) or not isinstance(after_text, str):
                    raise ValueError("Markdown 检查点内容必须是文本，不能删除文件。")
                if any(len(value) > 24_000 or "\x00" in value for value in (before_text or "", after_text)):
                    raise ValueError("Markdown 检查点超过文本编辑范围。")
                before = before_text.encode("utf-8") if before_text is not None else None
                after = after_text.encode("utf-8")
            before_limit = MAX_EXISTING_PNG if change["path"] in PNG_PATHS else MAX_FILE
            if len(before or b"") > before_limit or len(after) > MAX_FILE:
                raise ValueError("文档检查点单文件超过 256 KB。")
            if raw_digest(before) != change.get("before_hash") or raw_digest(after) != change.get("after_hash"):
                raise ValueError("文档检查点内容与 hash 不匹配。")
            mode = change.get("mode")
            if mode is not None and (type(mode) is not int or not 0 <= mode <= 0o7777):
                raise ValueError("文档检查点文件权限值无效。")
            total_before += len(before or b"")
            total_after += len(after)
        if total_after > MAX_DOCUMENTATION_BUNDLE or total_before > MAX_DOCUMENTATION_BACKUP:
            raise ValueError("文档检查点超过总大小限制。")

    @staticmethod
    def apply_edits(before: str | None, edits: list[dict], *, recover_comments: bool = False,
                    diagnostics: list[str] | None = None) -> str:
        """Build a full candidate in memory; exact matches refer to one baseline."""
        if before is None or not isinstance(edits, list) or not 1 <= len(edits) <= 100:
            raise ValueError("edits 仅适用于已有文件，每次需要 1–100 处替换。")
        spans = []
        for index, edit in enumerate(edits):
            if not isinstance(edit, dict):
                raise ValueError("每项 edits 需要 old/new 字符串。")
            old, new = edit.get("old"), edit.get("new")
            if not isinstance(old, str) or not old or not isinstance(new, str):
                raise ValueError("edits.old 必须为非空原文，new 必须为替换后的文本。")
            start = before.find(old)
            if start < 0 or before.find(old, start + 1) >= 0:
                recovered = Patches.recover_comment_edit(before, old, new) if recover_comments else None
                if recovered:
                    start, end, new = recovered
                    if diagnostics is not None:
                        diagnostics.append(f"edits[{index}] 已恢复唯一匹配的换行或注释块缩进；代码仍须通过静态校验。")
                else:
                    count = "0" if start < 0 else "多"
                    raise EditMatchError(f"edits[{index}].old 匹配 {count} 处，必须在原文件中精确且唯一匹配。"
                        "本批未写入；请使用返回的当前原文，保留逐行缩进与换行，并增加唯一上下文，勿原样重试。")
            else:
                end = start + len(old)
            spans.append((start, end, new))
        spans.sort(key=lambda span: span[0])
        if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
            raise ValueError("edits 替换范围不能重叠。")
        after = before
        for start, end, new in reversed(spans):
            after = after[:start] + new + after[end:]
        return after

    @staticmethod
    def recover_comment_edit(before: str, old: str, new: str) -> tuple[int, int, str] | None:
        """Recover line endings or uniform indentation of standalone comments.

        Do not fuzzy-match text, strip code indentation or choose among matches.
        This is used only for Python annotation candidates, before AST/token checks.
        """
        # Mixed source endings have no single deterministic replacement style.
        if "\r" in before.replace("\r\n", "") or 0 < before.count("\r\n") < before.count("\n"):
            return None
        newline = "\r\n" if "\r\n" in before else "\n"
        normalize = lambda value: value.replace("\r\n", "\n").replace("\n", newline)
        normalized_old, normalized_new = normalize(old), normalize(new)
        start = before.find(normalized_old)
        if start >= 0:
            return (start, start + len(normalized_old), normalized_new) if before.find(normalized_old, start + 1) < 0 else None
        old_lines, new_lines = normalized_old.splitlines(keepends=True), normalized_new.splitlines(keepends=True)
        if not old_lines or not new_lines or not any(line.strip() for line in new_lines):
            return None
        # Restore only comment lines. Any accompanying def/decorator/code must
        # already match byte-for-byte, including its own indentation.
        if not any(line.startswith("#") for line in old_lines) or not any(line.startswith("#") for line in new_lines):
            return None
        matches = []
        for prefix in set(re.findall(r"(?m)^([ \t]+)#", before)):
            candidate = "".join(prefix + line if line.startswith("#") else line for line in old_lines)
            for match in re.finditer(r"(?m)^" + re.escape(candidate), before):
                end = match.end()
                if not candidate.endswith("\n") and end < len(before) and before[end] not in "\r\n":
                    continue
                replacement = "".join(prefix + line if line.startswith("#") else line for line in new_lines)
                matches.append((match.start(), end, replacement))
        return matches[0] if len(matches) == 1 else None

    def get(self, patch_id: str) -> dict:
        patch = self.store.one("patches", patch_id)
        patch["changes"] = json.loads(patch["changes"])
        task = self.store.one("tasks", patch["task_id"])
        if task.get("skill") == DOCUMENTATION_SKILL and patch["workspace_id"] != task["workspace_id"]:
            raise ValueError("文档检查点与任务工作区不匹配。")
        self._validate_documentation_records(task, patch["changes"])
        for change in patch["changes"]:
            if change.get("encoding") == "base64":
                change["diff"] = ""
                continue
            change["diff"] = "".join(difflib.unified_diff(
                (change["before"] or "").splitlines(keepends=True),
                (change["after"] or "").splitlines(keepends=True),
                fromfile="a/" + change["path"], tofile="b/" + change["path"]))
        return patch

    @staticmethod
    def write(path: Path, content: str | bytes | None, mode: int | None = None):
        if content is None:
            if path.exists():
                path.unlink()
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        if mode is None and path.exists():
            mode = stat.S_IMODE(path.stat().st_mode)
        fd, temporary = tempfile.mkstemp(prefix=".code-assistant-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content if isinstance(content, bytes) else content.encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
            if mode is not None:
                os.chmod(temporary, mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def apply(self, patch_id: str, undo: bool = False) -> dict:
        patch = self.get(patch_id)
        allowed = {"applied", "recovery_required"} if undo else {"proposed"}
        if patch["status"] not in allowed:
            raise Conflict("补丁状态不允许此操作。")
        task = self.store.one("tasks", patch["task_id"])
        workspace = Workspace(self.store.one("workspaces", patch["workspace_id"])["root"],
                              include_build_sources=task.get("skill") == ANNOTATION_SKILL)
        expected, target = ("after", "before") if undo else ("before", "after")
        files = []
        for change in patch["changes"]:
            path = workspace.path(change["path"])
            binary = change.get("encoding") == "base64"
            if task.get("skill") == DOCUMENTATION_SKILL and path.relative_to(workspace.root).as_posix() != change["path"]:
                raise ValueError("文档输出不能通过链接改写其他文件。")
            if binary:
                if path.exists() and (not path.is_file() or path.stat().st_size > MAX_EXISTING_PNG):
                    raise Conflict(f"{change['path']} 当前不在图片文件范围内，未覆盖。")
                current = path.read_bytes() if path.exists() else None
                current_hash = raw_digest(current)
            else:
                current = workspace.read(change["path"])["content"] if path.exists() else None
                current_hash = digest(current)
            if patch["status"] == "recovery_required" and current_hash == change["before_hash"]:
                continue
            if current_hash != change[expected + "_hash"]:
                raise Conflict(f"{change['path']} 已被其他操作修改，未覆盖当前文件。")
            if not undo and task.get("skill") == ANNOTATION_SKILL:
                # Recheck legacy pending patches as well as newly generated ones.
                validate_annotation_change(change["path"], current, change["after"])
            replacement = checked_png(change[target], optional=undo,
                maximum=MAX_EXISTING_PNG if undo else MAX_FILE) if binary else change[target]
            files.append((path, current, change, replacement))
        self.store.execute("UPDATE patches SET status=? WHERE id=?", ("undoing" if undo else "applying", patch_id))
        written = []
        try:
            for path, current, change, replacement in files:
                self.write(path, replacement, change.get("mode"))
                written.append((path, current, change))
        except BaseException:
            for path, previous, change in reversed(written):
                self.write(path, previous, change.get("mode"))
            self.store.execute("UPDATE patches SET status=? WHERE id=?", (patch["status"], patch_id))
            raise
        self.store.execute("UPDATE patches SET status=? WHERE id=?", ("reverted" if undo else "applied", patch_id))
        return self.get(patch_id)
