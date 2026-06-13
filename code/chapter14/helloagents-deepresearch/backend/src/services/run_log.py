"""Run-level JSON logging for low-cost replay and debugging."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any


logger = logging.getLogger(__name__)
RUN_LOG_SCHEMA_VERSION = 2
PRIVACY_NOTICE = (
    "Raw user input, prompts, and tool inputs are omitted. LLM responses, "
    "parsed outputs, search results, and final answers may still echo user data."
)


def summarize_sensitive_payload(payload: Any) -> dict[str, Any]:
    """Return a stable length/hash summary without retaining the raw payload."""

    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return {
        "length": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


class RunLogger:
    """Append-only in-memory run trace that flushes to one JSON file."""

    def __init__(self, *, run_id: str, log_dir: str | Path, user_input: str) -> None:
        self.run_id = run_id
        self.log_dir = Path(log_dir)
        self.path = self.log_dir / f"run_{run_id}.json"
        self._lock = Lock()
        self.enabled = True
        self.payload: dict[str, Any] = {
            "schema_version": RUN_LOG_SCHEMA_VERSION,
            "privacy_notice": PRIVACY_NOTICE,
            "run_id": run_id,
            "user_input": summarize_sensitive_payload(user_input),
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
            message_summary = summarize_sensitive_payload(messages)
            tools_summary = summarize_sensitive_payload(tools or [])
            self.payload["messages"].append(
                {
                    "index": index,
                    "operation": operation,
                    "request_hash": request_hash,
                    "messages": message_summary,
                    "tools": tools_summary,
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
            self._flush_locked()

    def record_tool_result(
        self,
        *,
        tool_name: str,
        input_payload: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        with self._lock:
            input_summary = summarize_sensitive_payload(input_payload)
            self.payload["tool_result"].append(
                {
                    "index": len(self.payload["tool_result"]),
                    "tool_name": tool_name,
                    "input": input_summary,
                    "input_hash": input_summary["sha256"],
                    "result": result,
                }
            )
            self._flush_locked()

    def set_final_answer(self, final_answer: str) -> None:
        with self._lock:
            self.payload["final_answer"] = final_answer
            self._flush_locked()

    def set_error(self, error: BaseException | str) -> None:
        with self._lock:
            self.payload["error"] = str(error)
            self._flush_locked()

    def flush(self) -> None:
        with self._lock:
            self._flush_locked()

    def _flush_locked(self) -> None:
        if not self.enabled:
            return

        temp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            temp_path.write_text(
                json.dumps(self.payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_path.replace(self.path)
        except OSError as exc:
            self.enabled = False
            logger.warning("Run logging disabled for %s: %s", self.run_id, exc)
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def load_run_log(path: str | Path) -> dict[str, Any]:
    """Load a run log JSON file."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid run log: {path}")
    return payload
