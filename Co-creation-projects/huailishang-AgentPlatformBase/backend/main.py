from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.agents.registry import build_default_registry
from backend.config import settings
from backend.events import event_logger
from backend.models import AgentRequest, AgentResponse, BatchRunRequest, TaskCreateRequest, TaskRecord
from backend.tasks.batch import BatchRunner
from backend.tasks.manager import task_manager
from backend.tasks.runner import TaskRunner


if os.getenv("APP_ACCESS_LOG", "false").strip().lower() not in {"1", "true", "yes", "on"}:
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("uvicorn.access").setLevel(logging.CRITICAL + 1)

for noisy_logger in ("agent", "services", "services.planner", "services.tool_events"):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

registry = build_default_registry()
task_runner = TaskRunner(registry, task_manager)
batch_runner = BatchRunner(registry)

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

RSS_DIGEST_DIR = Path(settings.rss_digest_data_root).resolve() / "runs" / "digests"
if RSS_DIGEST_DIR.exists():
    app.mount("/rss-digests", StaticFiles(directory=RSS_DIGEST_DIR, html=True), name="rss_digests")


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse(url="/app/")


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "service": settings.app_name}


@app.get("/agents")
def list_agents() -> dict:
    profiles = registry.list_profiles()
    return {"agents": profiles, "total": len(profiles)}


@app.post("/agents/{agent_id}/run", response_model=AgentResponse)
def run_agent(agent_id: str, request: AgentRequest) -> AgentResponse:
    try:
        return registry.get(agent_id).run(request)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")


@app.post("/tasks", response_model=TaskRecord)
def create_task(request: TaskCreateRequest) -> TaskRecord:
    if request.agent_id not in set(registry.ids()):
        raise HTTPException(status_code=404, detail=f"Agent '{request.agent_id}' not found")
    return task_manager.create(request)


@app.get("/tasks")
def list_tasks() -> dict:
    tasks = task_manager.list()
    return {"tasks": tasks, "total": len(tasks)}


@app.get("/tasks/{task_id}", response_model=TaskRecord)
def get_task(task_id: str) -> TaskRecord:
    try:
        return task_manager.get(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")


@app.post("/tasks/{task_id}/run", response_model=TaskRecord)
def run_task(task_id: str, background: bool = True) -> TaskRecord:
    try:
        task_manager.get(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    if background:
        return task_runner.start_background(task_id)
    return task_runner.run(task_id)


@app.post("/batch/run")
def run_batch(request: BatchRunRequest) -> dict:
    try:
        return {"responses": batch_runner.run(request.requests)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Agent '{exc.args[0]}' not found")


@app.get("/events")
def list_events(task_id: str | None = None, limit: int = 100) -> dict:
    return {"events": event_logger.list_events(task_id=task_id, limit=limit)}
