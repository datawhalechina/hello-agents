"""Streaming ReAct chat agent for CryptoAnalysisAgent."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterator, List, Optional

from hello_agents import HelloAgentsLLM, ToolRegistry

from ..compat import tool_text, wrap_tools
from ..memory.store import MemoryStore
from ..session.store import SessionStore
from ..workspace.manager import WorkspaceManager
from ..tools.builtin import (
    CryptoAnalysisTool,
    ExecuteTool,
    FileTool,
    MemoryTool,
    WebFetchTool,
    WebSearchTool,
)

REACT_TEMPLATE = """{system}

## 近期日记
{daily}

## 可用工具
{tools}

## 对话上下文
{history}

## 当前问题
{question}

## 本轮执行记录
{scratch}

严格按下面格式之一输出，不要同时输出多种格式。

格式 A（继续行动）:
Thought: <你的推理>
Action: <工具名>
Action Input: <JSON 对象>

格式 B（给出最终回答）:
Thought: <简短推理>
Final Answer: <给用户的完整回答>
"""


class CryptoReActAgent:
    """ReAct loop with workspace memory, persistent sessions, and stream events."""

    def __init__(
        self,
        workspace: WorkspaceManager,
        memory: MemoryStore,
        sessions: SessionStore,
        llm: HelloAgentsLLM | None = None,
        get_coordinator=None,
        max_steps: int = 8,
    ):
        self.workspace = workspace
        self.memory = memory
        self.sessions = sessions
        self.llm = llm or HelloAgentsLLM()
        self.get_coordinator = get_coordinator
        self.max_steps = max_steps
        self.name = workspace.read_identity_name()
        self.tool_registry = self._setup_tools()

    def _setup_tools(self) -> ToolRegistry:
        tools = [
            MemoryTool(self.memory),
            FileTool(self.workspace.workspace_path),
            ExecuteTool(self.workspace.workspace_path),
            WebSearchTool(),
            WebFetchTool(),
        ]
        if self.get_coordinator is not None:
            tools.insert(0, CryptoAnalysisTool(self.get_coordinator))
        wrap_tools(*tools)
        registry = ToolRegistry()
        for tool in tools:
            registry.register_tool(tool)
        return registry

    def reload_identity(self) -> None:
        self.name = self.workspace.read_identity_name()

    def chat(self, message: str, session_id: str | None = None) -> str:
        final = ""
        for event in self.iter_events(message, session_id):
            if event["type"] == "done":
                final = event.get("content") or final
        return final

    def iter_events(self, message: str, session_id: str | None = None) -> Iterator[Dict[str, Any]]:
        self.workspace.ensure_workspace_exists()
        self.reload_identity()
        if not session_id:
            session_id = self.sessions.create(_title_from(message))
        yield {"type": "session", "session_id": session_id}

        history = self.sessions.history(session_id)
        scratch: List[str] = []
        tools_used: List[dict] = []
        final_answer = ""

        try:
            for step in range(1, self.max_steps + 1):
                yield {"type": "step_start", "step": step, "max_steps": self.max_steps}
                prompt = self._build_prompt(message, history, scratch)
                raw = ""
                for chunk in stream_llm(self.llm, [{"role": "user", "content": prompt}]):
                    raw += chunk
                parsed = parse_react(raw)
                thought = parsed.get("thought") or ""
                if thought:
                    yield {"type": "thought", "content": thought}

                if parsed.get("final"):
                    final_answer = parsed["final"].strip()
                    for piece in _chunk_text(final_answer):
                        yield {"type": "chunk", "content": piece}
                    break

                action = parsed.get("action")
                if not action:
                    final_answer = raw.strip() or "我暂时无法完成这次推理。"
                    for piece in _chunk_text(final_answer):
                        yield {"type": "chunk", "content": piece}
                    break

                args = parsed.get("input") or {}
                yield {"type": "tool_start", "tool": action, "args": args}
                observation = self._run_tool(action, args)
                tools_used.append({"tool": action, "args": args, "result": _clip(observation, 4000)})
                yield {"type": "tool_finish", "tool": action, "result": _clip(observation, 4000)}
                scratch.append(
                    f"Thought: {thought}\nAction: {action}\nAction Input: {json.dumps(args, ensure_ascii=False)}\nObservation: {_clip(observation, 6000)}"
                )
                yield {"type": "step_finish", "step": step}
            else:
                final_answer = "已达到最大推理步数。请把问题拆得更具体一些，或指定币种后再试。"
                yield {"type": "chunk", "content": final_answer}
        except Exception as exc:
            yield {"type": "error", "error": str(exc)}
            return

        self.sessions.save_turn(session_id, message, final_answer, tools=tools_used)
        try:
            if self.memory.maybe_capture(message):
                yield {"type": "memory", "saved": True}
        except Exception:
            pass
        try:
            self.memory.cleanup(days=30)
        except Exception:
            pass
        yield {"type": "done", "content": final_answer, "session_id": session_id}

    def _build_prompt(self, question: str, history: list[dict], scratch: list[str]) -> str:
        tools_desc = self._tools_description()
        history_text = _format_history(history)
        scratch_text = "\n\n".join(scratch) if scratch else "（尚无）"
        daily = self.memory.recent_daily_text() or "（今日暂无日记）"
        return REACT_TEMPLATE.format(
            system=self.workspace.build_system_prompt(),
            daily=daily,
            tools=tools_desc,
            history=history_text or "（新会话）",
            question=question,
            scratch=scratch_text,
        )

    def _tools_description(self) -> str:
        lines = []
        for name, tool in _iter_tools(self.tool_registry):
            params = []
            if hasattr(tool, "get_parameters"):
                for param in tool.get_parameters() or []:
                    flag = "必填" if getattr(param, "required", False) else "可选"
                    params.append(f"{param.name}({flag})")
            param_text = ", ".join(params) if params else "无"
            lines.append(f"- {name}: {getattr(tool, 'description', '')}\n  参数: {param_text}")
        return "\n".join(lines)

    def _run_tool(self, name: str, args: dict) -> str:
        tool = _get_tool(self.tool_registry, name)
        if tool is None:
            available = ", ".join(n for n, _ in _iter_tools(self.tool_registry))
            return f"未知工具 {name}。可用工具: {available}"
        try:
            return tool_text(tool.run(args or {}))
        except Exception as exc:
            return f"工具执行失败: {exc}"


def stream_llm(llm: HelloAgentsLLM, messages: List[dict]) -> Iterator[str]:
    client = getattr(llm, "client", None)
    model = getattr(llm, "model", None) or getattr(llm, "model_id", None)
    if client is not None and model:
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                stream=True,
            )
            for chunk in stream:
                if not getattr(chunk, "choices", None):
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None) or ""
                if content:
                    yield content
            return
        except Exception:
            pass
    text = _invoke(llm, messages)
    if text:
        yield text


def _invoke(llm: HelloAgentsLLM, messages: List[dict]) -> str:
    if hasattr(llm, "invoke"):
        result = llm.invoke(messages)
        return result if isinstance(result, str) else str(getattr(result, "content", result) or "")
    if hasattr(llm, "think"):
        return llm.think(messages) or ""
    raise RuntimeError("当前 HelloAgentsLLM 没有 invoke/think 方法")


def parse_react(text: str) -> dict:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", cleaned).strip()
    final = _extract(cleaned, r"Final Answer\s*:\s*(.*)$")
    if not final:
        finish = re.search(r"Finish\s*\[(.*)\]", cleaned, re.S | re.I)
        if finish:
            final = finish.group(1).strip()
    thought = _extract(cleaned, r"Thought\s*:\s*(.*?)(?=\n(?:Action|Final Answer)\s*:|\Z)")
    action = _extract(cleaned, r"Action\s*:\s*([^\n]+)")
    if action:
        action = action.strip().strip("`")
        if action.lower().startswith("finish"):
            match = re.search(r"\[(.*)\]", action, re.S)
            return {"thought": thought, "final": (match.group(1) if match else action), "action": None, "input": {}}
    raw_input = _extract(cleaned, r"Action Input\s*:\s*(.*?)(?=\n(?:Thought|Action|Observation|Final Answer)\s*:|\Z)")
    return {
        "thought": thought,
        "final": final,
        "action": None if final else action,
        "input": _parse_input(raw_input),
    }


def _extract(text: str, pattern: str) -> Optional[str]:
    match = re.search(pattern, text, re.S | re.I)
    if not match:
        return None
    return match.group(1).strip()


def _parse_input(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {"input": data}
        except json.JSONDecodeError:
            pass
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {"input": text}


def _iter_tools(registry: ToolRegistry):
    mapping = (
        getattr(registry, "tools", None)
        or getattr(registry, "_tools", None)
        or getattr(registry, "tool_map", None)
    )
    if isinstance(mapping, dict):
        for name, tool in mapping.items():
            yield name, tool
        return
    if hasattr(registry, "get_all_tools"):
        tools = registry.get_all_tools()
        if isinstance(tools, dict):
            yield from tools.items()
            return
        for tool in tools or []:
            yield getattr(tool, "name", str(tool)), tool


def _get_tool(registry: ToolRegistry, name: str):
    if hasattr(registry, "get_tool"):
        try:
            tool = registry.get_tool(name)
            if tool:
                return tool
        except Exception:
            pass
    for tool_name, tool in _iter_tools(registry):
        if tool_name == name:
            return tool
    return None


def _format_history(history: list[dict], limit: int = 12) -> str:
    lines = []
    for msg in history[-limit:]:
        role = "用户" if msg.get("role") == "user" else "助手"
        content = (msg.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {_clip(content, 1200)}")
    return "\n".join(lines)


def _chunk_text(text: str, size: int = 24) -> Iterator[str]:
    if not text:
        return
    for i in range(0, len(text), size):
        yield text[i:i + size]


def _clip(text: str, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "\n…(truncated)"


def _title_from(content: str) -> str:
    text = (content or "").strip().replace("\n", " ")
    return (text[:24] + "…") if len(text) > 24 else (text or "新会话")
