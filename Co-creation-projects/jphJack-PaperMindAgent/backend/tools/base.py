"""工具基类与注册表：统一管理 Function Calling 工具"""
from __future__ import annotations

import inspect
from typing import Any, Callable, Optional


class Tool:
    """单个工具：名称 + 描述 + JSON schema + 可调用函数"""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        func: Callable,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.func = func

    def to_schema(self) -> dict:
        """转为 DeepSeek/OpenAI function calling schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """工具注册表：管理多个工具，供 ToolLoop 使用"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def get_callable(self, name: str) -> Optional[Callable]:
        tool = self._tools.get(name)
        return tool.func if tool else None

    def get_callables(self) -> dict[str, Callable]:
        """返回 name -> func 字典，供 ToolLoop 使用"""
        return {name: tool.func for name, tool in self._tools.items()}

    def get_schemas(self) -> list[dict]:
        """返回所有工具的 JSON schema 列表"""
        return [tool.to_schema() for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())
