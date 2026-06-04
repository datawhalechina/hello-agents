"""Task summarization utilities."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from typing import Tuple

from tool_aware_agent import ToolAwareSimpleAgent

from models import SummaryState, TodoItem
from config import Configuration
from utils import strip_thinking_tokens
from services.llm_resilience import (
    is_rate_limit_error,
    run_with_llm_retry,
    stream_with_llm_retry,
)
from services.notes import build_note_guidance
from services.text_processing import strip_tool_calls

logger = logging.getLogger(__name__)
MAX_FALLBACK_CONTEXT_CHARS = 1800


class SummarizationService:
    """Handles synchronous and streaming task summarization."""

    def __init__(
        self,
        summarizer_factory: Callable[[], ToolAwareSimpleAgent],
        config: Configuration,
    ) -> None:
        self._agent_factory = summarizer_factory
        self._config = config

    def summarize_task(self, state: SummaryState, task: TodoItem, context: str) -> str:
        """Generate a task-specific summary using the summarizer agent."""

        prompt = self._build_prompt(state, task, context)

        agent = self._agent_factory()
        try:
            response = run_with_llm_retry(
                lambda: agent.run(prompt),
                self._config,
                operation=f"summarizer task {task.id}",
            )
        except Exception as exc:
            if not is_rate_limit_error(exc):
                raise
            logger.warning(
                "Task %s summary hit LLM rate limit; using fallback summary",
                task.id,
            )
            return self._build_rate_limit_fallback_summary(state, task, context)
        finally:
            agent.clear_history()

        summary_text = response.strip()
        if self._config.strip_thinking_tokens:
            summary_text = strip_thinking_tokens(summary_text)

        summary_text = strip_tool_calls(summary_text).strip()

        return summary_text or "暂无可用信息"

    def stream_task_summary(
        self, state: SummaryState, task: TodoItem, context: str
    ) -> Tuple[Iterator[str], Callable[[], str]]:
        """Stream the summary text for a task while collecting full output."""

        prompt = self._build_prompt(state, task, context)
        remove_thinking = self._config.strip_thinking_tokens
        raw_buffer = ""
        visible_output = ""
        emit_index = 0
        agent = self._agent_factory()

        def flush_visible() -> Iterator[str]:
            nonlocal emit_index, raw_buffer
            while True:
                start = raw_buffer.find("<think>", emit_index)
                if start == -1:
                    if emit_index < len(raw_buffer):
                        segment = raw_buffer[emit_index:]
                        emit_index = len(raw_buffer)
                        if segment:
                            yield segment
                    break

                if start > emit_index:
                    segment = raw_buffer[emit_index:start]
                    emit_index = start
                    if segment:
                        yield segment

                end = raw_buffer.find("</think>", start)
                if end == -1:
                    break
                emit_index = end + len("</think>")

        def generator() -> Iterator[str]:
            nonlocal raw_buffer, visible_output, emit_index
            try:
                for chunk in stream_with_llm_retry(
                    lambda: agent.stream_run(prompt),
                    self._config,
                    operation=f"summarizer stream task {task.id}",
                ):
                    raw_buffer += chunk
                    if remove_thinking:
                        for segment in flush_visible():
                            visible_output += segment
                            if segment:
                                yield segment
                    else:
                        visible_output += chunk
                        if chunk:
                            yield chunk
            except Exception as exc:
                if not is_rate_limit_error(exc):
                    raise

                logger.warning(
                    "Task %s streaming summary hit LLM rate limit; using fallback summary",
                    task.id,
                )
                fallback = self._build_rate_limit_fallback_summary(state, task, context)
                separator = "\n\n" if visible_output.strip() else ""
                visible_output += separator + fallback
                if separator:
                    yield separator
                yield fallback
            finally:
                if remove_thinking:
                    for segment in flush_visible():
                        visible_output += segment
                        if segment:
                            yield segment
                agent.clear_history()

        def get_summary() -> str:
            if remove_thinking:
                cleaned = strip_thinking_tokens(visible_output)
            else:
                cleaned = visible_output

            return strip_tool_calls(cleaned).strip()

        return generator(), get_summary

    def _build_rate_limit_fallback_summary(
        self, state: SummaryState, task: TodoItem, context: str
    ) -> str:
        """Build a deterministic task summary when the LLM is rate-limited."""

        source_excerpt = self._source_excerpt(context)
        user_needs = state.research_topic or "未确认"

        return (
            "## 任务总结\n\n"
            "> LLM 限流，已基于搜索来源生成兜底摘要。请优先点开来源核验岗位状态、JD、城市和截止日期。\n\n"
            "### 关键信息\n\n"
            f"- 用户需求：{user_needs}\n"
            f"- 当前任务：{task.title}\n"
            f"- 任务目标：{task.intent}\n"
            f"- 检索 query：{task.query}\n\n"
            "### 岗位/JD线索\n\n"
            "- 本次未完成模型归纳，岗位、公司、薪资、截止日期均不自动补全。\n"
            "- 如来源标题或摘要中出现招聘、JD、岗位详情、投递入口，请点开原链接确认。\n\n"
            "### 投递渠道\n\n"
            "- 优先核验招聘平台岗位详情页、公司招聘官网、校招官网、学校就业网和内推渠道。\n"
            "- 若来源多为教程、博客或面经，请调整 query 或切换搜索引擎后重跑。\n\n"
            "### 简历/项目建议\n\n"
            "- 先围绕目标岗位 JD 强化技术关键词、项目职责、量化结果和岗位匹配点。\n"
            "- 当前摘要为限流兜底版本，简历建议需结合确认后的 JD 再细化。\n\n"
            "### 下一步建议\n\n"
            "- 等待一段时间后重试，或降低同一账号的并发/调用频率。\n"
            "- 打开下列来源线索，手动确认可靠岗位并记录投递入口。\n\n"
            "### 来源线索\n\n"
            f"{source_excerpt}"
        )

    @staticmethod
    def _source_excerpt(context: str) -> str:
        cleaned = strip_tool_calls(context or "").strip()
        if not cleaned:
            return "- 暂无可靠来源上下文。"

        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        selected: list[str] = []

        for line in lines:
            if len(selected) >= 8:
                break
            if "http" in line.lower() or "标题" in line or "来源" in line:
                selected.append(line)

        if not selected:
            selected = lines[:6]

        excerpt = "\n".join(f"- {line[:220]}" for line in selected)
        if len(excerpt) > MAX_FALLBACK_CONTEXT_CHARS:
            excerpt = f"{excerpt[:MAX_FALLBACK_CONTEXT_CHARS].rstrip()}\n- ...[已截断]"
        return excerpt

    def _build_prompt(self, state: SummaryState, task: TodoItem, context: str) -> str:
        """Construct the summarization prompt shared by both modes."""

        return (
            "<用户需求>\n"
            f"{state.research_topic}\n"
            "</用户需求>\n\n"
            "<当前求职任务>\n"
            f"任务名称：{task.title}\n"
            f"任务目标：{task.intent}\n"
            f"检索 query：{task.query}\n"
            "</当前求职任务>\n\n"
            "<来源上下文>\n"
            f"{context}\n"
            "</来源上下文>\n\n"
            f"{build_note_guidance(task)}\n"
            "请直接返回一份面向用户的 Markdown 岗位分析总结，"
            "必须包含关键信息、岗位/JD线索、投递渠道、简历/项目建议、下一步建议。"
            "保留可追溯来源线索；不要编造岗位、薪资、截止日期或链接；"
            "不要输出或残留 [TOOL_CALL:...] 指令。"
        )
