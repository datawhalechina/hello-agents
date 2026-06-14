"""FastAPI entrypoint exposing the DeepResearchAgent via HTTP."""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any, AsyncIterator, Dict, Iterator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from config import Configuration, SearchAPI
from agent import DeepResearchAgent
from services.applications import APPLICATION_STATUSES, ApplicationStore

# 添加控制台日志处理程序
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <4}</level> | <cyan>using_function:{function}</cyan> | <cyan>{file}:{line}</cyan> | <level>{message}</level>",
    colorize=True,
)

class ResearchRequest(BaseModel):
    """Payload for triggering a research run."""

    topic: str = Field(..., description="Research topic supplied by the user")
    search_api: SearchAPI | None = Field(
        default=None,
        description="Override the default search backend configured via env",
    )


class ResearchResponse(BaseModel):
    """HTTP response containing the generated report and structured tasks."""

    report_markdown: str = Field(
        ..., description="Markdown-formatted research report including sections"
    )
    todo_items: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Structured TODO items with summaries and sources",
    )
    job_items: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Structured internship/job items with match signals",
    )
    search_diagnostics: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Search quality diagnostics for job/JD tasks",
    )


class JobApplicationPayload(BaseModel):
    """Saved internship/job item plus optional tracking metadata."""

    id: Optional[str] = None
    company: str = "未确认"
    title: str = "未确认"
    location: str = "未确认"
    source_url: str = ""
    source_title: str = "未确认"
    requirements: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    duration: str = "未确认"
    deadline: str = "未确认"
    match_score: Optional[int] = None
    match_reason: str = "信息不足，需点开来源确认"
    resume_advice: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    application_status: Optional[str] = Field(
        default=None,
        description="Optional tracking status for this application",
    )
    status_note: Optional[str] = Field(
        default=None,
        description="Optional user note for this saved application",
    )
    application_channel: Optional[str] = None
    applied_at: Optional[str] = None
    next_action: Optional[str] = None
    next_action_at: Optional[str] = None
    resume_version: Optional[str] = None
    withdrawal_reason: Optional[str] = None


class JobApplicationUpdate(BaseModel):
    """Mutable tracking fields for a saved application."""

    application_status: Optional[str] = None
    status_note: Optional[str] = None
    application_channel: Optional[str] = None
    applied_at: Optional[str] = None
    next_action: Optional[str] = None
    next_action_at: Optional[str] = None
    resume_version: Optional[str] = None
    withdrawal_reason: Optional[str] = None


class JobApplicationListResponse(BaseModel):
    """Response payload for saved internship applications."""

    job_items: list[dict[str, Any]] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=lambda: list(APPLICATION_STATUSES))


def _mask_secret(value: Optional[str], visible: int = 4) -> str:
    """Mask sensitive tokens while keeping leading and trailing characters."""
    if not value:
        return "unset"

    if len(value) <= visible * 2:
        return "*" * len(value)

    return f"{value[:visible]}...{value[-visible:]}"


def _build_config(payload: ResearchRequest) -> Configuration:
    overrides: Dict[str, Any] = {}

    if payload.search_api is not None:
        overrides["search_api"] = payload.search_api

    return Configuration.from_env(overrides=overrides)


def create_app(application_store: ApplicationStore | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        startup_config = Configuration.from_env()

        if startup_config.llm_provider == "ollama":
            base_url = startup_config.sanitized_ollama_url()
        elif startup_config.llm_provider == "lmstudio":
            base_url = startup_config.lmstudio_base_url
        else:
            base_url = startup_config.llm_base_url or "unset"

        logger.info(
            "DeepResearch configuration loaded: provider={} model={} base_url={} search_api={} "
            "max_loops={} fetch_full_page={} task_concurrency={} tool_calling={} "
            "strip_thinking={} api_key={}",
            startup_config.llm_provider,
            startup_config.resolved_model() or "unset",
            base_url,
            (
                startup_config.search_api.value
                if isinstance(startup_config.search_api, SearchAPI)
                else startup_config.search_api
            ),
            startup_config.max_web_research_loops,
            startup_config.fetch_full_page,
            startup_config.task_concurrency,
            startup_config.use_tool_calling,
            startup_config.strip_thinking_tokens,
            _mask_secret(startup_config.llm_api_key),
        )
        yield

    app = FastAPI(title="HelloAgents Deep Researcher", lifespan=lifespan)
    config = Configuration.from_env()
    store = application_store or ApplicationStore()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.resolved_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def health_check() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/applications", response_model=JobApplicationListResponse)
    def list_applications() -> JobApplicationListResponse:
        return JobApplicationListResponse(
            job_items=store.list_applications(),
            statuses=list(APPLICATION_STATUSES),
        )

    @app.post("/applications")
    def save_application(payload: JobApplicationPayload) -> dict[str, Any]:
        try:
            return store.save_application(
                payload.model_dump(
                    exclude={
                        "application_status",
                        "status_note",
                        "application_channel",
                        "applied_at",
                        "next_action",
                        "next_action_at",
                        "resume_version",
                        "withdrawal_reason",
                    },
                ),
                application_status=payload.application_status,
                status_note=payload.status_note,
                application_channel=payload.application_channel,
                applied_at=payload.applied_at,
                next_action=payload.next_action,
                next_action_at=payload.next_action_at,
                resume_version=payload.resume_version,
                withdrawal_reason=payload.withdrawal_reason,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.patch("/applications/{item_id}")
    def update_application(
        item_id: str,
        payload: JobApplicationUpdate,
    ) -> dict[str, Any]:
        try:
            return store.update_application(
                item_id,
                application_status=payload.application_status,
                status_note=payload.status_note,
                application_channel=payload.application_channel,
                applied_at=payload.applied_at,
                next_action=payload.next_action,
                next_action_at=payload.next_action_at,
                resume_version=payload.resume_version,
                withdrawal_reason=payload.withdrawal_reason,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Saved job not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/applications/{item_id}")
    def delete_application(item_id: str) -> dict[str, bool]:
        if not store.delete_application(item_id):
            raise HTTPException(status_code=404, detail="Saved job not found")
        return {"deleted": True}

    @app.post("/research", response_model=ResearchResponse)
    def run_research(payload: ResearchRequest) -> ResearchResponse:
        try:
            config = _build_config(payload)
            agent = DeepResearchAgent(config=config)
            result = agent.run(payload.topic)
        except ValueError as exc:  # Likely due to unsupported configuration
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive guardrail
            raise HTTPException(status_code=500, detail="Research failed") from exc

        todo_payload = [
            {
                "id": item.id,
                "title": item.title,
                "intent": item.intent,
                "query": item.query,
                "status": item.status,
                "summary": item.summary,
                "sources_summary": item.sources_summary,
                "note_id": item.note_id,
                "note_path": item.note_path,
            }
            for item in result.todo_items
        ]

        return ResearchResponse(
            report_markdown=(result.report_markdown or result.running_summary or ""),
            todo_items=todo_payload,
            job_items=[asdict(item) for item in result.job_items],
            search_diagnostics=result.search_diagnostics,
        )

    @app.post("/research/stream")
    def stream_research(payload: ResearchRequest) -> StreamingResponse:
        try:
            config = _build_config(payload)
            agent = DeepResearchAgent(config=config)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        def event_iterator() -> Iterator[str]:
            try:
                for event in agent.run_stream(payload.topic):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception as exc:  # pragma: no cover - defensive guardrail
                logger.exception("Streaming research failed")
                error_payload = {"type": "error", "detail": str(exc)}
                yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_iterator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
