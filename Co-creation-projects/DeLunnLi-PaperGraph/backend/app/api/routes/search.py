from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

import anyio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ...agents.search_agent import SearchAgent, SearchIntent, get_search_agent
from ...api.dependencies import get_searcher
from ...api.search_route_support import (
    ToolCallInfo,
    last_pipeline_tool_error,
    normalize_tool_calls,
    track_tool_call,
    user_facing_error_message,
)
from ...models.schemas import Paper
from ...services.papers.papers_converters import litpapers_to_api_papers
from ...services.retrieval.search_plan import ResolvedSearchPlan
from ...services.retrieval.search_pipeline import run_search_pipeline_async
from ..tool_events import ToolCallTracker, sse_pack

router = APIRouter(prefix="/papers", tags=["智能搜索"])
logger = logging.getLogger(__name__)

_SSE_QUEUE_SIZE = 128
_SEARCH_AGENT_WALL_SEC = max(
    120.0,
    min(900.0, float(os.getenv("PAPERGRAPH_SEARCH_AGENT_WALL_SEC") or 420.0)),
)
_SEARCH_AGENT_INIT_SEC = 25.0
_PREFIX_CONFLICT_MARKER = "为您找到"


class SearchAgentMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="用户搜索需求")
    mode: str = Field(default="accuracy", description="accuracy=准确性优先, novelty=新颖性优先")
    use_tavily: bool = Field(default=False, description="是否使用 Tavily 预搜索")
    history: List[Dict[str, str]] = Field(default_factory=list, description="对话历史")


class SearchAgentResponse(BaseModel):
    success: bool
    response: str
    search_params: Optional[Dict[str, Any]] = None
    tool_calls: List[ToolCallInfo] = Field(default_factory=list)
    papers: List[Paper] = Field(default_factory=list)
    total: int = 0
    message: Optional[str] = None


def _search_params_from_intent(intent: SearchIntent, **extra: Any) -> Dict[str, Any]:
    yf, yt = intent.year_from, intent.year_to
    if isinstance(yf, int) and isinstance(yt, int) and yf > yt:
        yf, yt = yt, yf
    out: Dict[str, Any] = {
        "query": intent.query,
        "keywords": intent.keywords,
        "authors": getattr(intent, "authors", []) or [],
        "arxiv_id_list": getattr(intent, "arxiv_id_list", []) or [],
        "venues": intent.venues,
        "year_from": yf,
        "year_to": yt,
        "sort": intent.sort,
        "use_llm_rank": intent.use_llm_rank,
        "rerank_recall_max": intent.rerank_recall_max,
        "ranking_rationale": intent.ranking_rationale or None,
    }
    out.update(extra)
    return out


def _generate_suggestions(intent: SearchIntent, papers: List[Paper]) -> List[str]:
    if len(papers) < 5:
        return [f"扩大搜索：尝试「{intent.query}」而不限定会议"]
    return []


def _strip_conflicting_search_summary_prefix(text: str) -> str:
    t = (text or "").strip()
    if not t or _PREFIX_CONFLICT_MARKER not in t:
        return t
    return t[: t.find(_PREFIX_CONFLICT_MARKER)].rstrip()


def _explanation_with_suggestions(
    agent: SearchAgent,
    intent: SearchIntent,
    papers: List[Paper],
    profile_mode: str,
    *,
    prefix_plain: str = "",
) -> str:
    base = _strip_conflicting_search_summary_prefix((prefix_plain or "").strip())
    expl = agent.explain_results(intent, papers, profile_mode)
    explanation = base + "\n\n---\n\n" + expl if (papers and base) else (base or expl)
    if papers:
        sug = _generate_suggestions(intent, papers)
        if sug:
            explanation += "\n\n🔍 **您可以这样优化**：\n" + "".join(
                f"{i}. {s}\n" for i, s in enumerate(sug, 1)
            )
    return explanation


def _error_response(msg: str) -> SearchAgentResponse:
    return SearchAgentResponse(
        success=False,
        response=user_facing_error_message(msg),
        message=msg,
    )


async def _prepare_agent_and_query(request: SearchAgentMessage) -> tuple[SearchAgent, str]:
    try:
        with anyio.fail_after(_SEARCH_AGENT_INIT_SEC):
            agent = await anyio.to_thread.run_sync(get_search_agent)
    except TimeoutError as exc:
        logger.warning("search-agent init timeout after %.0fs", _SEARCH_AGENT_INIT_SEC, exc_info=exc)
        raise HTTPException(status_code=504, detail="search_agent_init_timeout") from exc
    return agent, (request.message or "").strip()


async def _run_search_agent_core(
    *,
    agent: SearchAgent,
    request: SearchAgentMessage,
    merged_query: str,
    searcher: Any,
) -> SearchAgentResponse:
    tool_calls: List[ToolCallInfo] = []

    intent = agent.understand_intent(merged_query, request.mode)
    with track_tool_call(tool_calls, "understand_intent", {"query": merged_query}) as tc:
        tc.result_summary = f"sort={intent.sort}, venues={intent.venues}, yf={intent.year_from}, kw={intent.keywords}"

    plan = ResolvedSearchPlan.from_search_intent(intent)
    with track_tool_call(tool_calls, "search_pipeline", {"query": intent.query or merged_query}) as tc:
        tc.result_summary = "intent→SearchPlan→pipeline"
        mr = int(getattr(plan, "max_results", None) or intent.max_results or 10)
        pip = await run_search_pipeline_async(searcher=searcher, plan=plan, max_results=mr)
        tc.result_summary = f"ranked={len(pip.ranked or [])}"

    papers = litpapers_to_api_papers(rp.paper for rp in (pip.ranked or []))
    prefix = f"为您找到 {len(papers)} 篇论文。" if papers else "未找到相关论文。"

    pipeline_err = last_pipeline_tool_error(tool_calls)
    if not papers and pipeline_err:
        body = (
            "主检索未成功返回论文（多源召回或精排阶段出错），与「数据库里确实没有匹配文献」不同。\n\n"
            f"**错误摘要**：{pipeline_err}\n\n"
            "建议稍后重试，或略微改写查询；若频繁出现请查看服务端日志。"
        )
        return SearchAgentResponse(
            success=False,
            response=body,
            search_params=_search_params_from_intent(intent, mode=request.mode),
            tool_calls=normalize_tool_calls(tool_calls),
            papers=[],
            total=0,
            message="search_pipeline_error",
        )

    body = _explanation_with_suggestions(agent, intent, papers, request.mode, prefix_plain=prefix)
    return SearchAgentResponse(
        success=True,
        response=body,
        search_params=_search_params_from_intent(intent, mode=request.mode),
        tool_calls=normalize_tool_calls(tool_calls),
        papers=papers,
        total=len(papers),
    )


async def _search_agent_impl(request: SearchAgentMessage, searcher: Any):
    try:
        agent, merged_query = await _prepare_agent_and_query(request)
        resp = await asyncio.wait_for(
            _run_search_agent_core(
                agent=agent,
                request=request,
                merged_query=merged_query,
                searcher=searcher,
            ),
            timeout=_SEARCH_AGENT_WALL_SEC,
        )
        return resp, None
    except asyncio.TimeoutError as exc:
        logger.warning("search-agent timeout after %.0fs", _SEARCH_AGENT_WALL_SEC, exc_info=exc)
        return _error_response("search_agent_timeout"), HTTPException(status_code=504, detail="search_agent_timeout")
    except HTTPException as e:
        return _error_response(str(e.detail or "search_agent_http_error")), e
    except Exception:
        logger.exception("search-agent unexpected failure")
        return _error_response("search_agent_internal_error"), None


@router.post("/search-agent/stream")
async def search_agent_chat_stream(
    request: SearchAgentMessage,
    searcher=Depends(get_searcher),
):
    async def gen():
        send, recv = anyio.create_memory_object_stream(_SSE_QUEUE_SIZE)
        tracker = ToolCallTracker(sink=lambda ev: send.send_nowait(ev))
        tracker.emit("status", {"message": "search-agent 已接入，开始处理"})

        async def run_once() -> SearchAgentResponse:
            tracker.emit("status", {"message": f"初始化 SearchAgent（mode={request.mode})"})
            t0 = time.time()
            tracker.emit("status", {"message": "正在检索论文…"})
            resp, exc = await _search_agent_impl(request, searcher)
            if exc:
                code = (
                    str(exc.detail or "search_agent_http_error")
                    if isinstance(exc, HTTPException)
                    else "search_agent_internal_error"
                )
                msg = user_facing_error_message(code)
                tracker.emit("error", {"message": msg})
                if not isinstance(exc, HTTPException):
                    logger.exception("search-agent stream run loop failed")
                return _error_response(msg)
            tracker.emit(
                "final",
                {"elapsed_ms": int((time.time() - t0) * 1000), "success": bool(resp.success)},
            )
            return resp

        box: Dict[str, Any] = {"resp": None}
        cancelled_exc = anyio.get_cancelled_exc_class()
        try:
            async with anyio.create_task_group() as tg:

                async def _run() -> None:
                    try:
                        box["resp"] = await run_once()
                    finally:
                        try:
                            await send.aclose()
                        except Exception:
                            pass

                tg.start_soon(_run)

                async for ev in recv:
                    try:
                        yield sse_pack(ev)
                    except (cancelled_exc, asyncio.CancelledError):
                        return
                    except Exception:
                        return
        except (cancelled_exc, asyncio.CancelledError):
            return
        finally:
            try:
                await recv.aclose()
            except Exception:
                pass

        resp: Optional[SearchAgentResponse] = box.get("resp")
        if resp is None:
            resp = _error_response("search_agent_stream_incomplete")
            tracker.emit("error", {"message": resp.message or "search_agent_stream_incomplete"})
        yield sse_pack({"type": "final_result", "result": resp.model_dump(mode="json")})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
