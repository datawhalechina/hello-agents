"""
健康建议 Agent
"""

import json
from typing import Dict, Any, List
from agents.base import BaseAgent
from core.exceptions import AgentException

class AdviceAgent(BaseAgent):
    def __init__(self, task_id=None, llm=None):
        super().__init__(name="AdviceAgent",  task_id=task_id, llm=llm)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self.set_state("running")

        overall_risk_level = input_data.get("overall_risk_level")
        risk_factors = input_data.get("risk_factors", [])
        potential_conditions = input_data.get("potential_conditions", [])
        confidence = input_data.get("confidence", 0.0)
        if isinstance(input_data.get("risk_assessment"), dict):
            ra = input_data["risk_assessment"]
            overall_risk_level = ra.get("overall_risk_level", overall_risk_level)
            risk_factors = ra.get("risk_factors", risk_factors)
            potential_conditions = ra.get("potential_conditions", potential_conditions)
            confidence = ra.get("confidence", confidence)
        retrieved_memory = str(input_data.get("retrieved_memory") or "（暂无召回记忆）")

        prompt = self._build_prompt(
            overall_risk_level,
            risk_factors,
            potential_conditions,
            confidence,
            retrieved_memory,
        )

        response = await self.think(prompt)

        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            result = {
                "summary": "解析失败，返回原始结果",
                "raw_response": response
            }

        self.set_state("completed")
        return result

    def _build_prompt(
        self,
        overall_risk_level: str,
        risk_factors: List[str],
        potential_conditions: List[str],
        confidence: float,
        retrieved_memory: str,
    ) -> str:
        return f"""
你是一名专业的健康管理助手。
请基于以下健康风险评估结果，为用户生成合理、可执行的健康建议。

健康风险评估结果：
- 总体风险等级：{overall_risk_level}
- 风险因素：{risk_factors}
- 潜在健康问题：{potential_conditions}
- 评估置信度：{confidence}

历史记忆召回（RAG）：
{retrieved_memory}

请遵循以下原则：
- 不进行医学诊断
- 建议应偏向生活方式、预防、监测和就医提示
- 建议应具体、可执行
- 根据风险等级调整建议的优先级

请以 JSON 格式返回，例如：
{{
  "advice": [
    {{
      "target": "<对应的风险因素>",
      "category": "生活方式 | 饮食 | 运动 | 就医建议 | 监测",
      "suggestion": "<具体可执行建议>",
      "priority": "high | medium | low"
    }}
  ],
  "overall_tone": "<整体建议风格，如：保守 / 积极干预>"
}}
"""

    def get_required_fields(self) -> list[str]:
        return [
            "risk_level",
            "risk_factors"
        ]
        