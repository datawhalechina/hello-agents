"""Offline regressions for library saves, graph lifecycle and reading sessions."""
import asyncio
import logging
from pathlib import Path
import socket
import sqlite3
import sys
import threading
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import agents
from app.core import pdf_download
from app.core.author import Author
from app.core.paper import Paper
from app.core.storage import PaperDatabase
from app.models.schemas import Paper as ApiPaper, SavePapersRequest, ReadStatus
from app.services.graph import kg_relations as kg
from app.services.graph.graph_service import build_library_graph
from app.services.papers.papers_converters import api_paper_to_litpaper, litpaper_to_api_paper
from app.services.papers.papers_library_service import get_library, save_papers
from app.services.pdf import pdf_service
from app.services.reading_log.log import append_session, list_daily_aggregate


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Regression tests must not use network services")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(kg, "_kg_recent_fingerprints", {})


@pytest.fixture
def db(tmp_path):
    return PaperDatabase(str(tmp_path / "papers.db"))


def save(db, paper, *, pdf=False):
    return save_papers(
        db=db, request=SavePapersRequest(papers=[paper], llm_classify=False, download_pdfs=pdf),
        background_tasks=BackgroundTasks(), api_to_lit_fn=api_paper_to_litpaper,
        litpaper_to_api_paper_fn=litpaper_to_api_paper,
    )


def graph(db, *, category=None, limit=200, focus=None, edge_limit=400, authors=False):
    return build_library_graph(
        db=db, limit=limit, category=category, include_authors=authors,
        include_keywords=False, relation_edge_limit=edge_limit, focus_paper_id=focus,
    )


def test_filtered_totals_and_tags_are_applied_before_pagination(db):
    ids, _, _ = db.add_papers([
        Paper(title=f"Matching study {n}", category="Topic", year=2025, read_status="read")
        for n in range(25)
    ])
    pages = [get_library(
        db=db, litpaper_to_api_paper_fn=litpaper_to_api_paper, limit=10, offset=offset,
        q="Matching", category="Topic", year_from=2024, year_to=2026, read_status=ReadStatus.READ,
    ) for offset in (0, 10, 20, 30)]
    assert [(p.total, len(p.papers)) for p in pages] == [(25, 10), (25, 10), (25, 5), (25, 0)]
    assert len({p.id for page in pages for p in page.papers}) == 25
    db.update_paper(ids[0], tags=["wanted", "second"])
    with db._get_connection() as conn:
        conn.execute("UPDATE papers SET created_at='2001-01-01' WHERE id=?", (ids[0],))
    tagged = get_library(db=db, litpaper_to_api_paper_fn=litpaper_to_api_paper,
                         tags="wanted,second", limit=10)
    assert tagged.total == 1
    assert [p.id for p in tagged.papers] == [ids[0]]
    assert db.count_library(category="Missing", tags=["wanted"]) == 0


def test_duplicate_save_preserves_metadata_and_explicit_edits_can_clear(db, monkeypatch):
    monkeypatch.setattr(kg, "build_relations_for_new_paper", lambda *args: 0)
    rich = ApiPaper(title="Preserved", abstract="Known abstract", doi="10.test/rich",
                    category="My Topic", tags=["my-tag"], pdf_url="https://example.test/paper.pdf",
                    source_url="https://example.test/paper")
    first = asyncio.run(save(db, rich))
    second = asyncio.run(save(db, ApiPaper(title="Preserved", abstract="Known abstract", doi=rich.doi)))
    assert second.ids == first.ids and second.updated == 1
    row = db.get_paper_by_id(first.ids[0])
    assert (row.category, row.tags, row.pdf_url, row.source_url) == (
        "My Topic", ["my-tag"], rich.pdf_url, rich.source_url,
    )
    db.add_paper(Paper(title=rich.title, doi=rich.doi, tags=["my-tag", "new-tag"]))
    assert db.get_paper_by_id(row.id).tags == ["my-tag", "new-tag"]
    db.update_paper(row.id, tags=[], category="未分类")
    assert db.get_paper_by_id(row.id).tags == []
    assert db.get_paper_by_id(row.id).category == "未分类"


def test_author_identity_and_shared_author_edges_require_more_than_a_name(db):
    ids, _, _ = db.add_papers([
        Paper(title="University A paper", authors=[Author(name="Wei Wang", affiliation="University A")]),
        Paper(title="University B paper", authors=[Author(name="Wei Wang", affiliation="University B")]),
        Paper(title="Stable author one", authors=[Author(name="Pat", orcid="0000-0001")]),
        Paper(title="Stable author two", authors=[Author(name="Pat", orcid="0000-0001")]),
    ])
    a, b = [db.get_paper_by_id(pid).authors[0] for pid in ids[:2]]
    assert a.db_id != b.db_id
    assert (a.affiliation, b.affiliation) == ("University A", "University B")
    result = graph(db, authors=True)
    author_nodes = [n for n in result.nodes if n.type == "author"]
    assert len(author_nodes) == 3
    shared = [e for e in result.edges if e.type == "shared_author"]
    assert len(shared) == 1
    assert {shared[0].source, shared[0].target} == {f"paper:{ids[2]}", f"paper:{ids[3]}"}


def test_reads_use_persisted_timestamps(db):
    pid, _ = db.add_paper(Paper(title="Historical paper"))
    with db._get_connection() as conn:
        conn.execute("UPDATE papers SET created_at='2001-01-01 00:00:00', updated_at='2001-01-02 00:00:00' WHERE id=?", (pid,))
    for row in (db.get_paper_by_id(pid), db.search_library()[0], db.get_all_papers()[0]):
        api = litpaper_to_api_paper(row)
        assert api.created_at.isoformat() == "2001-01-01T00:00:00"
        assert api.updated_at.isoformat() == "2001-01-02T00:00:00"


def test_source_pdf_save_downloads_and_graph_receives_pdf_evidence(db, monkeypatch):
    db.add_paper(Paper(title="Graph retrieval baseline", category="Graph", abstract="Graph retrieval evidence"))
    observed = []
    class Agent:
        def infer_edges(self, *, new_paper, candidates):
            observed.append(new_paper)
            return [], None
    blob = b"%PDF-1.4\n" + b"x" * 500
    class Response:
        status_code = 200
        headers = {"content-type": "application/pdf"}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, **kwargs): yield blob
    monkeypatch.setattr(pdf_download.requests, "get", lambda *args, **kwargs: Response())
    monkeypatch.setattr(agents, "get_knowledge_graph_agent", lambda: Agent())
    monkeypatch.setattr(kg, "extract_pdf_text_full_cached", lambda *args: ("PDF-only experimental evidence", False))
    result = asyncio.run(save(db, ApiPaper(
        title="Graph retrieval evidence", abstract="Graph retrieval evidence", category="Graph",
        source_url="https://example.test/paper.pdf",
    ), pdf=True))
    assert result.pdf_downloaded == 1
    assert observed[0]["local_pdf_path"]
    assert observed[0]["pdf_excerpt"] == "PDF-only experimental evidence"
    assert Path(db.get_library_pdf_abspath(result.ids[0])).read_bytes() == blob


def test_save_keeps_event_loop_responsive_during_blocking_download(db, monkeypatch):
    started, release = threading.Event(), threading.Event()
    worker_resumed = []
    def blocked_download(*args, **kwargs):
        started.set()
        worker_resumed.append(release.wait(timeout=2))
        return False
    monkeypatch.setattr(pdf_download, "download_paper_pdf_to_path", blocked_download)
    monkeypatch.setattr(kg, "build_relations_for_new_paper", lambda *args: 0)
    async def scenario():
        task = asyncio.create_task(save(db, ApiPaper(title="Slow PDF", abstract="Known"), pdf=True))
        try:
            while not started.is_set():
                await asyncio.sleep(0.001)
            # This heartbeat can release the worker only if save yielded the event loop.
            await asyncio.sleep(0.01)
            release.set()
            await task
        finally:
            release.set()
    asyncio.run(scenario())
    assert worker_resumed == [True]


def test_graph_category_filter_precedes_limit(db):
    wanted, _ = db.add_paper(Paper(title="Older wanted", category="Wanted"))
    db.add_papers([Paper(title="Other one", category="Other"), Paper(title="Other two", category="Other")])
    with db._get_connection() as conn:
        conn.execute("UPDATE papers SET created_at='2001-01-01' WHERE id=?", (wanted,))
    assert [n.paper_id for n in graph(db, category="Wanted", limit=2).nodes] == [wanted]


def test_failed_graph_inference_retries_immediately_then_deduplicates(db, monkeypatch):
    ids, _, _ = db.add_papers([
        Paper(title="Graph retrieval source", category="Graph"),
        Paper(title="Graph retrieval target", category="Graph"),
    ])
    calls = []
    class Agent:
        def infer_edges(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise RuntimeError("transient failure")
            return [{"target_paper_id": ids[1], "relation": "related", "score": 0.8}], None
    monkeypatch.setattr(agents, "get_knowledge_graph_agent", lambda: Agent())
    with pytest.raises(RuntimeError, match="transient failure"):
        kg.build_relations_for_new_paper(db.db_path, ids[0])
    assert kg.build_relations_for_new_paper(db.db_path, ids[0]) == 1
    assert kg.build_relations_for_new_paper(db.db_path, ids[0]) == 0
    assert len(calls) == 2
    # Evidence changes must be eligible immediately, even inside the success window.
    db.update_paper(ids[0], abstract="Additional method evidence")
    assert kg.build_relations_for_new_paper(db.db_path, ids[0]) == 1
    assert len(calls) == 3


def test_deleted_and_legacy_orphan_relations_do_not_consume_focus_limit(db):
    ids, _, _ = db.add_papers([Paper(title=name) for name in ("A", "B", "C")])
    kg.upsert_relations(db.db_path, ids[0], [
        {"target_paper_id": ids[1], "relation": "related", "score": 0.99},
        {"target_paper_id": ids[2], "relation": "related", "score": 0.7},
    ])
    assert db.delete_paper(ids[1])
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM paper_relations WHERE target_paper_id=?", (ids[1],)).fetchone()[0] == 0
    # Also protect databases with orphan rows left by previous releases.
    kg.upsert_relations(db.db_path, ids[0], [{"target_paper_id": ids[1], "relation": "related", "score": 0.99}])
    result = graph(db, focus=ids[0], edge_limit=1)
    assert len(result.edges) == 2
    assert {n.paper_id for n in result.nodes} == {ids[0], ids[2]}


@pytest.mark.parametrize("header,status,expected", [
    ("bytes=-10", 206, (499, 508)), ("bytes=-1000", 206, (0, 508)),
    ("bytes=0-9", 206, (0, 9)), ("bytes=499-", 206, (499, 508)),
    ("bytes=-0", 416, None), ("bytes=509-", 416, None),
    ("bytes=10-9", 416, None), ("bytes=0-9garbage", 416, None),
])
def test_pdf_ranges(db, tmp_path, monkeypatch, header, status, expected):
    blob = b"%PDF-1.4\n" + b"0" * 500
    (tmp_path / "paper.pdf").write_bytes(blob)
    pid, _ = db.add_paper(Paper(title="PDF", local_pdf_path="paper.pdf"))
    monkeypatch.setattr(pdf_service, "get_settings", lambda: SimpleNamespace(data_dir=str(tmp_path)))
    response = pdf_service.build_library_pdf_response(
        paper_id=pid, request=Request({"type": "http", "headers": [(b"range", header.encode())]}),
        db_path=db.db_path, logger=logging.getLogger("test"),
    )
    assert response.status_code == status
    if expected:
        start, end = expected
        assert response.headers["content-range"] == f"bytes {start}-{end}/{len(blob)}"
        async def consume():
            return b"".join([chunk async for chunk in response.body_iterator])
        assert asyncio.run(consume()) == blob[start:end + 1]


def test_reading_session_migration_and_cumulative_retries_keep_legacy_append_semantics(tmp_path):
    path = str(tmp_path / "old.db")
    with sqlite3.connect(path) as conn:
        conn.execute("""CREATE TABLE paper_reading_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, paper_id INTEGER NOT NULL,
            duration_sec INTEGER NOT NULL, day_key TEXT NOT NULL, created_at INTEGER NOT NULL)""")
    for seconds in (30, 60, 60, 45):
        append_session(path, paper_id=1, duration_sec=seconds, session_id="session-a")
    append_session(path, paper_id=1, duration_sec=15)
    append_session(path, paper_id=1, duration_sec=15)
    append_session(path, paper_id=2, duration_sec=12, session_id="session-a")
    items = list_daily_aggregate(path, days=7)
    assert len(items) == 1
    assert (items[0]["seconds"], items[0]["sessions"]) == (102, 4)
    append_session(path, paper_id=1, duration_sec=999999, session_id="session-a")
    assert list_daily_aggregate(path, days=7)[0]["seconds"] == 86442


def test_concurrent_saves_share_identity_and_merge_all_tags(db, monkeypatch):
    monkeypatch.setattr(kg, "build_relations_for_new_paper", lambda *args: 0)
    ready = threading.Barrier(8)

    def synchronized_conversion(paper):
        ready.wait(timeout=5)
        return api_paper_to_litpaper(paper)

    async def scenario():
        return await asyncio.gather(*[
            save_papers(
                db=db,
                request=SavePapersRequest(papers=[ApiPaper(
                    title="Concurrent paper", abstract="Known abstract", doi="10.test/concurrent",
                    tags=[f"tag-{i}"],
                )], llm_classify=False, download_pdfs=False),
                background_tasks=BackgroundTasks(), api_to_lit_fn=synchronized_conversion,
                litpaper_to_api_paper_fn=litpaper_to_api_paper,
            ) for i in range(8)
        ])

    results = asyncio.run(scenario())
    ids = [result.ids[0] for result in results]
    assert len(set(ids)) == 1 and ids[0] > 0
    assert sum(result.added for result in results) == 1
    assert sum(result.updated for result in results) == 7
    assert db.count_papers() == 1
    assert set(db.get_paper_by_id(ids[0]).tags) == {f"tag-{i}" for i in range(8)}


@pytest.mark.parametrize("second_outcome", ["success", "request_error", "unexpected_error"])
def test_concurrent_save_downloads_publish_only_complete_owned_files(db, tmp_path, monkeypatch, second_outcome):
    monkeypatch.setattr(kg, "build_relations_for_new_paper", lambda *args: 0)
    second_open = threading.Event()
    release_second = threading.Event()
    request_lock = threading.Lock()
    requests_seen = []
    first_prefix = b"%PDF-1.4\n" + b"A" * 65536
    second_prefix = b"%PDF-1.4\n" + b"B" * 65536
    first_pdf = first_prefix + b"A-trailer" * 1024
    second_pdf = second_prefix + b"B-trailer" * 2048

    class StreamingResponse:
        status_code = 200
        headers = {"content-type": "application/pdf"}
        def __init__(self, index): self.index = index
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, **kwargs):
            if self.index == 0:
                yield first_prefix
                assert second_open.wait(timeout=5), "The second save must reach its own downloader"
                yield first_pdf[len(first_prefix):]
            else:
                yield second_prefix
                # The large first write has reached the staging file before publication.
                second_open.set()
                assert release_second.wait(timeout=5), "The event loop must observe the first publication"
                if second_outcome == "request_error":
                    raise pdf_download.requests.RequestException("Interrupted remote stream")
                if second_outcome == "unexpected_error":
                    raise RuntimeError("Unexpected stream failure")
                yield second_pdf[len(second_prefix):]

    def get_response(*args, **kwargs):
        with request_lock:
            index = len(requests_seen)
            requests_seen.append(index)
        return StreamingResponse(index)

    monkeypatch.setattr(pdf_download.requests, "get", get_response)

    async def scenario():
        tasks = [asyncio.create_task(save(db, ApiPaper(
            title="Concurrent PDF", abstract="Known abstract", doi="10.test/concurrent-pdf",
            pdf_url="https://example.test/paper.pdf", tags=[f"save-{i}"],
        ), pdf=True)) for i in range(2)]
        try:
            done, pending = await asyncio.wait(tasks, timeout=6, return_when=asyncio.FIRST_COMPLETED)
            assert len(done) == len(pending) == 1
            first = next(iter(done)).result()
            assert first.pdf_downloaded == 1
            destination = Path(db.get_library_pdf_abspath(first.ids[0]))
            # A paused writer must not be holding an fd to the published PDF inode.
            assert destination.read_bytes() == first_pdf
            release_second.set()
            results = await asyncio.gather(*tasks)
            expected = second_pdf if second_outcome == "success" else first_pdf
            assert destination.read_bytes() == expected
            assert not list(tmp_path.rglob("*.part"))
            return results
        finally:
            release_second.set()
            await asyncio.gather(*tasks, return_exceptions=True)

    results = asyncio.run(scenario())
    assert len(requests_seen) == 2
    assert results[0].ids == results[1].ids and results[0].ids[0] > 0
    assert set(db.get_paper_by_id(results[0].ids[0]).tags) == {"save-0", "save-1"}
    assert sorted(r.pdf_downloaded for r in results) == ([1, 1] if second_outcome == "success" else [0, 1])


def test_download_discovery_failure_does_not_unlink_another_attempt_file(tmp_path, monkeypatch):
    destination = tmp_path / "paper.pdf"
    unrelated = tmp_path / "paper.pdf.part"
    unrelated.write_bytes(b"owned by another download")
    def failed_discovery(*args, **kwargs):
        raise RuntimeError("Resolver unavailable")
    monkeypatch.setattr(pdf_download, "_pdf_download_candidates", failed_discovery)
    assert not pdf_download.download_paper_pdf_to_path(Paper(title="Unresolved"), str(destination))
    assert unrelated.read_bytes() == b"owned by another download"
