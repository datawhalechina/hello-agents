# -*- coding: utf-8 -*-
"""Local favorite-library retrieval followed by grounded LLM answering."""

from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter

from backend.app.schemas.rag import RagDocumentIn, RagQueryOut, RagSource
from backend.services.literature_summary import LiteratureSummarizer

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = (
    "You are a biomedical research assistant answering questions about the user's "
    "favorite PubMed library. Use ONLY the provided favorite article excerpts as "
    "evidence. Cite each claim with "
    "the corresponding PMID in brackets, e.g. [PMID:12345678]. If the evidence is "
    "insufficient, say so explicitly. Return your answer as valid JSON with keys: "
    '"answer" (string) and "sources" (array of PMID strings you actually used).'
)

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*|[\u4e00-\u9fff]")


class RagService:
    """Answer questions grounded only in a supplied favorite collection."""

    def __init__(
        self,
        llm: LiteratureSummarizer,
        top_k_default: int = 5,
    ) -> None:
        self.llm = llm
        self.top_k_default = top_k_default
        logger.info("RagService initialized (top_k_default=%d)", top_k_default)

    def answer(
        self,
        query: str,
        documents: list[RagDocumentIn],
        top_k: int = 5,
        language: str = "en",
    ) -> RagQueryOut:
        """Run the RAG pipeline and return the grounded answer + sources."""
        if not documents:
            return RagQueryOut(
                answer=(
                    "收藏夹中还没有文献。请先在检索结果中收藏文献，再进行问答。"
                    if language == "zh"
                    else "Your favorites library is empty. Save articles before asking questions."
                ),
                sources=[],
            )

        hits = self._rank_documents(query, documents, top_k or self.top_k_default)
        if not hits:
            return RagQueryOut(
                answer=(
                    "收藏文献中没有足够的信息回答该问题。"
                    if language == "zh"
                    else "The favorite articles do not contain enough evidence to answer this question."
                ),
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
    def _tokenize(text: str) -> list[str]:
        return [token.lower() for token in _TOKEN_PATTERN.findall(text or "")]

    @classmethod
    def _rank_documents(
        cls,
        query: str,
        documents: list[RagDocumentIn],
        top_k: int,
    ) -> list[dict]:
        """Rank the in-request favorite corpus with a small TF-IDF cosine index."""
        query_tokens = cls._tokenize(query)
        prepared: list[tuple[RagDocumentIn, Counter[str]]] = []
        document_frequency: Counter[str] = Counter()
        for document in documents:
            title_tokens = cls._tokenize(document.title)
            abstract_tokens = cls._tokenize(document.abstract)
            counts = Counter(title_tokens * 3 + abstract_tokens)
            prepared.append((document, counts))
            document_frequency.update(counts.keys())

        total_documents = max(1, len(prepared))

        def idf(token: str) -> float:
            return math.log((1 + total_documents) / (1 + document_frequency[token])) + 1

        query_counts = Counter(query_tokens)
        query_weights = {
            token: count * idf(token) for token, count in query_counts.items()
        }
        query_norm = math.sqrt(sum(weight * weight for weight in query_weights.values()))

        ranked: list[tuple[float, int, RagDocumentIn]] = []
        for index, (document, counts) in enumerate(prepared):
            document_weights = {
                token: count * idf(token) for token, count in counts.items()
            }
            document_norm = math.sqrt(
                sum(weight * weight for weight in document_weights.values())
            )
            dot_product = sum(
                query_weights[token] * document_weights.get(token, 0.0)
                for token in query_weights
            )
            score = (
                dot_product / (query_norm * document_norm)
                if query_norm and document_norm
                else 0.0
            )
            lowered_query = query.strip().lower()
            if lowered_query and lowered_query in document.title.lower():
                score += 0.25
            ranked.append((score, index, document))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        selected = ranked[: max(1, min(top_k, len(ranked)))]
        return [
            {
                "pmid": document.pmid,
                "title": document.title,
                "abstract": document.abstract,
                "journal": document.journal,
                "publish_date": document.publish_date,
                "score": round(score, 6),
            }
            for score, _, document in selected
        ]

    @staticmethod
    def _build_context(hits: list[dict]) -> str:
        """Format retrieved article payloads into an evidence block."""
        blocks = []
        for i, hit in enumerate(hits, start=1):
            blocks.append(
                f"[{i}] PMID: {hit.get('pmid', '')}\n"
                f"Title: {hit.get('title', '')}\n"
                f"Journal: {hit.get('journal', '')}\n"
                f"Published: {hit.get('publish_date', '')}\n"
                f"Abstract: {(hit.get('abstract') or '')[:3000]}"
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
