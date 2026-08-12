from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass
from typing import Any, Iterator, Optional

from hello_agents import HelloAgentsLLM, SimpleAgent


def _resolve_mcp_tool_class() -> Optional[type]:
    """Best-effort resolve for MCP tool class across hello-agents versions."""
    candidates = [
        ("hello_agents.tools", "MCPTool"),
        ("hello_agents.tools.mcp", "MCPTool"),
    ]
    for module_name, class_name in candidates:
        try:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name, None)
            if cls is not None:
                return cls
        except Exception:
            continue
    return None


MCPToolClass = _resolve_mcp_tool_class()


@dataclass
class AgentRuntime:
    llm: Optional[HelloAgentsLLM]
    mcp_tool: Optional[Any]


class BaseNetworkAgent:
    def __init__(self, name: str, system_prompt: str) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.runtime = self._bootstrap_runtime()

        self.agent: Optional[SimpleAgent] = None
        if self.runtime.llm is not None:
            self.agent = SimpleAgent(name=name, llm=self.runtime.llm, system_prompt=system_prompt)
            if self.runtime.mcp_tool is not None:
                self.agent.add_tool(self.runtime.mcp_tool)

    def _bootstrap_runtime(self) -> AgentRuntime:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key and api_key.startswith("your-"):
            api_key = None
        if not api_key:
            return AgentRuntime(llm=None, mcp_tool=None)

        base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        model = os.getenv("LLM_MODEL_ID") or os.getenv("OPENAI_MODEL")
        timeout_str = os.getenv("LLM_TIMEOUT", "15")
        try:
            timeout = int(timeout_str)
        except ValueError:
            timeout = 15

        llm_kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout}
        if base_url:
            llm_kwargs["base_url"] = base_url
        if model:
            llm_kwargs["model"] = model

        llm = HelloAgentsLLM(**llm_kwargs)
        mcp_tool = None
        if MCPToolClass is not None:
            mcp_tool = MCPToolClass(
                name="network_data",
                description="Network health data service",
                server_command=[sys.executable, "-m", "src.tools.data_mcp_server"],
                auto_expand=True,
            )
        return AgentRuntime(llm=llm, mcp_tool=mcp_tool)

    @property
    def enabled(self) -> bool:
        return self.agent is not None

    @property
    def llm_enabled(self) -> bool:
        return self.runtime.llm is not None

    @property
    def mcp_enabled(self) -> bool:
        return self.runtime.mcp_tool is not None

    def run_llm(self, prompt: str) -> Optional[str]:
        if self.agent is None:
            return None
        try:
            return self.agent.run(prompt)
        except Exception:
            return None

    def stream_llm(self, prompt: str) -> Optional[Iterator[str]]:
        if self.agent is None:
            return None
        try:
            return self.agent.stream_run(prompt)
        except Exception:
            return None

    def list_tool_names(self) -> list[str]:
        if self.agent is None:
            return []
        if not hasattr(self.agent, "list_tools"):
            return []
        try:
            tools = self.agent.list_tools()
        except Exception:
            return []
        names: list[str] = []
        for t in tools or []:
            names.append(getattr(t, "name", str(t)))
        return names
