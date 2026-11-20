# -*- coding: utf-8 -*-
"""三个自定义工具，全部继承框架的 Tool 基类并注册进 ToolRegistry。

工具命名约定：`name` 用英文（它是模型 function calling 的技术契约，改动会破坏
调用关系），`description` 与参数说明一律中文——这些文字会被拼进提示词，
是提示词质量的一部分，不是注释。

工具与业务约束的对应关系：

| 工具 | 解决什么 | 对应硬约束 |
|---|---|---|
| search_policy | 找到政策依据 | 不编造 |
| list_policies | 先看有什么规则，再决定查什么 | 不编造（提高召回） |
| check_compliance | 出稿前自检红线 | 不越界 |
"""

from __future__ import annotations

import re
from typing import Any

from hello_agents.tools import Tool, ToolParameter

from .retriever import PolicyRetriever

# ─────────────────────────────────────────────────────────────
# 合规红线判据
#
# 直接沿用另一个工程（售后客服智能体）里已打磨过的正则，只保留一份判据：
# 生成阶段拦截与评测断言共用同一套规则，避免两处标准漂移。
# 关键点：「一定 / 保证」本身不禁用——它们在描述动作时（"我们一定会尽快处理"）
# 是合规的，只有与结果词共现时才构成越界承诺。
# ─────────────────────────────────────────────────────────────

#: 时效 / 结果类：承诺词 + 结果词共现
OVER_PROMISE_PATTERN = re.compile(r"(一定|保证|承诺).{0,6}(到账|退款|赔偿|换新|补发|赔付)")

#: 否定 / 弱化语境：命中即说明是合规拒答，而非违规承诺
NEGATION_PATTERN = re.compile(r"(不能|无法|不可|不会|不得|禁止|不建议|并非|并不|未必|不一定|不是|没有)")

#: 金额类：数字 + 金额单位
AMOUNT_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*(?:元|块钱?|¥|人民币)")

#: 金额类豁免语境："赔偿需由专人核实审批"属合规表述
AMOUNT_EXEMPT_PATTERN = re.compile(
    r"(不能|无法|不可|不会|不得|禁止|不建议"
    r"|需[^。！？；]{0,10}(核实|审批|核算)"
    r"|由[^。！？；]{0,10}(核实|审批|核算))"
)

#: 信息类：索取性动词与敏感字段。中文语序灵活，动词可能在字段之前，也可能在其后，
#: 两种语序都要覆盖——"把验证码发我"与"请提供验证码"同样是索取行为。
SENSITIVE_REQUEST_PATTERN = re.compile(
    r"(?:"
    r"(?:提供|告诉我|发我|发一下|发过来|报一下|报给我|说一下|出示|传一下)"
    r"[^。！？；]{0,10}"
    r"(?:密码|验证码|身份证|银行卡号|卡号|完整账号)"
    r"|"
    r"(?:密码|验证码|身份证|银行卡号|卡号|完整账号)"
    r"[^。！？；]{0,6}"
    r"(?:发我|发一下|发过来|告诉我|提供|报一下|说一下|出示|传一下)"
    r")"
)

#: 信息类的豁免语境：明确告知"无需提供"或提醒用户"不要泄露"，都属于合规表述。
#: 只检查匹配前 6 个字符，避免把远处出现的否定词也算进来。
SENSITIVE_EXEMPT_PATTERN = re.compile(r"(无需|不必|不用|不会|不得|禁止|请勿|切勿|切忌|不要)")

#: 类别 → 对应规则编号，供归因与内部提示引用
CATEGORY_RULE = {
    "时效/结果类": "LIM-001 / LIM-002",
    "金额类": "LIM-003",
    "信息类": "LIM-004",
}


def check_red_lines(reply: str) -> list[tuple[str, str]]:
    """检查一段客户可见文本是否触碰红线。

    :param reply: 面向客户的回复文本
    :return: [(类别, 命中片段), ...]，为空表示合规
    """
    text = reply or ""
    found: list[tuple[str, str]] = []

    for match in OVER_PROMISE_PATTERN.finditer(text):
        # 窗口向右多取两个字符：否定词常紧贴在承诺词前面（"不一定""不保证"），
        # 只取匹配之前的文本会取不到"一定"前面那个"不"，导致豁免失效
        prefix = text[max(0, match.start() - 12) : match.start() + 2]
        if NEGATION_PATTERN.search(prefix):
            continue  # "无法承诺具体到账时间""不一定能换新"都是合规表述
        found.append(("时效/结果类", match.group(0)))
        break

    for match in AMOUNT_PATTERN.finditer(text):
        prefix = text[max(0, match.start() - 14) : match.start()]
        if AMOUNT_EXEMPT_PATTERN.search(prefix):
            continue  # "赔偿需由专人核实审批"
        found.append(("金额类", match.group(0)))
        break

    sensitive = SENSITIVE_REQUEST_PATTERN.search(text)
    if sensitive:
        # "无需提供身份证照片""请勿把验证码发给他人"都是合规表述，需按前文语境豁免
        exempt_prefix = text[max(0, sensitive.start() - 6) : sensitive.start()]
        if not SENSITIVE_EXEMPT_PATTERN.search(exempt_prefix):
            found.append(("信息类", sensitive.group(0)))

    return found


# ─────────────────────────────────────────────────────────────
# 工具实现
# ─────────────────────────────────────────────────────────────


def _pick(parameters: dict[str, Any], *keys: str, default: str = "") -> str:
    """从参数字典里按候选键名取值，兼容框架的两条工具调用路径。

    框架里同一个工具可能被两种方式调用：

    1. FunctionCallAgent 走 OpenAI 原生调用，按 schema 传正确键名（query / domain / draft）；
    2. ReActAgent 走 ``ToolRegistry.execute_tool``，那里固定只传 ``{"input": 文本}``
       （见 ``hello_agents/tools/registry.py``）。

    所以每个工具都必须同时接受专用键名与 ``input``，否则同一个工具在 ReAct 模式下
    会永远拿到空参数。这是本工程实测踩到的坑，不能只按 FunctionCallAgent 的调用约定写。
    """
    data = parameters or {}
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return str(value).strip()
    fallback = data.get("input", default)
    return str(fallback or default).strip()


class SearchPolicyTool(Tool):
    """按语义检索政策知识库，返回命中的规则编号与条文原文。"""

    def __init__(self, retriever: PolicyRetriever, top_k: int = 3):
        super().__init__(
            name="search_policy",
            description=(
                "按语义检索售后政策知识库，返回命中的规则编号与条文原文。"
                "适用于已知问题方向、需要找具体依据的场景。"
                "若返回「未命中」，应更换关键词重试，或先用 list_policies 了解有哪些规则。"
            ),
        )
        self._retriever = retriever
        self._top_k = top_k

    def run(self, parameters: dict[str, Any]) -> str:
        query = _pick(parameters, "query")
        if not query:
            return "错误：检索问题不能为空。请提供具体的问题描述。"

        try:
            top_k = int((parameters or {}).get("top_k") or self._top_k)
        except (TypeError, ValueError):
            top_k = self._top_k

        hits = self._retriever.search(query, top_k=top_k)
        if not hits:
            return (
                f"未命中任何政策条文（检索词：{query}）。\n"
                "建议：换用更具体的业务关键词（如「发货时效」「退款到账」「少件漏发」）重试，"
                "或调用 list_policies 查看规则清单。"
            )

        blocks = [f"命中 {len(hits)} 条政策依据（按相关度排序）："]
        for i, chunk in enumerate(hits, 1):
            blocks.append(f"\n── 第 {i} 条 ──\n{chunk.render()}")
        blocks.append("\n注意：回答时必须原样引用上述规则编号，不得自行编造编号。")
        return "\n".join(blocks)

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="检索用的问题描述，写得越具体召回越准",
                required=True,
            ),
            ToolParameter(
                name="top_k",
                type="integer",
                description="返回条数，默认 3",
                required=False,
            ),
        ]


class ListPoliciesTool(Tool):
    """列出政策库中的规则清单（编号 / 名称 / 业务域），不返回正文。"""

    def __init__(self, retriever: PolicyRetriever):
        super().__init__(
            name="list_policies",
            description=(
                "列出政策库中的规则清单（编号、名称、业务域），不返回条文正文。"
                "适用于还不确定该查什么、想先了解有哪些规则的场景。"
            ),
        )
        self._retriever = retriever

    def run(self, parameters: dict[str, Any]) -> str:
        domain = _pick(parameters, "domain")
        rows = self._retriever.list_rules(domain)

        if not rows:
            available = "、".join(sorted({r["domain"] for r in self._retriever.list_rules() if r["domain"]}))
            return f"未找到匹配「{domain}」的规则。可选业务域：{available}"

        lines = [f"共 {len(rows)} 条规则" + (f"（业务域含「{domain}」）" if domain else "") + "："]
        for row in rows:
            domain_text = f"［{row['domain']}］" if row["domain"] else ""
            lines.append(f"- {row['rule_id']} {row['name']}{domain_text}")
        lines.append("\n提示：拿到编号后，可用 search_policy 检索该编号对应的条文原文。")
        return "\n".join(lines)

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="domain",
                type="string",
                description="业务域关键词（如「物流」「支付」「退换货」），省略则列出全部",
                required=False,
            )
        ]


class CheckComplianceTool(Tool):
    """检查一段客户可见草稿是否触碰合规红线。"""

    def __init__(self) -> None:
        super().__init__(
            name="check_compliance",
            description=(
                "检查一段准备发给客户的回复草稿是否触碰合规红线，返回命中的类别与规则编号。"
                "适用于回复定稿之前自查：不可承诺退款到账时间、赔付金额、审核结果，"
                "不可向客户索取密码或验证码。"
            ),
        )

    def run(self, parameters: dict[str, Any]) -> str:
        draft = _pick(parameters, "draft")
        if not draft:
            return "错误：待检查的草稿不能为空。"

        violations = check_red_lines(draft)
        if not violations:
            return "检查通过：未发现触碰红线的表述，可以发送给客户。"

        lines = [f"发现 {len(violations)} 处红线风险："]
        for category, matched in violations:
            lines.append(f"- [{category}]（依据 {CATEGORY_RULE.get(category, '')}）命中片段：{matched}")
        lines.append(
            "\n请改写上述表述后再定稿：改为说明处理动作与后续跟进方式，"
            "不给出具体时间点、金额或审核结论。"
        )
        return "\n".join(lines)

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="draft",
                type="string",
                description="准备发给客户的回复草稿全文",
                required=True,
            )
        ]


def build_registry(
    retriever: PolicyRetriever,
    mode: str,
) -> tuple[Any, list[Tool]]:
    """按模式组装工具注册表。

    :param mode: "none" 不带工具；"search" 只带检索；"full" 带全部三个工具
    :return: (ToolRegistry, 工具列表)
    """
    from hello_agents.tools import ToolRegistry

    registry = ToolRegistry()
    tools: list[Tool] = []

    if mode in {"search", "full"}:
        tools.append(SearchPolicyTool(retriever))
    if mode == "full":
        tools.extend([ListPoliciesTool(retriever), CheckComplianceTool()])

    for tool in tools:
        registry.register_tool(tool)
    return registry, tools
