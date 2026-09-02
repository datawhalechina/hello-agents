"""
反思笔记数据层单元测试（agent_tools.agent_tools 的结构化访问函数）

用内存 fake Chroma 替换 _reflection_chroma 单例，避免网络（DashScope embedding）
与污染真实 Chromadb/knowledge_file。导入本模块会构建真实 Chroma 单例（本地 sqlite，
无网络），属预期行为（与 tests/test_agent_stream.py 一致）。
"""
import pytest

from agent_tools import agent_tools


class FakeChroma:
    """内存版 Chroma：模拟 get / add_texts / delete。重复 id 的 add 抛异常。"""

    def __init__(self, initial: list | None = None):
        self.records: dict[str, dict] = {}  # id -> {"document", "metadata"}
        for rid, doc, meta in (initial or []):
            self.records[rid] = {"document": doc, "metadata": meta}

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
def fake_chroma(monkeypatch):
    fake = FakeChroma()
    monkeypatch.setattr(agent_tools, "_reflection_chroma", fake)
    return fake


def _seed(fake, ref_id, timestamp="2026-08-01 10:00:00", tags="general", severity="medium"):
    fake.add_texts(
        texts=["错误描述:错\n解决方案:解\n哲学理解:哲"],
        ids=[ref_id],
        metadatas=[{
            "ref_id": ref_id,
            "error_desc": "错",
            "solution": "解",
            "philosophy": "哲",
            "tags": tags,
            "severity": severity,
            "timestamp": timestamp,
        }],
    )


# ── _next_ref_id 修复：max+1，删除后不复用 ──

def test_next_ref_id_max_plus_one(fake_chroma):
    _seed(fake_chroma, "ref_1")
    _seed(fake_chroma, "ref_3")
    assert agent_tools._next_ref_id() == "ref_4"


def test_next_ref_id_uses_max_not_count_after_restart(monkeypatch):
    """回归：库中 [ref_1, ref_2, ref_4, ref_5]（重启前已删过 ref_3）。
    旧实现按总数 len=4 会生成 ref_5（与现存冲突）；新实现按 max=5 → ref_6。"""
    fake = FakeChroma()
    for rid in ["ref_1", "ref_2", "ref_4", "ref_5"]:
        _seed(fake, rid)
    monkeypatch.setattr(agent_tools, "_reflection_chroma", fake)
    assert agent_tools._next_ref_id() == "ref_6"


def test_next_ref_id_ignores_malformed_ids(monkeypatch):
    fake = FakeChroma()
    _seed(fake, "ref_2")
    fake.add_texts(
        texts=["x"], ids=["ref_abc"],
        metadatas=[{"ref_id": "ref_abc", "error_desc": "e", "solution": "s", "philosophy": "p",
                    "tags": "g", "severity": "low", "timestamp": "2026-01-01 00:00:00"}],
    )
    monkeypatch.setattr(agent_tools, "_reflection_chroma", fake)
    assert agent_tools._next_ref_id() == "ref_3"


# ── create_reflection ──

def test_create_reflection_defaults(fake_chroma):
    item = agent_tools.create_reflection("空指针", "加检查", "先考虑边界")
    assert item["ref_id"] == "ref_1"
    assert item["tags"] == "general"
    assert item["severity"] == "medium"
    assert item["timestamp"]
    assert item["updated_at"] == ""
    # 底层 page_content 已组装
    stored = fake_chroma.get(ids=["ref_1"])
    assert "空指针" in stored["documents"][0]


def test_create_reflection_custom_normalizes_tags(fake_chroma):
    item = agent_tools.create_reflection("a", "b", "c", tags="  token ,截断 ", severity="high")
    assert item["ref_id"] == "ref_1"
    assert item["tags"] == "token,截断"
    assert item["severity"] == "high"


def test_create_reflection_validation(fake_chroma):
    with pytest.raises(ValueError):
        agent_tools.create_reflection("", "b", "c")
    with pytest.raises(ValueError):
        agent_tools.create_reflection("a", "", "c")
    with pytest.raises(ValueError):
        agent_tools.create_reflection("a", "b", "  ")
    with pytest.raises(ValueError):
        agent_tools.create_reflection("a", "b", "c", severity="urgent")


# ── update_reflection 局部更新 ──

def test_update_reflection_partial(fake_chroma):
    created = agent_tools.create_reflection("错", "解", "哲", tags="a", severity="low")
    item = agent_tools.update_reflection(created["ref_id"], solution="新解", tags="b", severity="high")
    assert item["solution"] == "新解"
    assert item["error_desc"] == "错"
    assert item["philosophy"] == "哲"
    assert item["tags"] == "b"
    assert item["severity"] == "high"
    assert item["timestamp"] == created["timestamp"]  # 原时间戳保留
    assert item["updated_at"]                          # 写入更新时间
    assert item["ref_id"] == created["ref_id"]         # id 不变


def test_update_reflection_validation(fake_chroma):
    agent_tools.create_reflection("a", "b", "c")
    with pytest.raises(ValueError):
        agent_tools.update_reflection("ref_1", solution="")


def test_update_reflection_not_found(fake_chroma):
    assert agent_tools.update_reflection("ref_999", solution="x") is None


# ── get / list / delete ──

def test_get_reflection(fake_chroma):
    agent_tools.create_reflection("a", "b", "c")
    assert agent_tools.get_reflection("ref_1")["ref_id"] == "ref_1"
    assert agent_tools.get_reflection("ref_9") is None


def test_list_reflections_empty(fake_chroma):
    assert agent_tools.list_reflections() == []


def test_list_reflections_sorted_desc(fake_chroma):
    _seed(fake_chroma, "ref_1", timestamp="2026-01-01 10:00:00")
    _seed(fake_chroma, "ref_2", timestamp="2026-03-01 10:00:00")
    _seed(fake_chroma, "ref_3", timestamp="2026-02-01 10:00:00")
    items = agent_tools.list_reflections()
    assert [i["ref_id"] for i in items] == ["ref_2", "ref_3", "ref_1"]


def test_list_reflections_sorted_by_severity_then_time(fake_chroma):
    """重要优先：fatal > high > medium > low；同级内按 timestamp 倒序。"""
    _seed(fake_chroma, "ref_1", timestamp="2026-01-01 10:00:00", severity="high")
    _seed(fake_chroma, "ref_2", timestamp="2026-03-01 10:00:00", severity="fatal")
    _seed(fake_chroma, "ref_3", timestamp="2026-02-01 10:00:00", severity="low")
    _seed(fake_chroma, "ref_4", timestamp="2026-04-01 10:00:00", severity="fatal")
    _seed(fake_chroma, "ref_5", timestamp="2026-05-01 10:00:00", severity="medium")
    items = agent_tools.list_reflections()
    assert [i["ref_id"] for i in items] == ["ref_4", "ref_2", "ref_1", "ref_5", "ref_3"]


def test_list_reflections_unknown_severity_sorted_last(fake_chroma):
    """未知严重程度兜底排最后（不影响既有顺序）。"""
    _seed(fake_chroma, "ref_1", timestamp="2026-01-01 10:00:00", severity="high")
    _seed(fake_chroma, "ref_2", timestamp="2026-02-01 10:00:00", severity="unknown")
    items = agent_tools.list_reflections()
    assert [i["ref_id"] for i in items] == ["ref_1", "ref_2"]


def test_delete_reflection(fake_chroma):
    agent_tools.create_reflection("a", "b", "c")
    assert agent_tools.delete_reflection("ref_1") is True
    assert agent_tools.get_reflection("ref_1") is None
    assert agent_tools.delete_reflection("ref_1") is False
