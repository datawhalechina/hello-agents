"""
健康指标分析 Agent
"""

import json
from typing import Dict, Any, List
from agents.base import BaseAgent

class HealthIndicatorAgent(BaseAgent):
    def __init__(self, task_id=None, llm=None):
        super().__init__(name="HealthIndicatorAgent",  task_id=task_id, llm=llm)
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        await self.validate_input(input_data)
        self.set_state("running")

        report_text = input_data["report_text"]

        prompt = f"""
你是一名专业的健康分析助手。
请从以下体检或健康报告中提取关键健康指标，并判断风险。

报告内容：
{report_text}

请返回 JSON，严格遵循以下格式：
{{
  "indicator_results": {{
    "<指标名>": {{
      "value": "<原始数值或描述>",
      "status": "<normal | borderline | high | low | abnormal>",
      "risk_level": "<low | medium | high>",
      "analysis": "<简要分析该指标的健康含义>"
    }}
  }}
}}

要求：
- 每个指标单独分析，不要给出综合结论
- 不要给出任何健康建议
- 如果报告中未提及明确数值，可用描述性判断
"""
        response = await self.think(prompt)
        indicators: List[Dict[str, Any]] = []

        try:
            result = json.loads(response)
            indicator_dict = result.get("indicator_results", {})
            for name, data in indicator_dict.items():
                indicators.append({
                    "name": name,
                    "value": data.get("value"),
                    "status": data.get("status"),
                    "risk_level": data.get("risk_level"),
                    "analysis": data.get("analysis")
                })
        except json.JSONDecodeError:
            # LLM 输出异常保护
            indicators = []

        self.set_state("completed")
        return {
            "indicators": indicators
        }
    
    def get_required_fields(self) -> List[str]:
        return ["report_text"]