"""
RAG 检索重排测试
===============
验证 get_rag_content 的「召回 retrieve_k 条 → Reranker 重排 → 保留 rerank_top_k 条」流程：
- 输出带序号（[1]..[N]），对齐 rag_prompt.txt 的「参考资料第X条」来源标注要求
- 空召回返回空串；仅 1 条时跳过重排；无 reranker 时回退取前 top_k 条
用 fake chroma / reranker 避免真实 Chroma 与网络调用。
"""
import pytest

from vector_uploader_service import rag_summarize


class FakeHit:
    def __init__(self, content: str):
        self.page_content = content


class FakeChroma:
    """模拟 similarity_search_with_score：按 k 召回，返回 (doc, score) 递减的列表"""

    def __init__(self, docs):
        self.docs = docs

    def similarity_search_with_score(self, query, k):
        return [(FakeHit(d), 1.0 - i / 100) for i, d in enumerate(self.docs[:k])]


class FakeReranker:
    """模拟 rerank：从 documents 中挑出 order 命中的前 top_n 条"""

    def __init__(self, order):
        self.order = order

    def rerank(self, query, documents, top_n):
        return [d for d in self.order if d in documents][:top_n]


def _make_summarizer(docs, reranker, retrieve_k=10, top_k=5):
    """绕过 __init__（会开真实 Chroma），只注入检索重排所需字段"""
    rs = object.__new__(rag_summarize._Rag_Summarize)
    rs.chroma = FakeChroma(docs)
    rs.reranker = reranker
    rs.retrieve_k = retrieve_k
    rs.rerank_top_k = top_k
    return rs


def test_get_rag_content_recall_rerank_topk_numbered():
    """召回 10 条 → 重排保留 5 条 → 带序号输出"""
    docs = [f"doc{i}" for i in range(10)]
    reranker = FakeReranker(["doc9", "doc0", "doc1", "doc2", "doc3"])
    s = _make_summarizer(docs, reranker, retrieve_k=10, top_k=5)
    out = s.get_rag_content("q")
    lines = out.split("\n")
    assert len(lines) == 5
    assert lines[0] == "[1] doc9"
    assert lines[1] == "[2] doc0"
    assert lines[4] == "[5] doc3"


def test_get_rag_content_empty():
    s = _make_summarizer([], FakeReranker([]), retrieve_k=10, top_k=5)
    assert s.get_rag_content("q") == ""


def test_get_rag_content_single_doc_skips_rerank():
    """仅 1 条命中时跳过 reranker，直接输出"""
    s = _make_summarizer(["only"], FakeReranker([]), retrieve_k=10, top_k=5)
    assert s.get_rag_content("q") == "[1] only"


def test_get_rag_content_no_reranker_falls_back_to_topk():
    """无 reranker 时回退取向量召回的前 top_k 条"""
    docs = [f"doc{i}" for i in range(8)]
    s = _make_summarizer(docs, None, retrieve_k=10, top_k=5)
    out = s.get_rag_content("q")
    lines = out.split("\n")
    assert len(lines) == 5
    assert lines[0] == "[1] doc0"
    assert lines[4] == "[5] doc4"
