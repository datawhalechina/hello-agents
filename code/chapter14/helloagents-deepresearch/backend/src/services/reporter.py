"""Service that consolidates task results into the final report."""

from __future__ import annotations

import logging

from tool_aware_agent import ToolAwareSimpleAgent

from models import JobItem, SummaryState
from config import Configuration
from utils import strip_thinking_tokens
from services.llm_resilience import run_with_llm_retry
from services.text_processing import strip_tool_calls

logger = logging.getLogger(__name__)

MAX_SUMMARY_CHARS = 1800
MAX_SOURCES_CHARS = 900


class ReportingService:
    """Generates the final structured report."""

    def __init__(self, report_agent: ToolAwareSimpleAgent, config: Configuration) -> None:
        self._agent = report_agent
        self._config = config

    def generate_report(self, state: SummaryState) -> str:
        """Generate a structured report based on completed tasks."""

        tasks_block = []
        for task in state.todo_items:
            summary_block = self._truncate(task.summary or "暂无可用信息", MAX_SUMMARY_CHARS)
            sources_block = self._truncate(task.sources_summary or "暂无来源", MAX_SOURCES_CHARS)
            tasks_block.append(
                f"### 任务 {task.id}: {task.title}\n"
                f"- 任务目标：{task.intent}\n"
                f"- 检索查询：{task.query}\n"
                f"- 执行状态：{task.status}\n"
                f"- 任务总结：\n{summary_block}\n"
                f"- 来源概览：\n{sources_block}\n"
            )

        prompt = (
            "<用户需求>\n"
            f"{state.research_topic}\n"
            "</用户需求>\n\n"
            "<任务总结与来源>\n"
            f"{''.join(tasks_block)}\n"
            "</任务总结与来源>\n\n"
            "请直接基于以上任务总结和来源概览撰写找实习行动报告。"
            "报告必须以 `# 找实习行动报告` 开始，并包含求职目标、机会渠道、"
            "岗位匹配、简历优化、投递计划、风险、参考来源。"
            "保留来源标题和链接；缺失信息写“暂无可靠信息”或“未确认”；"
            "不要编造具体岗位、薪资、截止日期或链接；不要输出工具调用指令。"
        )

        try:
            response = run_with_llm_retry(
                lambda: self._agent.run(prompt),
                self._config,
                operation="reporter",
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("Report generation failed; using fallback report", exc_info=exc)
            self._agent.clear_history()
            return self._build_fallback_report(state)
        else:
            self._agent.clear_history()

        report_text = response.strip()
        if self._config.strip_thinking_tokens:
            report_text = strip_thinking_tokens(report_text)

        report_text = strip_tool_calls(report_text).strip()
        if report_text and not report_text.startswith("# 找实习行动报告"):
            report_text = f"# 找实习行动报告\n\n{report_text}"

        return report_text or self._build_fallback_report(state)

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        """Trim long task material before sending it to the report writer."""

        text = text.strip()
        if len(text) <= max_chars:
            return text
        return f"{text[:max_chars].rstrip()}\n...[已截断，保留关键摘要]"

    def _build_fallback_report(self, state: SummaryState) -> str:
        """Build a deterministic report when the LLM report writer fails."""

        task_lines = []
        source_lines = []

        for task in state.todo_items:
            summary = self._truncate(task.summary or "暂无可靠信息", 700)
            sources = task.sources_summary or "暂无来源"
            task_lines.append(
                f"### 任务 {task.id}: {task.title}\n"
                f"- 状态：{task.status}\n"
                f"- 目标：{task.intent}\n"
                f"- 检索 query：{task.query}\n"
                f"- 摘要：\n{summary}\n"
            )
            source_lines.append(f"### 任务 {task.id}: {task.title}\n{sources}\n")

        return (
            "# 找实习行动报告\n\n"
            "## 1. 求职目标概览\n\n"
            f"{state.research_topic or '暂无可靠信息'}\n\n"
            "当前为快速版报告，岗位状态、城市、实习周期和截止日期请以来源页面为准。\n\n"
            "## 2. 推荐岗位 Top 5\n\n"
            f"{self._format_job_recommendations(state.job_items)}\n\n"
            "## 3. 岗位要求与匹配分析\n\n"
            f"{self._format_match_analysis(state.job_items)}\n\n"
            "## 4. 简历与项目优化建议\n\n"
            f"{self._format_resume_advice(state.job_items)}\n\n"
            "## 5. 搜索质量诊断\n\n"
            f"{self._format_search_diagnostics(state.search_diagnostics)}\n\n"
            "## 6. 投递行动计划\n\n"
            "- 今天：打开高相关来源，确认岗位是否仍在招聘，并记录投递链接。\n"
            "- 三天内：按城市和技术栈筛选岗位，优先投递官网、校招和内推渠道。\n"
            "- 一周内：根据 JD 更新简历项目描述，补齐高频技能短板。\n\n"
            "## 7. 风险与待确认信息\n\n"
            "- 招聘信息可能过期，需点开来源核验。\n"
            "- 城市、到岗时间、实习周期和截止日期若未在来源中明确，应标记为未确认。\n"
            "- 当前匹配分析未结构化评分，仅作为投递前的初筛参考。\n\n"
            "## 8. 任务摘要与参考来源\n\n"
            f"{''.join(task_lines) or '暂无可靠信息'}\n"
            f"{''.join(source_lines) or '暂无来源'}"
        )

    def _format_job_recommendations(self, jobs: list[JobItem]) -> str:
        ranked_jobs = self._rank_jobs(jobs)[:5]
        if not ranked_jobs:
            return (
                "暂无可靠岗位/JD链接。请优先查看任务摘要中的来源线索，"
                "并点开招聘平台或公司官网确认岗位是否仍在招聘。"
            )

        sections = []
        for index, job in enumerate(ranked_jobs, start=1):
            risks = self._format_items(job.risks, "暂无明确风险，仍需核验岗位状态。")
            sections.append(
                f"### {index}. {self._clean_field(job.title)}\n"
                f"- 公司：{self._clean_field(job.company)}\n"
                f"- 城市：{self._clean_field(job.location)}\n"
                f"- 匹配分：{self._format_match_score(job)}\n"
                f"- 实习周期：{self._clean_field(job.duration)}\n"
                f"- 截止日期：{self._clean_field(job.deadline)}\n"
                f"- 来源：{self._format_source(job)}\n"
                f"- 匹配理由：{self._clean_field(job.match_reason)}\n"
                f"- 风险与待确认：{risks}\n"
            )
        return "\n".join(sections)

    def _format_match_analysis(self, jobs: list[JobItem]) -> str:
        requirements = self._collect_unique(
            item for job in jobs for item in job.requirements
        )
        tech_stack = self._collect_unique(
            item for job in jobs for item in job.tech_stack
        )
        responsibilities = self._collect_unique(
            item for job in jobs for item in job.responsibilities
        )

        if not requirements and not tech_stack and not responsibilities:
            return (
                "暂无可靠信息。请优先点开推荐来源核验 JD，再根据岗位原文补充技能、"
                "项目经验、实习周期和学历要求。"
            )

        return (
            "### 高频技能关键词\n"
            f"{self._format_bullets(tech_stack, '暂无可靠信息')}\n\n"
            "### 常见 JD 要求\n"
            f"{self._format_bullets(requirements, '暂无可靠信息')}\n\n"
            "### 主要岗位职责\n"
            f"{self._format_bullets(responsibilities, '暂无可靠信息')}"
        )

    def _format_resume_advice(self, jobs: list[JobItem]) -> str:
        advice = self._collect_unique(
            item for job in jobs for item in job.resume_advice
        )
        if advice:
            return self._format_bullets(advice, "暂无可靠信息")

        return (
            "- 先打开高相关 JD，确认岗位真实职责、技术栈和投递入口。\n"
            "- 简历项目经历按“问题背景、你的职责、技术实现、量化结果、岗位匹配点”重写。\n"
            "- 对未确认岗位不要补写薪资、截止日期或城市，先标记为待核验。"
        )

    def _format_search_diagnostics(self, diagnostics: list[dict]) -> str:
        if not diagnostics:
            return "暂无搜索质量诊断。"

        total_raw = 0
        total_reliable = 0
        total_filtered = 0
        reject_reasons: dict[str, int] = {}
        suggestions: list[str] = []

        for item in diagnostics:
            counts = item.get("counts") if isinstance(item, dict) else None
            if isinstance(counts, dict):
                total_raw += self._safe_int(counts.get("raw"))
                total_reliable += self._safe_int(counts.get("reliable"))
                total_filtered += self._safe_int(counts.get("filtered"))

            reasons = item.get("reject_reasons") if isinstance(item, dict) else None
            if isinstance(reasons, dict):
                for reason, count in reasons.items():
                    if not isinstance(reason, str):
                        continue
                    reject_reasons[reason] = reject_reasons.get(reason, 0) + self._safe_int(count)

            suggestion = item.get("suggestion") if isinstance(item, dict) else None
            if isinstance(suggestion, str) and suggestion.strip():
                clean = suggestion.strip()
                if clean not in suggestions:
                    suggestions.append(clean)

        reason_text = "暂无主要过滤原因"
        if reject_reasons:
            top_reasons = sorted(
                reject_reasons.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:5]
            reason_text = "、".join(
                f"{self._format_reject_reason(reason)} × {count}"
                for reason, count in top_reasons
            )

        suggestion_text = self._format_bullets(suggestions[:3], "暂无额外建议")
        return (
            f"- 原始结果：{total_raw}\n"
            f"- 可靠来源：{total_reliable}\n"
            f"- 已过滤：{total_filtered}\n"
            f"- 主要过滤原因：{reason_text}\n"
            "- 诊断建议：\n"
            f"{suggestion_text}"
        )

    @staticmethod
    def _rank_jobs(jobs: list[JobItem]) -> list[JobItem]:
        indexed = list(enumerate(jobs))
        ranked = sorted(
            indexed,
            key=lambda item: (
                item[1].match_score if isinstance(item[1].match_score, int) else -1,
                -item[0],
            ),
            reverse=True,
        )
        return [job for _, job in ranked]

    @staticmethod
    def _collect_unique(items: object, limit: int = 10) -> list[str]:
        selected: list[str] = []
        seen: set[str] = set()
        for item in items:
            if not isinstance(item, str):
                continue
            clean = item.strip()
            if not clean or clean in {"未确认", "暂无可靠信息"}:
                continue
            key = clean.lower()
            if key in seen:
                continue
            seen.add(key)
            selected.append(clean)
            if len(selected) >= limit:
                break
        return selected

    @staticmethod
    def _format_bullets(items: list[str], empty_text: str) -> str:
        if not items:
            return f"- {empty_text}"
        return "\n".join(f"- {item}" for item in items)

    @staticmethod
    def _format_items(items: list[str], empty_text: str) -> str:
        cleaned = ReportingService._collect_unique(items, limit=3)
        if not cleaned:
            return empty_text
        return "；".join(cleaned)

    @staticmethod
    def _format_match_score(job: JobItem) -> str:
        if isinstance(job.match_score, int):
            return f"{job.match_score} 分"
        return "待确认"

    @staticmethod
    def _format_source(job: JobItem) -> str:
        title = ReportingService._clean_field(job.source_title, "岗位来源")
        url = (job.source_url or "").strip()
        if url and url != "未确认":
            return f"[{title}]({url})"
        return "未确认"

    @staticmethod
    def _clean_field(value: str | None, fallback: str = "未确认") -> str:
        if not isinstance(value, str):
            return fallback
        clean = value.strip()
        return clean or fallback

    @staticmethod
    def _safe_int(value: object) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return 0

    @staticmethod
    def _format_reject_reason(reason: str) -> str:
        labels = {
            "interview_noise": "面经/面试",
            "tutorial_or_blog": "教程/博客",
            "not_job_url": "非招聘页",
            "missing_jd_terms": "缺少 JD 关键词",
        }
        return labels.get(reason, reason)

