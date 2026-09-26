"""Offline search/SSE and daily recommendation regressions.

Real intent agents, retrieval orchestration, HTTP routes and SQLite stores run
against scripted model/provider boundaries; no credentials or live APIs needed.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import replace
import datetime
import json
import logging
from pathlib import Path
import socket
import sqlite3
import sys
import threading
import time
from types import SimpleNamespace

import anyio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents import base, search_agent
from app.api import dependencies
from app.api.routes import papers as papers_route, search as search_route
from app.core.paper import Paper
from app.core.search import paper_searcher
from app.core.storage import PaperDatabase
from app.models.schemas import DailyPapersRequest
from app.services.daily import daily_auto_refresh, daily_recommend_feedback as feedback
from app.services.daily import daily_service, daily_support
from app.services.daily.user_behavior_analytics import UserBehaviorAnalytics
from app.services.feedback import negative_feedback_memory
from app.services.llm import llm_service
from app.services.memory.memory_store import MemoryStore
from app.services.papers.papers_helpers import daily_paper_identity_sig as identity
from app.services.retrieval import paper_ranker, search_pipeline, web_presearch
from app.services.retrieval.pipeline_runtime import SearchRuntimeConfig
from app.services.retrieval.recall_jobs import RecallJob, _run_search_job
from app.services.retrieval.search_plan import ResolvedSearchPlan
from app.settings import get_settings

LOG = logging.getLogger(__name__)


class ScriptedLLM:
    model = "offline-search-daily-test"

    def __init__(self, payload=None):
        self.payload = payload or {"query": "graph learning", "use_llm_rank": False}
        self.calls = []

    def invoke(self, messages, **kwargs):
        self.calls.append(deepcopy(messages))
        payload = self.payload(messages) if callable(self.payload) else self.payload
        return json.dumps(payload)


class Sources:
    def __init__(self, papers=(), *, fail=False, fallback=()):
        self.papers, self.fail, self.fallback = list(papers), fail, list(fallback)
        self.calls = []

    async def search_async(self, query, **kwargs):
        self.calls.append((query, kwargs))
        if self.fallback and kwargs.get("sources") == ["arxiv"]:
            return self.fallback
        if self.fail:
            raise RuntimeError("synthetic provider unavailable")
        return self.papers

    async def search_arxiv_async(self, query, **kwargs):
        self.calls.append(("arxiv", kwargs))
        if self.fail:
            raise RuntimeError("synthetic arxiv outage")
        return self.papers

    async def search_openalex_async(self, query, **kwargs):
        self.calls.append(("openalex", kwargs))
        return self.fallback


@pytest.fixture(autouse=True)
def offline_environment(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("Search/daily regressions must not access the network")

    for key in list(__import__("os").environ):
        if key.startswith(("LLM_", "OPENAI_", "TAVILY_", "EMBED_")):
            monkeypatch.delenv(key)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    monkeypatch.setattr(get_settings(), "data_dir", str(tmp_path))
    monkeypatch.setattr(get_settings(), "tavily_api_key", "")
    monkeypatch.setattr(get_settings(), "papergraph_proceedings_supplement_enabled", False)
    llm = ScriptedLLM()
    monkeypatch.setattr(base, "get_llm", lambda: llm)
    monkeypatch.setattr(llm_service, "get_llm", lambda: llm)
    monkeypatch.setattr(llm_service, "is_llm_configured", lambda: False)
    monkeypatch.setattr(daily_service, "is_llm_configured", lambda: False)
    monkeypatch.setattr(negative_feedback_memory, "get_llm", lambda: llm)
    monkeypatch.setattr(search_agent, "_search_agent_singleton", None)
    monkeypatch.setattr(daily_auto_refresh, "_daily_compute_lock", None)
    search_agent._INTENT_CACHE.clear()
    daily_support.invalidate_user_profile_cache()
    yield llm
    search_agent._INTENT_CACHE.clear()
    daily_support.invalidate_user_profile_cache()


def api_client(tmp_path, provider):
    app = FastAPI()
    app.include_router(search_route.router, prefix="/api")
    app.include_router(papers_route.router, prefix="/api")
    db = PaperDatabase(str(tmp_path / "papers.db"))
    app.dependency_overrides[dependencies.get_searcher] = lambda: provider
    app.dependency_overrides[dependencies.get_database] = lambda: db
    app.dependency_overrides[dependencies.get_db_path] = lambda: db.db_path
    return TestClient(app), db


def search_result(client, **request):
    response = client.post("/api/papers/search-agent/stream", json=request)
    assert response.status_code == 200
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert events[-1]["type"] == "final_result"
    return events[-1]["result"]


@pytest.mark.parametrize("outcome", ["empty", "outage", "fallback"])
def test_search_stream_distinguishes_empty_outage_and_recovered_results(tmp_path, offline_environment, outcome):
    llm = offline_environment
    llm.payload = {"query": "graph learning", "use_llm_rank": False, "sources": ["openalex"]}
    paper = Paper(title="Graph learning", arxiv_id="2609.00001", year=2026)
    sources = Sources(fail=outcome != "empty", fallback=[paper] if outcome == "fallback" else [])
    client, _ = api_client(tmp_path, sources)
    with client:
        result = search_result(client, message="graph learning")
    assert result["success"] is (outcome != "outage")
    assert result["total"] == (1 if outcome == "fallback" else 0)
    pipeline = next(call for call in result["tool_calls"] if call["name"] == "search_pipeline")
    assert pipeline["status"] == ("error" if outcome == "outage" else "success")
    assert result["message"] == ("search_pipeline_error" if outcome == "outage" else None)


@pytest.mark.parametrize("outcome", ["empty", "outage", "partial"])
def test_real_multi_provider_searcher_preserves_failure_status(tmp_path, monkeypatch, outcome):
    async def failing_provider(*args, **kwargs):
        raise RuntimeError("synthetic provider unavailable")
    async def successful_provider(*args, **kwargs):
        return [Paper(title="Graph learning", arxiv_id="2609.00001", year=2026)] if outcome == "partial" else []
    for name in ("_search_arxiv_src", "_search_dblp_src", "_search_openalex_src"):
        monkeypatch.setattr(paper_searcher, name, successful_provider if outcome == "empty" else failing_provider)
    if outcome == "partial":
        monkeypatch.setattr(paper_searcher, "_search_openalex_src", successful_provider)
    sources = paper_searcher.PaperSearcher(download_dir=str(tmp_path / "downloads"))
    client, _ = api_client(tmp_path, sources)
    with client:
        result = search_result(client, message="graph learning")
    asyncio.run(sources.aclose())
    assert result["success"] is (outcome != "outage")
    assert result["total"] == (1 if outcome == "partial" else 0)
    assert result["message"] == ("search_pipeline_error" if outcome == "outage" else None)


def test_dblp_http_failure_survives_provider_fallback_chain(tmp_path, monkeypatch):
    sources = paper_searcher.PaperSearcher(download_dir=str(tmp_path / "downloads"))
    async def unavailable(*args, **kwargs):
        raise RuntimeError("synthetic HTTP 503")
    monkeypatch.setattr(sources, "_async_http_get_with_retry", unavailable)

    async def scenario():
        try:
            with pytest.raises(RuntimeError, match="synthetic HTTP 503"):
                await sources.search_async("graph learning", sources=["dblp"])
        finally:
            await sources.aclose()
    asyncio.run(scenario())


def test_intent_cache_uses_complete_input_and_never_shares_mutable_intents(offline_environment):
    llm = offline_environment
    llm.payload = lambda messages: {
        "query": "graph learning", "year_from": 2020 if "only 2020" in messages[-1]["content"] else 2025,
        "use_llm_rank": False,
    }
    agent = search_agent.SearchAgent()
    prefix = "Find graph learning research with robustness and generalization. " * 5
    first = agent.understand_intent(prefix + "only 2020")
    second = agent.understand_intent(prefix + "only 2025")
    assert (first.year_from, second.year_from) == (2020, 2025)
    second.year_from = 1999
    assert agent.understand_intent(prefix + "only 2025").year_from == 2025
    assert len(llm.calls) == 2
    assert all([m["role"] for m in call] == ["system", "user"] for call in llm.calls)


def test_search_history_is_bounded_explicit_and_not_retained_between_requests(tmp_path, offline_environment):
    llm = offline_environment
    client, _ = api_client(tmp_path, Sources())
    with client:
        search_result(client, message="PRIVATE_FIRST_REQUEST")
        history = [{"role": "user", "content": f"OLD_{i}" + "x" * 2000} for i in range(20)]
        history += [{"role": "system", "content": "UNTRUSTED_SYSTEM_ROLE"},
                    {"role": "user", "content": "Focus on graph neural networks"}]
        current = "c" * 1980 + "CURRENT_QUERY_END"
        search_result(client, message=current, history=history)
        search_result(client, message="INDEPENDENT_THIRD_REQUEST")
    prompt = llm.calls[1][-1]["content"]
    assert "Focus on graph neural networks" in prompt and current in prompt
    assert "OLD_0" not in prompt and "UNTRUSTED_SYSTEM_ROLE" not in prompt
    assert "PRIVATE_FIRST_REQUEST" not in prompt
    assert prompt.count("x") < 1100
    assert "Focus on graph neural networks" not in llm.calls[2][-1]["content"]
    assert all(len(call) == 2 for call in llm.calls)


@pytest.mark.parametrize("character", ["汉", "😀"])
@pytest.mark.parametrize("via_http", [False, True])
def test_intent_utf8_budget_preserves_schema_and_query_ends_during_retries(
    tmp_path, offline_environment, character, via_http,
):
    llm = offline_environment
    # The first response forces a genuine parser retry with an oversized model
    # output in the correction. SimpleAgent and prompt formatting remain real.
    llm.payload = lambda messages: character * 6000 if len(llm.calls) == 1 else {
        "query": "graph learning", "use_llm_rank": False,
    }
    query = "QUERY_BEGIN " + character * (1950 if via_http else 3500) + " QUERY_END only 2025"
    if via_http:
        history = [{"role": "user", "content": "OLD_HISTORY " + character * 6000} for _ in range(20)]
        client, _ = api_client(tmp_path, Sources())
        with client:
            result = search_result(client, message=query, history=history)
        assert result["success"]
    else:
        assert search_agent.SearchAgent().understand_intent(query).query == "graph learning"

    assert len(llm.calls) == 2
    for call in llm.calls:
        assert all(len(message["content"].encode("utf-8")) <= 9000 for message in call)
        prompt = call[-1]["content"]
        assert "QUERY_BEGIN" in prompt and "QUERY_END only 2025" in prompt
        schema_text = prompt.split("## 输出格式（只输出 JSON）\n", 1)[1]
        schema, _ = json.JSONDecoder().raw_decode(schema_text)
        assert set(schema) == {"search", "ranking", "flags"}
        assert "arxiv_id_list" in schema["search"] and "main_conference_proceedings_only" in schema["flags"]
        assert "## 核心原则" in prompt and "## 当前日期" in prompt
    assert "## 修正要求" in llm.calls[1][-1]["content"]
    assert "上次未返回可解析的 JSON 对象" in llm.calls[1][-1]["content"]


@pytest.mark.parametrize("request_flag,intent_flag,expected", [(True, False, True), (False, True, False), (None, True, True)])
def test_tavily_flags_reach_real_presearch(tmp_path, monkeypatch, offline_environment, request_flag, intent_flag, expected):
    offline_environment.payload = {"query": "graph learning", "use_llm_rank": False, "use_tavily": intent_flag}
    monkeypatch.setattr(get_settings(), "tavily_api_key", "offline-placeholder")
    calls = []

    async def tavily(**kwargs):
        calls.append(kwargs)
        return []

    monkeypatch.setattr(web_presearch, "tavily_search_async", tavily)
    client, _ = api_client(tmp_path, Sources())
    request = {"message": "graph learning"}
    if request_flag is not None:
        request["use_tavily"] = request_flag
    with client:
        result = search_result(client, **request)
    assert bool(calls) is expected
    assert result["search_params"]["use_tavily"] is expected


@pytest.mark.parametrize("stage", ["init", "intent"])
def test_search_deadline_releases_event_loop_while_model_is_running(monkeypatch, stage):
    released, entered, finished = threading.Event(), threading.Event(), threading.Event()
    llm = ScriptedLLM()

    def wait_for_release():
        entered.set()
        try:
            released.wait(1.0)
        finally:
            finished.set()

    if stage == "init":
        def make_llm():
            wait_for_release()
            return llm
        monkeypatch.setattr(base, "get_llm", make_llm)
        monkeypatch.setattr(search_route, "_SEARCH_AGENT_INIT_SEC", 0.06)
    else:
        invoke = llm.invoke
        def blocked_invoke(*args, **kwargs):
            wait_for_release()
            return invoke(*args, **kwargs)
        monkeypatch.setattr(llm, "invoke", blocked_invoke)
        monkeypatch.setattr(base, "get_llm", lambda: llm)
        monkeypatch.setattr(search_route, "_SEARCH_AGENT_WALL_SEC", 0.06)

    async def scenario():
        ticks = []
        async def tick():
            await asyncio.sleep(0.01)
            ticks.append(time.monotonic())
        tick_task = asyncio.create_task(tick())
        started = time.monotonic()
        try:
            result, error = await search_route._search_agent_impl(
                search_route.SearchAgentMessage(message="graph learning"), Sources()
            )
            elapsed = time.monotonic() - started
            await tick_task
            assert entered.is_set() and not released.is_set()
            assert elapsed < 0.5 and ticks[0] - started < 0.5
            assert not result.success and error.status_code == 504
        finally:
            released.set()
            await asyncio.to_thread(finished.wait, 1.0)
            # Let the released parser finish before fixtures restore its model.
            await asyncio.sleep(0.02)
    asyncio.run(scenario())


def test_pipeline_ranking_deadline_returns_recall_while_real_rank_model_waits(monkeypatch):
    released, entered = threading.Event(), threading.Event()
    llm = ScriptedLLM({"rankings": [{"index": 0, "score": 0.9}]})
    invoke = llm.invoke
    def blocked_invoke(*args, **kwargs):
        entered.set()
        released.wait(1.0)
        return invoke(*args, **kwargs)
    monkeypatch.setattr(llm, "invoke", blocked_invoke)
    monkeypatch.setattr(paper_ranker, "get_llm", lambda: llm)
    original = SearchRuntimeConfig.from_settings
    monkeypatch.setattr(SearchRuntimeConfig, "from_settings", classmethod(
        lambda cls, *args: replace(original(*args), rank_wall=0.06)
    ))
    paper = Paper(title="Graph learning", arxiv_id="2609.10001", year=2026)

    async def scenario():
        start = time.monotonic()
        try:
            result = await search_pipeline.run_search_pipeline_async(
                searcher=Sources([paper]), plan=ResolvedSearchPlan(query="graph learning")
            )
            assert entered.is_set() and time.monotonic() - start < 0.5
            assert result.ranking_method == "recall_fallback_timeout"
            assert result.metadata["ranking_timeout"] is True
            assert [r.paper.title for r in result.ranked] == [paper.title]
        finally:
            released.set()
            await asyncio.sleep(0.05)
    asyncio.run(scenario())


def test_sync_provider_timeout_is_cancellable():
    released = threading.Event()
    provider = SimpleNamespace(search=lambda *a, **kw: released.wait(1.0) and [])
    runtime = SearchRuntimeConfig.from_settings(get_settings(), ResolvedSearchPlan())

    async def scenario():
        start = time.monotonic()
        try:
            papers, error = await _run_search_job(
                provider, RecallJob("primary", "graph", ["arxiv"], 10, required=True, timeout_sec=0.04), runtime
            )
            assert time.monotonic() - start < 0.5 and not papers and "超时" in error
        finally:
            released.set()
    asyncio.run(scenario())


def test_pinned_provider_wait_obeys_request_cancellation():
    released, entered = threading.Event(), threading.Event()
    provider = Sources()
    def pinned(ids):
        entered.set()
        released.wait(1.0)
        return []
    provider.search_by_arxiv_ids = pinned

    async def scenario():
        start = time.monotonic()
        try:
            with pytest.raises(TimeoutError), anyio.fail_after(0.06):
                await search_pipeline.run_search_pipeline_async(
                    searcher=provider,
                    plan=ResolvedSearchPlan(query="graph learning", arxiv_id_list=["2609.00001"], use_llm_rank=False),
                )
            assert entered.is_set() and time.monotonic() - start < 0.5
        finally:
            released.set()
    asyncio.run(scenario())


def test_daily_http_fallback_deduplicates_and_excludes_freshly_shown_papers(tmp_path):
    papers = [Paper(title=f"Graph research {n}", doi=f"10.1234/{n}", year=2026) for n in range(2)]
    sources = Sources(fail=True, fallback=papers + [papers[0]])
    client, _ = api_client(tmp_path, sources)
    with client:
        first = client.post("/api/papers/daily", json={"personalized_k": 3, "use_llm_theme_keywords": False})
        assert first.status_code == 200, first.text
        first = first.json()
        assert first["personalized_total"] == 2 and first["arxiv_selected_total"] == 0
        assert len({p["doi"] for p in first["personalized"]}) == 2
        assert client.get("/api/papers/daily").json()["personalized_total"] == 2
        second = client.post("/api/papers/daily", json={"personalized_k": 3, "use_llm_theme_keywords": False}).json()
    assert second["personalized_total"] == second["arxiv_selected_total"] == 0
    assert any(call[0] == "openalex" for call in sources.calls)


def test_daily_http_llm_selection_never_repeats_papers_within_or_between_lists(tmp_path, monkeypatch):
    selector = ScriptedLLM({"personalized": [0, 0, 1], "general": [1, 2, 2]})
    monkeypatch.setattr(daily_service, "is_llm_configured", lambda: True)
    monkeypatch.setattr(daily_service, "get_llm", lambda: selector)
    papers = [Paper(title=f"Unique research {n}", arxiv_id=f"2609.0000{n}", year=2026) for n in range(3)]
    client, _ = api_client(tmp_path, Sources(papers))
    with client:
        response = client.post("/api/papers/daily", json={"personalized_k": 2, "use_llm_theme_keywords": False})
    assert response.status_code == 200, response.text
    result = response.json()
    ids = [p["arxiv_id"] for p in result["personalized"] + result["arxiv_selected"]]
    assert len(ids) == len(set(ids)) == 3
    assert result["personalized_total"] == 2 and result["arxiv_selected_total"] == 1


@pytest.mark.parametrize("paper", [
    Paper(title="Skipped arxiv", arxiv_id="2609.00001v2", year=2026),
    Paper(title="Skipped DOI", doi="10.1234/example", year=2026),
    Paper(title="Skipped title", year=2026),
    Paper(title="Skipped_title_no_year"),
])
def test_skip_http_persists_canonical_exclusion_and_negative_memory(tmp_path, offline_environment, paper):
    offline_environment.payload = {"topics_to_downrank": ["graph"], "confidence": 0.8}
    client, database = api_client(tmp_path, Sources([paper]))
    with client:
        result = client.post("/api/papers/daily/feedback", json={
            # Exercise the literal key emitted by the older real frontend too.
            "identity_key": (identity(paper) if paper.arxiv_id or paper.doi else
                             f"title_hash:{paper.title}_{paper.year if paper.year is not None else 'null'}"),
            "title": paper.title, "action": "skip",
        })
    assert result.status_code == 200 and result.json()["success"]
    assert identity(paper) in feedback.get_skipped_papers(database.db_path, include_shown=False)
    with sqlite3.connect(database.db_path) as conn:
        assert conn.execute("SELECT identity_key FROM negative_pref_memory").fetchone()[0] == identity(paper)
        assert conn.execute("SELECT paper_identity_key FROM daily_recommend_feedback").fetchone()[0] == identity(paper)
    selected, general = daily_service._select_personalized_and_general(
        candidates=[paper], external_unique=[paper], personalized_k=3, general_k=1,
        skipped_papers=feedback.get_skipped_papers(database.db_path), mem_kw=set(), daily_paper_identity_sig_fn=identity,
    )
    assert not selected and not general


def test_legacy_feedback_keys_remain_effective(tmp_path):
    db = str(tmp_path / "legacy.db")
    feedback.ensure_tables(db)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(db) as conn:
        conn.executemany(
            "INSERT INTO daily_recommend_feedback(date_key,paper_identity_key,identity_type,action,created_at) VALUES(?,?,?,'skip',?)",
            [(today, "2609.00001v2", "arxiv", 1), (today, "10.1234/ABC", "doi", 1),
             (today, "ty:old paper|2026", "title_hash", 1), (today, "arxiv:2609.00002", "title_hash", 1),
             (today, "Old_Title_2025", "title_hash", 1), (today, "title_hash:NoYear_undefined", "title_hash", 1)],
        )
    assert feedback.get_skipped_papers(db) == {
        "arxiv:2609.00001", "arxiv:2609.00002", "doi:10.1234/abc", "ty:old paper|2026",
        "ty:old_title|2025", "ty:noyear|0",
    }


def test_profile_cache_refreshes_feedback_exclusions_memory_and_database_dimensions(tmp_path):
    db = PaperDatabase(str(tmp_path / "first" / "papers.db"))
    other = PaperDatabase(str(tmp_path / "second" / "papers.db"))
    store = MemoryStore(db.db_path)
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    async def context(path=db.db_path, ids=(), shown=True):
        return await daily_support.get_or_load_user_context(
            db_path=path, lib_ids=list(ids), log=LOG, include_shown_exclusions=shown
        )

    async def scenario():
        first = await context(shown=False)
        assert not first[3]
        feedback.record_daily_shown_papers(db.db_path, today, [{"identity_key": "arxiv:2609.11111", "title": "Shown"}])
        feedback.record_feedback(db.db_path, date_key=today, paper_identity_key="doi:10.1/saved", identity_type="doi",
                                 action=feedback.FeedbackAction.SAVE, title="Quasistellar discovery")
        second = await context()
        assert "arxiv:2609.11111" in second[3] and "quasistellar" in second[0]
        assert "arxiv:2609.11111" not in (await context(shown=False))[3]
        store.add(scope="global", paper_id=None, kind="preference", content="spectroscopy")
        assert "spectroscopy" in (await context())[0]
        store.add(scope="paper", paper_id=42, kind="working", content="magnetohydrodynamics")
        assert "magnetohydrodynamics" in (await context(ids=[42]))[0]
        assert "magnetohydrodynamics" not in (await context(ids=[]))[0]
        isolated = await context(other.db_path)
        assert "spectroscopy" not in isolated[0] and not isolated[3]
    asyncio.run(scenario())


def test_behavior_profile_reads_rows_and_filters_real_saved_timestamps(tmp_path):
    db = PaperDatabase(str(tmp_path / "papers.db"))
    old, _ = db.add_paper(Paper(title="Ancient astronomy", category="Astronomy"))
    fresh, _ = db.add_paper(Paper(title="Modern spectroscopy", category="Physics"))
    with sqlite3.connect(db.db_path) as conn:
        conn.execute("UPDATE papers SET created_at='2000-01-01 00:00:00' WHERE id=?", (old,))
    profile = UserBehaviorAnalytics(db.db_path).get_user_interest_profile(saved_days=30)
    assert fresh in profile.high_interest_paper_ids and old not in profile.high_interest_paper_ids
    assert profile.top_subdomains == [("physics", 1)]
    assert "spectroscopy" in dict(profile.top_keywords)


def test_auto_refresh_rechecks_today_after_midnight(tmp_path, monkeypatch):
    class Clock(datetime.datetime):
        day_number = 26
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, cls.day_number)

    db = PaperDatabase(str(tmp_path / "papers.db"))
    from app.services.daily.daily_cache_store import set_cache
    set_cache(db.db_path, date_key="2026-09-26", cache_key="default", payload={"personalized": [{"title": "Yesterday"}]})
    monkeypatch.setattr(datetime, "datetime", Clock)
    monkeypatch.setattr(dependencies, "get_db_path", lambda: db.db_path)
    monkeypatch.setattr(dependencies, "get_searcher", lambda: Sources())
    monkeypatch.setattr(get_settings(), "papergraph_daily_auto_refresh", True)
    original_compute = daily_service.compute_daily_papers
    computations = []
    async def compute(**kwargs):
        result = await original_compute(**kwargs)
        computations.append(result.date_key)
        raise asyncio.CancelledError()
    monkeypatch.setattr(daily_service, "compute_daily_papers", compute)
    sleeps = 0
    original_sleep = asyncio.sleep
    async def sleep(seconds):
        nonlocal sleeps
        if seconds < 1:
            return await original_sleep(seconds)
        sleeps += 1
        if sleeps == 3:
            Clock.day_number = 27
        if sleeps > 3:
            raise asyncio.CancelledError()
    monkeypatch.setattr(daily_auto_refresh.asyncio, "sleep", sleep)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(daily_auto_refresh.daily_auto_refresh_loop(SimpleNamespace(state=SimpleNamespace())))
    assert computations == ["2026-09-27"]
