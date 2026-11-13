"""A local, tool-using agent for keeping contribution tasks and evidence in sync."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Callable


TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
STATUSES = {"claimed", "in_progress", "submitted", "under_review", "accepted"}
STATUS_LABELS = {
    "claimed": "已领取",
    "in_progress": "进行中",
    "submitted": "已提交",
    "under_review": "審核中",
    "accepted": "已验收",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def file_fingerprint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"size_bytes": path.stat().st_size, "sha256": digest.hexdigest()}


@dataclass
class ToolResult:
    ok: bool
    message: str
    data: dict[str, Any] | None = None


class LocalMemory:
    """JSON-backed long-term task memory and small conversation state."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir.expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.data_dir / "tasks.json"
        self.session_path = self.data_dir / "session.json"
        self.tasks: dict[str, dict[str, Any]] = self._read(self.state_path, {}).get("tasks", {})
        self.session: dict[str, Any] = self._read(
            self.session_path, {"last_task_id": None, "pending": None}
        )

    @staticmethod
    def _read(path: Path, default: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            return default
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"無法讀取記憶檔 {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"記憶檔格式錯誤：{path}")
        return value

    @staticmethod
    def _atomic_write(path: Path, value: dict[str, Any]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temporary.replace(path)

    def save_tasks(self) -> None:
        self._atomic_write(self.state_path, {"version": 1, "tasks": self.tasks})

    def save_session(self) -> None:
        self._atomic_write(self.session_path, self.session)


class BountyTrailAgent:
    """Rule-based planner that selects from a small, auditable local tool set."""

    def __init__(self, memory: LocalMemory):
        self.memory = memory
        self.tools: dict[str, Callable[..., ToolResult]] = {
            "add_task": self._add_task,
            "start_task": self._start_task,
            "list_tasks": self._list_tasks,
            "attach_artifact": self._attach_artifact,
            "record_pr": self._record_pr,
            "audit_task": self._audit_task,
            "mark_submitted": self._mark_submitted,
            "record_receipt": self._record_receipt,
        }

    def _invoke(self, name: str, **arguments: Any) -> ToolResult:
        result = self.tools[name](**arguments)
        if result.ok:
            task_id = arguments.get("task_id", "")
            if task_id in self.memory.tasks:
                self.memory.session["last_task_id"] = task_id
                self.memory.save_session()
        return result

    def _add_task(self, task_id: str, title: str) -> ToolResult:
        task_id = task_id.strip()
        title = title.strip()
        if not TASK_ID_RE.fullmatch(task_id):
            return ToolResult(False, "任務 ID 請使用英數字、點、底線或連字號。")
        if not title:
            return ToolResult(False, "任務名稱不能空白。")
        if task_id in self.memory.tasks:
            return ToolResult(False, f"{task_id} 已存在；為避免覆蓋紀錄，沒有重複建立。")
        self.memory.tasks[task_id] = {
            "task_id": task_id,
            "title": title,
            "status": "claimed",
            "artifacts": [],
            "pr_url": None,
            "receipt_url": None,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "events": [{"at": now_iso(), "action": "created"}],
        }
        self.memory.save_tasks()
        return ToolResult(True, f"已記錄 {task_id}「{title}」，狀態：已領取。")

    def _list_tasks(self, status: str | None = None) -> ToolResult:
        records = list(self.memory.tasks.values())
        if status:
            if status not in STATUSES:
                return ToolResult(False, "狀態可用：claimed、in_progress、submitted、under_review、accepted。")
            records = [item for item in records if item["status"] == status]
        records.sort(key=lambda item: item["updated_at"], reverse=True)
        if not records:
            return ToolResult(True, "目前沒有符合條件的任務。", {"count": 0})
        lines = [
            f"{item['task_id']}｜{STATUS_LABELS[item['status']]}｜{item['title']}"
            for item in records
        ]
        return ToolResult(True, "\n".join(lines), {"count": len(records)})

    def _start_task(self, task_id: str) -> ToolResult:
        record = self._find_task(task_id)
        if not record:
            return ToolResult(False, f"找不到任務 {task_id}，請先新增。")
        record["status"] = "in_progress"
        self._touch(record, "work_started")
        self.memory.save_tasks()
        return ToolResult(True, f"{task_id} 已標記為「進行中」。")

    def _find_task(self, task_id: str) -> dict[str, Any] | None:
        return self.memory.tasks.get(task_id.strip())

    @staticmethod
    def _touch(record: dict[str, Any], action: str) -> None:
        record["updated_at"] = now_iso()
        record["events"].append({"at": record["updated_at"], "action": action})

    def _attach_artifact(self, task_id: str, file_path: str) -> ToolResult:
        record = self._find_task(task_id)
        if not record:
            return ToolResult(False, f"找不到任務 {task_id}，請先新增。")
        path = Path(file_path.strip().strip('"')).expanduser()
        try:
            path = path.resolve(strict=True)
        except OSError as exc:
            return ToolResult(False, f"找不到交付檔：{exc}")
        if not path.is_file():
            return ToolResult(False, "交付路徑必須指向一個檔案。")
        fingerprint = file_fingerprint(path)
        artifact = {
            "path": str(path),
            **fingerprint,
            "attached_at": now_iso(),
        }
        record["artifacts"] = [
            old for old in record["artifacts"] if old["path"] != str(path)
        ] + [artifact]
        self._touch(record, "artifact_attached")
        self.memory.save_tasks()
        return ToolResult(
            True,
            f"已關聯交付檔 {path.name}（{fingerprint['size_bytes']} bytes，SHA-256 已記錄）。",
        )

    def _record_pr(self, task_id: str, url: str) -> ToolResult:
        record = self._find_task(task_id)
        if not record:
            return ToolResult(False, f"找不到任務 {task_id}，請先新增。")
        parsed = urlparse(url.strip())
        if parsed.scheme != "https" or parsed.hostname != "github.com" or not re.search(
            r"/pull/\d+/?$", parsed.path
        ):
            return ToolResult(False, "請提供 HTTPS GitHub Pull Request 連結，例如 https://github.com/org/repo/pull/12。")
        record["pr_url"] = url.strip()
        self._touch(record, "pr_recorded")
        self.memory.save_tasks()
        return ToolResult(True, f"已記錄 PR：{url.strip()}")

    def _audit_task(self, task_id: str) -> ToolResult:
        record = self._find_task(task_id)
        if not record:
            return ToolResult(False, f"找不到任務 {task_id}，請先新增。")
        problems: list[str] = []
        if not record["artifacts"]:
            problems.append("尚未關聯交付檔")
        for artifact in record["artifacts"]:
            path = Path(artifact["path"])
            if not path.is_file():
                problems.append(f"交付檔不存在：{path.name}")
                continue
            current = file_fingerprint(path)
            if current["sha256"] != artifact["sha256"]:
                problems.append(f"交付檔已變更，請重新關聯：{path.name}")
        if not record["pr_url"]:
            problems.append("尚未記錄 GitHub PR")
        if problems:
            return ToolResult(False, "提交前檢查未通過：\n- " + "\n- ".join(problems), {"ready": False})
        names = ", ".join(Path(item["path"]).name for item in record["artifacts"])
        return ToolResult(
            True,
            f"{task_id} 提交資料齊全：交付檔 {names}；PR 已記錄。",
            {"ready": True},
        )

    def _mark_submitted(self, task_id: str) -> ToolResult:
        record = self._find_task(task_id)
        if not record:
            return ToolResult(False, f"找不到任務 {task_id}，請先新增。")
        audit = self._audit_task(task_id)
        if not audit.ok:
            return audit
        record["status"] = "submitted"
        self._touch(record, "marked_submitted_locally")
        self.memory.save_tasks()
        return ToolResult(True, f"本機紀錄已標為「已提交」。這不會替你操作任何外部平台。")

    def _record_receipt(self, task_id: str, url: str) -> ToolResult:
        record = self._find_task(task_id)
        if not record:
            return ToolResult(False, f"找不到任務 {task_id}，請先新增。")
        parsed = urlparse(url.strip())
        if (
            parsed.scheme != "https"
            or parsed.hostname != "contributor.datawhale.cn"
            or not re.search(r"/tasks/\d+/?$", parsed.path)
        ):
            return ToolResult(False, "請提供 Datawhale 任務回執頁，例如 https://contributor.datawhale.cn/tasks/119。")
        record["receipt_url"] = url.strip()
        record["status"] = "under_review"
        self._touch(record, "platform_receipt_recorded")
        self.memory.save_tasks()
        return ToolResult(True, f"已記錄平台回執；狀態更新為「審核中」：{url.strip()}")

    def handle(self, message: str) -> ToolResult:
        text = message.strip()
        if not text:
            return ToolResult(False, "請輸入指令；輸入 /help 查看範例。")

        pending = self.memory.session.get("pending")
        if pending == "add_task":
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                return ToolResult(False, "請接著輸入「任務 ID 任務名稱」，例如：E58 一對一溝通準備。")
            self.memory.session["pending"] = None
            self.memory.save_session()
            return self._invoke("add_task", task_id=parts[0], title=parts[1])

        if re.fullmatch(r"/(?:help|帮助)|幫助|帮助", text, re.IGNORECASE):
            return ToolResult(True, self.help_text())

        add_match = re.match(r"^(?:/add|新增(?:任務|任务)?)(?:\s+(.*))?$", text, re.IGNORECASE)
        if add_match:
            payload = (add_match.group(1) or "").strip()
            parts = payload.split(maxsplit=1)
            if len(parts) < 2:
                self.memory.session["pending"] = "add_task"
                self.memory.save_session()
                return ToolResult(True, "好，請回覆任務 ID 和名稱，例如：E58 一對一溝通準備。")
            return self._invoke("add_task", task_id=parts[0], title=parts[1])

        start_match = re.match(r"^(?:/start|開始|开始)\s+(\S+)$", text, re.IGNORECASE)
        if start_match:
            return self._invoke("start_task", task_id=start_match.group(1))

        list_match = re.match(r"^(?:/list|列表|待辦)(?:\s+(\w+))?$", text, re.IGNORECASE)
        if list_match:
            return self._invoke("list_tasks", status=list_match.group(1))

        attach_match = re.match(r"^(?:/attach|關聯(?:交付檔|交付物)?|附檔)\s+(\S+)\s+(.+)$", text, re.IGNORECASE)
        if attach_match:
            return self._invoke(
                "attach_artifact", task_id=attach_match.group(1), file_path=attach_match.group(2)
            )

        pr_match = re.match(r"^(?:/pr|記錄PR|記錄 PR)\s+(\S+)\s+(https://\S+)$", text, re.IGNORECASE)
        if pr_match:
            return self._invoke("record_pr", task_id=pr_match.group(1), url=pr_match.group(2))

        check_match = re.match(r"^(?:/check|檢查|检查)(?:\s+(\S+))?$", text, re.IGNORECASE)
        if check_match:
            task_id = check_match.group(1) or self.memory.session.get("last_task_id")
            if not task_id:
                return ToolResult(False, "請提供任務 ID，或先查詢一項任務。")
            return self._invoke("audit_task", task_id=task_id)

        submit_match = re.match(r"^(?:/submit|標記已提交|標记已提交|提交)(?:\s+(\S+))?$", text, re.IGNORECASE)
        if submit_match:
            task_id = submit_match.group(1) or self.memory.session.get("last_task_id")
            if not task_id:
                return ToolResult(False, "請提供任務 ID，或先查詢一項任務。")
            return self._invoke("mark_submitted", task_id=task_id)

        receipt_match = re.match(r"^(?:/receipt|回執|回执)\s+(\S+)\s+(https://\S+)$", text, re.IGNORECASE)
        if receipt_match:
            return self._invoke(
                "record_receipt", task_id=receipt_match.group(1), url=receipt_match.group(2)
            )

        record = self._find_task(text)
        if record:
            self.memory.session["last_task_id"] = text
            self.memory.save_session()
            return ToolResult(
                True,
                f"{record['task_id']}｜{STATUS_LABELS[record['status']]}｜{record['title']}\n"
                f"交付檔 {len(record['artifacts'])} 個｜PR {'已記錄' if record['pr_url'] else '未記錄'}｜"
                f"回執 {'已記錄' if record['receipt_url'] else '未記錄'}",
            )
        return ToolResult(False, "我不確定要做什麼。輸入 /help 查看可用指令。")

    @staticmethod
    def help_text() -> str:
        return """可用指令（資料只保存在本機）：
  新增 E58 一對一溝通準備       建立任務；也可先輸入「新增」再於下一輪補上資料
  開始 E58                     將任務標記為進行中
  列表 [under_review]          列出全部任務或篩選狀態
  關聯 E58 C:\\path\\交付.zip   計算並記錄 SHA-256，不解析或上傳檔案內容
  記錄PR E58 https://github.com/org/repo/pull/12
  檢查 E58                     檢查檔案是否存在/變更、PR 是否已記錄
  提交 E58                     僅更新本機狀態；不會送出平台表單
  回執 E58 https://contributor.datawhale.cn/tasks/119
  E58                          查詢任務；「檢查」可沿用最近查詢的任務 ID
  列表、/help、/quit"""


def run_demo() -> int:
    with tempfile.TemporaryDirectory(prefix="bounty-trail-demo-") as temporary:
        root = Path(temporary)
        asset = root / "sample-deliverable.md"
        asset.write_text("虛構範例：本機交付物，用於展示檔案檢查。\n", encoding="utf-8")
        agent = BountyTrailAgent(LocalMemory(root / "memory"))
        messages = [
            "/add",
            "DEMO-119 任務追蹤小工具示範",
            f"/attach DEMO-119 {asset}",
            "/pr DEMO-119 https://github.com/example/hello-agents/pull/1",
            "/check DEMO-119",
            "/submit DEMO-119",
            "/receipt DEMO-119 https://contributor.datawhale.cn/tasks/119",
        ]
        for message in messages:
            print(f"你：{message}")
            result = agent.handle(message)
            print(f"Agent：{result.message}")
            if not result.ok:
                return 1
        resumed = BountyTrailAgent(LocalMemory(root / "memory")).handle("DEMO-119")
        print(f"\n重新啟動後查詢：{resumed.message}")
        print("\n示範完成：記憶檔建立於暫存目錄，結束後自動清除。")
    return 0


def run_chat(data_dir: Path) -> int:
    try:
        agent = BountyTrailAgent(LocalMemory(data_dir))
    except (OSError, ValueError) as exc:
        print(f"無法啟動：{exc}", file=sys.stderr)
        return 1
    print("BountyTrailAgent 已啟動。輸入 /help 查看指令，/quit 結束。")
    print(f"本機記憶位置：{agent.memory.data_dir}")
    while True:
        try:
            message = input("你：")
        except (EOFError, KeyboardInterrupt):
            print("\n已結束。")
            break
        if message.strip().lower() in {"/quit", "quit", "exit", "退出"}:
            print("已結束。")
            break
        result = agent.handle(message)
        print(f"Agent：{result.message}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="在本機追蹤貢獻任務、交付檔與 PR。")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path.home() / ".bounty-trail-agent",
        help="本機記憶目錄（預設 ~/.bounty-trail-agent）",
    )
    parser.add_argument("command", nargs="?", choices={"chat", "demo", "list"}, default="chat")
    args = parser.parse_args()
    if args.command == "demo":
        return run_demo()
    if args.command == "list":
        try:
            result = BountyTrailAgent(LocalMemory(args.data_dir)).handle("列表")
        except (OSError, ValueError) as exc:
            print(f"無法讀取記憶：{exc}", file=sys.stderr)
            return 1
        print(result.message)
        return 0
    return run_chat(args.data_dir)


if __name__ == "__main__":
    raise SystemExit(main())
