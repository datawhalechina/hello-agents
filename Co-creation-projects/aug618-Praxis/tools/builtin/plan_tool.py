from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional

from core.llm import HelloAgentsLLM
from tools.base import Tool, ToolParameter


class PlanTool(Tool):
    """规划工具（可选）

    用于在用户强制要求或任务明显需要多步执行时生成计划。
    建议在 ReAct 中按需调用：plan[{"goal":"..."}] 或 plan[目标文本]
    """

    def __init__(self, llm: HelloAgentsLLM, prompt_path: Optional[str] = None):
        super().__init__(name="plan", description="生成可执行计划（仅在需要时调用）")
        self.llm = llm
        self.prompt_path = Path(prompt_path).resolve() if prompt_path else None

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="goal",
                type="string",
                description="计划目标（例如：分析项目结构并说明模块职责）",
                required=True,
            ),
            ToolParameter(
                name="constraints",
                type="string",
                description="额外约束（可选）",
                required=False,
            ),
            ToolParameter(
                name="output",
                type="string",
                description="输出格式：markdown|json（默认 markdown）",
                required=False,
                default="markdown",
            ),
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        if not self.validate_parameters(parameters):
            return "❌ 参数验证失败：缺少 goal"

        goal = str(parameters.get("goal", "")).strip()
        constraints = parameters.get("constraints")
        output = str(parameters.get("output", "markdown")).strip() or "markdown"

        if not goal:
            return "❌ goal 不能为空"

        prompt = ""
        if self.prompt_path and self.prompt_path.exists():
            prompt = self.prompt_path.read_text(encoding="utf-8")
        else:
            prompt = (
                "你是一个规划助手。请输出一个可执行计划（5~12步），并包含 Risks 与 Validation。"
            )

        user_msg = f"目标：{goal}\n期望输出：{output}"
        if constraints:
            user_msg += f"\n约束：{constraints}"

        resp = self.llm.invoke(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=800,
        )
        return resp or ""

