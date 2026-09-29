"""章节规划服务"""
import json
import logging
from typing import Any, List

from hello_agents import ToolAwareSimpleAgent

from config import Configuration
from models import PaperSection, PaperState
from prompts import get_current_date, paper_planner_instructions
from utils import strip_thinking_tokens, strip_tool_calls

logger = logging.getLogger(__name__)


class PlanningService:
    """封装规划 Agent，产出结构化章节列表"""

    def __init__(self, planner_agent: ToolAwareSimpleAgent, config: Configuration):
        self._agent = planner_agent
        self._config = config

    def plan_outline(self, state: PaperState) -> List[PaperSection]:
        prompt = paper_planner_instructions.format(
            current_date=get_current_date(),
            research_topic=state.research_topic,
            paper_type=state.paper_type,
            target_sections=self._config.target_sections,
            target_words_per_section=self._config.target_words_per_section,
        )
        response = self._agent.run(prompt)
        self._agent.clear_history()

        logger.info("Planner raw output (truncated): %s", response[:500])

        payload = self._extract_payload(response)
        if payload.get("paper_title"):
            state.paper_title = str(payload["paper_title"]).strip()

        sections: List[PaperSection] = []
        for idx, item in enumerate(payload.get("sections") or [], start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or f"章节{idx}").strip()
            intent = str(item.get("intent") or "").strip()
            keywords = item.get("keywords") or []
            if isinstance(keywords, str):
                keywords = [keywords]
            target_words = int(item.get("target_words")
                               or self._config.target_words_per_section)
            sections.append(PaperSection(
                id=idx, title=title, intent=intent,
                keywords=list(keywords), target_words=target_words,
            ))

        return sections

    @staticmethod
    def create_fallback_sections() -> List[PaperSection]:
        """规划失败时的回退章节（参照第十四章 create_fallback_task）"""
        defaults = [
            ("Introduction", "介绍研究背景、问题与贡献", ["background", "motivation"]),
            ("Related Work", "梳理领域已有研究与差距", ["related work", "survey"]),
            ("Method", "阐述研究方法与实现细节",
             ["method", "approach", "algorithm"]),
            ("Experiments", "呈现实验设计与结果分析",
             ["experiment", "evaluation", "benchmark"]),
            ("Conclusion", "总结贡献与未来方向",
             ["conclusion", "future work"]),
        ]
        return [
            PaperSection(id=i + 1, title=t, intent=it, keywords=kw)
            for i, (t, it, kw) in enumerate(defaults)
        ]

    def _extract_payload(self, response: str) -> dict[str, Any]:
        """从 Agent 响应中提取 JSON（参照第十四章 PlanningService._extract_json）"""
        text = response.strip()
        if self._config.strip_thinking_tokens:
            text = strip_thinking_tokens(text)
        text = strip_tool_calls(text).strip()

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        return {}