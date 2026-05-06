"""高层策略：子目标规划器 (High-Level Policy: Subgoal Planner)

将任务分解为有序的子目标序列，每个子目标对应一个可执行的技能块。
使用 GRPO 训练优化子目标分解策略。
"""

import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class SubgoalType(Enum):
    """子目标类型"""

    SEARCH = "search"  # 搜索信息
    CALCULATE = "calculate"  # 计算
    CODE = "code"  # 代码执行
    READ_FILE = "read_file"  # 读取文件
    WRITE_FILE = "write_file"  # 写入文件
    VERIFY = "verify"  # 验证结果
    REASON = "reason"  # 纯推理（无需工具）


@dataclass
class SubgoalConfig:
    """子目标配置"""

    max_subgoals: int = 8
    subgoal_format: str = "json"  # "json" or "markdown"


@dataclass
class Subgoal:
    """单个子目标定义"""

    type: SubgoalType
    description: str
    expected_output: str = ""
    depends_on: List[int] = field(default_factory=list)  # 依赖的子目标索引
    tool_name: Optional[str] = None  # 建议使用的工具

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "description": self.description,
            "expected_output": self.expected_output,
            "depends_on": self.depends_on,
            "tool": self.tool_name,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Subgoal":
        return cls(
            type=SubgoalType(d.get("type", "reason")),
            description=d.get("description", ""),
            expected_output=d.get("expected_output", ""),
            depends_on=d.get("depends_on", []),
            tool_name=d.get("tool"),
        )


SUBPROMPT_TEMPLATE = """You are a high-level task planner. Given a task and a set of tools, decompose the task into a sequence of subgoals.

## Available Tools
{tool_descriptions}

## Task
{task}

## Instructions
1. Analyze the task and break it down into 2-8 subgoals
2. Each subgoal should be executable by one or more tool calls
3. Specify dependencies between subgoals (which subgoals must be completed first)
4. Assign the appropriate tool for each subgoal
5. Output as a JSON array, no other text

## Output Format
```json
[
  {{
    "type": "search|calculate|code|read_file|write_file|verify|reason",
    "description": "what to do in this subgoal",
    "expected_output": "what this subgoal should produce",
    "depends_on": [],
    "tool": "suggested_tool_name"
  }}
]
```"""


class HighLevelPolicy:
    """高层策略：负责任务规划与子目标分解

    输入：任务描述 + 可用工具列表
    输出：子目标序列 [Subgoal, Subgoal, ...]

    训练方式：GRPO
    - 奖励基于子目标序列的完成度（低层执行后反馈）
    - 鼓励合理的子目标粒度（不多不少）
    - 惩罚缺失关键子目标或冗余子目标
    """

    def __init__(
        self,
        model=None,
        tokenizer=None,
        config: Optional[SubgoalConfig] = None,
        llm_client=None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config or SubgoalConfig()
        self.llm_client = llm_client

    def generate(
        self,
        task: str,
        tool_descriptions: str = "",
        **kwargs,
    ) -> List[Subgoal]:
        """生成子目标序列

        Args:
            task: 任务描述
            tool_descriptions: 可用工具描述
            **kwargs: 额外参数

        Returns:
            子目标列表
        """
        if self.llm_client:
            return self._generate_with_llm(task, tool_descriptions, **kwargs)
        return self._generate_with_model(task, tool_descriptions, **kwargs)

    def _generate_with_llm(
        self,
        task: str,
        tool_descriptions: str,
        **kwargs,
    ) -> List[Subgoal]:
        """使用 LLM 客户端生成（推理阶段）"""
        prompt = SUBPROMPT_TEMPLATE.format(
            tool_descriptions=tool_descriptions or "No tools available",
            task=task,
        )
        messages = [{"role": "user", "content": prompt}]
        response = self.llm_client.invoke(messages, **kwargs) or "[]"
        return self._parse_subgoals(response)

    def _generate_with_model(
        self,
        task: str,
        tool_descriptions: str,
        **kwargs,
    ) -> List[Subgoal]:
        """使用本地模型生成（训练阶段）"""
        if self.model is None or self.tokenizer is None:
            return self._fallback_plan(task)

        prompt = SUBPROMPT_TEMPLATE.format(
            tool_descriptions=tool_descriptions or "No tools available",
            task=task,
        )
        inputs = self.tokenizer(prompt, return_tensors="pt")
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=kwargs.get("temperature", 0.7),
            do_sample=kwargs.get("do_sample", True),
        )
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return self._parse_subgoals(response)

    def _parse_subgoals(self, text: str) -> List[Subgoal]:
        """从模型输出解析子目标列表"""
        try:
            json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                data = json.loads(text)
            if isinstance(data, list):
                return [Subgoal.from_dict(item) for item in data]
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
        return self._fallback_plan(text[:100])

    def _fallback_plan(self, task_hint: str) -> List[Subgoal]:
        """兜底规划：当模型无法生成时提供简单计划"""
        return [
            Subgoal(
                type=SubgoalType.REASON,
                description=f"Analyze and solve: {task_hint[:100]}",
                expected_output="Final answer",
                depends_on=[],
            )
        ]

    def format_prompt(
        self,
        task: str,
        tool_descriptions: str = "",
    ) -> str:
        """格式化训练用的 prompt"""
        return SUBPROMPT_TEMPLATE.format(
            tool_descriptions=tool_descriptions,
            task=task,
        )

    def encode_subgoals(self, subgoals: List[Subgoal]) -> str:
        """将子目标编码为字符串（用于训练输出）"""
        return json.dumps([sg.to_dict() for sg in subgoals], ensure_ascii=False)

    def decode_response(self, response: str) -> List[Subgoal]:
        """将模型响应解码为子目标列表"""
        return self._parse_subgoals(response)
