"""章节撰写服务"""
import logging
from typing import Any, Callable, Dict, List

from hello_agents import ToolAwareSimpleAgent

from config import Configuration
from models import PaperSection, PaperState
from utils import strip_thinking_tokens, strip_tool_calls

logger = logging.getLogger(__name__)


class SectionWritingService:
    """调用写作 Agent 完成章节草稿"""

    def __init__(
        self,
        agent_factory: Callable[[], ToolAwareSimpleAgent],
        config: Configuration,
    ):
        self._agent_factory = agent_factory
        self._config = config

    def write_section(
        self,
        state: PaperState,
        section: PaperSection,
        references: List[Dict[str, Any]],
        previous_context: str = "",
    ) -> str:
        refs_block = self._format_references(references)

        prompt = (
            f"论文题目：{state.paper_title or state.research_topic}\n"
            f"章节标题：{section.title}\n"
            f"章节意图：{section.intent}\n"
            f"目标字数：{section.target_words}\n\n"
            f"## 可用文献（引用必须来自以下列表）\n{refs_block}\n\n"
            f"## 已完成章节的上下文\n{previous_context[-800:]}\n\n"
            f"## 撰写要求\n"
            f"1. 写作过程中如需了解论文原文细节，**调用 search_paper_library 工具**；\n"
            f"2. 引用必须来自上方文献列表，禁止引入网页链接；\n"
            f"3. 使用 format_citation 生成规范引用条目；\n"
            f"4. 撰写完成后将章节草稿写入笔记（note 工具）。"
        )

        agent = self._agent_factory()
        try:
            response = agent.run(prompt)
        finally:
            agent.clear_history()

        content = response.strip()
        if self._config.strip_thinking_tokens:
            content = strip_thinking_tokens(content)
        return strip_tool_calls(content).strip()

    @staticmethod
    def _format_references(references: List[Dict[str, Any]]) -> str:
        if not references:
            return "（暂无检索到的文献）"
        lines = []
        for i, ref in enumerate(references, start=1):
            lines.append(
                f"[{i}] {ref.get('title', '')} "
                f"({ref.get('year', '')}) — {ref.get('venue', '')} "
                f"DOI: {ref.get('doi', '')} "
                f"PDF: {'已索引' if ref.get('indexed') else '未下载'}"
            )
        return "\n".join(lines)