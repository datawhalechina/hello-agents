from __future__ import annotations

from datetime import date
from typing import Dict, Iterator, List

from src.agents.device_status_agent import DeviceStatusAgent
from src.agents.log_analysis_agent import LogAnalysisAgent
from src.agents.network_health_report_agent import NetworkHealthReportAgent
from src.agents.site_qa_agent import SiteQAAgent
from src.agents.user_status_agent import UserStatusAgent
from src.tools.data_repository import DataRepository


class NetworkHealthOrchestrator:
    def __init__(self) -> None:
        self.repo = DataRepository()
        self.log_agent = LogAnalysisAgent()
        self.device_agent = DeviceStatusAgent()
        self.user_agent = UserStatusAgent()
        self.report_agent = NetworkHealthReportAgent()
        self.qa_agent = SiteQAAgent()

    def list_sites(self) -> List[Dict]:
        return self.repo.list_sites()

    def get_site(self, site_id: str) -> Dict:
        site = self.repo.get_site(site_id)
        if not site:
            raise ValueError(f"site_id not found: {site_id}")
        return site

    def build_report(self, site_id: str, start: date, end: date) -> Dict:
        site = self.get_site(site_id)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        logs = self.repo.list_logs(site_id=site_id)
        inventory = self.repo.list_device_inventory(site_id=site_id)
        status_series = self.repo.list_device_status(site_id=site_id, start_date=start_str, end_date=end_str)
        compliance = self.repo.latest_terminal_compliance(site_id=site_id)

        log_result = self.log_agent.analyze(logs)
        device_result = self.device_agent.analyze(inventory=inventory, status_series=status_series)
        user_result = self.user_agent.analyze(terminal_row=compliance)

        return self.report_agent.synthesize(
            site=site,
            log_result=log_result,
            device_result=device_result,
            user_result=user_result,
            start_date=start_str,
            end_date=end_str,
        )

    def ask_site_question(self, site_id: str, question: str, start: date, end: date) -> Dict:
        site = self.get_site(site_id)
        report = self.build_report(site_id=site_id, start=start, end=end)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        payload = self.qa_agent.answer_global_payload(
            question=question,
            sites=[site],
            site_reports=[report],
            start_date=start_str,
            end_date=end_str,
            selected_site_id=site_id,
        )
        return {
            "site": site,
            "window": {"start_date": start_str, "end_date": end_str},
            "question": question,
            "answer": payload["answer"],
            "artifact": payload.get("artifact"),
            "debug": payload.get("debug"),
        }

    def ask_global_question(self, question: str, start: date, end: date, site_id: str | None = None) -> Dict:
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        sites = self.list_sites()
        reports = [self.build_report(site_id=s["site_id"], start=start, end=end) for s in sites]

        payload = self.qa_agent.answer_global_payload(
            question=question,
            sites=sites,
            site_reports=reports,
            start_date=start_str,
            end_date=end_str,
            selected_site_id=site_id,
        )
        return {
            "window": {"start_date": start_str, "end_date": end_str},
            "question": question,
            "answer": payload["answer"],
            "artifact": payload.get("artifact"),
            "debug": {
                **payload.get("debug", self.qa_agent.debug_meta()),
                "site_count": len(sites),
                "report_count": len(reports),
            },
        }

    def stream_global_question(self, question: str, start: date, end: date, site_id: str | None = None) -> Iterator[str]:
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        sites = self.list_sites()
        reports = [self.build_report(site_id=s["site_id"], start=start, end=end) for s in sites]

        yield from self.qa_agent.stream_answer_global(
            question=question,
            sites=sites,
            site_reports=reports,
            start_date=start_str,
            end_date=end_str,
            selected_site_id=site_id,
        )

    def runtime_status(self) -> Dict:
        return {
            "log_agent": {
                "llm_enabled": self.log_agent.llm_enabled,
                "mcp_enabled": self.log_agent.mcp_enabled,
            },
            "device_agent": {
                "llm_enabled": self.device_agent.llm_enabled,
                "mcp_enabled": self.device_agent.mcp_enabled,
            },
            "user_agent": {
                "llm_enabled": self.user_agent.llm_enabled,
                "mcp_enabled": self.user_agent.mcp_enabled,
            },
            "report_agent": {
                "llm_enabled": self.report_agent.llm_enabled,
                "mcp_enabled": self.report_agent.mcp_enabled,
            },
            "qa_agent": {
                "llm_enabled": self.qa_agent.llm_enabled,
                "mcp_enabled": self.qa_agent.mcp_enabled,
            },
        }
