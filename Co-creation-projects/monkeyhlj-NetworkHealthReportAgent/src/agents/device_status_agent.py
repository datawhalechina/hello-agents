from __future__ import annotations

from statistics import mean
from typing import Dict, List

from src.agents.base import BaseNetworkAgent


class DeviceStatusAgent(BaseNetworkAgent):
    def __init__(self) -> None:
        prompt = (
            "你是网络设备状态Agent。请调用network_data工具读取设备和状态，"
            "评估在线率、性能瓶颈和告警趋势。"
        )
        super().__init__(name="DeviceStatusAgent", system_prompt=prompt)

    def analyze(self, inventory: List[Dict], status_series: List[Dict]) -> Dict:
        if not status_series:
            return {
                "device_count": len(inventory),
                "online_rate": 0.0,
                "avg_packet_loss": 0.0,
                "avg_latency_ms": 0.0,
                "avg_cpu": 0.0,
                "avg_mem": 0.0,
                "status": "unknown",
                "summary": "无状态数据，无法评估设备健康。",
            }

        online_rates = [
            (x["wired_switch_online_rate"] + x["wireless_controller_online_rate"] + x["wireless_ap_online_rate"]) / 3
            for x in status_series
        ]
        avg_online_rate = mean(online_rates)
        avg_packet_loss = mean(x["packet_loss"] for x in status_series)
        avg_latency = mean(x["latency_ms"] for x in status_series)
        avg_cpu = mean(x["cpu_avg"] for x in status_series)
        avg_mem = mean(x["mem_avg"] for x in status_series)
        critical_alarms = sum(x["critical_alarm_count"] for x in status_series)

        status = "healthy"
        if avg_online_rate < 0.985 or avg_packet_loss > 0.01 or avg_latency > 20:
            status = "degraded"
        if avg_online_rate < 0.975 or avg_packet_loss > 0.015 or critical_alarms >= 12:
            status = "critical"

        return {
            "device_count": len(inventory),
            "online_rate": round(avg_online_rate, 4),
            "avg_packet_loss": round(avg_packet_loss, 4),
            "avg_latency_ms": round(avg_latency, 2),
            "avg_cpu": round(avg_cpu, 2),
            "avg_mem": round(avg_mem, 2),
            "critical_alarm_total": critical_alarms,
            "status": status,
            "summary": (
                f"设备总数{len(inventory)}，平均在线率{avg_online_rate:.2%}，"
                f"平均时延{avg_latency:.1f}ms。"
            ),
        }
