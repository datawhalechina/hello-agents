"""
报告质量规则化考核

对综合分析报告做三项自动检查，全部基于规则（无需 LLM、无第三方依赖）:

1. 结构合规率: 报告是否包含模板要求的全部章节和免责声明
2. 条件化检查: 建议是否为条件化表述，有无违反设计原则的绝对化预测
3. 数据真实性: 报告中的价格/百分比数字能否在工具返回结果中溯源
   (反幻觉抽查——Agent 不得编造模型自己"记忆"中的数字)
"""

import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 1. 结构合规率
# ---------------------------------------------------------------------------

# (章节名, 可接受的标志词列表)，与 coordinator 的报告模板对应
REQUIRED_SECTIONS = [
    ("技术面摘要", ["技术面"]),
    ("链上面摘要", ["链上面", "链上"]),
    ("情绪面摘要", ["情绪面", "情绪"]),
    ("信号一致性分析", ["信号一致性", "一致信号", "矛盾信号"]),
    ("综合判断", ["综合判断", "整体偏向"]),
    ("条件化建议", ["条件化建议", "如果你"]),
    ("风险提示", ["风险提示"]),
    ("免责声明", ["免责声明", "不构成投资建议"]),
]


def check_structure(report: str) -> Dict[str, Any]:
    """检查报告结构合规率，返回 {score, missing, passed}"""
    missing = [
        name for name, markers in REQUIRED_SECTIONS
        if not any(m in report for m in markers)
    ]
    found = len(REQUIRED_SECTIONS) - len(missing)
    return {
        "score": found / len(REQUIRED_SECTIONS),
        "found": found,
        "total": len(REQUIRED_SECTIONS),
        "missing": missing,
        "passed": not missing,
    }


# ---------------------------------------------------------------------------
# 2. 条件化建议检查
# ---------------------------------------------------------------------------

# 违反"不做绝对预测"原则的表述
ABSOLUTE_PATTERNS = [
    "必然", "必定", "一定会", "肯定会", "保证", "稳赚", "稳赢",
    "百分之百", "必涨", "必跌", "绝对会", "毫无疑问", "板上钉钉",
    "无风险", "闭眼买", "梭哈",
]

# 条件化表述的标志词
CONDITIONAL_MARKERS = ["如果", "若", "假如", "一旦", "情况", "持有", "计划"]


def check_conditional(report: str) -> Dict[str, Any]:
    """检查建议是否条件化、有无绝对化预测"""
    absolute_found = [p for p in ABSOLUTE_PATTERNS if p in report]
    conditional_count = sum(report.count(m) for m in CONDITIONAL_MARKERS)
    return {
        "absolute_claims": absolute_found,
        "conditional_count": conditional_count,
        "has_conditional": conditional_count >= 2,
        "passed": not absolute_found and conditional_count >= 2,
    }


# ---------------------------------------------------------------------------
# 3. 数据真实性 (数字溯源)
# ---------------------------------------------------------------------------

_MONEY_RE = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)")
_PCT_RE = re.compile(r"([+-]?\d+(?:\.\d+)?)\s?%")


def _extract_values(text: str):
    """提取文本中的金额和百分比数值"""
    money = [float(m.replace(",", "")) for m in _MONEY_RE.findall(text)]
    pct = [float(p) for p in _PCT_RE.findall(text)]
    return money, pct


def _is_grounded(value: float, sources: List[float],
                 rel_tol: float = 0.005, abs_tol: float = 0.05) -> bool:
    return any(
        abs(value - s) <= max(abs_tol, abs(s) * rel_tol)
        for s in sources
    )


def check_grounding(report: str, tool_outputs: List[str]) -> Dict[str, Any]:
    """
    抽查报告中的金额/百分比数字是否能在工具返回结果中找到来源。

    注意: 这是抽样检查而非完备验证——LLM 对数字的合理换算
    (如把支撑位换算成距离百分比) 会被记为"未溯源"，
    因此考核时应关注溯源率的趋势而非要求 100%。
    """
    source_money, source_pct = [], []
    for output in tool_outputs:
        m, p = _extract_values(output)
        source_money.extend(m)
        source_pct.extend(p)

    report_money, report_pct = _extract_values(report)

    ungrounded = []
    grounded = 0
    for v in report_money:
        if _is_grounded(v, source_money):
            grounded += 1
        else:
            ungrounded.append(f"${v:,.2f}")
    for v in report_pct:
        if _is_grounded(v, source_pct, abs_tol=0.5):
            grounded += 1
        else:
            ungrounded.append(f"{v}%")

    total = len(report_money) + len(report_pct)
    rate = grounded / total if total else 1.0
    return {
        "total_numbers": total,
        "grounded": grounded,
        "grounding_rate": rate,
        "ungrounded": ungrounded,
        "passed": rate >= 0.8,
    }


# ---------------------------------------------------------------------------
# 汇总入口
# ---------------------------------------------------------------------------

def evaluate_report(report: str,
                    tool_outputs: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    对一份综合分析报告执行全部规则化考核。

    Args:
        report: 综合分析报告全文
        tool_outputs: 本轮分析中各工具的原始返回 (可选，提供时执行数字溯源)
    """
    result = {
        "structure": check_structure(report),
        "conditional": check_conditional(report),
    }
    if tool_outputs:
        result["grounding"] = check_grounding(report, tool_outputs)

    result["overall_passed"] = all(
        v["passed"] for k, v in result.items() if isinstance(v, dict)
    )
    return result


def format_evaluation(result: Dict[str, Any]) -> str:
    """将考核结果渲染为可读的 Markdown 摘要"""
    lines = ["## 报告质量考核结果\n"]

    s = result["structure"]
    icon = "✅" if s["passed"] else "❌"
    lines.append(f"### 结构合规率 {icon}")
    lines.append(f"- 章节覆盖: {s['found']}/{s['total']} ({s['score']:.0%})")
    if s["missing"]:
        lines.append(f"- 缺失章节: {', '.join(s['missing'])}")
    lines.append("")

    c = result["conditional"]
    icon = "✅" if c["passed"] else "❌"
    lines.append(f"### 条件化建议 {icon}")
    lines.append(f"- 条件化表述数: {c['conditional_count']}")
    if c["absolute_claims"]:
        lines.append(f"- ⚠️ 绝对化表述: {', '.join(c['absolute_claims'])}")
    lines.append("")

    g = result.get("grounding")
    if g:
        icon = "✅" if g["passed"] else "❌"
        lines.append(f"### 数据真实性 (数字溯源) {icon}")
        lines.append(
            f"- 溯源率: {g['grounded']}/{g['total_numbers']} "
            f"({g['grounding_rate']:.0%})"
        )
        if g["ungrounded"]:
            preview = ", ".join(g["ungrounded"][:8])
            lines.append(f"- 未溯源数字: {preview}")
        lines.append("")

    overall = "✅ 通过" if result["overall_passed"] else "❌ 未通过"
    lines.append(f"### 总体: {overall}")
    return "\n".join(lines)
