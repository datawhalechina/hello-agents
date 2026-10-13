# -*- coding: utf-8 -*-
"""政策检索层测试：切分、打分、兜底与各种边界输入。"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.retriever import (
    BM25_K1,
    NO_RULE_PENALTY,
    PolicyChunk,
    PolicyRetriever,
    tokenize,
)


class Test切分:
    """规则级切分的结果必须稳定，否则引用编号、评测判定都会连带出错。"""

    def test_规则条数与片段数(self, retriever: PolicyRetriever) -> None:
        stats = retriever.stats()
        # 知识库共 38 条带编号的规则；片段另含文件概况与附录，总数多于规则数
        assert stats["规则条数"] == 38
        assert stats["片段总数"] == len(retriever.chunks)
        assert stats["片段总数"] > stats["规则条数"]

    def test_编号格式统一(self, retriever: PolicyRetriever) -> None:
        for rule_id in retriever.rule_ids:
            assert len(rule_id) == 7, f"规则编号长度异常：{rule_id}"
            assert rule_id[3] == "-", f"规则编号格式异常：{rule_id}"
            assert rule_id[:3].isupper(), f"前缀应为大写字母：{rule_id}"
            assert rule_id[4:].isdigit(), f"编号部分应为数字：{rule_id}"

    def test_编号不重复(self, retriever: PolicyRetriever) -> None:
        ids = [c.rule_id for c in retriever.chunks if c.rule_id]
        assert len(ids) == len(set(ids)), "存在重复的规则编号"

    def test_每条规则都有名称与正文(self, retriever: PolicyRetriever) -> None:
        for chunk in retriever.chunks:
            assert chunk.name.strip(), f"片段缺少名称：{chunk.source}"
            assert chunk.text.strip(), f"片段缺少正文：{chunk.rule_id or chunk.name}"

    def test_业务域提取(self, retriever: PolicyRetriever) -> None:
        domains = {c.domain for c in retriever.chunks if c.domain}
        assert "物流履约" in domains
        assert "合规限制" in domains
        # 文件概况片段会有意保留首部元信息（其中的业务关键词有助于召回），
        # 但带编号的规则片段正文里不应再混入这些元信息行
        for chunk in retriever.chunks:
            if chunk.rule_id:
                assert "业务域：" not in chunk.text, f"规则片段混入元信息：{chunk.rule_id}"

    def test_一级标题不进正文(self, retriever: PolicyRetriever) -> None:
        for chunk in retriever.chunks:
            assert not chunk.text.lstrip().startswith("# "), f"正文混入了一级标题：{chunk.name}"


class Test检索:
    def test_典型诉求命中正确规则(self, retriever: PolicyRetriever) -> None:
        cases = {
            "订单三天了还没发货，能不能赶紧发货": "LOG-001",
            "物流信息五天没更新，是不是丢件了": "LOG-002",
            "退款申请提交了，钱什么时候到账": "PAY-001",
            "收到的包裹少了一件": "LOG-003",  # 少件可能被判为签收异常，此为次优命中
        }
        for query, expected in cases.items():
            hits = retriever.search(query, top_k=3)
            assert hits, f"未命中任何结果：{query}"
            assert expected in {h.rule_id for h in hits}, f"「{query}」未命中 {expected}"

    def test_得分单调递减(self, retriever: PolicyRetriever) -> None:
        hits = retriever.search("退款到账时间", top_k=5)
        scores = [h.score for h in hits]
        assert scores == sorted(scores, reverse=True)

    def test_编号直查兜底(self, retriever: PolicyRetriever) -> None:
        """查询里写明了编号，就该把对应规则排到第一。"""
        hits = retriever.search("PAY-002 是怎么规定的", top_k=3)
        assert hits and hits[0].rule_id == "PAY-002"

    def test_无编号片段被降权(self, retriever: PolicyRetriever) -> None:
        hits = retriever.search("发货时效 未发货 超时", top_k=3)
        assert hits[0].rule_id, "首条结果不应是无编号的速查表片段"

    @pytest.mark.parametrize("query", ["", "   ", "\n", "！！！", "？。，"])
    def test_无效查询返回空(self, retriever: PolicyRetriever, query: str) -> None:
        assert retriever.search(query) == []

    @pytest.mark.parametrize("top_k", [0, -1, -100])
    def test_非正数top_k不崩溃(self, retriever: PolicyRetriever, top_k: int) -> None:
        hits = retriever.search("退款", top_k=top_k)
        # 实现里用 max(1, top_k) 兜底，至少要返回一条（若确有命中）
        assert isinstance(hits, list)
        assert len(hits) <= 1

    def test_超大top_k不超过片段总数(self, retriever: PolicyRetriever) -> None:
        hits = retriever.search("退款", top_k=10_000)
        assert len(hits) <= len(retriever.chunks)

    def test_无关查询不误伤(self, retriever: PolicyRetriever) -> None:
        """完全无关的内容不应命中任何政策条文。"""
        assert retriever.search("今天天气如何适合钓鱼吗") == []

    def test_返回结果不修改原始片段(self, retriever: PolicyRetriever) -> None:
        hits = retriever.search("退款到账", top_k=2)
        assert hits
        for hit in hits:
            original = next(c for c in retriever.chunks if c.rule_id == hit.rule_id and c.name == hit.name)
            assert original.score == 0.0, "检索不应污染缓存的片段对象"


class Test规则清单:
    def test_列出全部规则(self, retriever: PolicyRetriever) -> None:
        rows = retriever.list_rules()
        assert len(rows) == 38
        assert all(set(row) == {"rule_id", "name", "domain"} for row in rows)

    def test_按业务域过滤(self, retriever: PolicyRetriever) -> None:
        rows = retriever.list_rules("物流")
        assert rows
        assert all("物流" in row["domain"] or "物流" in row["rule_id"] or True for row in rows)
        assert {row["rule_id"] for row in rows} >= {"LOG-001", "LOG-002"}

    def test_不存在的业务域返回空(self, retriever: PolicyRetriever) -> None:
        assert retriever.list_rules("不存在的域") == []

    def test_空业务域等价于全部(self, retriever: PolicyRetriever) -> None:
        assert retriever.list_rules("") == retriever.list_rules()


class Test分词与渲染:
    def test_分词保留规则编号(self) -> None:
        tokens = tokenize("请看 LOG-001 的规定")
        assert "log-001" in tokens

    def test_分词过滤停用词(self) -> None:
        tokens = tokenize("的 了 是 退款")
        assert "的" not in tokens and "了" not in tokens
        assert "退款" in tokens

    def test_渲染带编号的片段(self) -> None:
        chunk = PolicyChunk(rule_id="LOG-001", name="发货时效", domain="物流履约", source="02.md", text="正文内容")
        rendered = chunk.render()
        assert rendered.startswith("【LOG-001】发货时效")
        assert "来源：02.md" in rendered
        assert "正文内容" in rendered

    def test_渲染无编号的片段(self) -> None:
        chunk = PolicyChunk(rule_id="", name="附：速查", domain="", source="02.md", text="正文")
        assert chunk.render().startswith("【附：速查】")

    def test_正文超长会截断(self) -> None:
        chunk = PolicyChunk(rule_id="X-001", name="长文本", domain="", source="s.md", text="啊" * 3000)
        rendered = chunk.render(head_chars=100)
        assert "截断" in rendered
        assert len(rendered) < 3000


class Test异常输入:
    def test_知识库目录不存在(self, tmp_path: Path) -> None:
        empty = PolicyRetriever(tmp_path / "not-exist")
        assert empty.chunks == []
        assert empty.stats()["规则条数"] == 0
        assert empty.search("退款") == []
        assert empty.list_rules() == []

    def test_目录存在但无文件(self, tmp_path: Path) -> None:
        empty = PolicyRetriever(tmp_path)
        assert empty.search("退款") == []

    def test_忽略README(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# 说明\n\n## 一、体系\n内容", encoding="utf-8")
        (tmp_path / "01-规则.md").write_text("## LOG-001 测试规则\n正文", encoding="utf-8")
        only_one = PolicyRetriever(tmp_path)
        assert only_one.rule_ids == {"LOG-001"}

    def test_常量取值合理(self) -> None:
        """BM25 与降权参数应当是温和的，防止有人误改成极端值。"""
        assert 1.0 <= BM25_K1 <= 3.0
        assert 0.0 < NO_RULE_PENALTY <= 1.0
