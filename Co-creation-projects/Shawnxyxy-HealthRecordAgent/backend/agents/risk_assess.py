"""
健康风险评估 Agent
"""
import json
from typing import Dict, Any, List
from agents.base import BaseAgent
from core.exceptions import AgentException

class RiskAssessmentAgent(BaseAgent):
    def __init__(self, task_id=None, llm=None):
        super().__init__(name="RiskAssessment", task_id=task_id, llm=llm)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            indicator_results = input_data["indicator_results"]
            if not indicator_results:
                raise AgentException("缺少健康指标分析结果")
            self.set_state("running")

            result = await self._assess_risk(indicator_results)

            self.set_state("completed")
            return result
        except Exception as e:
            self.set_state("error")
            raise AgentException(f"RiskAssessmentAgent 执行失败: {str(e)}")

    async def _assess_risk(self, indicator_results: Dict[str, Any]) -> Dict[str, Any]:
        risk_prompt = f"""
你是一名专业的健康风险评估专家。

以下是某用户的健康指标分析结果（已由其他智能体完成分析）：
{indicator_results}

请你完成以下任务：
1. 综合判断用户的整体健康风险等级（low / medium / high）
2. 列出主要风险因素（不超过 5 条）
3. 推测可能存在的潜在健康风险或疾病方向
4. 给出你评估的置信度（0~1 之间的小数）

请以 JSON 格式返回，例如：
{{
  "overall_risk_level": "medium",
  "risk_factors": ["高胆固醇", "睡眠不足"],
  "potential_conditions": ["心血管疾病风险"],
  "confidence": 0.78
}}
"""
        response = await self.think(risk_prompt)

        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            result = {
                "summary": "解析失败，返回原始结果",
                "raw_response": response
            }

        self.set_state("completed")
        return result
    
    def get_required_fields(self) -> list[str]:
        return ["age", "weight", "height", "blood_pressure"]