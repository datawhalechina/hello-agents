"""史观交锋 Web：提供静态页与辩论 API。"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from historical_review.debate_orchestrator import iter_debate_events, run_historical_debate

_STATIC = Path(__file__).resolve().parent / "static"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")
load_dotenv()

app = FastAPI(title="史观交锋", description="多角色历史辩论：官修/野史/政治语境/域外/蹊跷辨析")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if _STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


class DebateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=8000)
    api_key: str | None = Field(None, description="OpenRouter 等 API Key，可空则用服务端环境变量")
    base_url: str | None = Field(None, description="OpenAI 兼容 Base URL")
    model: str | None = Field(None, description="模型 ID，如 openai/gpt-4o-mini")
    max_tokens: int | None = Field(4096, ge=256, le=128000)
    timeout: int | None = Field(180, ge=30, le=600, description="单次 HTTP 请求超时秒数")
    debate_temperature: float = Field(0.72, ge=0.0, le=2.0)
    synthesizer_temperature: float = Field(0.22, ge=0.0, le=2.0)
    use_evidence_bundle: bool = True


class DebateResponse(BaseModel):
    ok: bool
    markdown: str | None = None
    error: str | None = None


def _api_key_error(req: DebateRequest) -> str | None:
    has_key = bool(req.api_key and req.api_key.strip())
    if not has_key and not (os.getenv("OPENROUTER_API_KEY") or os.getenv("LLM_API_KEY")):
        return "未配置 API Key：请在左侧填写 OpenRouter Key，或在服务器 .env 中设置 OPENROUTER_API_KEY。"
    return None


@app.get("/")
async def index_page() -> FileResponse:
    html = _STATIC / "index.html"
    if not html.is_file():
        raise HTTPException(status_code=500, detail="前端文件缺失，请检查 historical_review/web/static/")
    return FileResponse(html)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/debate", response_model=DebateResponse)
async def run_debate(req: DebateRequest) -> DebateResponse:
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="议题不能为空")

    key_err = _api_key_error(req)
    if key_err:
        return DebateResponse(ok=False, error=key_err)

    def _work() -> str:
        return run_historical_debate(
            topic,
            use_evidence_bundle=req.use_evidence_bundle,
            debate_temperature=req.debate_temperature,
            synthesizer_temperature=req.synthesizer_temperature,
            llm_api_key=req.api_key.strip() if req.api_key else None,
            llm_base_url=req.base_url.strip() if req.base_url else None,
            llm_model=req.model.strip() if req.model else None,
            llm_max_tokens=req.max_tokens,
            llm_timeout=req.timeout,
        )

    loop = asyncio.get_event_loop()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            md = await asyncio.wait_for(
                loop.run_in_executor(pool, _work),
                timeout=900.0,
            )
    except asyncio.TimeoutError:
        return DebateResponse(ok=False, error="任务超时（>15 分钟），请换小议题或提高超时/换更快模型。")
    except Exception as e:  # pragma: no cover
        return DebateResponse(ok=False, error=f"{type(e).__name__}: {e}")

    return DebateResponse(ok=True, markdown=md)


@app.post("/api/debate/stream")
def debate_stream(req: DebateRequest) -> StreamingResponse:
    """SSE：逐段推送辩论进度与各角色发言，最后 complete 带全文 Markdown。"""
    topic = req.topic.strip()
    if not topic:

        def err_only():
            import json

            yield f"data: {json.dumps({'event': 'error', 'message': '议题不能为空'}, ensure_ascii=False)}\n\n".encode(
                "utf-8"
            )

        return StreamingResponse(err_only(), media_type="text/event-stream")

    key_err = _api_key_error(req)
    if key_err:

        def err_key():
            import json

            yield f"data: {json.dumps({'event': 'error', 'message': key_err}, ensure_ascii=False)}\n\n".encode("utf-8")

        return StreamingResponse(err_key(), media_type="text/event-stream")

    def event_bytes():
        import json

        try:
            for ev in iter_debate_events(
                topic,
                use_evidence_bundle=req.use_evidence_bundle,
                debate_temperature=req.debate_temperature,
                synthesizer_temperature=req.synthesizer_temperature,
                llm_api_key=req.api_key.strip() if req.api_key else None,
                llm_base_url=req.base_url.strip() if req.base_url else None,
                llm_model=req.model.strip() if req.model else None,
                llm_max_tokens=req.max_tokens,
                llm_timeout=req.timeout,
            ):
                line = f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                yield line.encode("utf-8")
        except Exception as e:  # pragma: no cover
            err_ev = {"event": "error", "message": f"{type(e).__name__}: {e}"}
            yield f"data: {json.dumps(err_ev, ensure_ascii=False)}\n\n".encode("utf-8")

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_bytes(), media_type="text/event-stream", headers=headers)
