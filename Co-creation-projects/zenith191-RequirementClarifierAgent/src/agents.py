"""使用官方 HelloAgents SimpleAgent 构建协作团队。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from hello_agents import Config, HelloAgentsLLM, SimpleAgent
from hello_agents.tools import ToolRegistry

from .config import LLMSettings
from .prompts import (
    REPORT_SYNTHESIZER_PROMPT,
    REQUIREMENT_ANALYST_PROMPT,
    RISK_REVIEWER_PROMPT,
    SOLUTION_ARCHITECT_PROMPT,
)


class AgentLike(Protocol):
    """便于离线测试注入替身，同时生产环境始终使用 SimpleAgent。"""

    def run(self, input_text: str, **kwargs: object) -> str:
        """处理一个阶段的输入并返回文本。"""

        ...


@dataclass(frozen=True)
class AgentTeam:
    """顺序协作的四个角色。"""

    analyst: AgentLike
    architect: AgentLike
    reviewer: AgentLike
    synthesizer: AgentLike


def build_agent_team(settings: LLMSettings, tool_registry: ToolRegistry) -> AgentTeam:
    """用同一个 HelloAgentsLLM 实例创建四个官方 SimpleAgent。"""

    settings.validate()
    llm = HelloAgentsLLM(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.base_url,
        temperature=settings.temperature,
        timeout=settings.timeout,
    )
    config = Config(debug=False, max_history_length=20)

    return AgentTeam(
        analyst=SimpleAgent(
            name="需求分析师",
            llm=llm,
            system_prompt=REQUIREMENT_ANALYST_PROMPT,
            config=config,
            tool_registry=tool_registry,
        ),
        architect=SimpleAgent(
            name="方案架构师",
            llm=llm,
            system_prompt=SOLUTION_ARCHITECT_PROMPT,
            config=config,
        ),
        reviewer=SimpleAgent(
            name="风险审查员",
            llm=llm,
            system_prompt=RISK_REVIEWER_PROMPT,
            config=config,
        ),
        synthesizer=SimpleAgent(
            name="报告整合员",
            llm=llm,
            system_prompt=REPORT_SYNTHESIZER_PROMPT,
            config=config,
            tool_registry=tool_registry,
        ),
    )
