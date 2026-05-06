"""上下文质量评估器

为 ContextBuilder 提供上下文质量评估功能：
- 信息密度评估
- 相关性评估
- 完整性评估
- 优化建议生成
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import re


class QualityLevel(Enum):
    """质量等级"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    INSUFFICIENT = "insufficient"


@dataclass
class QualityMetrics:
    """质量指标"""

    information_density: float = 0.0
    relevance_score: float = 0.0
    completeness_score: float = 0.0
    overall_score: float = 0.0
    density_level: QualityLevel = QualityLevel.FAIR
    relevance_level: QualityLevel = QualityLevel.FAIR
    completeness_level: QualityLevel = QualityLevel.FAIR
    overall_level: QualityLevel = QualityLevel.FAIR


@dataclass
class QualityReport:
    """质量评估报告"""

    metrics: QualityMetrics
    sections_present: Dict[str, bool]
    missing_components: List[str]
    optimization_suggestions: List[str]
    evaluation_details: Dict[str, any] = field(default_factory=dict)
    timestamp: str = ""

    def to_markdown(self) -> str:
        """生成 Markdown 格式的报告"""
        lines = [
            "# 上下文质量评估报告",
            "",
            "## 整体评分",
            "",
            "| 指标 | 分数 | 等级 |",
            "|------|------|------|",
            f"| 信息密度 | {self.metrics.information_density:.2f}/1.0 | {self.metrics.density_level.value} |",
            f"| 相关性 | {self.metrics.relevance_score:.2f}/1.0 | {self.metrics.relevance_level.value} |",
            f"| 完整性 | {self.metrics.completeness_score:.2f}/1.0 | {self.metrics.completeness_level.value} |",
            f"| **综合评分** | **{self.metrics.overall_score:.2f}/1.0** | **{self.metrics.overall_level.value}** |",
            "",
        ]

        if self.sections_present:
            lines.append("## 各部分状态")
            lines.append("")
            for section, present in self.sections_present.items():
                status = "[OK] 存在" if present else "[X] 缺失"
                lines.append(f"- **{section}**: {status}")
            lines.append("")

        if self.missing_components:
            lines.append("## 缺失内容")
            lines.append("")
            for component in self.missing_components:
                lines.append(f"- [!] {component}")
            lines.append("")

        if self.optimization_suggestions:
            lines.append("## 优化建议")
            lines.append("")
            for i, suggestion in enumerate(self.optimization_suggestions, 1):
                lines.append(f"{i}. {suggestion}")
            lines.append("")

        if self.evaluation_details:
            lines.append("## 详细评估数据")
            lines.append("")
            for key, value in self.evaluation_details.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")

        return "\n".join(lines)


class ContextEvaluator:
    """上下文质量评估器"""

    REQUIRED_SECTIONS = [
        ("role", [r"\[role", r"\[role & policies\]", r"\[system", r"\[角色"]),
        ("task", [r"\[task\]", r"\[任务\]"]),
        ("evidence", [r"\[evidence\]", r"\[证据\]", r"\[fact", r"\[facts\]"]),
        ("context", [r"\[context\]", r"\[上下文\]", r"\[history\]", r"\[历史\]"]),
    ]

    KEY_INDICATORS = {
        "代码示例": r"```|`[^`]+`",
        "具体数据": r"\d+([.,]\d+)?[%%]|百分比|比例",
        "引用来源": r"来源|引用|参考|依据|source",
        "行动建议": r"下一步|建议|action|建议您",
    }

    def __init__(self, user_query: str = ""):
        self.user_query = user_query

    def evaluate(
        self, context: str, user_query: Optional[str] = None, token_count: int = 0
    ) -> QualityReport:
        """评估上下文质量

        Args:
            context: 待评估的上下文文本
            user_query: 用户查询（可选）
            token_count: token数量（可选）

        Returns:
            质量评估报告
        """
        query = user_query or self.user_query

        density_metrics = self._evaluate_information_density(context)
        relevance_metrics = self._evaluate_relevance(context, query)
        completeness_metrics = self._evaluate_completeness(context)

        metrics = QualityMetrics(
            information_density=density_metrics["score"],
            relevance_score=relevance_metrics["score"],
            completeness_score=completeness_metrics["score"],
            overall_score=self._calculate_overall_score(
                density_metrics["score"],
                relevance_metrics["score"],
                completeness_metrics["score"],
            ),
            density_level=self._score_to_level(density_metrics["score"]),
            relevance_level=self._score_to_level(relevance_metrics["score"]),
            completeness_level=self._score_to_level(completeness_metrics["score"]),
            overall_level=QualityLevel.EXCELLENT,
        )

        metrics.overall_level = self._score_to_level(metrics.overall_score)

        sections_present = completeness_metrics.get("sections_present", {})
        missing = self._identify_missing_components(sections_present)
        suggestions = self._generate_optimization_suggestions(
            context=context,
            metrics=metrics,
            sections_present=sections_present,
            query=query,
            token_count=token_count,
        )

        return QualityReport(
            metrics=metrics,
            sections_present=sections_present,
            missing_components=missing,
            optimization_suggestions=suggestions,
            evaluation_details={
                "上下文长度": len(context),
                "Token数量": token_count,
                "段落数": len([p for p in context.split("\n\n") if p.strip()]),
                "句子数": len(re.split(r"[.!?。！？]+", context)),
                "关键词覆盖": relevance_metrics.get("keyword_coverage", 0),
                "信息密度详情": density_metrics,
            },
        )

    def _evaluate_information_density(self, context: str) -> Dict:
        """评估信息密度"""
        if not context.strip():
            return {"score": 0.0, "details": "上下文为空"}

        lines = [line for line in context.split("\n") if line.strip()]
        total_lines = len(lines)

        filler_words = [
            "嗯",
            "啊",
            "这个",
            "那个",
            "的话",
            "是这样的",
            "其实",
            "可能",
            "大概",
            "应该",
            "我觉得",
            "okay",
            "ok",
            "so",
            "well",
            "like",
        ]

        filler_count = 0
        for line in lines:
            line_lower = line.lower()
            for filler in filler_words:
                filler_count += line_lower.count(filler)

        filler_ratio = filler_count / max(total_lines, 1)

        code_indicators = ["```", "    ", "\t", "def ", "class ", "import "]
        code_lines = sum(
            1 for line in lines for indicator in code_indicators if indicator in line
        )
        code_ratio = code_lines / max(total_lines, 1)

        list_indicators = ["1.", "2.", "- ", "* ", "• ", "· "]
        list_lines = sum(
            1
            for line in lines
            for indicator in list_indicators
            if line.strip().startswith(indicator)
        )
        list_ratio = list_lines / max(total_lines, 1)

        structure_score = code_ratio * 0.4 + list_ratio * 0.3 + (1 - filler_ratio) * 0.3

        non_empty_chars = sum(1 for c in context if c not in " \n\t")
        total_chars = len(context)
        char_ratio = non_empty_chars / max(total_chars, 1)

        density_score = structure_score * 0.6 + char_ratio * 0.4

        return {
            "score": min(density_score, 1.0),
            "details": {
                "结构化程度": structure_score,
                "字符密度": char_ratio,
                "代码比例": code_ratio,
                "列表比例": list_ratio,
                "填充词比例": filler_ratio,
            },
        }

    def _evaluate_relevance(self, context: str, query: str) -> Dict:
        """评估相关性"""
        if not query.strip():
            return {"score": 0.5, "keyword_coverage": 0, "details": "无查询内容"}

        query_lower = query.lower()
        context_lower = context.lower()

        def extract_words(text: str) -> set:
            words = set(re.findall(r"\w+", text))
            chinese_chars = set(re.findall(r"[\u4e00-\u9fff]", text))
            return words | chinese_chars

        query_words = extract_words(query_lower)
        context_words = extract_words(context_lower)

        if not query_words:
            return {"score": 0.5, "keyword_coverage": 0}

        matched_words = query_words & context_words
        keyword_coverage = len(matched_words) / len(query_words)

        important_words = {
            "pandas": 1.5,
            "python": 1.3,
            "优化": 1.4,
            "内存": 1.5,
            "数据": 1.2,
            "分析": 1.2,
            "csv": 1.3,
            "读取": 1.2,
            "转换": 1.2,
            "清洗": 1.3,
            "统计": 1.1,
            "计算": 1.1,
        }

        weighted_coverage = keyword_coverage
        for word in matched_words:
            if word in important_words:
                weighted_coverage += (important_words[word] - 1) * 0.1

        weighted_coverage = min(weighted_coverage, 1.0)

        query_segments = query.split()
        segment_coverage = sum(
            1 for seg in query_segments if seg.lower() in context_lower
        ) / max(len(query_segments), 1)

        relevance_score = (
            keyword_coverage * 0.4 + weighted_coverage * 0.4 + segment_coverage * 0.2
        )

        return {
            "score": min(relevance_score, 1.0),
            "keyword_coverage": keyword_coverage,
            "weighted_coverage": weighted_coverage,
            "segment_coverage": segment_coverage,
        }

    def _evaluate_completeness(self, context: str) -> Dict:
        """评估完整性"""
        context_lower = context.lower()

        sections_present = {}
        for section_name, patterns in self.REQUIRED_SECTIONS:
            found = any(re.search(pattern, context_lower) for pattern in patterns)
            sections_present[section_name] = found

        present_count = sum(sections_present.values())
        total_sections = len(self.REQUIRED_SECTIONS)
        section_score = present_count / total_sections

        indicators_found = {}
        for indicator_name, pattern in self.KEY_INDICATORS.items():
            indicators_found[indicator_name] = bool(
                re.search(pattern, context, re.IGNORECASE)
            )

        indicator_score = sum(indicators_found.values()) / len(self.KEY_INDICATORS)

        completeness_score = section_score * 0.6 + indicator_score * 0.4

        return {
            "score": completeness_score,
            "sections_present": sections_present,
            "indicators_found": indicators_found,
            "section_coverage": section_score,
            "indicator_coverage": indicator_score,
        }

    def _identify_missing_components(
        self, sections_present: Dict[str, bool]
    ) -> List[str]:
        """识别缺失的组件"""
        missing = []
        section_names = {
            "role": "系统角色与策略说明",
            "task": "当前任务描述",
            "evidence": "支撑证据或事实依据",
            "context": "对话上下文或背景信息",
        }

        for section, present in sections_present.items():
            if not present:
                name = section_names.get(section, section)
                missing.append(name)

        return missing

    def _generate_optimization_suggestions(
        self,
        context: str,
        metrics: QualityMetrics,
        sections_present: Dict[str, bool],
        query: str,
        token_count: int,
    ) -> List[str]:
        """生成优化建议"""
        suggestions = []

        if metrics.density_level in (QualityLevel.POOR, QualityLevel.INSUFFICIENT):
            suggestions.append(
                "📝 **信息密度优化**: 上下文包含较多冗余或填充内容。"
                "建议精简表达，移除重复描述，使用列表和代码块提高结构化程度。"
            )

        if metrics.relevance_level in (QualityLevel.POOR, QualityLevel.INSUFFICIENT):
            suggestions.append(
                "🎯 **相关性优化**: 上下文与查询的匹配度较低。"
                f'建议引入与"{query[:20]}..."相关度更高的记忆或知识库内容。'
            )

        if not sections_present.get("evidence", False):
            suggestions.append(
                "📚 **证据补充**: 缺少支撑证据或事实依据。"
                "建议添加相关知识库内容或历史经验作为参考。"
            )

        if not sections_present.get("role", False):
            suggestions.append(
                "🎭 **角色定义**: 缺少系统角色与策略说明。"
                "建议添加明确的角色定义和行为约束。"
            )

        if metrics.completeness_score < 0.5:
            suggestions.append(
                "📋 **结构完整性**: 上下文结构不够完整。"
                "建议使用标准模板：[Role & Policies] → [Task] → [Evidence] → [Context]"
            )

        indicators = self._evaluate_completeness(context).get("indicators_found", {})
        if not indicators.get("代码示例", False):
            suggestions.append("💻 **示例代码**: 如果涉及技术实现，建议添加代码示例。")

        if not indicators.get("行动建议", False):
            suggestions.append("🚀 **行动建议**: 建议添加下一步行动建议，提升实用性。")

        if token_count > 6000:
            suggestions.append(
                f"📏 **长度控制**: 上下文较长({token_count} tokens)，"
                "建议启用压缩或精简非关键内容以节省token预算。"
            )

        if not suggestions:
            suggestions.append("✅ 上下文质量良好，无需额外优化。")

        return suggestions

    def _calculate_overall_score(
        self, density: float, relevance: float, completeness: float
    ) -> float:
        """计算综合评分"""
        weights = {"density": 0.25, "relevance": 0.45, "completeness": 0.30}

        overall = (
            density * weights["density"]
            + relevance * weights["relevance"]
            + completeness * weights["completeness"]
        )

        return min(overall, 1.0)

    def _score_to_level(self, score: float) -> QualityLevel:
        """将分数映射到质量等级"""
        if score >= 0.85:
            return QualityLevel.EXCELLENT
        elif score >= 0.70:
            return QualityLevel.GOOD
        elif score >= 0.50:
            return QualityLevel.FAIR
        elif score >= 0.30:
            return QualityLevel.POOR
        else:
            return QualityLevel.INSUFFICIENT


def evaluate_context(
    context: str, user_query: str, token_count: int = 0
) -> QualityReport:
    """便捷函数：评估上下文质量

    Args:
        context: 待评估的上下文文本
        user_query: 用户查询
        token_count: token数量

    Returns:
        质量评估报告（Markdown格式）
    """
    evaluator = ContextEvaluator(user_query=user_query)
    report = evaluator.evaluate(context, user_query, token_count)
    return report
