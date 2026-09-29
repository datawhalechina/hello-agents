"""论文审校服务"""
from typing import Callable

from hello_agents import ToolAwareSimpleAgent

from config import Configuration
from models import PaperState
from utils import strip_thinking_tokens, strip_tool_calls


class ReviewService:
    """调用审校 Agent 对论文草稿进行审阅"""

    def __init__(
        self,
        agent_factory: Callable[[], ToolAwareSimpleAgent],
        config: Configuration,
    ):
        self._agent_factory = agent_factory
        self._config = config

    def review(self, state: PaperState, full_draft: str) -> str:
        prompt = (
            f"论文题目：{state.paper_title or state.research_topic}\n"
            f"引用格式：{state.citation_style}\n\n"
            f"论文草稿：\n{full_draft[:8000]}\n\n"
            f"请从逻辑、引用、术语、连贯性和可复现性五个维度审校。"
        )

        agent = self._agent_factory()
        try:
            response = agent.run(prompt)
        finally:
            agent.clear_history()

        notes = response.strip()
        if self._config.strip_thinking_tokens:
            notes = strip_thinking_tokens(notes)
        return strip_tool_calls(notes).strip()