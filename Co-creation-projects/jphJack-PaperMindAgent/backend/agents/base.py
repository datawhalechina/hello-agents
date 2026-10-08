"""Agent 基类：所有专职 Agent 与 Controller 的公共接口"""
from __future__ import annotations

from typing import Any, Optional

from backend.llm.client import DeepSeekClient
from backend.llm.function_calling import ToolLoop
from backend.tools.base import ToolRegistry


class BaseAgent:
    """专职 Agent 基类：绑定角色提示词 + 工具子集，通过 ToolLoop 执行任务"""

    def __init__(
        self,
        name: str,
        role: str,
        client: DeepSeekClient,
        registry: ToolRegistry,
        tool_names: Optional[list[str]] = None,
    ):
        self.name = name
        self.role = role  # system prompt 角色描述
        self.client = client
        self.registry = registry
        # 该 Agent 可用的工具子集（None 表示全部）
        self.tool_names = tool_names or registry.names()

    def _build_tools_schema(self) -> list[dict]:
        """构建该 Agent 可用工具的 JSON schema 列表"""
        all_schemas = {s["function"]["name"]: s for s in self.registry.get_schemas()}
        return [all_schemas[n] for n in self.tool_names if n in all_schemas]

    def _build_callables(self) -> dict:
        """构建该 Agent 可用工具的 name->func 字典"""
        all_callables = self.registry.get_callables()
        return {n: all_callables[n] for n in self.tool_names if n in all_callables}

    async def run(self, task: str, context: Optional[str] = None) -> dict:
        """执行任务：构造消息→ToolLoop 循环→返回结果与工具调用记录"""
        messages = [{"role": "system", "content": self.role}]
        user_content = task
        if context:
            user_content = f"上下文：\n{context}\n\n任务：\n{task}"
        messages.append({"role": "user", "content": user_content})

        tool_loop = ToolLoop(self.client, self._build_callables())
        result_text = await tool_loop.run(
            messages=messages,
            tools_schema=self._build_tools_schema(),
            max_iterations=15,
        )

        return {
            "agent": self.name,
            "result": result_text,
            "tool_calls": [tc.model_dump() for tc in tool_loop.get_tool_records()],
        }
