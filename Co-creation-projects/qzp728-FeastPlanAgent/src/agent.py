"""HelloAgents-orchestrated banquet planning workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import BanquetRequest
from .research import BanquetResearchTeam
from .report import render_markdown, write_report
from .tools import HelloAgentsToolRuntime


class BanquetPlannerAgent:
    """A transparent workflow using tools registered in HelloAgents ToolRegistry."""

    def __init__(self) -> None:
        self.runtime = HelloAgentsToolRuntime()

    def plan(self, request_data: dict[str, Any], output_path: Path) -> Path:
        request = BanquetRequest.from_dict(request_data)
        venue_result = self.runtime.invoke("venue_search", request)
        research_result, research_warnings = BanquetResearchTeam(self.runtime).research(
            request, venue_result.data
        )
        self._apply_verified_venue_claims(venue_result.data, research_result)
        menu_examples_result = self.runtime.invoke("published_menu_examples", request)
        seating_result = self.runtime.invoke("seating_plan", request)
        etiquette_result = self.runtime.invoke("regional_etiquette", request, {"research": research_result})
        menu_result = self.runtime.invoke("menu_budget", request, {"research": research_result})
        warnings = (
            venue_result.warnings
            + research_warnings
            + menu_examples_result.warnings
            + seating_result.warnings
            + etiquette_result.warnings
            + menu_result.warnings
        )
        markdown = render_markdown(
            request,
            venue_result.data,
            seating_result.data,
            etiquette_result.data,
            menu_result.data,
            menu_examples_result.data,
            research_result,
            warnings,
        )
        return write_report(markdown, output_path)

    @staticmethod
    def _apply_verified_venue_claims(venues: list[dict[str, Any]], research: dict[str, Any]) -> None:
        """Only reviewer-approved claims may enrich the original AMap candidates."""
        by_name = {str(venue.get("name")): venue for venue in venues}
        for claim in research.get("venue_claims", []):
            venue = by_name.get(str(claim.get("venue")))
            if not venue:
                continue
            if claim.get("package_price"):
                venue["price_from"] = claim["package_price"]
            if claim.get("phone"):
                venue["phone"] = claim["phone"]
            if claim.get("capacity"):
                venue["capacity"] = claim["capacity"]
            venue["web_evidence_url"] = claim.get("source_url", "")
            venue["web_evidence"] = claim.get("evidence", "")
