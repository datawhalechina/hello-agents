from __future__ import annotations

import json
import os
from typing import Dict, List

from src.agents.base import BaseNetworkAgent


class NetworkHealthReportAgent(BaseNetworkAgent):
    def __init__(self) -> None:
        prompt = (
            "你是网络健康报告Agent。请综合日志分析、设备状态、终端状态，"
            "给出健康分、风险等级和可执行建议。"
        )
        super().__init__(name="NetworkHealthReportAgent", system_prompt=prompt)

    def synthesize(
        self,
        site: Dict,
        log_result: Dict,
        device_result: Dict,
        user_result: Dict,
        start_date: str,
        end_date: str,
    ) -> Dict:
        score = 100.0

        score -= min(20.0, log_result.get("critical_events", 0) * 3.0)
        score -= min(10.0, log_result.get("warning_events", 0) * 1.0)
        score -= max(0.0, (1.0 - device_result.get("online_rate", 1.0)) * 200)
        score -= max(0.0, device_result.get("avg_packet_loss", 0.0) * 800)
        score -= max(0.0, (1.0 - user_result.get("compliant_rate", 1.0)) * 150)
        score -= min(10.0, user_result.get("high_risk_terminals", 0) * 0.3)

        score = max(0.0, min(100.0, round(score, 1)))

        if score >= 85:
            level = "healthy"
        elif score >= 70:
            level = "warning"
        else:
            level = "critical"

        recommendations: List[str] = []
        if log_result.get("critical_events", 0) > 0:
            recommendations.append("优先排查critical日志对应链路与设备，执行根因定位和变更回滚检查。")
        if device_result.get("avg_latency_ms", 0) > 18:
            recommendations.append("针对高时延站点执行链路压测和QoS策略复核，优化关键业务队列。")
        if device_result.get("avg_packet_loss", 0) > 0.01:
            recommendations.append("对丢包异常端口进行误码与光模块巡检，必要时更换线缆或模块。")
        if user_result.get("compliant_rate", 1.0) < 0.96:
            recommendations.append("提升终端准入合规率，收敛未知终端与高风险终端访问权限。")
        if not recommendations:
            recommendations.append("维持现网策略并持续观察峰值时段容量，建议周度复盘。")

        llm_insight = None
        llm_insight_enabled = os.getenv("ENABLE_REPORT_LLM_INSIGHT", "false").lower() in {"1", "true", "yes"}
        if llm_insight_enabled:
            llm_prompt = (
                "请作为网络健康报告专家，总结该站点网络健康情况。"
                "输出三段：总体判断、主要风险、本周优先动作。"
                "\n\n输入JSON:\n"
                + json.dumps(
                    {
                        "site": site,
                        "window": {"start_date": start_date, "end_date": end_date},
                        "score": score,
                        "level": level,
                        "log_analysis": log_result,
                        "device_status": device_result,
                        "user_status": user_result,
                        "recommendations": recommendations,
                    },
                    ensure_ascii=False,
                )
            )
            llm_result = self.run_llm(llm_prompt)
            if llm_result:
                llm_insight = llm_result

        return {
            "site": site,
            "window": {"start_date": start_date, "end_date": end_date},
            "health_score": score,
            "health_level": level,
            "summary": f"{site['site_name']}在统计周期内网络健康评分为{score}，等级为{level}。",
            "llm_insight": llm_insight,
            "debug": {
                "llm_enabled": self.llm_enabled,
                "mcp_enabled": self.mcp_enabled,
                "tools": self.list_tool_names(),
                "llm_insight_enabled": llm_insight_enabled,
                "llm_insight_used": llm_insight is not None,
            },
            "sections": {
                "log_analysis": log_result,
                "device_status": device_result,
                "user_status": user_result,
            },
            "recommendations": recommendations,
        }
