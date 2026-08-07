"""
FastAPI server for the SRE On-Call Agent.

Run with: uvicorn src.api.main:app --reload --port 8000

Endpoints:
  GET  /health                       — liveness check
  GET  /incidents/fixtures           — list available sample incident IDs
  POST /incidents/investigate        — run the full 3-agent pipeline
  GET  /incidents/{id}/report        — retrieve a previously generated report
"""
import time
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agents.pipeline import run_pipeline, list_incidents, load_incident

app = FastAPI(
    title="SRE On-Call Agent",
    description="AI-powered incident triage and post-mortem generation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten this when adding a specific frontend origin
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for generated reports (replace with Redis/DB for production)
_report_store: Dict[str, Any] = {}


class InvestigateRequest(BaseModel):
    incident_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/incidents/fixtures")
def get_fixtures():
    """List all available sample incident IDs."""
    return {"incidents": list_incidents()}


@app.post("/incidents/investigate")
def investigate(req: InvestigateRequest):
    """
    Run the full triage → investigation → post-mortem pipeline for an incident.

    This runs synchronously (suitable for demo; upgrade to background task + SSE for prod).
    """
    try:
        load_incident(req.incident_id)  # Validate early
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    start = time.time()
    try:
        result = run_pipeline(req.incident_id, verbose=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    elapsed = round(time.time() - start, 1)
    result["elapsed_seconds"] = elapsed
    _report_store[req.incident_id] = result
    return result


@app.get("/incidents/{incident_id}/report")
def get_report(incident_id: str):
    """Retrieve a previously generated post-mortem report."""
    if incident_id not in _report_store:
        raise HTTPException(
            status_code=404,
            detail=f"No report found for '{incident_id}'. Call POST /incidents/investigate first.",
        )
    return {
        "incident_id": incident_id,
        "report": _report_store[incident_id]["report"],
    }
