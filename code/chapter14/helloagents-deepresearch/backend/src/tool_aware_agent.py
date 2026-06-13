"""Compatibility wrapper adding tool-call event hooks to SimpleAgent."""

from __future__ import annotations

import json
import io
from contextlib import redirect_stdout
from collections.abc import Iterator
from typing import Any, Callable

from hello_agents import SimpleAgent
from hello_agents.tools import ToolRegistry


class ToolAwareSimpleAgent(SimpleAgent):
    """SimpleAgent variant that reports each tool call to a listener."""

    def __init__(
        self,
        name: str,
        llm: Any,
        system_prompt: str | None = None,
        tool_registry: ToolRegistry | None = None,
        enable_tool_calling: bool = True,
        tool_call_listener: Callable[[dict[str, Any]], None] | None = None,
        **kwargs: Any,
    ) -> None:
        with redirect_stdout(io.StringIO()):
            super().__init__(
                name=name,
                llm=llm,
                system_prompt=system_prompt,
                tool_registry=tool_registry,
                enable_tool_calling=enable_tool_calling,
                **kwargs,
            )
        self._tool_call_listener = tool_call_listener

    def _execute_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool call and notify the listener with normalized details."""
        result = super()._execute_tool_call(tool_name, arguments)

        if self._tool_call_listener:
            self._tool_call_listener(
                {
                    "agent_name": self.name,
                    "tool_name": tool_name,
                    "raw_parameters": json.dumps(arguments, ensure_ascii=False),
                    "parsed_parameters": arguments,
                    "result": result,
                }
            )

        return result

    def run(self, input_text: str, **kwargs: Any) -> str:
        """Run while suppressing third-party console output that may break GBK."""
        with redirect_stdout(io.StringIO()):
            return super().run(input_text, **kwargs)

    def stream_run(self, input_text: str, **kwargs: Any) -> Iterator[str]:
        """Stream while suppressing third-party console output that may break GBK."""
        with redirect_stdout(io.StringIO()):
            yield from super().stream_run(input_text, **kwargs)
