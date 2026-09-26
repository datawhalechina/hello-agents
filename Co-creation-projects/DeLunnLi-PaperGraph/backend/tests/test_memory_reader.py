"""Offline regressions for restored memory and the reader HTTP workflow."""

from __future__ import annotations

import socket
import sqlite3
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.paper import Paper
from app.core.storage import PaperDatabase
from app.services.memory.agent_memory import AgentMemory
from app.services.memory.memory_store import MemoryStore
from app.services.memory.sqlite_document_store_compat import SQLiteDocumentStore


@pytest.fixture(autouse=True)
def offline_data_dir(tmp_path, monkeypatch):
    from app.services.llm import llm_service
    from app.settings import get_settings

    def no_network(*args, **kwargs):
        raise AssertionError("This regression suite must not access the network")

    def no_llm():
        raise RuntimeError("LLM intentionally unconfigured for offline tests")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    monkeypatch.setattr(llm_service, "get_llm", no_llm)
    monkeypatch.setattr(get_settings(), "data_dir", str(tmp_path))
    monkeypatch.setattr(get_settings(), "tavily_api_key", "")


def test_reader_memory_persists_and_isolates_papers(tmp_path):
    app_db = str(tmp_path / "papers.db")
    memory = MemoryStore(app_db)
    memory.add(scope="paper", paper_id=1, kind="working", content="第一篇独有的实验结论")
    memory.add(scope="paper", paper_id=2, kind="working", content="第二篇独有的推导过程")
    memory.upsert_single(scope="global", paper_id=None, kind="preference", content="偏好中文解释")
    memory.upsert_single(scope="global", paper_id=None, kind="preference", content="偏好简洁中文解释")

    reopened = MemoryStore(app_db)
    first = reopened.build_context_block(paper_id=1)
    second = reopened.build_context_block(paper_id=2)
    assert "第一篇独有的实验结论" in first
    assert "第二篇独有的推导过程" not in first
    assert "第二篇独有的推导过程" in second
    assert "第一篇独有的实验结论" not in second
    assert "偏好简洁中文解释" in first and "偏好简洁中文解释" in second
    assert reopened.list_recent_contents(scope="global", paper_id=None, kinds=["preference"]) == ["偏好简洁中文解释"]
    assert reopened.get_context_for_query(paper_id=2, query="第一篇") == ""
    assert reopened.clear_all(scope="paper", paper_id=1) == 1
    assert "第二篇独有的推导过程" in reopened.build_context_block(paper_id=2)
    assert Path(memory.db_path) == tmp_path / "reader_memory.db"
    assert not Path(app_db).exists(), "reader memory must use its own SQLite file"


def test_memory_creates_data_directory_without_embedding_service(tmp_path):
    memory = MemoryStore(str(tmp_path / "fresh" / "papers.db"))
    memory.add(scope="paper", paper_id=4, kind="short", content="稀疏注意力降低计算开销")
    assert "稀疏注意力" in memory.search(scope="paper", paper_id=4, query="稀疏注意力")
    agent_memory = AgentMemory()
    assert Path(agent_memory.db_path) == tmp_path / "agent_memory.db"
    assert agent_memory.db_path != memory.db_path


def test_agent_memories_same_second_persist_without_overwriting(tmp_path, monkeypatch):
    from app.services.memory import agent_memory

    monkeypatch.setattr(agent_memory.time, "time", lambda: 1_800_000_000.0)
    memory = AgentMemory()
    first_id = memory.add(agent_name="reader", content="Sparse attention reduces quadratic compute")
    second_id = memory.add(agent_name="reader", content="Protein folding predicts molecular geometry")
    assert first_id != second_id
    assert memory.add(agent_name="reader", content="Sparse attention reduces quadratic compute") == first_id
    memory.add(agent_name="search", content="Private search results")
    memory.add(agent_name="reader", content="Shared benchmark insight", shared=True, tags=["reader"])

    reopened = AgentMemory(db_path=memory.db_path)
    own = reopened.recent(agent_name="reader", memory_types=["working"], limit=10, shared=False)
    assert set(own) == {"Sparse attention reduces quadratic compute", "Protein folding predicts molecular geometry"}
    context = reopened.build_context_block(agent_name="reader", tags=["reader"])
    assert "Shared benchmark insight" in context
    assert "Private search results" not in context
    assert "Shared benchmark insight" not in reopened.build_context_block(agent_name="search", tags=["search"])


def test_compat_store_reads_legacy_metadata(tmp_path):
    db_path = str(tmp_path / "legacy.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute("""CREATE TABLE memories (
            memory_id TEXT PRIMARY KEY, user_id TEXT, content TEXT, memory_type TEXT,
            importance REAL, metadata TEXT, created_at REAL, updated_at REAL
        )""")
        conn.execute("INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     ("old", "reader", "Saved note", "working", 0.7, '{"tags":["reader"]}', 100, 200))
    store = SQLiteDocumentStore(db_path)
    row = store.search_memories(user_id="reader")[0]
    assert row["timestamp"] == 200
    assert row["properties"] == {"tags": ["reader"]}
    assert store.add_memory(user_id="reader", content="New note")
    assert len(SQLiteDocumentStore(db_path).search_memories(user_id="reader")) == 2


def test_failed_llm_compression_keeps_original_memories(tmp_path):
    memory = MemoryStore(str(tmp_path / "papers.db"))
    notes = [f"独立研究问题{i}" for i in range(8)]
    for note in notes:
        memory.add(scope="paper", paper_id=1, kind="working", content=note)
    assert memory.compress_working(paper_id=1) == "compression failed"
    assert set(memory.list_recent_contents(scope="paper", paper_id=1, kinds=["working"])) == set(notes)


@pytest.mark.parametrize("structured_response", [False, True])
def test_memory_llm_adapter_is_stateless_and_accepts_framework_outputs(tmp_path, monkeypatch, structured_response):
    from app.services.llm import llm_service

    calls = []

    class StubLLM:
        def invoke(self, messages, **kwargs):
            calls.append(messages)
            return SimpleNamespace(content="合并后的阅读重点") if structured_response else "合并后的阅读重点"

    monkeypatch.setattr(llm_service, "get_llm", lambda: StubLLM())
    memory = MemoryStore(str(tmp_path / "papers.db"))
    assert memory._summarize_via_llm([{"content": "第一篇独有的实验"}]) == "合并后的阅读重点"
    assert memory._summarize_via_llm([{"content": "第二篇独有的方法"}]) == "合并后的阅读重点"
    assert len(calls) == 2
    assert all(len(messages) == 1 for messages in calls)
    assert "第一篇独有的实验" not in calls[1][0]["content"]


def test_reader_agent_keeps_current_question_with_full_context_and_memory(monkeypatch):
    from app.agents.paper_analysis_agent import PaperAnalysisAgent
    from app.services.memory import agent_memory

    memory = AgentMemory()
    for i in range(12):
        memory.add(agent_name="paper_analysis", content=chr(0x4E00 + i) * 400)
    for i in range(8):
        memory.add(agent_name="paper_analysis", content=chr(0x4F00 + i) * 400, shared=True)
    assert len(memory.build_context_block(agent_name="paper_analysis", max_chars=10000)) > 7200
    assert len(memory.build_context_block(agent_name="paper_analysis")) <= 1200
    monkeypatch.setattr(agent_memory, "_agent_memory_singleton", memory)

    recorded_prompts = []

    class RecordingReader:
        def run(self, prompt):
            recorded_prompts.append(prompt)
            return "回答当前问题。"

    agent = PaperAnalysisAgent.__new__(PaperAnalysisAgent)
    agent._reader_lookup_lock = threading.Lock()
    agent._reader_lookup_buffer = []
    agent._reader_reco_ref_offset = {}
    agent._reader = RecordingReader()
    marker = "CURRENT_QUESTION_EXACT_MARKER"
    question = "问" * (900 - len(marker)) + marker
    context = "CURRENT_PAPER_EVIDENCE\n" + "当篇证据" * 3000
    history = ("用户：" + "往" * 100 + "\n助手：" + "昔" * 100 + "\n") * 40 + "RECENT_HISTORY_MARKER"
    reply, _, _ = agent.paper_reader_reply(
        context, history, question + "OUTSIDE_QUESTION_BUDGET",
        {"paper_id": 1, "title": "Current paper"},
    )
    assert reply == "回答当前问题。"
    assert len(recorded_prompts) == 1
    prompt = recorded_prompts[0]
    assert len(prompt) <= 7200
    assert prompt.startswith("【当前文献材料】\nCURRENT_PAPER_EVIDENCE")
    assert "RECENT_HISTORY_MARKER" in prompt
    assert "【共享/独立记忆】" in prompt
    history_section = prompt.split("【对话历史】\n", 1)[1].split("\n\n【共享/独立记忆】", 1)[0]
    assert len(history_section.encode("utf-8")) >= 2000
    assert len(prompt.encode("utf-8")) <= 9000
    assert prompt.endswith(f"【用户最新问题】\n{question}")
    assert "OUTSIDE_QUESTION_BUDGET" not in prompt


def test_memory_extractor_bounds_accumulated_notes_and_maximum_input(tmp_path, monkeypatch):
    from app.services.llm import llm_service
    from app.services.memory import memory_store

    memory = MemoryStore(str(tmp_path / "papers.db"))
    memory.upsert_single(scope="global", paper_id=None, kind="preference", content="偏" * 10000)
    for i in range(8):
        memory.add(scope="paper", paper_id=1, kind="short", content=chr(0x4E00 + i) * 240)
    captured = []

    def extract_stub(**kwargs):
        captured.append(kwargs["user_prompt"])
        return {}

    monkeypatch.setattr(memory_store, "run_json_task", extract_stub)
    monkeypatch.setattr(llm_service, "get_llm", lambda: object())
    question = "问" * (900 - len("LATEST_QUESTION")) + "LATEST_QUESTION"
    memory.extract_memory_via_llm(1, question + "问" * 11100, "答" * 12000)
    assert len(captured) == 1
    prompt = captured[0]
    assert len(prompt) <= 3600
    assert f"【用户最新问题】\n{question}\n\n" in prompt
    assert prompt.endswith("【助手回复】\n" + "答" * 1200)
    assert "偏" * 600 in prompt and "偏" * 601 not in prompt
    # Prompt clipping must not rewrite the stored preference.
    assert memory.list_recent_contents(scope="global", paper_id=None, kinds=["preference"]) == ["偏" * 10000]


class StubReaderAgent:
    def __init__(self):
        self.calls = []

    def paper_reader_reply(self, context, history, message, snapshot):
        self.calls.append((context, history, message, snapshot))
        return f"测试回复：{snapshot['title']}", [], []


@pytest.fixture
def reader_api(tmp_path):
    from app.api.routes.paper_reader import get_paper_reader_service, router
    from app.services.reader.paper_reader_service import PaperReaderService

    db = PaperDatabase(str(tmp_path / "papers.db"))
    first_id, _ = db.add_paper(Paper(title="Attention study", abstract="Sparse attention reduces computation."))
    second_id, _ = db.add_paper(Paper(title="Protein study", abstract="Protein geometry prediction."))
    agent = StubReaderAgent()
    service = PaperReaderService(db, agent=agent)
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_paper_reader_service] = lambda: service
    with TestClient(app) as client:
        yield client, db, agent, first_id, second_id


def test_reader_opening_chat_and_history_use_persisted_memory(reader_api):
    client, db, agent, first_id, second_id = reader_api
    memory = MemoryStore(db.db_path)
    memory.add(scope="paper", paper_id=first_id, kind="working", content="第一篇实验备注")
    memory.add(scope="paper", paper_id=second_id, kind="working", content="第二篇实验备注")
    opening = client.post("/api/ai/paper-reader/opening", json={"paper_id": first_id})
    assert opening.status_code == 200, opening.text
    assert opening.json()["opening"] == "测试回复：Attention study"
    assert "第一篇实验备注" in agent.calls[0][0]
    assert "第二篇实验备注" not in agent.calls[0][0]
    cached = client.post("/api/ai/paper-reader/opening", json={"paper_id": first_id})
    assert cached.json() == opening.json()
    assert len(agent.calls) == 1

    question = "算法复杂度是多少？"
    response = client.post("/api/ai/paper-reader/chat", json={
        "paper_id": first_id,
        "user_message": question,
        "messages": [{"role": "assistant", "content": opening.json()["opening"]}],
    })
    assert response.status_code == 200, response.text
    assert response.json()["success"] is True
    assert response.json()["reply"] == "测试回复：Attention study"
    assert "助手：测试回复：Attention study" in agent.calls[-1][1]
    assert question in MemoryStore(db.db_path).build_context_block(paper_id=first_id)
    assert question not in MemoryStore(db.db_path).build_context_block(paper_id=second_id)

    history = client.get("/api/ai/paper-reader/history", params={"paper_id": first_id}).json()["turns"]
    assert [turn["role"] for turn in history] == ["assistant", "user", "assistant"]
    assert history[1]["content"] == question
    followup = client.post("/api/ai/paper-reader/chat", json={
        "paper_id": first_id,
        "user_message": "继续解释",
        "messages": [{"role": turn["role"], "content": turn["content"]} for turn in history],
    })
    assert followup.status_code == 200, followup.text
    assert question in agent.calls[-1][0], "a new request must recover saved reading memory"
    assert question in agent.calls[-1][1]

    other_opening = client.post("/api/ai/paper-reader/opening", json={"paper_id": second_id})
    assert other_opening.status_code == 200, other_opening.text
    assert "第二篇实验备注" in agent.calls[-1][0]
    assert "第一篇实验备注" not in agent.calls[-1][0]
    assert question not in agent.calls[-1][0]


@pytest.mark.parametrize("endpoint,body", [
    ("opening", {"paper_id": 99999}),
    ("chat", {"paper_id": 99999, "user_message": "What is the method?", "messages": []}),
])
def test_reader_missing_paper_returns_404(reader_api, endpoint, body):
    client, _, agent, _, _ = reader_api
    response = client.post(f"/api/ai/paper-reader/{endpoint}", json=body)
    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "文献不存在"
    assert not agent.calls
