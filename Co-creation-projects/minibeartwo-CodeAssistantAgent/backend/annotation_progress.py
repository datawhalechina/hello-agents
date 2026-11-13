"""Persistent annotation coverage and bounded, exact source pages; never execute code."""
from __future__ import annotations

import json
from pathlib import Path

from .skills import annotation_read_hints, validate_annotation_change
from .store import identifier
from .workspace import MAX_FILE, Workspace


PAGE_CHARS = 18_000
SNAPSHOT_CHARS = 8_000
DONE = {"verified", "applied"}
DOCUMENTS = {".md", ".rst", ".txt", ".json", ".jsonl", ".csv", ".tsv", ".log", ".lock"}
BINARY = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
          ".7z", ".exe", ".dll", ".so", ".pyc", ".pyo", ".woff", ".woff2", ".ttf",
          ".mp3", ".mp4", ".wav", ".npy", ".npz", ".pt", ".pth", ".onnx", ".bin"}


def encoded_size(value) -> int:
    return len(json.dumps(value, ensure_ascii=False))


class AnnotationProgress:
    """One task's durable ledger. Public methods are synchronous for ``to_thread``."""

    def __init__(self, store, task_id: str, workspace: Workspace):
        self.store, self.task_id, self.workspace = store, task_id, workspace
        self.read_baselines: dict[str, str] = {}
        self.owner = identifier()
        # Claim before walking/validating files. A cancelled old worker can
        # continue running, but may never overwrite a later resumed run.
        with store.connect() as db:
            saved = db.execute("SELECT state FROM annotation_progress WHERE task_id=?", (task_id,)).fetchone()
            self.state = json.loads(saved["state"]) if saved else {"revision": 0, "files": {}, "inventory_pages": []}
            self.state["owner"] = self.owner
            if db.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone():
                db.execute("INSERT INTO annotation_progress(task_id,state) VALUES(?,?) "
                           "ON CONFLICT(task_id) DO UPDATE SET state=excluded.state",
                           (task_id, json.dumps(self.state, ensure_ascii=False)))
        self._listed = set(self.state.get("inventory_seen", []))
        # Enumerate once per run, including resumes. The model can request any
        # cached page repeatedly without another walk of the selected project.
        self.files = list(workspace.files(limit=None))
        entries = self.state["files"]
        present = set(self.files)
        for path in list(entries):
            if path not in present:
                del entries[path]
                self._advance()
        for path in self.files:
            if path not in entries:
                entries[path] = self._initial(path)
            elif entries[path].get("status") == "blocked":
                # User edits between runs may shrink a file, restore UTF-8 or
                # split an oversized line. A resumed run must try it afresh.
                entries[path] = self._initial(path)
        self.reconcile()
        self.observe_existing_patches()
        self._save()

    def _initial(self, path: str) -> dict:
        suffix = Path(path).suffix.lower()
        if suffix in DOCUMENTS or Path(path).name.upper() in {"LICENSE", "LICENSE-MIT", "COPYING"}:
            return {"status": "skipped", "reason": "文档、数据或严格 JSON 不添加源码注释；可按需读取了解项目。"}
        if suffix in BINARY:
            return {"status": "skipped", "reason": "二进制、媒体、模型权重或生成文件不添加源码注释。"}
        try:
            if self.workspace.path(path).stat().st_size > MAX_FILE:
                return {"status": "blocked", "reason": "文件超过 256 KB 文本访问上限；请拆分文件后重试。"}
        except (OSError, ValueError):
            return {"status": "blocked", "reason": "文件已不存在或无法访问。"}
        return {"status": "pending"}

    def _advance(self):
        self.state["revision"] = self.state.get("revision", 0) + 1

    def _save(self):
        # A cancelled to_thread operation can finish after history deletion.
        # Check task existence and run ownership in the same transaction.
        with self.store.connect() as db:
            row = db.execute("SELECT state FROM annotation_progress WHERE task_id=?", (self.task_id,)).fetchone()
            if (row and json.loads(row["state"]).get("owner") == self.owner
                    and db.execute("SELECT 1 FROM tasks WHERE id=?", (self.task_id,)).fetchone()):
                db.execute("UPDATE annotation_progress SET state=? WHERE task_id=?",
                           (json.dumps(self.state, ensure_ascii=False), self.task_id))

    def _blocked(self, path: str, reason: str):
        previous = self.state["files"].get(path, {})
        reason = reason[:500]
        if previous.get("status") != "blocked" or previous.get("reason") != reason:
            self.state["files"][path] = {**previous, "status": "blocked", "reason": reason}
            self._advance()

    def inventory(self, args: dict) -> dict:
        offset = args.get("offset", 0)
        if type(offset) is not int or offset < 0:
            raise ValueError("inventory.offset 必须是大于或等于 0 的整数。")
        page = self.files[offset:offset + 100]
        def result():
            return {"files": page, "total": len(self.files),
                    "next_offset": offset + len(page) if offset + len(page) < len(self.files) else None,
                    "page_status": {path: self.state["files"][path]["status"] for path in page},
                    "message": "清单已缓存。按待处理项继续，勿为恢复上下文反复从第一页扫描。"}
        while len(page) > 1 and encoded_size(result()) > PAGE_CHARS:
            page.pop()
        if encoded_size(result()) > PAGE_CHARS:
            raise ValueError("单条路径过长，无法安全提供文件清单页；请缩短项目路径。")
        # Offset changes alone are not progress: overlapping views of already
        # delivered paths must not reset the runtime's no-progress detector.
        if set(page) - self._listed:
            self._listed.update(page)
            self.state["inventory_seen"] = sorted(self._listed)
            self._advance()
            self._save()
        return result()

    def _hints(self, hints: dict | None, start: int, end: int) -> dict | None:
        if hints is None:
            return None
        hints = dict(hints)
        positions = hints.get("function_comment_positions", [])
        current = [item for item in positions if start <= item["comment_before_line"] <= end]
        hints["function_comment_positions"] = current[:20]
        hints["functions_in_page"] = len(current)
        # Metadata must not make an otherwise small source page overflow.
        while hints["function_comment_positions"] and encoded_size(hints) > 4_000:
            hints["function_comment_positions"].pop()
        hints["positions_truncated"] = len(hints["function_comment_positions"]) < len(current)
        return hints

    @staticmethod
    def _ranges(ranges: list, start: int, end: int) -> list:
        merged = []
        for left, right in sorted([*ranges, [start, end]]):
            if not merged or left > merged[-1][1] + 1:
                merged.append([left, right])
            else:
                merged[-1][1] = max(merged[-1][1], right)
        return merged

    def read(self, args: dict) -> dict:
        relative = args.get("path")
        if not isinstance(relative, str):
            raise ValueError("read.path 必须是工作区相对路径。")
        # Validate even when the ledger says done. Never persist unsafe paths.
        path = self.workspace.path(relative).relative_to(self.workspace.root).as_posix()
        for key in ("start_line", "end_line"):
            if key in args and (type(args[key]) is not int or args[key] < 1):
                raise ValueError(f"read.{key} 必须是从 1 开始的整数。")
        if args.get("end_line", args.get("start_line", 1)) < args.get("start_line", 1):
            raise ValueError("read.end_line 不能早于 start_line。")
        if "force" in args and type(args["force"]) is not bool:
            raise ValueError("read.force 必须是布尔值。")
        try:
            file = self.workspace.read(path)
        except (ValueError, OSError) as exc:
            # Invented missing paths are errors, not discovered project work.
            # Only a known file becoming unavailable changes the durable ledger.
            if path in self.state["files"]:
                self._blocked(path, str(exc))
                self._save()
            return {"path": path, "status": "blocked", "error": str(exc), "message": "该文件无法读取，请处理其他待办项，勿原样重试。"}
        content, hash_value = file["content"], file["hash"]
        self.read_baselines[path] = hash_value
        entry = self.state["files"].setdefault(path, self._initial(path))
        if entry.get("hash") != hash_value:
            old_hash = entry.get("hash")
            entry = self._initial(path)
            entry.update(hash=hash_value, ranges=[], cursor=1)
            self.state["files"][path] = entry
            if old_hash is not None:
                self._advance()
        # Static format checks are insufficient to infer whether descriptions
        # match the implementation. The model must still read existing source.
        if Path(path).suffix.lower() in {".py", ".pyi"} and not entry.get("checked"):
            entry["checked"] = True
            try:
                validate_annotation_change(path, content, content)
            except (ValueError, SyntaxError):
                pass
            else:
                entry["format_verified"] = True
        lines = content.splitlines(keepends=True)
        total = len(lines)
        if entry["status"] in DONE and not args.get("force"):
            self._save()
            return {"path": path, "hash": hash_value, "content": "", "status": entry["status"],
                    "already_complete": True, "total_lines": total, "start_line": 1, "end_line": 0,
                    "next_start_line": None, "truncated": False,
                    "message": "当前 hash 的注释已完成源码读取与静态格式检查，或已应用本任务补丁。静态格式通过不代表说明含义已核对；确需复查原文时使用 force:true。"}
        start = args.get("start_line", entry.get("cursor", 1))
        if start > max(total, 1):
            raise ValueError(f"start_line 超出文件范围，当前共 {total} 行。")
        requested_end = min(args.get("end_line", total), total)
        # An end-only range starts at line one, rather than a persisted cursor.
        if "end_line" in args and "start_line" not in args:
            start = 1
        source_hints = annotation_read_hints(path, content)

        def result(end):
            value = {"path": path, "hash": hash_value, "content": "".join(lines[start - 1:end]),
                     "status": entry["status"], "start_line": start, "end_line": end,
                     "total_lines": total, "next_start_line": end + 1 if end < total else None,
                     "truncated": start > 1 or end < total}
            if entry.get("reason"):
                value["reason"] = entry["reason"]
            if entry.get("format_verified"):
                value["format_verified"] = True
                value["format_note"] = "静态注释格式与覆盖检查通过，仍须阅读真实源码核对说明含义；勿仅因格式完整就认定语义准确。"
            hints = self._hints(source_hints, start, end)
            if hints:
                value["annotation_format"] = hints
            if "start_line" not in args and start > 1:
                value["message"] = "已自动接续未读片段；content 保留原始换行，无行号前缀。需要指定片段时使用 start_line/end_line。"
            return value

        # Measure escaped JSON, not raw source length (quotes/backslashes and
        # CRLF expand). Never split or manufacture part of a physical line.
        low, high, best = start, requested_end, None
        if not total:
            best = result(0)
        while low <= high:
            middle = (low + high) // 2
            candidate = result(middle)
            if encoded_size(candidate) <= PAGE_CHARS - 100:
                best, low = candidate, middle + 1
            else:
                high = middle - 1
        if best is None or encoded_size(best) > PAGE_CHARS:
            reason = f"第 {start} 行的单行文本超过安全观察上限；不能截断源码行，请拆分该行后重试。"
            self._blocked(path, reason)
            self._save()
            return {"path": path, "hash": hash_value, "status": "blocked", "error": reason,
                    "message": "已记录阻塞原因，请继续其他文件，勿重复请求同一超长行。"}
        end = best["end_line"]
        ranges = self._ranges(entry.get("ranges", []), start, end) if total else []
        if ranges != entry.get("ranges", []) or not entry.get("observed"):
            self._advance()
        entry.update(ranges=ranges, observed=True, total_lines=total)
        # Advance to the first uncovered line, not merely the last page end.
        entry["cursor"] = ranges[0][1] + 1 if ranges and ranges[0][0] == 1 else 1
        if entry["cursor"] > total:
            entry["cursor"] = 1
        if entry["status"] == "pending":
            entry["status"] = "reading"
        if entry.get("format_verified") and entry["status"] not in DONE and self.fully_read(path, hash_value):
            entry["status"] = "verified"
            entry.pop("reason", None)
            self._advance()
        best["status"] = entry["status"]
        best["fully_read"] = self.fully_read(path, hash_value)
        self._save()
        return best

    def fully_read(self, path: str, hash_value: str) -> bool:
        entry = self.state["files"].get(path, {})
        if entry.get("hash") != hash_value or not entry.get("observed"):
            return False
        total, ranges = entry.get("total_lines", 0), entry.get("ranges", [])
        return total == 0 or bool(ranges and ranges[0][0] == 1 and ranges[0][1] >= total)

    def applied(self, patch: dict) -> None:
        changes = patch.get("changes", [])
        if isinstance(changes, str):
            changes = json.loads(changes)
        for change in changes:
            path = change.get("path")
            try:
                file = self.workspace.read(path)
            except (ValueError, OSError, TypeError):
                continue
            if file["hash"] != change.get("after_hash"):
                continue
            status = "applied"
            if Path(path).suffix.lower() in {".py", ".pyi"}:
                try:
                    validate_annotation_change(path, file["content"], file["content"])
                except (ValueError, SyntaxError):
                    continue
                status = "verified"
            current = self.state["files"].get(file["path"], {})
            if current.get("status") != status or current.get("hash") != file["hash"]:
                self.state["files"][file["path"]] = {"status": status, "hash": file["hash"], "checked": True,
                                                     "applied_checkpoint": True}
                self._advance()
            self.read_baselines.pop(file["path"], None)
        self._save()

    def observe_existing_patches(self):
        for patch in self.store.rows("SELECT changes FROM patches WHERE task_id=? AND status='applied' ORDER BY created_at",
                                     (self.task_id,)):
            self.applied(patch)

    def reconcile(self, refresh_inventory: bool = False) -> None:
        """Recheck final baselines, optionally refreshing the project once at final."""
        if refresh_inventory:
            self.files = list(self.workspace.files(limit=None))
            present = set(self.files)
            for path in self.files:
                if path not in self.state["files"]:
                    self.state["files"][path] = self._initial(path)
            for path in list(self.state["files"]):
                if path not in present:
                    self._blocked(path, "文件已从可访问项目清单移除；请核对是否在任务运行期间删除或移动。")
        for path, entry in list(self.state["files"].items()):
            if entry.get("status") not in DONE:
                continue
            try:
                current = self.workspace.read(path)
            except (ValueError, OSError) as exc:
                self._blocked(path, str(exc))
                self.read_baselines.pop(path, None)
                continue
            if current["hash"] != entry.get("hash"):
                self.state["files"][path] = self._initial(path)
                self.read_baselines.pop(path, None)
                self._advance()
            elif (entry["status"] == "verified" and not entry.get("applied_checkpoint")
                  and not self.fully_read(path, current["hash"])):
                # Migrate early ledgers that called untouched Python files
                # verified from format alone before delivering their source.
                entry.update(status="reading" if entry.get("observed") else "pending",
                             format_verified=True, checked=True)
                self._advance()
        self._save()

    def snapshot(self) -> dict:
        entries = self.state["files"]
        counts = {status: 0 for status in ("pending", "reading", "verified", "applied", "skipped", "blocked")}
        for entry in entries.values():
            counts[entry["status"]] += 1
        value = {"counts": {"total": len(entries), **counts}, "next_files": [], "blocked": [], "recent_completed": [],
                 "message": "进度来自持久记录。verified 仅表示 Python 注释格式与覆盖静态检查通过，说明语义仍需核对；applied 表示其他语言补丁已应用。优先待办项，勿重复扫描清单。"}
        # Bound every append against the complete snapshot, including escaped
        # long file names. Keep exact paths; never truncate into a fake path.
        def append(key, item):
            value[key].append(item)
            if encoded_size(value) > SNAPSHOT_CHARS:
                value[key].pop()
                return False
            return True

        pending = [(path, entry) for path, entry in entries.items() if entry["status"] in {"pending", "reading"}]
        pending.sort(key=lambda item: (item[1]["status"] != "reading", item[0]))
        for path, entry in pending[:20]:
            fully_read = self.fully_read(path, entry.get("hash"))
            append("next_files", {"path": path, "status": entry["status"], "fully_read": fully_read,
                                  "next_action": "propose_patch" if fully_read else "read",
                                  "next_start_line": None if fully_read else entry.get("cursor", 1)})
        for path, entry in entries.items():
            if entry["status"] == "blocked" and len(value["blocked"]) < 5:
                append("blocked", {"path": path, "reason": entry.get("reason", "无法读取")})
        completed = [(path, entry) for path, entry in entries.items() if entry["status"] in DONE]
        for path, entry in completed[-8:]:
            append("recent_completed", {"path": path, "status": entry["status"], "hash": entry.get("hash")})
        return value

    def token(self) -> str:
        return str(self.state["revision"])

    def block(self, path: str, reason: str) -> None:
        relative = self.workspace.path(path).relative_to(self.workspace.root).as_posix()
        self._blocked(relative, reason)
        self._save()
