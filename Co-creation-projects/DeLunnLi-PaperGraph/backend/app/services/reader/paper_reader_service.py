
from __future__ import annotations

import logging
from typing import Any
from collections.abc import Iterable

from fastapi import BackgroundTasks, HTTPException
from starlette.concurrency import run_in_threadpool

from ...agents import get_paper_analysis_agent
from ...agents.support.reader_reference_lookup_tool import READER_RELATED_FROM_BIBLIOGRAPHY, READER_RELATED_FROM_PRE_SEARCH
from ...utils.common import suppress_exceptions_async

logger = logging.getLogger(__name__)

_OPENING_PROMPT = (
    "请用中文写一段不超过 380 字的导读：研究问题、核心方法、实验与结论的阅读要点。"
    "仅依据当前提供的摘要与摘录组织表述；勿单列「不确定处」「局限」或待查清单（用户追问时再说明材料范围即可）。"
)
_NO_HISTORY_PLACEHOLDER = "（尚无对话历史）"

def _update_memory_from_turn(*, store: Any, paper_id: int, user_message: str, assistant_reply: str) -> None:
    um = (user_message or "").strip()
    if not um:
        return
    store.add(scope="paper", paper_id=paper_id, kind="working", content=f"用户问：{um[:220]}", importance=0.5)
    try:
        store.extract_memory_via_llm(paper_id, um, assistant_reply)
    except Exception:
        logger.debug("extract_memory_via_llm failed for paper %s", paper_id, exc_info=True)

class PaperReaderService:
    def __init__(self, db: Any, agent: Any | None = None) -> None:
        self._db = db
        self._agent = agent or get_paper_analysis_agent()

    @property
    def db(self) -> Any:
        return self._db

    @staticmethod
    def _format_reader_history(turns: Iterable[Any]) -> str:
        lines: list[str] = []
        tail = list(turns or [])[-24:]
        for t in tail:
            role = (getattr(t, "role", None) or "").strip().lower()
            content = (getattr(t, "content", None) or "").strip()
            if not content:
                continue
            if role not in ("user", "assistant"):
                role = "user"
            label = "用户" if role == "user" else "助手"
            lines.append(f"{label}：{content}")
        return "\n\n".join(lines)

    async def _build_reader_context(self, paper_id: int, user_message: str = "") -> tuple[Any, str, str]:
        from ..memory.memory_store import MemoryStore
        from .paper_reader_context import build_reader_context_for_paper

        paper, base_ctx, pdf_ref_text, pdf_parsing = await run_in_threadpool(build_reader_context_for_paper, self._db, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="文献不存在")

        mem = await run_in_threadpool(
            MemoryStore(self._db.db_path).build_context_block,
            paper_id=paper_id,
        )
        title_hint = str(getattr(paper, "title", None) or "")
        ctx = (base_ctx + ("\n\n" + mem if mem else "")).strip()
        return paper, ctx, title_hint, pdf_ref_text, pdf_parsing

    def _schedule_pdf_excerpt(self, paper_id: int, ctx: str, background_tasks: BackgroundTasks) -> None:
        from .paper_reader_context import compute_and_cache_excerpt

        try:
            pdf_path = self._db.get_library_pdf_abspath(paper_id)
            if pdf_path and "【PDF 正文摘录" not in ctx:
                background_tasks.add_task(compute_and_cache_excerpt, self._db.db_path, paper_id, pdf_path)
        except Exception as exc:
            logger.debug("paper_reader.schedule_pdf_excerpt_failed", extra={"paper_id": paper_id}, exc_info=exc)

    @suppress_exceptions_async(default_return=None, log_level="warning", log_message="paper_reader.ensure_opening_turn_failed")
    async def _ensure_opening_turn_safe(self, *, paper_id: int, opening_text: str) -> None:
        from .paper_reader_history import ensure_opening_turn

        await run_in_threadpool(
            ensure_opening_turn,
            self._db.db_path,
            paper_id=int(paper_id),
            opening_text=opening_text,
        )

    @suppress_exceptions_async(default_return=None, log_level="warning", log_message="paper_reader.append_history_failed")
    async def _append_history(self, *, paper_id: int, user_message: str, reply: str) -> None:
        from .paper_reader_history import append_turn

        await run_in_threadpool(
            append_turn,
            self._db.db_path,
            paper_id=int(paper_id),
            role="user",
            content=user_message,
        )
        await run_in_threadpool(
            append_turn,
            self._db.db_path,
            paper_id=int(paper_id),
            role="assistant",
            content=reply,
        )

    @suppress_exceptions_async(default_return=None, log_level="warning", log_message="paper_reader.memory_update_failed")
    async def _update_memory(self, *, store: Any, paper_id: int, user_message: str, reply: str) -> None:
        await run_in_threadpool(
            _update_memory_from_turn,
            store=store, paper_id=paper_id,
            user_message=user_message, assistant_reply=reply,
        )

    async def get_opening(self, *, paper_id: int, background_tasks: BackgroundTasks) -> dict:
        from .reader_opening_cache import get_cached_opening, set_cached_opening

        from .paper_reader_context import build_reader_snap

        paper, ctx, title_hint, pdf_ref_text, pdf_parsing = await self._build_reader_context(paper_id)

        reader_snap = build_reader_snap(paper, pdf_text_for_references=pdf_ref_text)
        try:
            pdf_path = self._db.get_library_pdf_abspath(paper_id)
            if pdf_path:
                reader_snap["_pdf_abspath"] = pdf_path
        except Exception:
            pass
        if pdf_parsing:
            self._schedule_pdf_excerpt(paper_id, ctx, background_tasks)

        cached, fresh = await run_in_threadpool(get_cached_opening, self._db.db_path, paper_id, 72)
        if cached and fresh:
            op = cached.strip()
            await self._ensure_opening_turn_safe(paper_id=paper_id, opening_text=op)
            return {"opening": op, "pdf_parsing": pdf_parsing}

        if cached and not fresh:
            def _refresh() -> None:
                try:
                    opening2, _, _ = self._agent.paper_reader_reply(
                        ctx, _NO_HISTORY_PLACEHOLDER, _OPENING_PROMPT, reader_snap
                    )
                    set_cached_opening(self._db.db_path, paper_id, opening2.strip())
                except Exception as exc:
                    logger.warning("paper_reader.opening_refresh_failed", extra={"paper_id": paper_id}, exc_info=exc)

            background_tasks.add_task(_refresh)
            op = cached.strip()
            await self._ensure_opening_turn_safe(paper_id=paper_id, opening_text=op)
            return {"opening": op, "pdf_parsing": pdf_parsing}

        opening, _, _ = await run_in_threadpool(
            lambda: self._agent.paper_reader_reply(ctx, _NO_HISTORY_PLACEHOLDER, _OPENING_PROMPT, reader_snap)
        )
        op = opening.strip()
        await run_in_threadpool(set_cached_opening, self._db.db_path, paper_id, op)
        await self._ensure_opening_turn_safe(paper_id=paper_id, opening_text=op)
        return {"opening": op, "pdf_parsing": pdf_parsing}

    async def process_chat(
        self,
        *,
        paper_id: int,
        messages: list[Any],
        user_message: str,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        from ..memory.memory_store import MemoryStore

        paper, ctx, title_hint, pdf_ref_text, pdf_parsing = await self._build_reader_context(paper_id, user_message)
        from .paper_reader_context import build_reader_snap

        reader_snap = build_reader_snap(paper, pdf_text_for_references=pdf_ref_text)
        try:
            pdf_path = self._db.get_library_pdf_abspath(paper_id)
            if pdf_path:
                reader_snap["_pdf_abspath"] = pdf_path
        except Exception:
            pass
        self._schedule_pdf_excerpt(paper_id, ctx, background_tasks)

        store = MemoryStore(self._db.db_path)
        rel_mem = await run_in_threadpool(
            store.get_context_for_query,
            paper_id=int(paper_id),
            query=user_message,
            limit=6,
        )
        if rel_mem:
            ctx += "\n\n" + rel_mem
        hist = self._format_reader_history(messages)

        reply, related_papers, related_sources = await run_in_threadpool(
            lambda: self._agent.paper_reader_reply(ctx, hist, user_message, reader_snap)
        )
        rs = list(related_sources or [])
        related_hints: list[dict[str, Any]] = [
            {
                "ref_idx": i,
                "title": getattr(p, "title", None),
                "reason": (
                    "来自当前文献参考文献题录（OpenAlex 解析）"
                    if i - 1 < len(rs) and rs[i - 1] == READER_RELATED_FROM_BIBLIOGRAPHY
                    else "基于论文主题相似度匹配"
                    if i - 1 < len(rs) and rs[i - 1] == READER_RELATED_FROM_PRE_SEARCH
                    else "来自用户给定英文短语或外部题名检索（OpenAlex）"
                ),
            }
            for i, p in enumerate(related_papers or [], start=1)
        ]

        await self._append_history(paper_id=paper_id, user_message=user_message, reply=reply)
        await self._update_memory(store=store, paper_id=paper_id, user_message=user_message, reply=reply)
        background_tasks.add_task(store.compress_working, scope="paper", paper_id=int(paper_id), min_entries=6)

        return {
            "reply": reply.strip(),
            "pdf_parsing": pdf_parsing,
            "related_papers": related_papers,
            "related_hints": related_hints,
            "kg_edges": [],
        }

    async def get_history(self, *, paper_id: int, limit: int) -> list[dict[str, Any]]:
        from .paper_reader_history import list_turns

        paper = await run_in_threadpool(self._db.get_paper_by_id, int(paper_id))
        if not paper:
            raise HTTPException(status_code=404, detail="文献不存在")
        return await run_in_threadpool(
            list_turns,
            self._db.db_path,
            paper_id=int(paper_id),
            limit=int(limit),
        )
