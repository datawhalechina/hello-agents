"""
HealthRecord 健康档案规划师 (planner Agent)
负责对健康档案、体检报告进行分析任务的拆解和规划
"""

import os
import json
from datetime import datetime
from core.exceptions import AgentException
from typing import Dict, Any, List
from agents.base import BaseAgent

class PlannerAgent(BaseAgent):
    """任务规划智能体"""
    def __init__(self, task_id=None, llm=None):
        super().__init__(name="Planner", task_id=task_id, llm=llm)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Planner 的唯一入口
        """
        await self.validate_input(input_data)
        self.set_state("running")

        try:
            goal = input_data["goal"]
            context = input_data.get("context", {})

            prompt = self._build_planner_prompt(goal, context)

            response = await self.think(prompt)

            plan = self._parse_plan(response)

            self.set_state("completed")
            self._add_to_history(f"生成计划，包含 {len(plan)} 个步骤")

            result = {
                "status": "success",
                "goal": goal,
                "plan": plan,
                "created_at": datetime.now().isoformat()
            }

            self.set_state("completed")

            return result

        except Exception as e:
            self.set_state("error")
            raise AgentException(f"PlannerAgent 执行失败: {str(e)}")
    
    def get_required_fields(self) -> List[str]:
        """
        Planner 只关心 goal
        """
        return ["goal"]

    # ======================
    # 内部方法
    # ======================
    def _build_planner_prompt(self, goal: str, context: Dict[str, Any]) -> str:
        """
        构造 Planner Prompt (Plan-And-Solve)
        """
        return f"""
你是一个 Planner Agent，擅长将复杂目标拆解为可执行的子任务。

【总目标】
{goal}

【上下文信息】
{json.dumps(context, ensure_ascii=False, indent=2)}

请遵循以下原则：
1.将目标拆解为 3 到 6 个清晰、可执行的步骤
2.每个步骤只做一件事
3.明确该步骤最适合由哪类智能体完成
4.步骤之间应具有逻辑顺序
5.不要执行任务，只做规划

【可用智能体类型示例】
- HealthAnalyzer：健康数据解析
- RiskEvaluator：风险评估
- KnowledgeRetriever：医学知识查询
- ReportWriter：总结与建议生成

【输出格式】
请严格以 JSON 格式输出，不要包含多余解释：

{{
  "plan": [
    {{
      "step": 1,
      "agent": "AgentName",
      "task": "任务描述",
      "input": "该步骤需要的输入"
    }}
  ]
}}
"""
    def _parse_plan(self, response: str) -> List[Dict[str, Any]]:
        """
        解析 LLM 输出的 Plan
        """
        try:
            data = json.loads(response)
            plan = data.get("plan", [])
            if not plan:
                raise ValueError("Plan 为空")
            return plan
        except Exception:
            return [
                {
                    "step": 1,
                    "agent": "FallbackAgent",
                    "task": "解析失败，需人工或二次规划",
                    "input": response
                }
            ]