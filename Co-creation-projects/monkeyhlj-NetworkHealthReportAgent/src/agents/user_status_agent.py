from __future__ import annotations

from typing import Dict, Optional

from src.agents.base import BaseNetworkAgent


class UserStatusAgent(BaseNetworkAgent):
    def __init__(self) -> None:
        prompt = (
            "你是网络用户状态分析Agent。请调用network_data工具读取终端接入与合规数据，"
            "输出终端风险和访问健康度。"
        )
        super().__init__(name="UserStatusAgent", system_prompt=prompt)

    def analyze(self, terminal_row: Optional[Dict]) -> Dict:
        if not terminal_row:
            return {
                "wired_clients": 0,
                "wireless_clients": 0,
                "unknown_clients": 0,
                "compliant_rate": 0.0,
                "high_risk_terminals": 0,
                "status": "unknown",
                "summary": "无终端合规数据。",
            }

        compliant_rate = terminal_row["compliant_rate"]
        unknown_clients = terminal_row["unknown_clients"]
        high_risk = terminal_row["high_risk_terminals"]

        status = "healthy"
        if compliant_rate < 0.96 or unknown_clients > 20:
            status = "degraded"
        if compliant_rate < 0.94 or high_risk > 25:
            status = "critical"

        return {
            "wired_clients": terminal_row["wired_clients"],
            "wireless_clients": terminal_row["wireless_clients"],
            "unknown_clients": unknown_clients,
            "compliant_rate": compliant_rate,
            "high_risk_terminals": high_risk,
            "guest_network_ratio": terminal_row["guest_network_ratio"],
            "status": status,
            "summary": (
                f"终端合规率{compliant_rate:.2%}，高风险终端{high_risk}台，"
                f"未知终端{unknown_clients}台。"
            ),
        }
