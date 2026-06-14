"""Run-level JSON logging for low-cost replay and debugging."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any


logger = logging.getLogger(__name__)
RUN_LOG_SCHEMA_VERSION = 3
RUN_LOG_LEVELS = ("metadata", "full", "off")
METADATA_PRIVACY_NOTICE = (
    "Sensitive run content is omitted. User input, prompts, tool inputs, LLM "
    "responses, parsed outputs, tool results, final answers, and errors are stored "
    "only as length and SHA-256 summaries."
)
FULL_PRIVACY_NOTICE = (
    "WARNING: Full replay content is enabled. LLM responses, parsed outputs, tool "
    "results, final answers, and errors may contain sensitive user data."
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

    def __init__(
        self,
        *,
        run_id: str,
        log_dir: str | Path,
        user_input: str,
        level: str = "metadata",
    ) -> None:
        if level not in RUN_LOG_LEVELS:
            raise ValueError(
                f"Unsupported run log level: {level}. "
                f"Expected one of: {', '.join(RUN_LOG_LEVELS)}"
            )
        self.run_id = run_id
        self.log_dir = Path(log_dir)
        self.path = self.log_dir / f"run_{run_id}.json"
        self.level = level
        self._lock = Lock()
        self.enabled = level != "off"
        self.payload: dict[str, Any] = {
            "schema_version": RUN_LOG_SCHEMA_VERSION,
            "log_level": level,
            "privacy_notice": (
                FULL_PRIVACY_NOTICE if level == "full" else METADATA_PRIVACY_NOTICE
            ),
            "run_id": run_id,
            "user_input": summarize_sensitive_payload(user_input),
            "messages": [],
            "llm_response": [],
            "parsed_action": [],
            "tool_result": [],
            "final_answer": None,
            "error": None,
        }
        if self.enabled:
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
            response_payload = (
                response
                if self.level == "full"
                else {
                    "model": str(response.get("model") or "unknown"),
                    "usage": dict(response.get("usage") or {}),
                    "latency_ms": int(response.get("latency_ms") or 0),
                    "response": summarize_sensitive_payload(response),
                }
            )
            parsed_payload = (
                parsed_action
                if self.level == "full"
                else {"parsed_action": summarize_sensitive_payload(parsed_action)}
            )
            self.payload["llm_response"].append(
                {
                    "index": index,
                    "operation": operation,
                    "request_hash": request_hash,
                    **response_payload,
                }
            )
            self.payload["parsed_action"].append(
                {
                    "index": index,
                    "operation": operation,
                    "request_hash": request_hash,
                    **parsed_payload,
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
                    "result": (
                        result
                        if self.level == "full"
                        else summarize_sensitive_payload(result)
                    ),
                }
            )
            self._flush_locked()

    def set_final_answer(self, final_answer: str) -> None:
        with self._lock:
            self.payload["final_answer"] = (
                final_answer
                if self.level == "full"
                else summarize_sensitive_payload(final_answer)
            )
            self._flush_locked()

    def set_error(self, error: BaseException | str) -> None:
        with self._lock:
            error_text = str(error)
            self.payload["error"] = (
                error_text
                if self.level == "full"
                else {
                    "type": type(error).__name__ if isinstance(error, BaseException) else "error",
                    **summarize_sensitive_payload(error_text),
                }
            )
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


def load_run_log(
    path: str | Path,
    *,
    require_replay: bool = False,
) -> dict[str, Any]:
    """Load a run log JSON file."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid run log: {path}")
    if require_replay:
        schema_version = payload.get("schema_version")
        log_level = payload.get("log_level")
        if schema_version == 2:
            return payload
        if schema_version == RUN_LOG_SCHEMA_VERSION and log_level == "full":
            return payload
        raise ValueError(
            "Replay requires a schema v2 log or a schema v3 log created with "
            "LLM_RUN_LOG_LEVEL=full"
        )
    return payload
