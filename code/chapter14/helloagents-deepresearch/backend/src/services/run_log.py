"""Run-level JSON logging for low-cost replay and debugging."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


class RunLogger:
    """Append-only in-memory run trace that flushes to one JSON file."""

    def __init__(self, *, run_id: str, log_dir: str | Path, user_input: str) -> None:
        self.run_id = run_id
        self.log_dir = Path(log_dir)
        self.path = self.log_dir / f"run_{run_id}.json"
        self._lock = Lock()
        self.payload: dict[str, Any] = {
            "run_id": run_id,
            "user_input": user_input,
            "messages": [],
            "llm_response": [],
            "parsed_action": [],
            "tool_result": [],
            "final_answer": None,
            "error": None,
        }
        self.flush()

    def record_llm(
        self,
        *,
        operation: str,
        request_hash: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        response: dict[str, Any],
        parsed_action: dict[str, Any],
    ) -> None:
        with self._lock:
            index = len(self.payload["llm_response"])
            self.payload["messages"].append(
                {
                    "index": index,
                    "operation": operation,
                    "request_hash": request_hash,
                    "messages": messages,
                    "tools": tools or [],
                }
            )
            self.payload["llm_response"].append(
                {
                    "index": index,
                    "operation": operation,
                    "request_hash": request_hash,
                    **response,
                }
            )
            self.payload["parsed_action"].append(
                {
                    "index": index,
                    "operation": operation,
                    "request_hash": request_hash,
                    **parsed_action,
                }
            )
        self.flush()

    def record_tool_result(
        self,
        *,
        tool_name: str,
        input_payload: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        with self._lock:
            self.payload["tool_result"].append(
                {
                    "index": len(self.payload["tool_result"]),
                    "tool_name": tool_name,
                    "input": input_payload,
                    "result": result,
                }
            )
        self.flush()

    def set_final_answer(self, final_answer: str) -> None:
        with self._lock:
            self.payload["final_answer"] = final_answer
        self.flush()

    def set_error(self, error: BaseException | str) -> None:
        with self._lock:
            self.payload["error"] = str(error)
        self.flush()

    def flush(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def load_run_log(path: str | Path) -> dict[str, Any]:
    """Load a run log JSON file."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid run log: {path}")
    return payload
