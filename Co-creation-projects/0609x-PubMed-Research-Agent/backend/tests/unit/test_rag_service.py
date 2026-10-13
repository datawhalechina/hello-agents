# -*- coding: utf-8 -*-
"""Unit tests for favorite-library RAG and its HTTP endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.rag import RagDocumentIn, RagQueryOut
from backend.services.rag_service import RagService


class FakeLLM:
    def __init__(self, raw: str):
        self.raw = raw
        self.last_prompt: str | None = None
        self.call_count = 0

    def _call_llm(self, system: str, user: str) -> str:
        self.call_count += 1
        self.last_prompt = user
        return self.raw


def _documents() -> list[RagDocumentIn]:
    return [
        RagDocumentIn(
            pmid="100",
            title="SEC61G in lung cancer",
            abstract="We studied SEC61G expression and prognosis in lung cancer.",
            journal="Cancer Research",
            publish_date="2025",
        ),
        RagDocumentIn(
            pmid="200",
            title="SEC61G review",
            abstract="A review of SEC61G in solid tumors.",
        ),
        RagDocumentIn(
            pmid="300",
            title="Diabetes lifestyle intervention",
            abstract="Exercise and nutrition improve glucose control.",
        ),
    ]


def test_local_retrieval_ranks_matching_favorite_first():
    hits = RagService._rank_documents(
        "What is the role of SEC61G in lung cancer?",
        _documents(),
        top_k=2,
    )
    assert [hit["pmid"] for hit in hits] == ["100", "200"]
    assert hits[0]["score"] > hits[1]["score"]


def test_answer_returns_sources_and_uses_only_selected_favorites():
    llm = FakeLLM('{"answer": "SEC61G is upregulated.", "sources": ["100"]}')
    service = RagService(llm)
    out = service.answer(
        "What is the role of SEC61G in lung cancer?",
        documents=_documents(),
        top_k=2,
        language="en",
    )

    assert isinstance(out, RagQueryOut)
    assert out.answer == "SEC61G is upregulated."
    assert [source.pmid for source in out.sources] == ["100", "200"]
    assert out.sources[0].relevance_score > out.sources[1].relevance_score
    assert "PMID: 100" in (llm.last_prompt or "")
    assert "PMID: 300" not in (llm.last_prompt or "")


def test_answer_tolerates_plain_text_llm_output():
    llm = FakeLLM("Plain text answer without JSON.")
    service = RagService(llm)
    out = service.answer("SEC61G", documents=_documents(), top_k=2)
    assert out.answer == "Plain text answer without JSON."


def test_zh_language_instruction_is_passed():
    llm = FakeLLM('{"answer": "中文答案"}')
    service = RagService(llm)
    service.answer("SEC61G 是什么？", documents=_documents(), top_k=2, language="zh")
    assert "Answer in Chinese" in (llm.last_prompt or "")


def test_empty_favorites_returns_localized_message_without_llm_call():
    llm = FakeLLM("ignored")
    service = RagService(llm)
    out = service.answer("问题", documents=[], language="zh")
    assert "收藏夹" in out.answer
    assert out.sources == []
    assert llm.call_count == 0


def test_rag_endpoint_accepts_favorite_documents(monkeypatch):
    service = RagService(FakeLLM('{"answer": "ok"}'))
    monkeypatch.setattr("backend.app.api.v1.rag.get_rag_service", lambda: service)
    documents = [document.model_dump() for document in _documents()]

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rag/query",
            json={
                "query": "role of SEC61G in lung cancer",
                "top_k": 2,
                "language": "en",
                "documents": documents,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "ok"
    assert [source["pmid"] for source in body["sources"]] == ["100", "200"]
