"""ReAct Agent实现 - 推理与行动结合的智能体"""

import re
from typing import Optional, List, Tuple, Iterator
from ..core.agent import Agent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.stream import StreamEvent
from ..tools.registry import ToolRegistry

# 默认ReAct提示词模板
DEFAULT_REACT_PROMPT = """你是一个具备推理和行动能力的AI助手。你可以通过思考分析问题，然后调用合适的工具来获取信息，最终给出准确的答案。

## 可用工具
{tools}

## 工作流程
请严格按照以下格式进行回应，每次只能执行一个步骤：

Thought: 分析问题，确定需要什么信息，制定研究策略。
Action: 选择合适的工具获取信息，格式为：
- `{{tool_name}}[{{tool_input}}]`：调用工具获取信息。
- `Finish[研究结论]`：当你有足够信息得出结论时。

## 重要提醒
1. 每次回应必须包含Thought和Action两部分
2. 工具调用的格式必须严格遵循：工具名[参数]
3. 只有当你确信有足够信息回答问题时，才使用Finish
4. 如果工具返回的信息不够，继续使用其他工具或相同工具的不同参数

## 当前任务
**Question:** {question}

## 执行历史
{history}

现在开始你的推理和行动："""


class ReActAgent(Agent):
    """
    ReAct (Reasoning and Acting) Agent

    结合推理和行动的智能体，能够：
    1. 分析问题并制定行动计划
    2. 调用外部工具获取信息
    3. 基于观察结果进行推理
    4. 迭代执行直到得出最终答案

    这是一个经典的Agent范式，特别适合需要外部信息的任务。
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: Optional[ToolRegistry] = None,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: int = 5,
        custom_prompt: Optional[str] = None,
    ):
        """
        初始化ReActAgent

        Args:
            name: Agent名称
            llm: LLM实例
            tool_registry: 工具注册表（可选，如果不提供则创建空的工具注册表）
            system_prompt: 系统提示词
            config: 配置对象
            max_steps: 最大执行步数
            custom_prompt: 自定义提示词模板
        """
        super().__init__(name, llm, system_prompt, config)

        # 如果没有提供tool_registry，创建一个空的
        if tool_registry is None:
            self.tool_registry = ToolRegistry()
        else:
            self.tool_registry = tool_registry

        self.max_steps = max_steps
        self.current_history: List[str] = []

        # 设置提示词模板：用户自定义优先，否则使用默认模板
        self.prompt_template = custom_prompt if custom_prompt else DEFAULT_REACT_PROMPT

    def add_tool(self, tool):
        """添加工具到工具注册表"""
        self.tool_registry.register_tool(tool)

    def run(self, input_text: str, **kwargs) -> str:
        """
        运行ReAct Agent

        Args:
            input_text: 用户问题
            **kwargs: 支持 conversation_id 参数

        Returns:
            最终答案
        """
        conversation_id = kwargs.pop("conversation_id", None)
        self.current_history = []
        current_step = 0

        print(f"\n🤖 {self.name} 开始处理问题: {input_text}")

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")

            tools_desc = self.tool_registry.get_tools_description()
            history_str = "\n".join(self.current_history)
            prompt = self.prompt_template.format(
                tools=tools_desc, question=input_text, history=history_str
            )

            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm.invoke(messages, **kwargs)

            if not response_text:
                print("❌ 错误：LLM未能返回有效响应。")
                break

            thought, action = self._parse_output(response_text)

            if thought:
                print(f"🤔 思考: {thought}")

            if not action:
                print("⚠️ 警告：未能解析出有效的Action，流程终止。")
                break

            if action.startswith("Finish"):
                final_answer = self._parse_action_input(action)
                print(f"🎉 最终答案: {final_answer}")

                self._save_conversation_messages(
                    input_text, final_answer, conversation_id
                )

                return final_answer

            tool_name, tool_input = self._parse_action(action)
            if not tool_name or tool_input is None:
                self.current_history.append("Observation: 无效的Action格式，请检查。")
                continue

            print(f"🎬 行动: {tool_name}[{tool_input}]")

            observation = self.tool_registry.execute_tool(tool_name, tool_input)
            print(f"👀 观察: {observation}")

            self.current_history.append(f"Action: {action}")
            self.current_history.append(f"Observation: {observation}")

        print("⏰ 已达到最大步数，流程终止。")
        final_answer = "抱歉，我无法在限定步数内完成这个任务。"

        self._save_conversation_messages(input_text, final_answer, conversation_id)

        return final_answer

    def stream_run(self, input_text: str, **kwargs) -> Iterator[StreamEvent]:
        """
        流式运行ReAct Agent，输出Thought/Action/Observation事件

        Args:
            input_text: 用户问题
            **kwargs: 支持 conversation_id 参数

        Yields:
            StreamEvent: 流式事件
        """
        conversation_id = kwargs.pop("conversation_id", None)
        yield StreamEvent.status(f"开始处理问题: {input_text}")

        self.current_history = []
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            yield StreamEvent.status(f"第 {current_step}/{self.max_steps} 步")

            tools_desc = self.tool_registry.get_tools_description()
            history_str = "\n".join(self.current_history)
            prompt = self.prompt_template.format(
                tools=tools_desc, question=input_text, history=history_str
            )

            messages = [{"role": "user", "content": prompt}]

            full_response = ""
            for chunk in self.llm.stream_invoke(messages, **kwargs):
                if chunk:
                    full_response += chunk
                    yield StreamEvent.text(chunk)

            if not full_response:
                yield StreamEvent.error("LLM未能返回有效响应")
                break

            thought, action = self._parse_output(full_response)

            if thought:
                yield StreamEvent.thought(thought)

            if not action:
                yield StreamEvent.status("未能解析出有效的Action，流程终止")
                break

            if action.startswith("Finish"):
                final_answer = self._parse_action_input(action)
                yield StreamEvent.action("Finish", action=action)
                yield StreamEvent.text(final_answer)

                self._save_conversation_messages(
                    input_text, final_answer, conversation_id
                )
                yield StreamEvent.done(final_answer)
                return

            tool_name, tool_input = self._parse_action(action)
            if not tool_name or tool_input is None:
                self.current_history.append("Observation: 无效的Action格式")
                continue

            yield StreamEvent.action(action, tool_name=tool_name, tool_input=tool_input)

            observation = self.tool_registry.execute_tool(tool_name, tool_input)
            yield StreamEvent.observation(str(observation))

            self.current_history.append(f"Action: {action}")
            self.current_history.append(f"Observation: {observation}")

        yield StreamEvent.status("已达到最大步数，流程终止")
        final_answer = "抱歉，我无法在限定步数内完成这个任务。"

        self._save_conversation_messages(input_text, final_answer, conversation_id)
        yield StreamEvent.done(final_answer)

    def _parse_output(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """解析LLM输出，提取思考和行动"""
        thought_match = re.search(r"Thought: (.*)", text)
        action_match = re.search(r"Action: (.*)", text)

        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None

        return thought, action

    def _parse_action(self, action_text: str) -> Tuple[Optional[str], Optional[str]]:
        """解析行动文本，提取工具名称和输入"""
        match = re.match(r"(\w+)\[(.*)\]", action_text)
        if match:
            return match.group(1), match.group(2)
        return None, None

    def _parse_action_input(self, action_text: str) -> str:
        """解析行动输入"""
        match = re.match(r"\w+\[(.*)\]", action_text)
        return match.group(1) if match else ""
