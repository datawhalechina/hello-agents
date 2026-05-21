from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, List, Optional

from pydantic import BaseModel

SEARCH_AGENT_ERROR_MESSAGES: dict[str, str] = {
    "search_agent_init_timeout": "检索服务初始化超时，请稍后重试。",
    "search_agent_timeout": "检索超时，请稍后重试或缩短描述。",
    "search_agent_intent_failed": "暂时无法理解检索意图（LLM 不可用或返回异常），请改写为更具体的会议/主题/年份。",
    "search_agent_internal_error": "检索服务内部错误，请查看后端日志或稍后重试。",
    "search_agent_stream_incomplete": "检索流未正常结束，请重试。",
    "search_agent_llm_unavailable": "未配置 LLM，无法解析复杂检索意图；请配置 API Key 或使用更明确的会议+年份查询。",
}


class ToolCallInfo(BaseModel):
    name: str
    status: str
    params: Optional[dict[str, Any]] = None
    result_summary: Optional[str] = None


def user_facing_error_message(code: str) -> str:
    return SEARCH_AGENT_ERROR_MESSAGES.get(code, code or "search_agent_error")


@contextmanager
def track_tool_call(
    tool_calls: List[ToolCallInfo],
    name: str,
    params: Optional[dict[str, Any]] = None,
) -> Iterator[ToolCallInfo]:
    tc = ToolCallInfo(name=name, status="running", params=params)
    tool_calls.append(tc)
    try:
        yield tc
        if tc.status == "running":
            tc.status = "success"
    except Exception as e:
        tc.status = "error"
        if not tc.result_summary:
            tc.result_summary = f"执行失败: {str(e)[:120]}"
        raise


def normalize_tool_calls(tool_calls: List[Any]) -> List[ToolCallInfo]:
    safe_calls: List[ToolCallInfo] = []
    for x in tool_calls:
        if isinstance(x, ToolCallInfo):
            safe_calls.append(x)
        elif isinstance(x, dict):
            try:
                safe_calls.append(ToolCallInfo(**x))
            except Exception:
                safe_calls.append(
                    ToolCallInfo(
                        name="tool_call",
                        status="error",
                        result_summary=str(x)[:200],
                    )
                )
        else:
            safe_calls.append(
                ToolCallInfo(name="tool_call", status="error", result_summary=str(x)[:200])
            )
    return safe_calls


def last_pipeline_tool_error(tool_calls: List[ToolCallInfo]) -> Optional[str]:
    for tc in reversed(tool_calls or []):
        if getattr(tc, "name", None) != "search_pipeline":
            continue
        if getattr(tc, "status", None) != "error":
            continue
        s = (getattr(tc, "result_summary", None) or "").strip()
        return s or "search_pipeline_error"
    return None
