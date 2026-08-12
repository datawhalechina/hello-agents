from __future__ import annotations

from pathlib import Path
from typing import Iterator

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from src.agents.orchestrator import NetworkHealthOrchestrator
from src.utils.date_utils import default_date_window

app = FastAPI(title="Network Health Report Agent API", version="0.1.0")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Agent-LLM",
        "X-Agent-MCP",
        "X-Agent-Report-Intent",
        "X-Agent-Artifact-Url",
        "X-Agent-Artifact-Name",
    ],
)

orchestrator = NetworkHealthOrchestrator()


class AskRequest(BaseModel):
    question: str
    start_date: str | None = None
    end_date: str | None = None
    site_id: str | None = None


@app.get("/api/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/api/runtime")
def runtime_status() -> dict:
    return {"runtime": orchestrator.runtime_status()}


@app.get("/api/sites")
def list_sites() -> dict:
    return {"sites": orchestrator.list_sites()}


@app.get("/api/sites/{site_id}")
def get_site(site_id: str) -> dict:
    try:
        return {"site": orchestrator.get_site(site_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/api/reports/{site_id}")
def get_site_report(
    site_id: str,
    start_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="YYYY-MM-DD"),
) -> dict:
    start, end = default_date_window(start_date=start_date, end_date=end_date, days=7)
    try:
        report = orchestrator.build_report(site_id=site_id, start=start, end=end)
        return {"report": report}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/api/reports")
def get_all_site_reports(
    start_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="YYYY-MM-DD"),
) -> dict:
    start, end = default_date_window(start_date=start_date, end_date=end_date, days=7)
    reports = []
    for site in orchestrator.list_sites():
        reports.append(orchestrator.build_report(site_id=site["site_id"], start=start, end=end))

    return {"count": len(reports), "reports": reports}


@app.get("/api/outputs/{filename}", name="download_generated_report")
def download_generated_report(filename: str) -> FileResponse:
    file_path = OUTPUTS_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="report artifact not found")
    return FileResponse(file_path, filename=filename, media_type="text/markdown; charset=utf-8")


@app.post("/api/chat")
def ask_global_question(payload: AskRequest, request: Request) -> dict:
    start, end = default_date_window(
        start_date=payload.start_date,
        end_date=payload.end_date,
        days=7,
    )
    try:
        answer = orchestrator.ask_global_question(
            question=payload.question,
            start=start,
            end=end,
            site_id=payload.site_id,
        )
        artifact = answer.get("artifact")
        if artifact:
            artifact["download_url"] = str(request.url_for("download_generated_report", filename=artifact["file_name"]))
        return answer
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/api/chat/stream")
def stream_global_question(payload: AskRequest, request: Request):
    start, end = default_date_window(
        start_date=payload.start_date,
        end_date=payload.end_date,
        days=7,
    )

    report_intent = any(keyword in payload.question for keyword in ["生成", "导出", "下载", "报告", "周报", "近一周", "一周"])
    answer_payload = None
    artifact = None
    debug = orchestrator.runtime_status().get("qa_agent", {})

    if report_intent:
        answer_payload = orchestrator.ask_global_question(
            question=payload.question,
            start=start,
            end=end,
            site_id=payload.site_id,
        )
        artifact = answer_payload.get("artifact")
        debug = answer_payload.get("debug", debug)

    headers = {
        "X-Agent-LLM": str(debug.get("llm_enabled", False)).lower(),
        "X-Agent-MCP": str(debug.get("mcp_enabled", False)).lower(),
        "X-Agent-Report-Intent": str(debug.get("intent") == "site_report_export").lower(),
    }
    if artifact:
        artifact_url = str(request.url_for("download_generated_report", filename=artifact["file_name"]))
        headers["X-Agent-Artifact-Url"] = artifact_url
        headers["X-Agent-Artifact-Name"] = artifact["file_name"]

    def generator() -> Iterator[str]:
        if answer_payload is not None and (artifact or debug.get("intent") == "site_report_export"):
            yield answer_payload.get("answer", "")
            return

        for chunk in orchestrator.stream_global_question(
            question=payload.question,
            start=start,
            end=end,
            site_id=payload.site_id,
        ):
            if chunk:
                yield chunk

    return StreamingResponse(generator(), media_type="text/plain; charset=utf-8", headers=headers)
