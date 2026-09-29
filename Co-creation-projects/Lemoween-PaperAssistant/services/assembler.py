"""论文汇总服务"""
from typing import Callable, List

from hello_agents import ToolAwareSimpleAgent

from config import Configuration
from models import PaperSection, PaperState
from utils import strip_thinking_tokens, strip_tool_calls


class ReportAssemblyService:
    """调用汇总 Agent 生成最终论文"""

    def __init__(
        self,
        agent_factory: Callable[[], ToolAwareSimpleAgent],
        config: Configuration,
    ):
        self._agent_factory = agent_factory
        self._config = config

    def assemble(
        self,
        state: PaperState,
        sections: List[PaperSection],
        review_notes: str,
    ) -> str:
        section_blocks = []
        for s in sections:
            section_blocks.append(f"## {s.title}\n\n{s.content or '（暂无内容）'}\n")

        all_refs = [r for s in sections for r in s.references]
        ref_lines = [
            f"[{i}] {ref.get('citation') or ref.get('title', '')}"
            for i, ref in enumerate(all_refs, start=1)
        ]

        prompt = (
            f"论文题目：{state.paper_title or state.research_topic}\n"
            f"研究主题：{state.research_topic}\n"
            f"引用格式：{state.citation_style}\n\n"
            f"章节草稿：\n{''.join(section_blocks)}\n\n"
            f"参考文献条目：\n" + "\n".join(ref_lines) + "\n\n"
            f"审校意见：\n{review_notes}\n\n"
            f"请整合为一份完整论文（标题、摘要、正文、参考文献）。"
        )

        agent = self._agent_factory()
        try:
            response = agent.run(prompt)
        finally:
            agent.clear_history()

        paper = response.strip()
        if self._config.strip_thinking_tokens:
            paper = strip_thinking_tokens(paper)
        return strip_tool_calls(paper).strip()