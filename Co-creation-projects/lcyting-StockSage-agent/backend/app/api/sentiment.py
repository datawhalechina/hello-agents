"""AI 舆情分析流式 API — 实现方案约定路径"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.agent_api import AnalysisRequest, iter_sentiment_analysis_ndjson

router = APIRouter(prefix="/sentiment", tags=["AI舆情分析"])


@router.post("/analyze/stream")
async def sentiment_analyze_stream(body: AnalysisRequest):
    """POST /api/v1/sentiment/analyze/stream"""
    return StreamingResponse(
        iter_sentiment_analysis_ndjson(body.stock_code, body.stock_name),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
