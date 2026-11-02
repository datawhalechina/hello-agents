"""结果落盘与导出（FR-10、6.5）。

所有写操作均“尽力而为”：失败只记录日志并返回 False，不影响主流程与接口返回。
目录结构见需求文档 6.5 节：

``outputs/runs/<run_id>/{request.json, trace.jsonl, draft_vN.md, review_vN.json,
result.json, final.md}``
"""

from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .logging_utils import append_jsonl, get_logger
from .models import GenerationResult, StoryRequest

logger = get_logger("storage")

RUN_ID_PATTERN = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{4}$")


class RunStorage:
    """负责运行目录的创建、写入、读取与清理。"""

    def __init__(self, output_dir: Path | str) -> None:
        """初始化存储。

        Args:
            output_dir: 结果根目录，通常是 ``outputs``。
        """
        self.output_dir = Path(output_dir)
        self.runs_dir = self.output_dir / "runs"

    def new_run_id(self) -> str:
        """生成 ``YYYYMMDD-HHMMSS-<4位随机>`` 格式的运行 ID。"""
        return f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"

    def run_dir(self, run_id: str) -> Path:
        """返回运行目录，并校验 run_id 防止路径穿越。

        Args:
            run_id: 运行 ID。

        Returns:
            运行目录路径。

        Raises:
            ValueError: run_id 格式非法。
        """
        if not RUN_ID_PATTERN.match(run_id or ""):
            raise ValueError(f"非法的 run_id：{run_id!r}")
        return self.runs_dir / run_id

    def prepare_run(self, run_id: str, request: StoryRequest) -> Path:
        """创建运行目录并写入 request.json 与空的 trace.jsonl。"""
        try:
            directory = self.run_dir(run_id)
            directory.mkdir(parents=True, exist_ok=True)
            self._write_json(directory / "request.json", request.model_dump(mode="json"))
            (directory / "trace.jsonl").touch(exist_ok=True)
            return directory
        except (OSError, ValueError) as exc:  # pragma: no cover - 依赖文件系统
            logger.warning("创建运行目录失败 %s: %s", run_id, exc)
            return self.runs_dir / str(run_id)

    def save_draft(self, run_id: str, round_no: int, text: str) -> bool:
        """保存第 N 轮草稿为 ``draft_vN.md``。"""
        return self._write_text(self._path(run_id, f"draft_v{round_no}.md"), text)

    def save_review(self, run_id: str, round_no: int, payload: dict[str, Any]) -> bool:
        """保存第 N 轮审稿原始输出与解析结果。"""
        return self._write_json(
            self._path(run_id, f"review_v{round_no}.json"), payload
        )

    def append_trace(self, run_id: str, payload: dict[str, Any]) -> bool:
        """向 ``trace.jsonl`` 追加一轮追踪记录。"""
        try:
            return append_jsonl(self.run_dir(run_id) / "trace.jsonl", payload)
        except ValueError:
            return False

    def save_result(self, run_id: str, result: GenerationResult) -> bool:
        """保存最终 ``result.json``。"""
        return self._write_json(
            self._path(run_id, "result.json"), result.model_dump(mode="json")
        )

    def save_final(self, run_id: str, result: GenerationResult) -> bool:
        """保存导出用 ``final.md``（含标题与元信息）。"""
        header = [
            f"# 智能故事生成器 · {result.request.genre.label}",
            "",
            f"> 运行 ID：{result.run_id}  ",
            f"> 状态：{result.status.value}  ",
            f"> 采用轮次：{result.best_round if result.best_round is not None else '-'}  ",
            f"> 模型：{result.model or '未记录'}  ",
            f"> 生成时间：{result.created_at:%Y-%m-%d %H:%M:%S}",
            "",
            "---",
            "",
            result.final_text or "（无正文）",
            "",
        ]
        return self._write_text(self._path(run_id, "final.md"), "\n".join(header))

    def finalize(self, run_id: str, result: GenerationResult) -> None:
        """一次性写入 result.json 与 final.md，并按保留策略清理历史。"""
        self.save_result(run_id, result)
        self.save_final(run_id, result)

    def load_result(self, run_id: str) -> dict[str, Any] | None:
        """读取指定运行的 ``result.json``。"""
        try:
            path = self.run_dir(run_id) / "result.json"
        except ValueError:
            return None
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover
            logger.warning("读取结果失败 %s: %s", run_id, exc)
            return None

    def final_markdown_path(self, run_id: str) -> Path | None:
        """返回 ``final.md`` 路径（不存在时返回 None）。"""
        try:
            path = self.run_dir(run_id) / "final.md"
        except ValueError:
            return None
        return path if path.exists() else None

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        """列出历史运行摘要（按时间倒序）。"""
        if not self.runs_dir.exists():
            return []
        summaries: list[dict[str, Any]] = []
        for directory in self.runs_dir.iterdir():
            if not directory.is_dir():
                continue
            payload = self.load_result(directory.name)
            if not payload:
                continue
            request = payload.get("request") or {}
            rounds = payload.get("rounds") or []
            best_round = payload.get("best_round")
            score = 0
            if isinstance(best_round, int) and 0 < best_round <= len(rounds):
                score = int(rounds[best_round - 1].get("overall_score", 0) or 0)
            summaries.append(
                {
                    "run_id": payload.get("run_id", directory.name),
                    "status": payload.get("status", ""),
                    "genre": request.get("genre", ""),
                    "prompt": (request.get("prompt") or "")[:80],
                    "best_round": best_round,
                    "overall_score": score,
                    "rounds": len(rounds),
                    "created_at": payload.get("created_at", ""),
                }
            )
        summaries.sort(
            key=lambda item: (str(item.get("created_at", "")), item["run_id"]),
            reverse=True,
        )
        return summaries[: max(1, limit)]

    def cleanup(self, keep: int = 50) -> int:
        """按修改时间保留最近 N 次运行，删除更早的目录。"""
        if keep <= 0 or not self.runs_dir.exists():
            return 0
        directories = [item for item in self.runs_dir.iterdir() if item.is_dir()]
        directories.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        removed = 0
        for directory in directories[keep:]:
            try:
                shutil.rmtree(directory)
                removed += 1
            except OSError as exc:  # pragma: no cover
                logger.warning("清理旧运行目录失败 %s: %s", directory, exc)
        return removed

    def _path(self, run_id: str, filename: str) -> Path:
        """拼接运行目录下的文件路径（静默兜底）。"""
        try:
            return self.run_dir(run_id) / filename
        except ValueError:
            return self.runs_dir / str(run_id) / filename

    @staticmethod
    def _write_text(path: Path, content: str) -> bool:
        """写文本文件，失败返回 False。"""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content or "", encoding="utf-8")
            return True
        except OSError as exc:  # pragma: no cover
            logger.warning("写入文件失败 %s: %s", path, exc)
            return False

    def _write_json(self, path: Path, payload: Any) -> bool:
        """写 JSON 文件，失败返回 False。"""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            return True
        except (OSError, TypeError) as exc:  # pragma: no cover
            logger.warning("写入 JSON 失败 %s: %s", path, exc)
            return False

