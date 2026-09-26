"""Real reader/service/storage regressions with offline model and search boundaries."""
from __future__ import annotations

import asyncio
import copy
import json
import os
import socket
import sqlite3
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace as NS

import fitz
import pytest
from fastapi import BackgroundTasks

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.agents import base, paper_analysis_agent
from app.agents.paper_analysis_agent import PaperAnalysisAgent
from app.agents.support.reader_pdf_parse_tool import ReaderPdfParseTool
from app.agents.support.reader_reference_lookup_tool import (
    ReaderReferenceLookupTool, paper_matches_reference, resolve_references_via_openalex,
)
from app.agents.support.reader_table_tool import ReaderTableTool
from app.core.paper import Paper
from app.core.storage import PaperDatabase
from app.services.llm import agent_runtime, llm_service
from app.services.llm.agent_config import papergraph_agent_config
from app.services.memory import agent_memory
from app.services.memory.memory_store import MemoryStore
from app.services.reader import paper_reader_context as context
from app.services.reader.paper_reader_history import append_turn, ensure_opening_turn, list_turns
from app.services.reader.paper_reader_service import PaperReaderService
from app.services.reader.paper_reader_structure import parse_pdf_merged_text_to_json
from app.settings import get_settings


def response(text="Offline answer.", tool=None, args=None):
    calls = [] if tool is None else [NS(id="tool-" + str(time.monotonic_ns()), function=NS(name=tool, arguments=json.dumps(args or {})))]
    return NS(choices=[NS(message=NS(content=text if tool is None else None, tool_calls=calls))], usage={})


class Model:
    model = "offline-reader-regressions"

    def __init__(self):
        self.calls = []
        self.plain_calls = []
        self.fail = False

    def invoke_with_tools(self, messages, tools, **kwargs):
        self.calls.append(copy.deepcopy(messages))
        if self.fail:
            raise RuntimeError("Temporary offline provider failure")
        return response()

    def invoke(self, messages, **kwargs):
        self.plain_calls.append(copy.deepcopy(messages))
        return NS(content="[]", usage={})


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("No network is allowed in reader regression tests")
    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr(socket, "create_connection", reject)
    monkeypatch.setattr(socket, "getaddrinfo", reject)
    monkeypatch.setattr(get_settings(), "data_dir", str(tmp_path))
    monkeypatch.setattr(get_settings(), "tavily_api_key", "")
    monkeypatch.setattr(agent_memory, "_agent_memory_singleton", None)
    monkeypatch.setattr(paper_analysis_agent, "is_llm_configured", lambda: False)

    def config():
        conf = papergraph_agent_config()
        conf.trace_enabled = conf.session_enabled = conf.subagent_enabled = False
        conf.todowrite_enabled = conf.devlog_enabled = False
        return conf
    monkeypatch.setattr(paper_analysis_agent, "papergraph_agent_config", config)
    monkeypatch.setattr(agent_runtime, "papergraph_agent_config", config)


@pytest.fixture
def make_agent(monkeypatch):
    def make(model=None):
        model = model or Model()
        monkeypatch.setattr(base, "get_llm", lambda: model)
        monkeypatch.setattr(llm_service, "get_llm", lambda: model)
        return PaperAnalysisAgent(), model
    return make


def fake_search(monkeypatch, results):
    from app.api import dependencies
    queries = []
    class Search:
        async def search_async(self, query, **kwargs):
            queries.append(query)
            return results(query) if callable(results) else results
    monkeypatch.setattr(dependencies, "get_searcher", lambda: Search())
    return queries


def test_reader_request_owns_pdf_results_and_framework_history(make_agent, monkeypatch):
    a_ready, b_ready, release_b = (threading.Event() for _ in range(3))
    class ConcurrentModel(Model):
        def __init__(self):
            super().__init__()
            self.by_thread = {}
            self.outputs = {}
        def invoke_with_tools(self, messages, tools, **kwargs):
            name = threading.current_thread().name
            step = self.by_thread.get(name, 0)
            self.by_thread[name] = step + 1
            if step == 0:
                if name == "A":
                    a_ready.set()
                    assert b_ready.wait(5)
                else:
                    b_ready.set()
                    assert release_b.wait(5)
                return response(tool="reader_pdf_structure")
            if step == 1:
                return response(tool="reader_reference_lookup")
            self.outputs[name] = [item["content"] for item in messages if item["role"] == "tool"]
            return response()
    model = ConcurrentModel()
    agent, _ = make_agent(model)
    fake_search(monkeypatch, lambda q: [Paper(title=f"{q[0]} verified benchmark method", doi=f"10.1234/{q[0]}")])
    replies, errors = {}, []
    def run(name, pid):
        try:
            replies[name] = agent.paper_reader_reply(f"{name} evidence", "", "Explain the method", {
                "paper_id": pid, "title": f"Current {name}",
                "references": [f"{name} verified benchmark method. doi:10.1234/{name}"],
                "_pdf_merged_for_structure": f"# 1 Introduction\n{name}_PDF_SENTINEL " + name * 300,
            })
        except Exception as exc:
            errors.append(exc)
    a = threading.Thread(target=run, args=("A", 11), name="A")
    b = threading.Thread(target=run, args=("B", 12), name="B")
    try:
        a.start()
        assert a_ready.wait(5)
        b.start()
        a.join(5)
    finally:
        release_b.set()
        a.join(5)
        if b.ident:
            b.join(5)
    assert not errors and not a.is_alive() and not b.is_alive()
    for name, other in [("A", "B"), ("B", "A")]:
        assert name + "_PDF_SENTINEL" in model.outputs[name][0]
        assert other + "_PDF_SENTINEL" not in model.outputs[name][0]
        assert [p.title for p in replies[name][1]] == [name + " verified benchmark method"]
        assert replies[name][2] == ["bibliography"]


def test_sequential_papers_and_interpreter_do_not_inherit_model_history(make_agent):
    agent, model = make_agent()
    agent.paper_reader_reply("ONLY_A_FULL_PDF_EVIDENCE", "", "Explain A", {"paper_id": 1})
    agent.paper_reader_reply("ONLY_B_EVIDENCE", "", "Explain B", {"paper_id": 2})
    assert [m["role"] for m in model.calls[1]] == ["system", "user"]
    assert "ONLY_A_FULL_PDF_EVIDENCE" not in json.dumps(model.calls[1])
    agent._reader_chat_llm("INTERPRETER_A")
    agent._reader_chat_llm("INTERPRETER_B")
    assert "INTERPRETER_A" not in json.dumps(model.plain_calls[-1])


def test_real_pdf_table_keeps_header_separator_and_rows(tmp_path):
    path = tmp_path / "table.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        xs, ys = [70, 250, 400], [90, 120, 150, 180]
        for x in xs:
            page.draw_line((x, ys[0]), (x, ys[-1]))
        for y in ys:
            page.draw_line((xs[0], y), (xs[-1], y))
        for row, values in enumerate([["Method", "Score"], ["Alpha", "91.5"], ["Beta", "87.2"]]):
            for col, text in enumerate(values):
                page.insert_text((xs[col] + 8, ys[row] + 20), text)
        doc.save(path)
    md = context.extract_pdf_tables_markdown(str(path))
    assert len(ReaderTableTool._parse_table_blocks(md)) == 1
    result = ReaderTableTool(get_snap=lambda: {"_pdf_abspath": str(path)}).run({"table_ref": "1"})
    assert all(x in result.text for x in ["Method", "Score", "Alpha", "91.5", "Beta", "87.2"])
    multiple = ReaderTableTool._parse_table_blocks("## Table 3\n|a|b|\n|---|---|\n|1|2|\n\n## Table 4\n|x|y|\n|---|---|\n|3|4|")
    assert [t["label"] for t in multiple] == ["Table 3", "Table 4"]


def test_timeout_returns_at_deadline_and_bounds_orphan_workers(monkeypatch):
    monkeypatch.setattr(agent_runtime, "_TIMEOUT_SLOTS", threading.BoundedSemaphore(1))
    entered, release, done = (threading.Event() for _ in range(3))
    def slow():
        entered.set()
        release.wait(5)
        done.set()
    begin = time.monotonic()
    try:
        with pytest.raises(TimeoutError):
            agent_runtime._run_with_optional_timeout(slow, .03)
        assert entered.is_set() and not done.is_set()
        assert time.monotonic() - begin < .4
        with pytest.raises(TimeoutError, match="capacity"):
            agent_runtime._run_with_optional_timeout(lambda: None, 1)
    finally:
        release.set()
        assert done.wait(2)
    # The worker releases its slot just after finishing its function.
    for _ in range(100):
        try:
            assert agent_runtime._run_with_optional_timeout(lambda: "recovered", .2) == "recovered"
            break
        except TimeoutError:
            time.sleep(.001)
    else:
        pytest.fail("Completed timeout worker leaked its slot")


def test_history_window_contains_latest_turns_without_reinserting_opening(tmp_path):
    path = str(tmp_path / "history.db")
    ensure_opening_turn(path, paper_id=8, opening_text="Initial opening")
    for i in range(202):
        append_turn(path, paper_id=8, role="user" if i % 2 == 0 else "assistant", content=f"TURN_{i:03}")
    turns = list_turns(path, paper_id=8, limit=200)
    assert (turns[0]["content"], turns[-1]["content"]) == ("TURN_002", "TURN_201")
    ensure_opening_turn(path, paper_id=8, opening_text="Initial opening")
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM paper_reader_turns").fetchone()[0] == 203


def test_reference_fallback_queries_actual_bibliography_and_merges_only_verified_results(make_agent, monkeypatch):
    matching = Paper(title="A reproducible sparse attention benchmark", doi="10.1234/correct")
    unrelated = Paper(title="Broad survey of sparse attention", doi="10.1234/unrelated")
    queries = fake_search(monkeypatch, [unrelated, matching])
    agent, _ = make_agent()
    result = agent.paper_reader_reply("Evidence", "", "推荐两篇参考文献，只要引用", {
        "title": "Current source paper", "references": ["Doe. A reproducible sparse attention benchmark. doi:10.1234/correct"],
    })
    assert len(queries) == 1 and "doi:10.1234/correct" in queries[0]
    assert [p.title for p in result[1]] == [matching.title]
    assert result[2] == ["bibliography"]


def test_reference_tool_rejects_topic_hits_and_conflicting_identifiers(monkeypatch):
    ref = "Doe. A reproducible sparse attention benchmark. doi:10.1234/correct"
    wrong = Paper(title="A reproducible sparse attention benchmark", doi="10.1234/wrong")
    queries = fake_search(monkeypatch, [wrong, Paper(title="A related benchmark survey")])
    collected = []
    tool = ReaderReferenceLookupTool(get_snap=lambda: {"references": [ref]}, on_papers_found=lambda ps, source: collected.extend(ps), get_user_message=lambda: "推荐相关论文")
    tool.run({"reference_focus": "sparse attention"})
    assert queries == [ref] and collected == []
    assert not paper_matches_reference(wrong, ref)
    assert paper_matches_reference(Paper(title="Attention Is All You Need"), "Vaswani et al. Attention Is All You Need. 2017.")
    assert paper_matches_reference(Paper(title="Identifier match", arxiv_id="2307.05973"), "arXiv:2307.05973v2")


def test_failed_opening_is_not_cached_or_recorded_and_next_call_recovers(tmp_path, make_agent):
    db = PaperDatabase(str(tmp_path / "papers.db"))
    pid, _ = db.add_paper(Paper(title="Transient opening", abstract="Evidence"))
    agent, model = make_agent()
    service = PaperReaderService(db, agent)
    model.fail = True
    first = asyncio.run(service.get_opening(paper_id=pid, background_tasks=BackgroundTasks()))
    assert "请稍后重试" in first["opening"]
    assert list_turns(db.db_path, paper_id=pid) == []
    model.fail = False
    second = asyncio.run(service.get_opening(paper_id=pid, background_tasks=BackgroundTasks()))
    third = asyncio.run(service.get_opening(paper_id=pid, background_tasks=BackgroundTasks()))
    assert second["opening"] == third["opening"] == "Offline answer."
    assert len(model.calls) == 2
    assert [t["content"] for t in list_turns(db.db_path, paper_id=pid)] == ["Offline answer."]


def test_opening_invalidates_when_metadata_or_pdf_changes(tmp_path, make_agent):
    db = PaperDatabase(str(tmp_path / "papers.db"))
    pid, _ = db.add_paper(Paper(title="Original", abstract="Original findings"))
    class OpeningModel(Model):
        def invoke_with_tools(self, messages, tools, **kwargs):
            self.calls.append(copy.deepcopy(messages))
            return response(text=f"OPENING_VERSION_{len(self.calls)}")
    agent, model = make_agent(OpeningModel())
    service = PaperReaderService(db, agent)
    def opening():
        return asyncio.run(service.get_opening(paper_id=pid, background_tasks=BackgroundTasks()))
    opening()
    append_turn(db.db_path, paper_id=pid, role="user", content="Keep this question")
    append_turn(db.db_path, paper_id=pid, role="assistant", content="Keep this ordinary answer")
    db.update_paper(pid, title="Corrected", abstract="Corrected findings")
    opening()
    assert len(model.calls) == 2
    history = asyncio.run(service.get_history(paper_id=pid, limit=200))
    assert [t["content"] for t in history] == ["OPENING_VERSION_2", "Keep this question", "Keep this ordinary answer"]
    path = tmp_path / "evidence.pdf"
    def write_pdf(marker):
        with fitz.open() as doc:
            doc.new_page().insert_text((72, 72), marker + "\n" + "PDF evidence. " * 20)
            doc.save(path)
    write_pdf("PDF_VERSION_A")
    db.set_local_pdf_path(pid, path.name)
    opening()
    write_pdf("PDF_VERSION_B")
    opening()
    assert len(model.calls) == 4
    assert "PDF_VERSION_B" in context._cache_get(db.db_path, pid, str(path))

    history = asyncio.run(service.get_history(paper_id=pid, limit=200))
    assert [t["content"] for t in history] == ["OPENING_VERSION_4", "Keep this question", "Keep this ordinary answer"]


@pytest.mark.parametrize("heading", ["References", "## References", "## 7 References", "# Bibliography", "## 参考文献"])
def test_reference_section_never_contains_body(heading):
    parsed = parse_pdf_merged_text_to_json("# 1 Introduction\nNOT_A_REFERENCE_BODY\n" + heading + "\n[1] Doe, A. A reference title with enough detail. 2024.\n[2] Roe, B. Another genuine reference title. 2025.")
    assert "NOT_A_REFERENCE_BODY" not in parsed["references"]["raw"]
    assert parsed["references"]["entry_count"] == 2
    assert context.extract_references_section_raw_from_pdf_text("# Introduction\n" + "No references here. " * 20) == ""


def test_section_numbers_pagination_valid_json_and_oversized_errors_are_bounded():
    merged = "# 1 Introduction\n" + "INTRO " * 100 + "\n# 4.5 Experiments\n" + "实验数据" * 12000 + "\n## References\n[1] Doe, A. A verified reference title. 2024."
    tool = ReaderPdfParseTool(get_snap=lambda: {"_pdf_merged_for_structure": merged})
    first = tool.run({"focus_section": "Sec 4.5"}).text
    assert "实验数据" in first and "next_offset=" in first
    offset = int(first.rsplit("next_offset=", 1)[1].split(")", 1)[0])
    second = tool.run({"focus_section": "4.5", "offset": offset}).text
    assert "实验数据" in second
    directory = tool.run({}).text
    obj = json.loads(directory.split("\n", 1)[1])
    assert obj["references"]["entry_count"] == 1
    assert any(ch.get("number") == "4.5" for ch in obj["chapters"])
    errors = [tool.run({"focus_section": "不存在" * 20000}).text]
    table = ReaderTableTool(get_snap=lambda: {"_pdf_merged_for_structure": "Table 1\n|a|b|\n|---|---|\n|1|2|\n" + "x" * 250})
    errors.append(table.run({"table_ref": "不存在" * 20000}).text)
    assert all(len(x.encode("utf-8")) <= 6000 for x in [first, second, directory, *errors])


def test_repeated_chat_reuses_pdf_cache_and_schedules_no_reextraction(tmp_path, make_agent, monkeypatch):
    path = tmp_path / "cached.pdf"
    with fitz.open() as doc:
        doc.new_page().insert_text((72, 72), "# 1 Introduction\nCached real PDF evidence. " * 10)
        doc.save(path)
    db = PaperDatabase(str(tmp_path / "papers.db"))
    pid, _ = db.add_paper(Paper(title="Cached PDF", abstract="Evidence", local_pdf_path=path.name))
    agent, _ = make_agent()
    service = PaperReaderService(db, agent)
    original, count = context.extract_pdf_text_full, []
    def extract(pdf):
        count.append(pdf)
        return original(pdf)
    monkeypatch.setattr(context, "extract_pdf_text_full", extract)
    for _ in range(2):
        tasks = BackgroundTasks()
        asyncio.run(service.process_chat(paper_id=pid, messages=[], user_message="Explain the method", background_tasks=tasks))
        assert "compute_and_cache_excerpt" not in [t.func.__name__ for t in tasks.tasks]
    assert count == [str(path)]


def test_taxonomy_uses_valid_retry_response(make_agent, monkeypatch):
    class TaxonomyModel(Model):
        def invoke(self, messages, **kwargs):
            self.plain_calls.append(copy.deepcopy(messages))
            return NS(content="not JSON" if len(self.plain_calls) == 1 else '{"majors":["计算机","数学","生物","未分类"]}')
    agent, model = make_agent(TaxonomyModel())
    monkeypatch.setattr(paper_analysis_agent, "_MAJOR_WHITELIST", None)
    assert agent._get_major_whitelist() == ("计算机", "数学", "生物", "未分类")
    assert len(model.plain_calls) == 2


def test_backlogged_compression_deletes_only_complete_notes_sent_to_model(tmp_path, monkeypatch):
    class SummaryModel(Model):
        def invoke(self, messages, **kwargs):
            self.plain_calls.append(copy.deepcopy(messages))
            return NS(content="A saved compressed summary.")
    model = SummaryModel()
    monkeypatch.setattr(llm_service, "get_llm", lambda: model)
    store = MemoryStore(str(tmp_path / "papers.db"))
    notes = [f"BACKLOG_NOTE_{i:02}" for i in range(31)] + ["LARGE_UNSENT_NOTE " + "汉" * 12000]
    for note in notes:
        store.add(scope="paper", paper_id=3, kind="working", content=note)
    assert store.compress_working(paper_id=3) == "compressed"
    sent = model.plain_calls[-1][0]["content"]
    remaining = store.list_recent_contents(scope="paper", paper_id=3, kinds=["working"], limit=100)
    assert all(note in sent or note in remaining for note in notes)
    assert len(remaining) >= 12 and notes[-1] in remaining
    assert len(sent.encode("utf-8")) <= 9000
    assert store.list_recent_contents(scope="paper", paper_id=3, kinds=["long"])


def test_recommendation_prompts_bound_metadata_and_aggregate_candidates(monkeypatch):
    from app.services.reader import reader_recommend_llm as recommend
    model = Model()
    monkeypatch.setattr(recommend, "is_llm_configured", lambda: True)
    monkeypatch.setattr(recommend, "get_llm", lambda: model)
    snap = {"title": "题" * 30000, "abstract": "摘要" * 30000, "keywords": ["关键词" * 10000] * 24}
    recommend.extract_title_queries_from_ref_blob_llm("Reference " * 10000, snap)
    pairs = [(Paper(title=str(i) + "候选" * 10000, doi="d" * 10000, journal="期刊" * 10000), "bibliography") for i in range(80)]
    recommend.rerank_reader_recommend_pairs_by_llm(snap, pairs, user_message="问" * 10000, history_lines="史" * 10000)
    assert len(model.plain_calls) == 2
    assert all(len(m["content"].encode("utf-8")) <= 9000 for call in model.plain_calls for m in call)


def test_reader_preserves_latest_question_under_byte_budget(make_agent):
    agent, model = make_agent()
    question = "🧠" * 890 + "QUESTION!"
    agent.paper_reader_reply("证据" * 10000, "历史" * 10000 + "RECENT", question, {})
    prompt = model.calls[0][-1]["content"]
    assert prompt.endswith(question) and "RECENT" in prompt
    assert len(prompt.encode("utf-8")) <= 9000


def test_parallel_classifications_use_independent_bounded_prompts(make_agent, monkeypatch):
    a_ready, b_ready, release_b = (threading.Event() for _ in range(3))
    class ClassifierModel(Model):
        def invoke(self, messages, **kwargs):
            self.plain_calls.append(copy.deepcopy(messages))
            prompt = messages[-1]["content"]
            if "任务：归类（大类）" in prompt:
                if "PAPER_A" in prompt:
                    a_ready.set()
                    assert b_ready.wait(5)
                else:
                    b_ready.set()
                    assert release_b.wait(5)
                return NS(content='{"major":"计算机"}')
            return NS(content='{"category":"计算机／机器学习","tags":["实验"]}')
    agent, model = make_agent(ClassifierModel())
    monkeypatch.setattr(paper_analysis_agent, "_MAJOR_WHITELIST", ("计算机", "数学", "生物", "未分类"))
    errors, outputs = [], []
    def classify(name):
        try:
            outputs.append(agent.classify_for_library(name, "大型摘要" * 10000, None, existing_categories=["计算机／机器学习", "计算机／视觉"]))
        except Exception as exc:
            errors.append(exc)
    a = threading.Thread(target=classify, args=("PAPER_A",))
    b = threading.Thread(target=classify, args=("PAPER_B",))
    try:
        a.start()
        assert a_ready.wait(5)
        b.start()
        a.join(5)
    finally:
        release_b.set()
        a.join(5)
        if b.ident:
            b.join(5)
    assert not errors and len(outputs) == 2
    assert len(model.plain_calls) == 4
    for messages in model.plain_calls:
        assert [m["role"] for m in messages] == ["system", "user"]
        prompt = messages[-1]["content"]
        assert not ("PAPER_A" in prompt and "PAPER_B" in prompt)
        assert len(prompt.encode("utf-8")) <= 9000


def test_automatic_memory_backlog_recovery_preserves_unsent_notes(tmp_path, monkeypatch):
    class SummaryModel(Model):
        def invoke(self, messages, **kwargs):
            self.plain_calls.append(copy.deepcopy(messages))
            return NS(content="Saved batch summary")
    model = SummaryModel()
    monkeypatch.setattr(llm_service, "get_llm", lambda: model)
    store = MemoryStore(str(tmp_path / "papers.db"))
    notes = [f"AUTO_BACKLOG_{i:03}" for i in range(60)]
    for note in notes:
        store.store.add_memory(user_id="papergraph:paper:8", content=note, memory_type="working")
    store.add(scope="paper", paper_id=8, kind="working", content="LATEST_TRIGGER")
    sent = model.plain_calls[-1][0]["content"]
    remaining = store.list_recent_contents(scope="paper", paper_id=8, kinds=["working"], limit=100)
    assert all(note in sent or note in remaining for note in notes)
    assert "LATEST_TRIGGER" in remaining
    assert len(remaining) == 41


@pytest.mark.parametrize("first,second", [("[1]", "[2]"), ("1.", "2.")])
def test_explicit_reference_numbers_survive_pdf_line_unwrapping(first, second):
    parsed = parse_pdf_merged_text_to_json(
        f"# 1 Introduction\nBody facts.\n# 9 References\n{first} Jane Doe. A complete first reference title. 2024.\n"
        f"{second} John Roe. A complete second reference title. 2025."
    )
    assert parsed["references"]["entry_count"] == 2
    assert "first reference" in parsed["references"]["entries"][0]
    assert "second reference" in parsed["references"]["entries"][1]


def test_opening_history_adopts_only_verified_legacy_opening(tmp_path):
    from app.services.reader.reader_opening_cache import set_cached_opening
    path = str(tmp_path / "legacy.db")
    # Build the pre-marker schema to exercise migration as well as adoption.
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE paper_reader_turns(id INTEGER PRIMARY KEY AUTOINCREMENT,paper_id INTEGER NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created_at INTEGER NOT NULL)")
        conn.execute("INSERT INTO paper_reader_turns(paper_id,role,content,created_at) VALUES(1,'assistant','Old cached opening',100)")
        conn.execute("INSERT INTO paper_reader_turns(paper_id,role,content,created_at) VALUES(2,'assistant','Ordinary historical answer',100)")
    set_cached_opening(path, 1, "Old cached opening")
    ensure_opening_turn(path, paper_id=1, opening_text="New generated opening")
    ensure_opening_turn(path, paper_id=2, opening_text="Generated introduction")
    assert [t["content"] for t in list_turns(path, paper_id=1)] == ["New generated opening"]
    assert [t["content"] for t in list_turns(path, paper_id=2)] == ["Generated introduction", "Ordinary historical answer"]
    ensure_opening_turn(path, paper_id=2, opening_text="Updated introduction")
    assert [t["content"] for t in list_turns(path, paper_id=2)] == ["Updated introduction", "Ordinary historical answer"]


@pytest.mark.parametrize("caption", ["Caption" * 10000, "超长表注🧠" * 10000])
def test_table_tool_bounds_unmatched_captions_and_retains_matched_rows(caption):
    merged = "\n\n".join(
        f"Table {number} {caption}\n| a | b |\n|---|---|\n|1|2|" for number in range(1, 9)
    )
    tool = ReaderTableTool(get_snap=lambda: {"_pdf_merged_for_structure": merged})
    missing = tool.run({"table_ref": "not-found"}).text
    matched = tool.run({"table_ref": "1"}).text
    assert "未找到匹配" in missing and "Table 8" in missing
    assert "|1|2|" in matched
    assert all(len(text.encode("utf-8")) <= 6000 for text in (missing, matched))


def test_pdf_focus_bounds_pathological_numeric_heading():
    merged = "# " + "4" * 20000 + " Method\n" + "METHOD_EVIDENCE " * 400
    tool = ReaderPdfParseTool(get_snap=lambda: {"_pdf_merged_for_structure": merged})
    focused = tool.run({"focus_section": "Method"}).text
    unmatched = tool.run({"focus_section": "absent"}).text
    directory = tool.run({}).text
    assert "METHOD_EVIDENCE" in focused
    assert all(len(text.encode("utf-8")) <= 6000 for text in (focused, unmatched, directory))
    assert json.loads(directory.split("\n", 1)[1])["chapter_count"] == 1


@pytest.mark.parametrize("tool_name", ["table", "pdf", "paper", "references"])
def test_reader_tool_snapshot_errors_bound_exception_text(tool_name):
    from app.agents.support.reader_paper_lookup_tool import ReaderPaperLookupTool
    def unavailable():
        raise RuntimeError("超长快照错误🧠" * 10000)
    if tool_name == "table":
        tool, arguments = ReaderTableTool(get_snap=unavailable), {"table_ref": "1"}
    elif tool_name == "pdf":
        tool, arguments = ReaderPdfParseTool(get_snap=unavailable), {}
    elif tool_name == "paper":
        tool = ReaderPaperLookupTool(get_snap=unavailable, on_papers_found=lambda *args: None)
        arguments = {"query": "A real title", "from_pdf_references_section": True}
    else:
        tool = ReaderReferenceLookupTool(get_snap=unavailable, on_papers_found=lambda *args: None, get_user_message=lambda: "References")
        arguments = {}
    assert len(tool.run(arguments).text.encode("utf-8")) <= 6000


@pytest.mark.parametrize("invalid_task", ["taxonomy", "major", "fine"])
def test_analysis_json_retry_discards_oversized_malformed_history(make_agent, monkeypatch, invalid_task):
    malformed = "MALFORMED_OUTPUT_SENTINEL:" + "无效输出🧠" * 2500
    assert len(malformed.encode("utf-8")) > 37500

    class RetryModel(Model):
        def __init__(self):
            super().__init__()
            self.failed = False
        def invoke(self, messages, **kwargs):
            self.plain_calls.append(copy.deepcopy(messages))
            prompt = messages[-1]["content"]
            task = "taxonomy" if "生成顶层大类" in prompt else "major" if "任务：归类（大类）" in prompt else "fine"
            if task == invalid_task and not self.failed:
                self.failed = True
                return NS(content=malformed)
            content = {
                "taxonomy": '{"majors":["计算机","数学","生物","未分类"]}',
                "major": '{"major":"计算机"}',
                "fine": '{"category":"计算机／机器学习","tags":["实验"]}',
            }[task]
            return NS(content=content)

    agent, model = make_agent(RetryModel())
    if invalid_task == "taxonomy":
        monkeypatch.setattr(paper_analysis_agent, "_MAJOR_WHITELIST", None)
        assert agent._get_major_whitelist() == ("计算机", "数学", "生物", "未分类")
        assert len(model.plain_calls) == 2
    else:
        monkeypatch.setattr(paper_analysis_agent, "_MAJOR_WHITELIST", ("计算机", "数学", "生物", "未分类"))
        category, tags = agent.classify_for_library(
            "CURRENT_CLASSIFICATION_TASK", "Methods evidence", None,
            existing_categories=["计算机／机器学习", "计算机／视觉"],
        )
        assert "机器学习" in category and tags == ["实验"]
        assert len(model.plain_calls) == 3
    retries = [call for call in model.plain_calls if "上次输出无法解析" in call[-1]["content"]]
    assert len(retries) == 1
    for call in model.plain_calls:
        assert [item["role"] for item in call] == ["system", "user"]
        assert "MALFORMED_OUTPUT_SENTINEL" not in json.dumps(call, ensure_ascii=False)
        assert all(len(item["content"].encode("utf-8")) <= 9000 for item in call)
    task_marker = "生成顶层大类" if invalid_task == "taxonomy" else "CURRENT_CLASSIFICATION_TASK"
    assert task_marker in retries[0][-1]["content"]


def test_memory_block_keeps_long_preference_prefix_inside_complete_byte_budget(tmp_path):
    store = MemoryStore(str(tmp_path / "papers.db"))
    preference = "PREFERENCE_PREFIX:" + "偏" * 699
    assert len(preference.encode("utf-8")) == 2115
    store.upsert_single(scope="global", paper_id=None, kind="preference", content=preference)
    block = store.build_context_block(paper_id=1)
    assert block.startswith("[preference] PREFERENCE_PREFIX:")
    assert 1100 < len(block.encode("utf-8")) <= 1200
    assert store.list_recent_contents(scope="global", paper_id=None, kinds=["preference"]) == [preference]


@pytest.mark.parametrize("budget", [0, 12, 13, 16, 40, 1200, 9500])
def test_memory_block_reserves_labels_separators_and_remaining_bytes(tmp_path, budget):
    store = MemoryStore(str(tmp_path / "papers.db"))
    store.add(scope="paper", paper_id=1, kind="long", content="FIRST", importance=1)
    store.upsert_single(scope="global", paper_id=None, kind="preference", content="PREFERENCE_PREFIX:" + "🧠" * 4000, importance=.5)
    block = store.build_context_block(paper_id=1, max_tokens=budget)
    assert len(block.encode("utf-8")) <= min(budget, 9000)
    if budget >= 40:
        assert block.startswith("[long] FIRST\n[preference] PREF")
    if budget >= 1200:
        assert "PREFERENCE_PREFIX:" in block
