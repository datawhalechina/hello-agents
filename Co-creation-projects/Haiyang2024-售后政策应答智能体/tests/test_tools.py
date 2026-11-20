# -*- coding: utf-8 -*-
"""工具层测试：参数兼容、红线判据、未命中与异常输入。"""

from __future__ import annotations

import pytest

from src.retriever import PolicyRetriever
from src.tools import (
    CheckComplianceTool,
    ListPoliciesTool,
    SearchPolicyTool,
    _pick,
    build_registry,
    check_red_lines,
)


class Test参数提取:
    """同一个工具会被两条调用路径命中：原生函数调用传专用键，ReAct 只传 input。"""

    def test_专用键优先(self) -> None:
        assert _pick({"query": "退款", "input": "别的"}, "query") == "退款"

    def test_回退到input(self) -> None:
        assert _pick({"input": "退款"}, "query") == "退款"

    def test_空值会继续回退(self) -> None:
        assert _pick({"query": "", "input": "兜底"}, "query") == "兜底"

    def test_全空返回默认(self) -> None:
        assert _pick({}, "query") == ""
        assert _pick({}, "query", default="默认值") == "默认值"

    def test_None与非字典输入(self) -> None:
        assert _pick(None, "query") == ""
        assert _pick({}, "query") == ""

    def test_自动去除首尾空白(self) -> None:
        assert _pick({"query": "  退款  "}, "query") == "退款"

    def test_非字符串值被转换(self) -> None:
        assert _pick({"top_k": 5}, "top_k") == "5"


class Test检索工具:
    def test_命中时给出编号与提示(self, retriever: PolicyRetriever) -> None:
        output = SearchPolicyTool(retriever).run({"query": "发货超过 48 小时怎么处理"})
        assert "命中" in output
        assert "LOG-001" in output
        assert "不得自行编造编号" in output

    def test_空查询给出明确错误(self, retriever: PolicyRetriever) -> None:
        assert "不能为空" in SearchPolicyTool(retriever).run({"query": "   "})

    def test_未命中时给出重试建议(self, retriever: PolicyRetriever) -> None:
        output = SearchPolicyTool(retriever).run({"query": "今天天气如何适合钓鱼吗"})
        assert "未命中" in output
        assert "list_policies" in output

    def test_兼容ReAct的input参数(self, retriever: PolicyRetriever) -> None:
        via_native = SearchPolicyTool(retriever).run({"query": "退款到账"})
        via_text = SearchPolicyTool(retriever).run({"input": "退款到账"})
        assert via_native == via_text

    @pytest.mark.parametrize("bad", ["abc", None, [], {}, 3.7])
    def test_非法top_k不崩溃(self, retriever: PolicyRetriever, bad) -> None:
        output = SearchPolicyTool(retriever).run({"query": "退款到账", "top_k": bad})
        assert "命中" in output or "未命中" in output

    def test_返回条数受top_k约束(self, retriever: PolicyRetriever) -> None:
        output = SearchPolicyTool(retriever).run({"query": "退款", "top_k": 1})
        assert output.count("── 第") == 1

    def test_参数声明完整(self, retriever: PolicyRetriever) -> None:
        params = SearchPolicyTool(retriever).get_parameters()
        names = {p.name for p in params}
        assert names == {"query", "top_k"}
        assert next(p for p in params if p.name == "query").required is True


class Test规则清单工具:
    def test_列出全部(self, retriever: PolicyRetriever) -> None:
        output = ListPoliciesTool(retriever).run({})
        assert "共 38 条规则" in output
        assert "LOG-001" in output

    def test_按域过滤(self, retriever: PolicyRetriever) -> None:
        output = ListPoliciesTool(retriever).run({"domain": "退换货"})
        assert "RET-001" in output
        assert "LOG-001" not in output

    def test_无匹配时给出可选域(self, retriever: PolicyRetriever) -> None:
        output = ListPoliciesTool(retriever).run({"domain": "不存在的域"})
        assert "未找到" in output
        assert "物流履约" in output

    def test_兼容input参数(self, retriever: PolicyRetriever) -> None:
        assert ListPoliciesTool(retriever).run({"input": "物流"}) == ListPoliciesTool(retriever).run({"domain": "物流"})


class Test红线判据:
    @pytest.mark.parametrize("text", ["", "   ", None])
    def test_空输入无命中(self, text) -> None:
        assert check_red_lines(text) == []

    @pytest.mark.parametrize(
        "text",
        ["退款明天一定到账", "我们保证给您退款", "承诺后天赔偿", "一定给您换新"],
    )
    def test_时效结果类命中(self, text: str) -> None:
        hits = check_red_lines(text)
        assert hits and hits[0][0] == "时效/结果类"

    @pytest.mark.parametrize(
        "text",
        [
            "无法承诺具体到账时间",
            "我们不能保证一定退款",
            "并不会承诺赔偿",
            "不一定能换新",
            "我们一定会尽快处理",  # 承诺词 + 动作，不构成结果承诺
        ],
    )
    def test_否定与动作描述被豁免(self, text: str) -> None:
        assert all(category != "时效/结果类" for category, _ in check_red_lines(text)), text

    def test_金额类命中(self) -> None:
        hits = check_red_lines("最多陪您 100 元")
        assert any(category == "金额类" for category, _ in hits)

    @pytest.mark.parametrize("text", ["赔偿需由专人核实审批", "不能承诺具体金额 500 元"])
    def test_金额豁免语境(self, text: str) -> None:
        assert all(category != "金额类" for category, _ in check_red_lines(text)), text

    def test_信息类命中(self) -> None:
        hits = check_red_lines("请提供您的验证码")
        assert any(category == "信息类" for category, _ in hits)

    @pytest.mark.parametrize(
        "text",
        [
            "麻烦把验证码发我",
            "把银行卡号报一下",
            "验证码告诉我一下",
            "请出示一下身份证",
        ],
    )
    def test_信息类命中_动词在后的语序(self, text: str) -> None:
        """中文语序灵活，动词出现在敏感字段之后同样属于索取行为。"""
        hits = check_red_lines(text)
        assert any(category == "信息类" for category, _ in hits), f"漏检：{text}"

    @pytest.mark.parametrize(
        "text",
        ["我们不会向您索取验证码", "请您注意保护银行卡号", "无需提供身份证照片"],
    )
    def test_信息类不误报(self, text: str) -> None:
        assert all(category != "信息类" for category, _ in check_red_lines(text)), text

    def test_多类同时命中时都能报出(self) -> None:
        text = "保证明天到账，赔您 200 元，请提供验证码"
        categories = {category for category, _ in check_red_lines(text)}
        assert {"时效/结果类", "金额类", "信息类"} <= categories

    def test_正常回复不误报(self) -> None:
        text = (
            "您好，非常抱歉让您久等了。根据平台规则（LOG-001），订单应在付款后 48 小时内发出。"
            "我们已为您升级加急催发，会持续跟进并在有结果后第一时间同步您。"
            "退款一般 1-3 个工作日到账，具体以支付渠道实际处理为准。"
        )
        assert check_red_lines(text) == []


class Test合规检查工具:
    def test_合规草稿通过(self) -> None:
        output = CheckComplianceTool().run({"draft": "我们已为您发起加急催发，会持续跟进。"})
        assert "检查通过" in output

    def test_违规草稿给出类别与编号(self) -> None:
        output = CheckComplianceTool().run({"draft": "您的退款明天一定到账。"})
        assert "红线风险" in output
        assert "LIM-001" in output

    def test_空草稿给出明确错误(self) -> None:
        assert "不能为空" in CheckComplianceTool().run({"draft": ""})
        assert "不能为空" in CheckComplianceTool().run({})

    def test_兼容input参数(self) -> None:
        assert CheckComplianceTool().run({"input": "退款明天一定到账"}) == CheckComplianceTool().run(
            {"draft": "退款明天一定到账"}
        )


class Test注册表组装:
    def test_模式A无工具(self, retriever: PolicyRetriever) -> None:
        _, tools = build_registry(retriever, "none")
        assert tools == []

    def test_模式B只有检索(self, retriever: PolicyRetriever) -> None:
        registry, tools = build_registry(retriever, "search")
        assert [t.name for t in tools] == ["search_policy"]
        assert registry.get_tool("search_policy") is not None

    def test_模式C三件套(self, retriever: PolicyRetriever) -> None:
        registry, tools = build_registry(retriever, "full")
        assert [t.name for t in tools] == ["search_policy", "list_policies", "check_compliance"]
        assert registry.get_tool("check_compliance") is not None

    def test_未知模式不报错(self, retriever: PolicyRetriever) -> None:
        _, tools = build_registry(retriever, "unknown")
        assert tools == []
