#!/usr/bin/env python3
"""CryptoAnalysisAgent web console: chat + analysis reports.

    python web.py
    # open http://127.0.0.1:8765

Frontend (optional Vite dev server):
    cd frontend && npm install && npm run dev
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from analyze import OUTPUT_DIR, load_runtime_env, normalize_symbol, run_one
from src.api import chat, config, memory, session
from src.api.deps import get_pipeline, get_workspace

ROOT = Path(__file__).parent
WEB_DIR = ROOT / "web"
FRONT_DIST = ROOT / "frontend" / "dist"

app = FastAPI(title="CryptoAnalysisAgent", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:8765").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if WEB_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

_lock = threading.Lock()
_busy = False


class AnalyzeRequest(BaseModel):
    symbol: str = Field(..., examples=["BTC"])
    record: bool = False


@app.on_event("startup")
def _startup():
    load_runtime_env()
    get_workspace().ensure_workspace_exists()


@app.get("/api/health")
def health():
    load_runtime_env()
    key = (os.getenv("LLM_API_KEY") or "").strip()
    configured = bool(key) and key not in {
        "your_api_key_here",
        "your_deepseek_api_key",
        "your_openai_api_key",
    }
    return {"ok": True, "busy": _busy, "llm_configured": configured, "agent": get_workspace().read_identity_name()}


@app.get("/health")
def health_alias():
    return health()


def _parse_report_name(path: Path) -> dict:
    stem = path.stem
    passed = not stem.endswith("_NOT_PASSED")
    core = stem[:-11] if not passed else stem
    symbol, _, stamp = core.partition("_")
    return {
        "filename": path.name,
        "symbol": symbol,
        "stamp": stamp,
        "passed": passed,
        "created_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "size": path.stat().st_size,
    }


@app.get("/api/reports")
def list_reports():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(OUTPUT_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [_parse_report_name(p) for p in files[:30]]


@app.get("/api/reports/{filename}")
def get_report(filename: str):
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="非法文件名")
    path = OUTPUT_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="报告不存在")
    text = path.read_text(encoding="utf-8")
    report, _, tail = text.partition("\n---\n")
    meta = _parse_report_name(path)
    meta["report"] = report.strip()
    meta["appendix"] = tail.strip()
    return meta


@app.post("/api/analyze")
def analyze(body: AnalyzeRequest):
    global _busy
    try:
        symbol = normalize_symbol(body.symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not _lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="已有分析正在进行，请稍候")
    _busy = True
    try:
        pipe = get_pipeline()
        return run_one(
            symbol,
            record=body.record,
            llm=pipe["llm"],
            counter=pipe["counter"],
            coordinator=pipe["coordinator"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"分析失败: {exc}") from exc
    finally:
        _busy = False
        _lock.release()


app.include_router(chat.router, prefix="/api")
app.include_router(session.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(memory.router, prefix="/api")


@app.get("/legacy")
def legacy_index():
    return FileResponse(WEB_DIR / "index.html")


if FRONT_DIST.is_dir() and (FRONT_DIST / "index.html").is_file():
    assets_dir = FRONT_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("static/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = FRONT_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONT_DIST / "index.html")
else:
    @app.get("/")
    def index():
        return FileResponse(WEB_DIR / "index.html")


def main() -> None:
    load_runtime_env()
    print("\nCryptoAnalysisAgent  Web  http://127.0.0.1:8765")
    print("对话界面开发: cd frontend && npm install && npm run dev\n")
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", 8765)), log_level="info")


if __name__ == "__main__":
    main()
