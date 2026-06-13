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
REQUIRED_REPORT_SECTIONS = (
    "## 1. 结论：今天优先投递",
    "## 2. 推荐理由",
    "## 3. 简历修改清单",
    "## 4. 7 天投递计划",
    "## 5. 风险与待确认项",
    "## 6. 附录：来源与搜索诊断",
)


class ReportingService:
    """Generates the final structured report."""

    def __init__(self, report_agent: ToolAwareSimpleAgent, config: Configuration) -> None:
        self._agent = report_agent
        self._config = config

    def generate_report(self, state: SummaryState) -> str:
        """Generate a structured report based on completed tasks."""

        prompt = self.build_prompt(state)

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

        if report_text and self._has_required_sections(report_text):
            return report_text

        if report_text:
            logger.warning("Report missing required action sections; using fallback report")
        return self._build_fallback_report(state)

    def build_prompt(self, state: SummaryState) -> str:
        """Build the final report prompt sent to the reporter LLM."""

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

        return (
            "<用户需求>\n"
            f"{state.research_topic}\n"
            "</用户需求>\n\n"
            "<任务总结与来源>\n"
            f"{''.join(tasks_block)}\n"
            "</任务总结与来源>\n\n"
            "请直接基于以上任务总结和来源概览撰写找实习行动报告。"
            "报告必须以 `# 找实习行动报告` 开始，并严格包含："
            "1. 结论：今天优先投递；2. 推荐理由；3. 简历修改清单；"
            "4. 7 天投递计划；5. 风险与待确认项；6. 附录：来源与搜索诊断。"
            "请先给 3-5 个今天优先人工投递的岗位，再解释推荐依据和待确认项。"
            "7 天计划必须拆成今天、3 天内、7 天内。"
            "保留来源标题和链接；缺失信息写“暂无可靠信息”或“未确认”；"
            "不要编造具体岗位、薪资、截止日期、链接或用户经历；"
            "不要生成自动投递、平台登录、批量联系 HR 或绕过平台规则的建议；"
            "不要输出工具调用指令。"
        )

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        """Trim long task material before sending it to the report writer."""

        text = text.strip()
        if len(text) <= max_chars:
            return text
        return f"{text[:max_chars].rstrip()}\n...[已截断，保留关键摘要]"

    @staticmethod
    def _has_required_sections(report: str) -> bool:
        return all(section in report for section in REQUIRED_REPORT_SECTIONS)

    def _build_fallback_report(self, state: SummaryState) -> str:
        """Build a deterministic report when the LLM report writer fails."""

        task_lines = []
        source_lines = []
        ranked_jobs = self._rank_jobs(state.job_items)

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
            "## 1. 结论：今天优先投递\n\n"
            f"{self._format_today_priorities(ranked_jobs)}\n\n"
            "## 2. 推荐理由\n\n"
            f"{self._format_recommendation_reasons(ranked_jobs)}\n\n"
            "## 3. 简历修改清单\n\n"
            f"{self._format_resume_advice(ranked_jobs)}\n\n"
            "## 4. 7 天投递计划\n\n"
            f"{self._format_action_plan(ranked_jobs)}\n\n"
            "## 5. 风险与待确认项\n\n"
            f"{self._format_risks_and_confirmations(ranked_jobs, state.search_diagnostics)}\n\n"
            "## 6. 附录：来源与搜索诊断\n\n"
            "### 求职目标\n\n"
            f"{state.research_topic or '暂无可靠信息'}\n\n"
            "### 搜索质量诊断\n\n"
            f"{self._format_search_diagnostics(state.search_diagnostics)}\n\n"
            "### 任务摘要\n\n"
            f"{''.join(task_lines) or '暂无可靠信息'}\n"
            "### 参考来源\n\n"
            f"{''.join(source_lines) or '暂无来源'}"
        )

    def _format_today_priorities(self, ranked_jobs: list[JobItem]) -> str:
        top_jobs = ranked_jobs[:5]
        if not top_jobs:
            return (
                "暂无可靠岗位/JD链接。暂无可靠信息可用于直接排序投递。"
                "今天建议先根据附录来源补搜企业官网、校招官网、学校就业网或可信招聘平台，"
                "再人工确认岗位是否仍开放。"
            )

        sections = []
        for index, job in enumerate(top_jobs, start=1):
            sections.append(
                f"{index}. **{self._clean_field(job.title)}**"
                f"（{self._clean_field(job.company)}，{self._clean_field(job.location)}）\n"
                f"- 匹配分：{self._format_match_score(job)}\n"
                f"- 实习周期：{self._clean_field(job.duration)}\n"
                f"- 截止日期：{self._clean_field(job.deadline)}\n"
                f"- 来源：{self._format_source(job)}\n"
            )
        return "\n".join(sections)

    def _format_recommendation_reasons(self, ranked_jobs: list[JobItem]) -> str:
        top_jobs = ranked_jobs[:5]
        if not top_jobs:
            return (
                "暂无可靠岗位/JD链接。请先补充搜索条件并核验来源，"
                "不要根据不完整摘要直接投递。"
            )

        sections = []
        for index, job in enumerate(top_jobs, start=1):
            confirmations = self._format_items(
                self._confirmation_items(job),
                "暂无明显待确认项，投递前仍需打开来源最终核验。",
            )
            sections.append(
                f"### {index}. {self._clean_field(job.company)} · {self._clean_field(job.title)}\n"
                f"- 推荐依据：{self._clean_field(job.match_reason)}\n"
                f"- 关键要求：{self._format_items(job.requirements, '暂无可靠信息')}\n"
                f"- 技术栈：{self._format_items(job.tech_stack, '暂无可靠信息')}\n"
                f"- 待确认项：{confirmations}\n"
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
            return (
                "### 可直接执行的修改\n"
                f"{self._format_bullets(advice, '暂无可靠信息')}\n\n"
                "### 需要补充事实后再写\n"
                "- 对没有真实经历支撑的技能，只标记为待学习或待补充，不要写成熟练掌握。\n"
                "- 对未确认岗位，不要补写薪资、截止日期、城市或公司要求。"
            )

        return (
            "### 可直接执行的修改\n"
            "- 先打开高相关 JD，确认岗位真实职责、技术栈和投递入口。\n"
            "- 简历项目经历按“问题背景、你的职责、技术实现、量化结果、岗位匹配点”重写。\n"
            "- 将 JD 高频技能词映射到已有项目，不要添加没有事实支撑的经历。\n\n"
            "### 需要补充事实后再写\n"
            "- 如果缺少量化结果，先回忆真实数据、性能指标、用户规模或项目产出。\n"
            "- 对未确认岗位不要补写薪资、截止日期或城市，先标记为待核验。"
        )

    def _format_action_plan(self, ranked_jobs: list[JobItem]) -> str:
        top_targets = self._format_target_names(ranked_jobs[:3])
        if not top_targets:
            top_targets = "附录中的可靠来源线索"

        return (
            f"- 今天：优先打开 {top_targets}，核验岗位是否仍开放、城市和实习周期是否匹配；"
            "只进行人工投递，并把投递入口、状态和备注记录到本地清单。\n"
            "- 3 天内：围绕已确认岗位改一版简历，突出 JD 中反复出现的技能、项目职责和可验证成果；"
            "补搜企业官网、校招官网、学校就业网和内推渠道。\n"
            "- 7 天内：复盘已投递岗位的反馈，把状态推进到已投递、笔试、面试或放弃；"
            "对长期未确认或来源不可靠的岗位降级处理。"
        )

    def _format_risks_and_confirmations(
        self,
        ranked_jobs: list[JobItem],
        diagnostics: list[dict],
    ) -> str:
        items: list[str] = []
        for job in ranked_jobs[:5]:
            job_label = f"{self._clean_field(job.company)} · {self._clean_field(job.title)}"
            for item in self._confirmation_items(job):
                items.append(f"{job_label}：{item}")

        suggestions = self._collect_diagnostic_suggestions(diagnostics)
        for suggestion in suggestions[:3]:
            items.append(f"搜索诊断：{suggestion}")

        if not items:
            items = [
                "招聘信息可能过期，投递前必须点开来源核验。",
                "城市、到岗时间、实习周期和截止日期未明确时，应标记为待确认。",
                "匹配分仅用于排序参考，不代表录用概率。",
            ]

        return self._format_bullets(self._collect_unique(items, limit=12), "暂无可靠信息")

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

    @classmethod
    def _confirmation_items(cls, job: JobItem) -> list[str]:
        items: list[str] = []
        if not cls._has_confirmed(job.source_url):
            items.append("来源链接未确认")
        if not cls._has_confirmed(job.location):
            items.append("城市/远程或现场要求未确认")
        if not cls._has_confirmed(job.duration):
            items.append("到岗时间或实习周期未确认")
        if not cls._has_confirmed(job.deadline):
            items.append("截止日期未确认")
        if not job.requirements and not job.responsibilities:
            items.append("JD 要求和岗位职责不完整")
        if not job.tech_stack:
            items.append("技术栈要求不明确")
        items.extend(cls._collect_unique(job.risks, limit=3))
        return cls._collect_unique(items, limit=8)

    @staticmethod
    def _collect_diagnostic_suggestions(diagnostics: list[dict]) -> list[str]:
        suggestions: list[str] = []
        for item in diagnostics:
            suggestion = item.get("suggestion") if isinstance(item, dict) else None
            if isinstance(suggestion, str) and suggestion.strip():
                suggestions.append(suggestion.strip())
        return ReportingService._collect_unique(suggestions, limit=5)

    @staticmethod
    def _format_target_names(jobs: list[JobItem]) -> str:
        names = []
        for job in jobs:
            title = ReportingService._clean_field(job.title)
            company = ReportingService._clean_field(job.company)
            if title == "未确认" and company == "未确认":
                continue
            names.append(f"{company} · {title}")
        return "、".join(names)

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
    def _has_confirmed(value: str | None) -> bool:
        if not isinstance(value, str):
            return False
        clean = value.strip()
        return bool(clean) and clean not in {"未确认", "暂无可靠信息", "未知"}

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

