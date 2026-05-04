"""
对 PyPI / 本地安装的 hello_agents 做运行时补丁（pip 升级后若问题复现可继续依赖此模块）。

1. MemoryTool.execute — ContextBuilder 仍调用 execute(action, **kwargs)，与新版 run({"action": ...}) 对齐。
2. FunctionCallAgent.run — 思考模式 API 要求把 assistant 的 reasoning_content 随 messages 传回。
"""

from __future__ import annotations

from typing import Any, Optional, Union

from hello_agents.core.message import Message


def apply() -> None:
    _patch_memory_tool_execute()
    _patch_function_call_agent_reasoning()


def _patch_memory_tool_execute() -> None:
    from hello_agents.tools.builtin.memory_tool import MemoryTool

    if getattr(MemoryTool, "execute", None):
        return

    def execute(self, action: str, **kwargs) -> str:
        return self.run({"action": action, **kwargs})

    MemoryTool.execute = execute


def _patch_function_call_agent_reasoning() -> None:
    from hello_agents.agents.function_call_agent import FunctionCallAgent

    if getattr(FunctionCallAgent, "_reasoning_fields_from_assistant", None):
        return

    @staticmethod
    def _reasoning_fields_from_assistant(assistant_message: Any) -> dict[str, Any]:
        extra: dict[str, Any] = {}
        rc = getattr(assistant_message, "reasoning_content", None)
        if rc is not None and rc != "":
            extra["reasoning_content"] = rc
        return extra

    FunctionCallAgent._reasoning_fields_from_assistant = _reasoning_fields_from_assistant

    def run(
        self,
        input_text: str,
        *,
        max_tool_iterations: Optional[int] = None,
        tool_choice: Optional[Union[str, dict]] = None,
        **kwargs,
    ) -> str:
        messages: list[dict[str, Any]] = []
        system_prompt = self._get_system_prompt()
        messages.append({"role": "system", "content": system_prompt})

        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": input_text})

        tool_schemas = self._build_tool_schemas()
        if not tool_schemas:
            response_text = self.llm.invoke(messages, **kwargs)
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(response_text, "assistant"))
            return response_text

        iterations_limit = (
            max_tool_iterations if max_tool_iterations is not None else self.max_tool_iterations
        )
        effective_tool_choice: Union[str, dict] = (
            tool_choice if tool_choice is not None else self.default_tool_choice
        )

        current_iteration = 0
        final_response = ""

        while current_iteration < iterations_limit:
            response = self._invoke_with_tools(
                messages,
                tools=tool_schemas,
                tool_choice=effective_tool_choice,
                **kwargs,
            )

            choice = response.choices[0]
            assistant_message = choice.message
            content = self._extract_message_content(assistant_message.content)
            tool_calls = list(assistant_message.tool_calls or [])

            if tool_calls:
                assistant_payload: dict[str, Any] = {"role": "assistant", "content": content}
                assistant_payload.update(
                    FunctionCallAgent._reasoning_fields_from_assistant(assistant_message)
                )
                assistant_payload["tool_calls"] = []

                for tool_call in tool_calls:
                    assistant_payload["tool_calls"].append(
                        {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                    )
                messages.append(assistant_payload)

                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    arguments = self._parse_function_call_arguments(tool_call.function.arguments)
                    result = self._execute_tool_call(tool_name, arguments)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": result,
                        }
                    )

                current_iteration += 1
                continue

            final_response = content
            final_msg: dict[str, Any] = {"role": "assistant", "content": final_response}
            final_msg.update(
                FunctionCallAgent._reasoning_fields_from_assistant(assistant_message)
            )
            messages.append(final_msg)
            break

        if current_iteration >= iterations_limit and not final_response:
            final_choice = self._invoke_with_tools(
                messages,
                tools=tool_schemas,
                tool_choice="none",
                **kwargs,
            )
            final_assistant = final_choice.choices[0].message
            final_response = self._extract_message_content(final_assistant.content)
            limit_msg: dict[str, Any] = {"role": "assistant", "content": final_response}
            limit_msg.update(FunctionCallAgent._reasoning_fields_from_assistant(final_assistant))
            messages.append(limit_msg)

        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_response, "assistant"))
        return final_response

    FunctionCallAgent.run = run
