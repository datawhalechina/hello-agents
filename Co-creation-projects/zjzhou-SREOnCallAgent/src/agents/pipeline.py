"""
SRE pipeline orchestrator — wires TriageAgent → InvestigationAgent → PostmortemAgent.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any

from src.core.llm_client import HelloAgentsLLM
from src.agents.triage_agent import TriageAgent
from src.agents.investigation_agent import InvestigationAgent
from src.agents.postmortem_agent import PostmortemAgent

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
INCIDENTS_DIR = DATA_DIR / "incidents"
RUNBOOKS_DIR = DATA_DIR / "runbooks"


def list_incidents():
    return [p.stem for p in INCIDENTS_DIR.glob("*.json")]


def load_incident(incident_id: str) -> Dict[str, Any]:
    path = INCIDENTS_DIR / f"{incident_id}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Incident '{incident_id}' not found. "
            f"Available: {list_incidents()}"
        )
    with open(path) as f:
        return json.load(f)


def run_pipeline(incident_id: str, verbose: bool = True) -> Dict[str, Any]:
    """
    Full three-stage SRE pipeline for a given incident ID.

    Returns a dict with: incident_id, plan, findings, report
    """
    incident = load_incident(incident_id)
    llm = HelloAgentsLLM(verbose=verbose)

    # Stage 1: Triage — Plan-and-Solve
    triage = TriageAgent(llm)
    plan = triage.run(incident)

    # Stage 2: Investigation — ReAct
    investigator = InvestigationAgent(llm, incident, str(RUNBOOKS_DIR))
    findings = investigator.run(plan)

    # Stage 3: Post-mortem — Reflection
    postmortem = PostmortemAgent(llm)
    report = postmortem.run(incident, findings)

    return {
        "incident_id": incident_id,
        "service": incident["service"],
        "severity": incident["severity"],
        "plan": plan,
        "findings": findings,
        "report": report,
    }
