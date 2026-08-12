"""
饮食流水线统一错误码（便于 Observability / failure mode 统计）。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class DietErrorCode(str, Enum):
    LLM_PARSE_ERROR = "LLM_PARSE_ERROR"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    TOOL_ERROR = "TOOL_ERROR"
    STAGE_ABORTED = "STAGE_ABORTED"
    DEGRADED_FALLBACK = "DEGRADED_FALLBACK"


def diet_error_record(
    stage: str,
    code: DietErrorCode | str,
    message: str,
    *,
    attempt: Optional[int] = None,
    detail: Any = None,
) -> Dict[str, Any]:
    rec: Dict[str, Any] = {
        "stage": stage,
        "code": str(code),
        "message": message,
    }
    if attempt is not None:
        rec["attempt"] = attempt
    if detail is not None:
        rec["detail"] = detail
    return rec
