"""低层策略：工具调用执行器 (Low-Level Policy: Tool Executor)

接收高层的子目标，生成具体的工具调用序列来执行该子目标。
使用 SFT + GRPO 训练优化工具调用能力。
"""

import re
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass


@dataclass
class ToolCallConfig:
    """工具调用配置"""

    max_tool_calls_per_subgoal: int = 5
    max_retries: int = 2
    temperature: float = 0.7
    tool_call_delimiter: str = "\n---\n"


@dataclass
class ToolCall:
    """单个工具调用"""

    tool_name: str
    arguments: Dict[str, Any]
    thought: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool_name,
            "arguments": self.arguments,
            "thought": self.thought,
        }

    def to_string(self) -> str:
        """转为文本表示"""
        args_str = ", ".join(f"{k}={v}" for k, v in self.arguments.items())
        thought_part = f"Thought: {self.thought}\n" if self.thought else ""
        return f"{thought_part}Action: {self.tool_name}[{args_str}]"

    @classmethod
    def from_string(cls, text: str) -> Optional["ToolCall"]:
        """从文本解析工具调用"""
        match = re.search(r"Action:\s*(\w+)\[(.*)\]", text)
        if not match:
            return None
        tool_name = match.group(1)
        args_str = match.group(2)
        arguments = {}
        for pair in args_str.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                arguments[k.strip()] = v.strip().strip("'\"")

        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else ""

        return cls(tool_name=tool_name, arguments=arguments, thought=thought)


TOOL_CALL_PROMPT_TEMPLATE = """You are a tool-use agent. Execute the given subgoal by calling tools.

## Available Tools
{tool_descriptions}

## Subgoal
{subgoal_description}

## Expected Output
{expected_output}

## Execution History
{history}

## Instructions
1. Think about what tool to call and why
2. Call ONE tool at a time using format: Action: tool_name[arg1=val1, arg2=val2]
3. Wait for the observation before calling the next tool
4. When the subgoal is complete, output: Finish[result]

## Output Format
Thought: your reasoning
Action: tool_name[key1=value1, key2=value2]
"""


class LowLevelPolicy:
    """低层策略：负责具体工具调用

    输入：子目标 (Subgoal) + 环境状态
    输出：工具调用序列 [ToolCall, ToolCall, ...]

    训练方式：
    - 阶段1：SFT 基于专家轨迹学习基本工具调用
    - 阶段2：GRPO 优化工具调用策略（选择时机、参数构建）
    """

    def __init__(
        self,
        model=None,
        tokenizer=None,
        config: Optional[ToolCallConfig] = None,
        tool_executor: Optional[Callable] = None,
        llm_client=None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config or ToolCallConfig()
        self.tool_executor = tool_executor
        self.llm_client = llm_client

    def execute(
        self,
        subgoal_description: str,
        expected_output: str = "",
        tool_descriptions: str = "",
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """执行子目标：生成并执行工具调用序列

        Args:
            subgoal_description: 子目标描述
            expected_output: 期望输出
            tool_descriptions: 可用工具描述

        Returns:
            执行轨迹列表 [{"tool_call": ToolCall, "observation": str}, ...]
        """
        history = ""
        trajectory = []
        max_calls = self.config.max_tool_calls_per_subgoal

        for step in range(max_calls):
            prompt = TOOL_CALL_PROMPT_TEMPLATE.format(
                tool_descriptions=tool_descriptions,
                subgoal_description=subgoal_description,
                expected_output=expected_output,
                history=history or "No steps executed yet.",
            )

            # 生成下一步
            response = self._generate(prompt, **kwargs)

            # 解析工具调用
            tool_call = self._parse_tool_call(response)
            if tool_call is None:
                # 检查是否完成
                if "Finish[" in response:
                    result = self._extract_finish_result(response)
                    trajectory.append({"type": "finish", "result": result})
                    break
                continue

            # 执行工具
            observation = self._execute_tool(tool_call)
            trajectory.append(
                {
                    "type": "tool_call",
                    "tool_call": tool_call,
                    "observation": observation,
                    "response": response,
                }
            )

            # 更新历史
            history += (
                f"\nAction: {tool_call.to_string()}\nObservation: {observation}\n"
            )

        return trajectory

    def _generate(self, prompt: str, **kwargs) -> str:
        """生成下一步行动"""
        if self.llm_client:
            messages = [{"role": "user", "content": prompt}]
            return self.llm_client.invoke(messages, **kwargs) or ""
        if self.model and self.tokenizer:
            inputs = self.tokenizer(prompt, return_tensors="pt")
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=kwargs.get("temperature", self.config.temperature),
                do_sample=True,
            )
            return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return ""

    def _parse_tool_call(self, text: str) -> Optional[ToolCall]:
        """从文本解析工具调用"""
        return ToolCall.from_string(text)

    def _extract_finish_result(self, text: str) -> str:
        """提取 Finish 结果"""
        match = re.search(r"Finish\[(.*)\]", text, re.DOTALL)
        return match.group(1).strip() if match else ""

    def _execute_tool(self, tool_call: ToolCall) -> str:
        """执行工具调用"""
        if self.tool_executor:
            try:
                return self.tool_executor(tool_call.tool_name, tool_call.arguments)
            except Exception as e:
                return f"Error: {e}"
        return f"Executed {tool_call.tool_name} with {tool_call.arguments}"

    def format_prompt(
        self,
        subgoal: Any,
        tool_descriptions: str = "",
        history: str = "",
    ) -> str:
        """格式化训练用的 prompt"""
        return TOOL_CALL_PROMPT_TEMPLATE.format(
            tool_descriptions=tool_descriptions,
            subgoal_description=getattr(subgoal, "description", str(subgoal)),
            expected_output=getattr(subgoal, "expected_output", ""),
            history=history or "No steps executed yet.",
        )
