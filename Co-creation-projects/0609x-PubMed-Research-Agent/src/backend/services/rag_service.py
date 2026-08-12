# -*- coding: utf-8 -*-
"""RAG chat service: retrieve evidence from Qdrant, answer with the LLM.

Problem Solved:
    After literature has been indexed into the Qdrant vector store, users
    want to ask follow-up questions grounded in that corpus. This service
    retrieves the top-k relevant articles, builds a prompt with the evidence,
    and asks the LLM to answer with citations (PMIDs).

Pipeline:
    query -> embed -> Qdrant semantic_search -> context -> LLM -> answer + sources
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from backend.app.schemas.rag import RagQueryOut, RagSource
from backend.services.literature_summary import LiteratureSummarizer
from backend.services.vector_store import QdrantVectorStore

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = (
    "You are a biomedical research assistant. Answer the user's question using "
    "ONLY the provided PubMed article excerpts as evidence. Cite each claim with "
    "the corresponding PMID in brackets, e.g. [PMID:12345678]. If the evidence is "
    "insufficient, say so explicitly. Return your answer as valid JSON with keys: "
    '"answer" (string) and "sources" (array of PMID strings you actually used).'
)


class RagService:
    """Answer questions grounded in the Qdrant-indexed literature corpus."""

    def __init__(
        self,
        vector_store: Optional[QdrantVectorStore],
        llm: LiteratureSummarizer,
        top_k_default: int = 5,
    ) -> None:
        self.vector_store = vector_store
        self.llm = llm
        self.top_k_default = top_k_default
        logger.info("RagService initialized (top_k_default=%d)", top_k_default)

    def answer(
        self,
        query: str,
        top_k: int = 5,
        language: str = "en",
    ) -> RagQueryOut:
        """Run the RAG pipeline and return the grounded answer + sources."""
        if self.vector_store is None:
            return RagQueryOut(
                answer="Vector store is not configured. Run a PubMed search first.",
                sources=[],
            )

        hits = self.vector_store.semantic_search(query, top_k=top_k)
        if not hits:
            return RagQueryOut(
                answer="No relevant articles found in the vector store. "
                "Run a PubMed search to index literature first.",
                sources=[],
            )

        context = self._build_context(hits)
        sources = [
            RagSource(
                pmid=str(h.get("pmid", "")),
                title=h.get("title", "") or "",
                relevance_score=float(h.get("score", 0.0)),
            )
            for h in hits
        ]

        lang_instruction = "Answer in Chinese." if language == "zh" else "Answer in English."
        user_prompt = f"{lang_instruction}\n\nQuestion: {query}\n\nEvidence:\n{context}"

        try:
            raw = self.llm._call_llm(RAG_SYSTEM_PROMPT, user_prompt)
        except Exception as exc:
            logger.error("RAG LLM call failed: %s", exc)
            raise

        answer = self._parse_answer(raw)
        return RagQueryOut(answer=answer, sources=sources)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_context(hits: list[dict]) -> str:
        """Format retrieved article payloads into an evidence block."""
        blocks = []
        for i, hit in enumerate(hits, start=1):
            blocks.append(
                f"[{i}] PMID: {hit.get('pmid', '')}\n"
                f"Title: {hit.get('title', '')}\n"
                f"Abstract: {(hit.get('abstract') or '')[:1500]}"
            )
        return "\n\n".join(blocks)

    @staticmethod
    def _parse_answer(raw: str) -> str:
        """Extract the answer string, tolerating JSON or plain-text output."""
        text = (raw or "").strip()
        if not text:
            return "No answer was generated."
        try:
            data = json.loads(text)
            if isinstance(data, dict) and data.get("answer"):
                return str(data["answer"])
        except json.JSONDecodeError:
            pass
        return text
