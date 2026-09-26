"""Exercise actual SimpleAgent messages for isolated, bounded graph extraction."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys
from types import SimpleNamespace

import pytest
from hello_agents import SimpleAgent

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents import base, knowledge_graph_agent
from app.agents.knowledge_graph_agent import KnowledgeGraphAgent
from app.services.llm.context_budget import MODEL_ITEM_BYTES
from app.services.memory import agent_memory
from app.settings import get_settings


class RecordingModel:
    model = "offline-graph-recording-model"

    def __init__(self):
        self.calls = []

    def invoke(self, messages, **kwargs):
        self.calls.append(deepcopy(messages))
        payload = json.loads(messages[-1]["content"])
        return json.dumps({"edges": [
            {"target_paper_id": c["paper_id"], "relation": "references", "score": 0.9,
             "evidence": "Abstract explicitly references the candidate method."}
            for c in payload["candidates"]
        ]})


@pytest.fixture
def model(tmp_path, monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Graph tests must not access external services")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(get_settings(), "data_dir", str(tmp_path))
    model = RecordingModel()
    monkeypatch.setattr(base, "get_llm", lambda: model)
    monkeypatch.setattr(agent_memory, "get_agent_memory", lambda: SimpleNamespace(add=lambda **kwargs: None))
    return model


@pytest.mark.parametrize("injected", [False, True])
def test_real_simple_agent_history_isolated_across_chunks_and_papers(model, injected):
    runner = None
    if injected:
        runner = SimpleAgent(
            name="injected-graph-test", llm=model, system_prompt="Extract graph relations.",
            config=knowledge_graph_agent.papergraph_agent_config(),
        )
        runner.run(json.dumps({"new_paper": {"title": "STALE_PREVIOUS_HISTORY"}, "candidates": []}))
        model.calls.clear()
    agent = KnowledgeGraphAgent(agent=runner, chunk_size=1)
    edges, error = agent.infer_edges(
        new_paper={"id": 1, "title": "FIRST_PAPER", "abstract": "References methods A and B."},
        candidates=[{"id": 2, "title": "Method A"}, {"id": 3, "title": "Method B"}],
    )
    assert error is None and {e["target_paper_id"] for e in edges} == {2, 3}
    agent.infer_edges(new_paper={"id": 4, "title": "SECOND_PAPER"},
                      candidates=[{"id": 5, "title": "Different method"}])
    assert len(model.calls) == 3
    assert all([m["role"] for m in call] == ["system", "user"] for call in model.calls)
    assert all("STALE_PREVIOUS_HISTORY" not in str(call) for call in model.calls)
    assert "FIRST_PAPER" not in str(model.calls[-1])
    payloads = [json.loads(call[-1]["content"]) for call in model.calls]
    assert [[c["paper_id"] for c in p["candidates"]] for p in payloads] == [[2], [3], [5]]
    if runner is not None:
        assert runner._build_messages("next") == [
            {"role": "system", "content": "Extract graph relations."},
            {"role": "user", "content": "next"},
        ]


@pytest.mark.parametrize("text", ["中文证据" * 10000, '\x00\\\n"证据' * 10000])
def test_large_metadata_packs_valid_json_by_serialized_utf8_bytes(model, text):
    def paper(pid):
        return {
            "id": pid, "title": f"Paper {pid}: {text}", "abstract": text,
            "keywords": [text] * 30, "category": text, "source": text,
            "pdf_excerpt": text, "related_work_excerpt": text, "year": "2025",
        }
    agent = KnowledgeGraphAgent(chunk_size=20, max_edges=32)
    edges, error = agent.infer_edges(new_paper=paper(1), candidates=[paper(i) for i in range(2, 26)])
    assert error is None
    assert {edge["target_paper_id"] for edge in edges} == set(range(2, 26))
    # Two count-only chunks would overflow. Actual packing must use the byte ceiling.
    assert len(model.calls) > 2
    seen = []
    for call in model.calls:
        assert [message["role"] for message in call] == ["system", "user"]
        assert all(len(message["content"].encode("utf-8")) <= MODEL_ITEM_BYTES for message in call)
        payload = json.loads(call[-1]["content"])
        assert payload["new_paper"]["paper_id"] == 1
        assert payload["new_paper"]["title"].startswith("Paper 1:")
        assert payload["new_paper"]["abstract"]
        assert payload["new_paper"]["pdf_excerpt"]
        assert payload["new_paper"]["related_work_excerpt"]
        assert "Partial" in payload["evidence_scope"]
        assert payload["candidates"]
        for candidate in payload["candidates"]:
            assert candidate["abstract"] and candidate["pdf_excerpt"]
            assert len(candidate["keywords"]) <= 12
            assert all(len(k.encode("utf-8")) <= 64 for k in candidate["keywords"])
            assert len(candidate["source"].encode("utf-8")) <= 96
            assert len(candidate["category"].encode("utf-8")) <= 96
            seen.append(candidate["paper_id"])
    assert seen == list(range(2, 26))


def test_injected_run_only_agent_remains_supported(model):
    class Runner:
        def __init__(self):
            self.payloads = []

        def run(self, text):
            self.payloads.append(json.loads(text))
            return '{"edges": []}'

    runner = Runner()
    agent = KnowledgeGraphAgent(agent=runner)
    assert agent.infer_edges(new_paper={"id": 1, "title": "New"},
                             candidates=[{"id": 2, "title": "Candidate"}]) == ([], None)
    assert runner.payloads[0]["candidates"][0]["paper_id"] == 2
