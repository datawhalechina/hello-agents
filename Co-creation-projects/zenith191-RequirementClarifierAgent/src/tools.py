"""基于 HelloAgents 0.2.9 Tool 协议的确定性检查工具。"""

from __future__ import annotations

import io
import json
import re
from contextlib import redirect_stdout
from typing import Any

from hello_agents.tools import Tool, ToolParameter, ToolRegistry


REQUIREMENT_DIMENSIONS: dict[str, tuple[tuple[str, ...], str]] = {
    "目标与价值": (
        ("目标", "希望", "解决", "价值", "为了", "痛点"),
        "这个需求要解决什么问题，成功后产生什么价值？",
    ),
    "目标用户": (
        ("用户", "成员", "客户", "管理员", "居民", "工作人员", "面向", "使用者"),
        "谁会使用系统？不同角色分别能做什么？",
    ),
    "核心范围": (
        ("功能", "支持", "可以", "需要", "浏览", "发布", "报名", "管理"),
        "首个版本必须包含和明确不包含哪些功能？",
    ),
    "约束条件": (
        ("预算", "成本", "时间", "上线", "周期", "技术栈", "平台", "中文"),
        "交付时间、预算、平台或技术栈有哪些硬约束？",
    ),
    "数据与集成": (
        ("数据", "数据库", "接口", "api", "导入", "导出", "第三方", "同步"),
        "需要保存哪些数据，并与哪些现有系统或第三方服务集成？",
    ),
    "非功能需求": (
        ("并发", "性能", "安全", "隐私", "可用性", "响应时间", "人数", "容量"),
        "对性能、容量、安全、隐私和可用性有什么要求？",
    ),
    "验收标准": (
        ("验收", "成功标准", "通过", "指标", "完成标准", "可演示"),
        "哪些可观察、可测试的条件满足后可以验收？",
    ),
}


REQUIRED_REPORT_HEADINGS = (
    "1. 需求摘要",
    "2. 已确认信息",
    "3. 待确认问题",
    "4. 范围与优先级",
    "5. 技术方案",
    "6. 风险与对策",
    "7. 验收标准",
    "8. 下一步行动",
)


class RequirementAuditTool(Tool):
    """扫描原始需求覆盖了哪些关键信息维度。"""

    def __init__(self) -> None:
        super().__init__(
            name="requirement_audit",
            description=(
                "检查需求文本的完整度，返回已覆盖维度、缺失维度和澄清问题；"
                "参数名为 requirement_text"
            ),
        )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="requirement_text",
                type="string",
                description="需要检查的原始需求文本",
                required=True,
            )
        ]

    def run(self, parameters: dict[str, Any]) -> str:
        requirement_text = parameters.get(
            "requirement_text", parameters.get("input", "")
        )
        if not isinstance(requirement_text, str) or not requirement_text.strip():
            return json.dumps(
                {
                    "ok": False,
                    "error_code": "INVALID_PARAM",
                    "message": "requirement_text 必须是非空字符串",
                },
                ensure_ascii=False,
            )

        normalized = requirement_text.casefold()
        covered: list[str] = []
        missing: list[str] = []
        evidence: dict[str, list[str]] = {}
        questions: list[str] = []

        for dimension, (keywords, question) in REQUIREMENT_DIMENSIONS.items():
            hits = [keyword for keyword in keywords if keyword.casefold() in normalized]
            if hits:
                covered.append(dimension)
                evidence[dimension] = hits
            else:
                missing.append(dimension)
                questions.append(question)

        total = len(REQUIREMENT_DIMENSIONS)
        coverage = round(len(covered) / total * 100)
        summary = (
            f"需求完整度初检：{coverage}%（{len(covered)}/{total} 个维度）。\n"
            f"已覆盖：{'、'.join(covered) if covered else '无'}。\n"
            f"待补充：{'、'.join(missing) if missing else '无'}。"
        )
        return json.dumps(
            {
                "ok": True,
                "summary": summary,
                "coverage_percent": coverage,
                "covered_dimensions": covered,
                "missing_dimensions": missing,
                "evidence_keywords": evidence,
                "clarifying_questions": questions,
            },
            ensure_ascii=False,
            indent=2,
        )


class ReportQualityTool(Tool):
    """检查最终报告是否包含模板规定的八个核心章节。"""

    def __init__(self) -> None:
        super().__init__(
            name="report_quality_check",
            description=(
                "检查需求澄清报告的章节完整性、章节内容和待确认标记；"
                "参数名为 report_text"
            ),
        )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="report_text",
                type="string",
                description="Markdown 格式的需求澄清报告",
                required=True,
            )
        ]

    def run(self, parameters: dict[str, Any]) -> str:
        report_text = parameters.get("report_text", parameters.get("input", ""))
        if not isinstance(report_text, str) or not report_text.strip():
            return json.dumps(
                {
                    "ok": False,
                    "error_code": "INVALID_PARAM",
                    "message": "report_text 必须是非空字符串",
                },
                ensure_ascii=False,
            )

        heading_matches = list(
            re.finditer(r"^##\s+(.+?)\s*$", report_text, flags=re.MULTILINE)
        )
        headings = {match.group(1).strip() for match in heading_matches}
        missing = [heading for heading in REQUIRED_REPORT_HEADINGS if heading not in headings]

        section_content: dict[str, str] = {}
        for index, match in enumerate(heading_matches):
            heading = match.group(1).strip()
            content_end = (
                heading_matches[index + 1].start()
                if index + 1 < len(heading_matches)
                else len(report_text)
            )
            section_content[heading] = report_text[match.end() : content_end].strip()
        empty = [
            heading
            for heading in REQUIRED_REPORT_HEADINGS
            if heading in headings and not section_content.get(heading)
        ]

        body_without_headings = re.sub(
            r"^#{1,6}\s+.*$", "", report_text, flags=re.MULTILINE
        )
        has_pending_markers = any(
            marker in body_without_headings for marker in ("待确认", "假设", "建议")
        )

        total = len(REQUIRED_REPORT_HEADINGS)
        heading_score = (total - len(missing)) / total * 50
        content_score = (total - len(missing) - len(empty)) / total * 40
        score = round(
            heading_score + content_score + (10 if has_pending_markers else 0)
        )
        summary = (
            f"报告结构评分：{score}/100。"
            + (f" 缺少章节：{'、'.join(missing)}。" if missing else " 八个章节齐全。")
            + (f" 空章节：{'、'.join(empty)}。" if empty else " 章节均有内容。")
            + (" 已区分待确认信息。" if has_pending_markers else " 未发现待确认/假设/建议标记。")
        )
        return json.dumps(
            {
                "ok": True,
                "summary": summary,
                "score": score,
                "missing_headings": missing,
                "empty_headings": empty,
                "has_pending_markers": has_pending_markers,
            },
            ensure_ascii=False,
            indent=2,
        )


def create_tool_registry() -> ToolRegistry:
    """创建并注册项目所需的 HelloAgents 工具。"""

    registry = ToolRegistry()
    # 0.2.9 注册时会打印包含 emoji 的日志；Windows GBK 终端可能编码失败。
    with redirect_stdout(io.StringIO()):
        registry.register_tool(RequirementAuditTool())
        registry.register_tool(ReportQualityTool())
    return registry
