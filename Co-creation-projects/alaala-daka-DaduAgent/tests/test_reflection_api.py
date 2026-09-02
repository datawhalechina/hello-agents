"""
反思笔记 REST API 测试（api/reflections）

临时组装 FastAPI app 挂载 router，用内存 fake Chroma 替换 _reflection_chroma 单例，
避免网络（DashScope embedding）与污染真实 Chromadb/knowledge_file。
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_tools import agent_tools
from api.reflections import router


class FakeChroma:
    """内存版 Chroma：模拟 get / add_texts / delete。重复 id 的 add 抛异常。"""

    def __init__(self):
        self.records: dict[str, dict] = {}

    def get(self, ids=None, include=None):
        matched = list(self.records.keys()) if ids is None else [i for i in ids if i in self.records]
        return {
            "ids": matched,
            "metadatas": [self.records[i]["metadata"] for i in matched],
            "documents": [self.records[i]["document"] for i in matched],
        }

    def add_texts(self, texts, ids, metadatas):
        for text, rid, meta in zip(texts, ids, metadatas):
            if rid in self.records:
                raise Exception(f"duplicate id: {rid}")
            self.records[rid] = {"document": text, "metadata": meta}

    def delete(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        for rid in ids:
            self.records.pop(rid, None)


@pytest.fixture
def ctx(monkeypatch):
    fake = FakeChroma()
    monkeypatch.setattr(agent_tools, "_reflection_chroma", fake)
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app), fake


def _create(client, **overrides):
    body = {"error_desc": "错", "solution": "解", "philosophy": "哲"}
    body.update(overrides)
    return client.post("/api/reflections", json=body)


def test_list_empty(ctx):
    client, _ = ctx
    r = client.get("/api/reflections")
    assert r.status_code == 200
    assert r.json() == {"reflections": []}


def test_create_and_list(ctx):
    client, _ = ctx
    r = _create(client, tags="a,b", severity="high")
    assert r.status_code == 200
    item = r.json()["reflection"]
    assert item["ref_id"] == "ref_1"
    assert item["tags"] == "a,b"
    assert item["severity"] == "high"

    r2 = client.get("/api/reflections")
    assert r2.status_code == 200
    assert len(r2.json()["reflections"]) == 1


def test_create_validation_400(ctx):
    client, _ = ctx
    r = _create(client, error_desc="")
    assert r.status_code == 400
    assert "不能为空" in r.json()["detail"]


def test_get_single(ctx):
    client, _ = ctx
    _create(client)
    assert client.get("/api/reflections/ref_1").status_code == 200
    assert client.get("/api/reflections/ref_1").json()["reflection"]["ref_id"] == "ref_1"
    assert client.get("/api/reflections/ref_9").status_code == 404


def test_update_partial(ctx):
    client, _ = ctx
    _create(client, tags="x", severity="low")
    r = client.put("/api/reflections/ref_1", json={"solution": "B", "severity": "high"})
    assert r.status_code == 200
    item = r.json()["reflection"]
    assert item["solution"] == "B"
    assert item["severity"] == "high"
    assert item["error_desc"] == "错"
    assert item["tags"] == "x"


def test_update_not_found_404(ctx):
    client, _ = ctx
    r = client.put("/api/reflections/ref_9", json={"solution": "x"})
    assert r.status_code == 404


def test_delete(ctx):
    client, _ = ctx
    _create(client)
    assert client.delete("/api/reflections/ref_1").json() == {"deleted": "ref_1"}
    assert client.delete("/api/reflections/ref_1").status_code == 404
