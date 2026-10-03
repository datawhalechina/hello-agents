"""HelloAgents 框架 Agent 封装：把框架原生 Agent 接入 PaperMind 执行链路

提供两类框架 Agent 封装：
- build_reviewer_agent: 基于框架 SimpleAgent 的质量审核 Agent（Reflexion 自校验使用）
- run_react_task: 基于框架 ReActAgent 的单步任务执行（桥接项目工具，框架原生工具调度）
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from hello_agents import HelloAgentsLLM, ReActAgent, SimpleAgent

from backend.tools.base import ToolRegistry as PaperMindToolRegistry
from backend.tools.hello_agents_bridge import build_hello_agents_registry

logger = logging.getLogger(__name__)


def build_reviewer_agent(
    llm: HelloAgentsLLM,
    name: str = "QualityReviewer",
    system_prompt: str = "你是质量审核员，负责对照上下文检查 Agent 输出质量。只输出 JSON。",
) -> SimpleAgent:
    """构建框架 SimpleAgent 形态的质量审核 Agent（无工具，纯推理）"""
    return SimpleAgent(name=name, llm=llm, system_prompt=system_prompt)


async def run_reviewer_check(agent: SimpleAgent, prompt: str) -> str:
    """通过框架 SimpleAgent 异步执行审核，返回文本结果"""
    return await agent.arun(prompt)


def build_react_agent(
    name: str,
    llm: HelloAgentsLLM,
    registry: PaperMindToolRegistry,
    system_prompt: str,
    tool_names: Optional[list[str]] = None,
    max_steps: int = 8,
) -> ReActAgent:
    """构建框架 ReActAgent：项目工具经桥接进入框架工具注册表"""
    ha_registry = build_hello_agents_registry(registry, tool_names)
    return ReActAgent(
        name=name,
        llm=llm,
        tool_registry=ha_registry,
        system_prompt=system_prompt,
        max_steps=max_steps,
    )


async def run_react_task(
    name: str,
    llm: HelloAgentsLLM,
    registry: PaperMindToolRegistry,
    system_prompt: str,
    task: str,
    tool_names: Optional[list[str]] = None,
    max_steps: int = 8,
) -> dict[str, Any]:
    """用框架 ReActAgent 执行单步任务，返回项目统一的结果结构

    Returns:
        {"agent": name, "result": str, "tool_calls": []}
        （框架 ReActAgent 内部完成工具调度，工具明细由框架 TraceLogger 记录）
    """
    agent = build_react_agent(name, llm, registry, system_prompt, tool_names, max_steps)
    result = await agent.arun(task)
    return {"agent": name, "result": result, "tool_calls": []}
