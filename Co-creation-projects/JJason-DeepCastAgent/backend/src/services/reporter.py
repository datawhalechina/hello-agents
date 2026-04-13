"""将任务结果整合为最终报告的服务。"""

from __future__ import annotations

import json

from hello_agents import ToolAwareSimpleAgent

from config import Configuration
from models import SummaryState
from services.text_processing import strip_tool_calls
from utils import strip_thinking_tokens


class ReportingService:
    """生成最终的结构化报告。"""

    def __init__(  # noqa: D107
        self, report_agent: ToolAwareSimpleAgent, config: Configuration
    ) -> None:
        self._agent = report_agent
        self._config = config

    def generate_report(self, state: SummaryState) -> str:
        """
        基于完成的任务生成结构化报告。

        Args:
            state: 包含任务结果和笔记的研究状态。

        Returns:
            Markdown 格式的报告文本。
        """
        tasks_block = []
        for task in state.todo_items:
            summary_block = task.summary or "暂无可用信息"
            sources_block = task.sources_summary or "暂无来源"
            tasks_block.append(
                f"### 任务 {task.id}: {task.title}\n"
                f"- 任务目标：{task.intent}\n"
                f"- 检索查询：{task.query}\n"
                f"- 执行状态：{task.status}\n"
                f"- 任务总结：\n{summary_block}\n"
                f"- 来源概览：\n{sources_block}\n"
            )

        note_references = []
        for task in state.todo_items:
            if task.note_id:
                note_references.append(
                    f"- 任务 {task.id}《{task.title}》：note_id={task.note_id}"
                )

        notes_section = (
            "\n".join(note_references) if note_references else "- 暂无可用任务笔记"
        )

        read_template = json.dumps(
            {"action": "read", "note_id": "<note_id>"}, ensure_ascii=False
        )
        # 结论笔记模板，让 LLM 自己填充实际内容
        create_conclusion_template = json.dumps(
            {
                "action": "create",
                "title": f"研究报告：{state.research_topic}",
                "note_type": "conclusion",
                "tags": ["deep_research", "report"],
                "content": "<请在此填写报告核心要点>",
            },
            ensure_ascii=False,
        )

        prompt = (
            f"研究主题：{state.research_topic}\n"
            f"任务概览：\n{''.join(tasks_block)}\n"
            f"可用任务笔记：\n{notes_section}\n"
            f"请针对每条任务笔记使用格式：[TOOL_CALL:note:{read_template}] 读取内容，整合所有信息后撰写报告。\n"
            f"如需输出汇总结论，可追加调用 note 工具保存报告要点，参数模板如下（需将 content 替换为实际报告要点）：\n"
            f"  {create_conclusion_template}\n"
            "**重要**：content 字段必须填写本次研究的实际核心发现和结论，不要使用占位文本。"
        )

        response = self._agent.run(prompt)
        self._agent.clear_history()

        report_text = response.strip()
        if self._config.strip_thinking_tokens:
            report_text = strip_thinking_tokens(report_text)

        report_text = strip_tool_calls(report_text).strip()

        return report_text or "报告生成失败，请检查输入。"
