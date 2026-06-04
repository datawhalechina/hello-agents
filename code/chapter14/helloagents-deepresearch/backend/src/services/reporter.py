"""Service that consolidates task results into the final report."""

from __future__ import annotations

import logging

from tool_aware_agent import ToolAwareSimpleAgent

from models import SummaryState
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
            "## 2. 机会与渠道发现\n\n"
            "以下内容来自各求职任务的搜索和总结结果；因最终报告模型调用失败，"
            "本报告使用后端兜底模板生成，请优先点开来源核验岗位状态。\n\n"
            f"{''.join(task_lines) or '暂无可靠信息'}\n"
            "## 3. 岗位要求与匹配分析\n\n"
            "暂无完整自动汇总。请优先查看各任务摘要中的 JD、技能栈、城市和时间要求。\n\n"
            "## 4. 简历与项目优化建议\n\n"
            "优先围绕目标岗位 JD 强化技能关键词、项目职责、量化结果和与岗位要求的对应关系。\n\n"
            "## 5. 投递行动计划\n\n"
            "- 今天：打开高相关来源，确认岗位是否仍在招聘，并记录投递链接。\n"
            "- 三天内：按城市和技术栈筛选岗位，优先投递官网、校招和内推渠道。\n"
            "- 一周内：根据 JD 更新简历项目描述，补齐高频技能短板。\n\n"
            "## 6. 风险与待确认信息\n\n"
            "- 招聘信息可能过期，需点开来源核验。\n"
            "- 城市、到岗时间、实习周期和截止日期若未在来源中明确，应标记为未确认。\n"
            "- 当前匹配分析未结构化评分，仅作为投递前的初筛参考。\n\n"
            "## 7. 参考来源\n\n"
            f"{''.join(source_lines) or '暂无来源'}"
        )

