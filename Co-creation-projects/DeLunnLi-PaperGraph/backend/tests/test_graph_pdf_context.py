"""Exercise PDF evidence through graph construction without a model service."""
from pathlib import Path
import sqlite3
import sys

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import agents
from app.core.paper import Paper
from app.core.storage import PaperDatabase
from app.services.graph import kg_relations
from app.services.reader.paper_reader_context import _cache_get, _cache_set


@pytest.fixture
def graph_case(tmp_path, monkeypatch):
    db = PaperDatabase(str(tmp_path / "papers.db"))
    ids, _, _ = db.add_papers([
        Paper(title="Graph retrieval methods", abstract="Graph retrieval evidence",
              doi="10.0000/graph-source", category="Graph", keywords=["graph", "retrieval"]),
        Paper(title="Graph retrieval baseline", abstract="Graph retrieval comparison",
              doi="10.0000/graph-target", category="Graph", keywords=["graph", "retrieval"]),
    ])
    pdf = tmp_path / "source.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), "Related Work\nGRAPH_PDF_EVIDENCE: compares graph retrieval methods.")
        doc.save(pdf)
    db.set_local_pdf_path(ids[0], pdf.name)
    observations = []

    class GraphAgent:
        def infer_edges(self, *, new_paper, candidates):
            observations.append(dict(new_paper))
            assert any(p["id"] == ids[1] for p in candidates)
            return [{"target_paper_id": ids[1], "relation": "compares",
                     "score": 0.9, "evidence": "GRAPH_PDF_EVIDENCE"}], None

    monkeypatch.setattr(agents, "get_knowledge_graph_agent", lambda: GraphAgent())
    monkeypatch.setattr(kg_relations, "_kg_recent_fingerprints", {})
    return db, ids, pdf, observations


def test_graph_extracts_pdf_evidence_and_persists_relation(graph_case):
    db, ids, pdf, observations = graph_case
    assert kg_relations.build_relations_for_new_paper(db.db_path, ids[0]) == 1
    assert "GRAPH_PDF_EVIDENCE" in observations[0]["pdf_excerpt"]
    assert "Related Work" in observations[0]["related_work_excerpt"]
    assert "GRAPH_PDF_EVIDENCE" in _cache_get(db.db_path, ids[0], str(pdf))
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute(
            "SELECT source_paper_id, target_paper_id, relation FROM paper_relations"
        ).fetchall() == [(ids[0], ids[1], "compares")]


def test_graph_reuses_full_cache_but_bounds_model_excerpt(graph_case, monkeypatch):
    db, ids, pdf, observations = graph_case
    full_text = ("Related Work\nGRAPH_PDF_EVIDENCE\n" + "graph evidence " * 1000).strip()
    _cache_set(db.db_path, ids[0], str(pdf), full_text)

    def unexpected_parse(_path):
        raise AssertionError("A cached PDF must not be parsed again")

    monkeypatch.setattr(kg_relations, "extract_pdf_text_full", unexpected_parse)
    assert kg_relations.build_relations_for_new_paper(db.db_path, ids[0]) == 1
    assert observations[0]["pdf_excerpt"] == full_text[:9000]
    assert len(observations[0]["related_work_excerpt"]) <= 1600
    assert _cache_get(db.db_path, ids[0], str(pdf)) == full_text
