"""
健康报告生成 Agent
"""

import json
from typing import Dict, Any, List
from agents.base import BaseAgent
from core.exceptions import AgentException

class ReportAgent(BaseAgent):
    def __init__(self, task_id=None, llm=None):
        super().__init__(name="ReportAgent",  task_id=task_id, llm=llm)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self.set_state("running")

        indicators = input_data.get("indicators", [])
        risk_assessment = input_data.get("risk_assessment", {})
        advice = input_data.get("advice") or {}
        confidence = risk_assessment.get("confidence", 0.5)
        retrieved_memory = str(input_data.get("retrieved_memory") or "（暂无召回记忆）")

        advice_list = advice.get("advice", [])

        prompt = self._build_prompt(
            indicators, risk_assessment, advice_list, confidence, retrieved_memory
        )
        response = await self.think(prompt)

        try:
            result = json.loads(response)
            summary = result.get("summary", "根据当前分析生成的健康报告摘要。")
        except json.JSONDecodeError:
            result = {
                "summary": "解析失败，返回原始结果",
                "raw_response": response
            }

        # 构建最终报告
        report = {
            "title": "个人健康评估报告",
            "summary": summary,
            "indicator_section": indicators,
            "risk_section": risk_assessment,
            "advice_section": advice_list,
            "confidence": confidence,
            "disclaimer": "本报告仅供健康管理参考，不构成医疗诊断。"
        }

        self.set_state("completed")

        return {
            "report": {
                **report,
                "report_text": summary
            }
        }
    
    def _build_prompt(
    self,
    indicators: List[Dict[str, Any]],
    risk_assessment: Dict[str, Any],
    advice_list: List[Dict[str, Any]],
    confidence: float,
    retrieved_memory: str,
) -> str:

        return f"""
你是一名健康报告整理助手。
请根据以下结构化分析结果，生成一份清晰、专业、易读的健康评估报告。

健康指标分析结果：
{json.dumps(indicators, ensure_ascii=False, indent=2)}

健康风险评估结果：
{json.dumps(risk_assessment, ensure_ascii=False, indent=2)}

健康建议：
{json.dumps(advice_list, ensure_ascii=False, indent=2)}

整体置信度：
{confidence}

历史记忆召回（RAG）：
{retrieved_memory}

要求：
- 不新增分析结论
- 不修改已有判断
- 语言清晰、结构清楚
- 面向普通用户

请返回 JSON 格式：
{{
  "summary": "..."
}}
"""

    def get_required_fields(self) -> list[str]:
        return []