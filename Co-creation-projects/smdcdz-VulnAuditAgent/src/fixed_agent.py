# -*- coding: utf-8 -*-
"""修复 hello_agents SimpleAgent 的兼容性问题的子类
问题：当模型回复只包含工具调用标记时，框架把空字符串作为 assistant 消息
加入历史，部分模型服务（如 Kimi）会拒绝空 assistant 内容（400 错误）。
修复：空内容时保留原文，保证消息非空。
"""
from hello_agents import SimpleAgent
from hello_agents.core.message import Message


class FixedSimpleAgent(SimpleAgent):
    """修复空 assistant 消息兼容性问题的 SimpleAgent"""

    def run(self, input_text: str, max_tool_iterations: int = 3, **kwargs) -> str:
        messages = []
        enhanced_system_prompt = self._get_enhanced_system_prompt()
        messages.append({"role": "system", "content": enhanced_system_prompt})
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": input_text})

        if not self.enable_tool_calling:
            response = self.llm.invoke(messages, **kwargs)
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(response, "assistant"))
            return response

        current_iteration = 0
        final_response = ""
        while current_iteration < max_tool_iterations:
            response = self.llm.invoke(messages, **kwargs)
            tool_calls = self._parse_tool_calls(response)

            if tool_calls:
                tool_results = []
                clean_response = response
                for call in tool_calls:
                    result = self._execute_tool_call(call["tool_name"], call["parameters"])
                    tool_results.append(result)
                    clean_response = clean_response.replace(call["original"], "")

                # 修复：空 assistant 内容会导致部分模型服务 400
                if not clean_response.strip():
                    clean_response = response

                messages.append({"role": "assistant", "content": clean_response})
                tool_results_text = "\n\n".join(tool_results)
                messages.append({"role": "user", "content": f"工具执行结果：\n{tool_results_text}\n\n请基于这些结果给出完整的回答。"})
                current_iteration += 1
                continue

            final_response = response
            break

        if current_iteration >= max_tool_iterations and not final_response:
            final_response = self.llm.invoke(messages, **kwargs)

        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_response, "assistant"))
        return final_response
