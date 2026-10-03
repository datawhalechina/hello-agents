"""工具桥接：把 PaperMind 工具注册表适配为 HelloAgents 框架的 ToolRegistry

项目的 Function Calling 工具通过桥接成为框架原生 Tool（ToolResponse 协议），
供框架的 SimpleAgent/ReActAgent 直接调度，享受框架的熔断器与参数校验能力。
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Optional

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.registry import ToolRegistry as HelloAgentsToolRegistry
from hello_agents.tools.response import ToolResponse, ToolStatus

from backend.tools.base import Tool as PaperMindTool
from backend.tools.base import ToolRegistry as PaperMindToolRegistry

logger = logging.getLogger(__name__)


class PaperMindHelloAgentsTool(Tool):
    """框架 Tool 适配器：把 PaperMind 工具包装为框架原生工具

    - arun: 项目工具为 async 函数时直接 await
    - run: 同步执行（内部用事件循环驱动 async 工具）
    """

    def __init__(self, tool: PaperMindTool) -> None:
        super().__init__(name=tool.name, description=tool.description)
        self._func = tool.func
        self._schema = tool.to_schema()

    def to_openai_schema(self) -> dict[str, Any]:
        """直接沿用项目工具的 OpenAI function calling schema（参数定义更完整）"""
        return self._schema

    def get_parameters(self) -> list[ToolParameter]:
        """从项目工具 schema 转换出框架 ToolParameter 列表"""
        params: list[ToolParameter] = []
        properties = self._schema.get("function", {}).get("parameters", {}).get("properties", {})
        required = self._schema.get("function", {}).get("parameters", {}).get("required", [])
        for pname, pspec in properties.items():
            params.append(
                ToolParameter(
                    name=pname,
                    type=pspec.get("type", "string"),
                    description=pspec.get("description", ""),
                    required=pname in required,
                )
            )
        return params

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        """同步执行项目工具，返回框架 ToolResponse"""
        try:
            if inspect.iscoroutinefunction(self._func):
                result = asyncio.run(self._func(**parameters))
            else:
                result = self._func(**parameters)
            return self._to_success_response(result)
        except Exception as exc:
            logger.warning("工具 %s 执行失败: %s", self.name, exc)
            return ToolResponse(
                status=ToolStatus.ERROR,
                text=f"工具执行失败: {exc}",
                error_info={"tool": self.name, "message": str(exc)},
            )

    async def arun(self, parameters: dict[str, Any]) -> ToolResponse:
        """异步执行项目工具（优先路径），返回框架 ToolResponse"""
        try:
            if inspect.iscoroutinefunction(self._func):
                result = await self._func(**parameters)
            else:
                result = await asyncio.to_thread(self._func, **parameters)
            return self._to_success_response(result)
        except Exception as exc:
            logger.warning("工具 %s 执行失败: %s", self.name, exc)
            return ToolResponse(
                status=ToolStatus.ERROR,
                text=f"工具执行失败: {exc}",
                error_info={"tool": self.name, "message": str(exc)},
            )

    def _to_success_response(self, result: Any) -> ToolResponse:
        """把项目工具返回值转为 ToolResponse：字符串走 text，结构化对象走 data"""
        if isinstance(result, str):
            return ToolResponse(status=ToolStatus.SUCCESS, text=result)
        if isinstance(result, dict):
            return ToolResponse(status=ToolStatus.SUCCESS, text="ok", data=result)
        return ToolResponse(status=ToolStatus.SUCCESS, text=str(result))


def build_hello_agents_registry(
    registry: PaperMindToolRegistry,
    tool_names: Optional[list[str]] = None,
) -> HelloAgentsToolRegistry:
    """把 PaperMind 工具注册表转换为 HelloAgents 框架工具注册表

    Args:
        registry: 项目工具注册表
        tool_names: 仅桥接指定工具子集（None 表示全部）

    Returns:
        HelloAgents ToolRegistry，框架 Agent 可直接使用
    """
    ha_registry = HelloAgentsToolRegistry()
    names = tool_names or registry.names()
    for name in names:
        tool = registry.get(name)
        if tool is None:
            logger.warning("桥接跳过：未注册的工具 %s", name)
            continue
        ha_registry.register_tool(PaperMindHelloAgentsTool(tool))
    return ha_registry
