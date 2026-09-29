"""Local-only workbench API; model output never reaches a shell."""

from __future__ import annotations

import io
import json
import os
import re
import threading
import time
import uuid
import zipfile
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from .artifacts import write_result
from .figma import fetch_figma, parse_figma_url
from .pipeline import run_pipeline

ROOT = Path(__file__).resolve().parent.parent
RUN_ROOT = ROOT / "outputs/runs"
MAX_BODY = 2 * 1024 * 1024
app = FastAPI(title="FrameCraft", version="0.1.0", docs_url="/api/docs")
_runs: dict[str, dict] = {}
_lock = threading.RLock()
_slots = threading.BoundedSemaphore(2)


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Literal["sample", "json", "figma"] = "sample"
    payload: dict | None = None
    figma_url: str = Field(default="", max_length=2048)
    node_id: str | None = Field(default=None, max_length=100)
    mode: Literal["demo", "live"] = "demo"
    brief: str = Field(default="", max_length=2000)


def _availability() -> dict:
    return {
        "status": "ok",
        "live_available": bool((os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"))
                               and (os.getenv("LLM_MODEL_ID") or os.getenv("MODEL_NAME"))),
        "figma_available": bool(os.getenv("FIGMA_ACCESS_TOKEN")),
    }


def _safe_error(exc: Exception) -> str:
    message = str(exc)
    for key, value in os.environ.items():
        if any(word in key for word in ("KEY", "TOKEN", "PASSWORD", "SECRET")) and len(value) > 5:
            message = message.replace(value, "[redacted]")
    return message[:800]


@app.middleware("http")
async def local_request_guard(request: Request, call_next):
    # The app is a localhost utility, not an authenticated multi-user service.
    host = request.url.hostname
    if host not in ("localhost", "127.0.0.1", "testserver"):
        return JSONResponse({"detail": "仅支持 localhost 访问。"}, status_code=400)
    if request.method == "POST":
        origin = request.headers.get("origin")
        allowed = {f"http://127.0.0.1:{request.url.port or 80}", f"http://localhost:{request.url.port or 80}"}
        if origin and origin not in allowed:
            return JSONResponse({"detail": "不允许跨站提交生成请求。"}, status_code=403)
        size = 0
        pieces = []
        async for part in request.stream():
            size += len(part)
            if size > MAX_BODY:
                return JSONResponse({"detail": "请求超过 2 MB，请缩小设计 JSON。"}, status_code=413)
            pieces.append(part)
        request._body = b"".join(pieces)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health():
    return _availability()


@app.get("/api/sample")
def sample():
    return json.loads((ROOT / "data/sample-design.json").read_text(encoding="utf-8"))


def _record(run_id: str, event: dict):
    with _lock:
        _runs[run_id]["events"].append(dict(event))


def _work(run_id: str, spec: RunRequest):
    try:
        with _lock:
            _runs[run_id]["status"] = "running"
        selected = spec.node_id
        if spec.source == "sample":
            payload = sample()
        elif spec.source == "figma":
            _record(run_id, {"stage": "import", "status": "running", "message": "正在读取选中的 Figma 节点…"})
            payload, selected = fetch_figma(spec.figma_url, os.getenv("FIGMA_ACCESS_TOKEN", ""), spec.node_id)
        else:
            payload = spec.payload
        result = run_pipeline(payload, node_id=selected, mode=spec.mode, brief=spec.brief,
                              on_event=lambda event: _record(run_id, event))
        output = write_result(result, RUN_ROOT / run_id)
        public = {k: v for k, v in result.items() if k not in ("events", "files")}
        # Export both source files and evidence files.
        artifacts = {str(path.relative_to(output)): path.read_text(encoding="utf-8")
                     for path in output.rglob("*") if path.is_file()}
        public["files"] = [{"path": path, "size": len(content.encode("utf-8"))}
                           for path, content in sorted(artifacts.items())]
        with _lock:
            _runs[run_id].update(status="completed", result=public, _files=artifacts)
    except Exception as exc:
        error = _safe_error(exc)
        with _lock:
            _runs[run_id].update(status="failed", error=error)
        _record(run_id, {"stage": "error", "status": "failed", "message": error})
    finally:
        _slots.release()


@app.post("/api/runs", status_code=202)
def create_run(spec: RunRequest, tasks: BackgroundTasks):
    availability = _availability()
    if spec.mode == "live" and not availability["live_available"]:
        raise HTTPException(400, "在线模式需要在项目 .env 中配置 LLM_API_KEY 和 LLM_MODEL_ID。")
    if spec.source == "json" and spec.payload is None:
        raise HTTPException(400, "请上传 Figma REST 格式的 JSON 对象。")
    if spec.source == "figma":
        try:
            parse_figma_url(spec.figma_url, spec.node_id)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        if not availability["figma_available"]:
            raise HTTPException(400, "请在项目 .env 中配置 FIGMA_ACCESS_TOKEN。")
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, "已有两个任务正在运行，请等待完成后重试。")
    run_id = uuid.uuid4().hex
    with _lock:
        if len(_runs) >= 24:
            old = next((key for key, run in _runs.items() if run["status"] in ("completed", "failed")), None)
            if old:
                _runs.pop(old)
        _runs[run_id] = {"id": run_id, "status": "queued", "events": [], "created_at": time.time()}
    tasks.add_task(_work, run_id, spec)
    return {"id": run_id, "status": "queued"}


def _get_run(run_id: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise HTTPException(404, "任务不存在。")
    with _lock:
        run = _runs.get(run_id)
        if run is None:
            raise HTTPException(404, "任务不存在或已离开当前会话。已保存的产物仍在 outputs/runs 中。")
        return run


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = _get_run(run_id)
    with _lock:
        return {key: value for key, value in run.items() if not key.startswith("_")}


def _files(run_id: str) -> dict[str, str]:
    run = _get_run(run_id)
    if run["status"] != "completed":
        raise HTTPException(409, "任务尚未完成。")
    return run["_files"]


@app.get("/api/runs/{run_id}/files", response_class=PlainTextResponse)
def get_file(run_id: str, path: str):
    files = _files(run_id)
    if path not in files:
        raise HTTPException(404, "产物中没有此文件。")
    return PlainTextResponse(files[path])


@app.get("/api/runs/{run_id}/preview", response_class=HTMLResponse)
def preview(run_id: str):
    return HTMLResponse(_files(run_id)["preview.html"], headers={
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:; frame-ancestors 'self'; sandbox",
    })


@app.get("/api/runs/{run_id}/download")
def download(run_id: str):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in _files(run_id).items():
            archive.writestr(path, content)
    return Response(buffer.getvalue(), media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="framecraft-{run_id[:8]}.zip"',
    })


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="workbench")
