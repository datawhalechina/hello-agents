"""论文阅读助手 API 路由 —— PDF 打开、AI 导读、对话问答与阅读历史."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from ...models.schemas import (
    PaperReaderChatRequest,
    PaperReaderChatResponse,
    PaperReaderHistoryItem,
    PaperReaderHistoryResponse,
    PaperReaderOpeningRequest,
    PaperReaderOpeningResponse,
)
from ..dependencies import get_database
from ...utils.common import safe_http_500
from ...services.reader.paper_reader_service import PaperReaderService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI 分析"])

def get_paper_reader_service() -> PaperReaderService:
    db = get_database()
    return PaperReaderService(db=db)

# 首次打开论文 → 生成 AI 导读和结构化摘要
@router.post("/paper-reader/opening", response_model=PaperReaderOpeningResponse)
async def paper_reader_opening(
    body: PaperReaderOpeningRequest,
    background_tasks: BackgroundTasks,
    service: PaperReaderService = Depends(get_paper_reader_service),
):
    try:
        result = await service.get_opening(paper_id=int(body.paper_id), background_tasks=background_tasks)
        return PaperReaderOpeningResponse(success=True, **result)
    except HTTPException:
        raise
    except Exception as e:
        raise safe_http_500("paper_reader_opening", e)

# 论文对话：基于 PDF 全文 + 参考文献上下文的问答
@router.post("/paper-reader/chat", response_model=PaperReaderChatResponse)
async def paper_reader_chat(
    body: PaperReaderChatRequest,
    background_tasks: BackgroundTasks,
    service: PaperReaderService = Depends(get_paper_reader_service),
):
    try:
        out = await service.process_chat(
            paper_id=int(body.paper_id),
            messages=list(body.messages or []),
            user_message=body.user_message,
            background_tasks=background_tasks,
        )
        return PaperReaderChatResponse(
            success=True,
            reply=str(out.get("reply") or "").strip(),
            pdf_parsing=bool(out.get("pdf_parsing", False)),
            related_papers=list(out.get("related_papers") or []),
            related_hints=list(out.get("related_hints") or []),
            kg_edges=list(out.get("kg_edges") or []),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise safe_http_500("paper_reader_chat", e)

@router.get("/paper-reader/history", response_model=PaperReaderHistoryResponse)
async def paper_reader_history(
    paper_id: int = Query(..., ge=1),
    limit: int = Query(default=200, ge=1, le=1000),
    service: PaperReaderService = Depends(get_paper_reader_service),
):
    try:
        turns = await service.get_history(paper_id=int(paper_id), limit=int(limit))
        return PaperReaderHistoryResponse(
            success=True,
            paper_id=int(paper_id),
            turns=[PaperReaderHistoryItem(**t) for t in turns],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise safe_http_500("paper_reader_history", e)
