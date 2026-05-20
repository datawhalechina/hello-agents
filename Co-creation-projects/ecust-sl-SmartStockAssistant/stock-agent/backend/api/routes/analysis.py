# backend/api/routes/analysis.py
from fastapi import APIRouter, HTTPException, Query
from api.schemas import AnalysisRequest, AnalysisResponse, ScoreDetail, SearchResult
from agent.graph import run_analysis
import akshare as ak
from data.sources.stock_list import ensure_stock_list, search_stocks, resolve_symbol
from data.sources.hot_stocks import get_hot_stocks
router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.get("/search", response_model=list[SearchResult])
async def search_stock(
    q: str = Query(..., min_length=1, description="股票代码或名称关键词"),
    market: str = Query(None, description="市场过滤：A股 | 美股"),
):
    await ensure_stock_list()
    results = search_stocks(q.strip(), market=market, limit=10)
    return [SearchResult(**r) for r in results]


@router.get("/hot/all")
async def hot_all():
    """三市热门股票（A股/港股/美股 各 8 只），含价格、涨跌、7 日 sparkline。"""
    return await get_hot_stocks()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_stock(request: AnalysisRequest):
    if request.market not in ("A股", "港股", "美股"):
        raise HTTPException(status_code=400, detail="market 必须为 'A股' | '港股' | '美股'")

    code = request.symbol.strip()

    # A股代码格式校验
    if request.market == "A股":
        if not (code.isdigit() and len(code) == 6):
            raise HTTPException(
                status_code=400,
                detail="A股代码格式错误，请输入6位数字代码，如 600519"
            )

    # 港股代码格式校验（1~5位数字，会自动补零到 5 位）
    if request.market == "港股":
        if not (code.isdigit() and 1 <= len(code) <= 5):
            raise HTTPException(
                status_code=400,
                detail="港股代码格式错误，请输入1~5位数字代码，如 700 或 00700"
            )

    # 美股代码格式校验
    if request.market == "美股":
        upper = code.upper()
        if not (1 <= len(upper) <= 6 and upper.replace("-", "").replace(".", "").isalpha()):
            raise HTTPException(
                status_code=400,
                detail="美股代码格式错误，请输入1~6位字母代码，如 AAPL"
            )

    try:
        result = await run_analysis(request.symbol.strip(), request.market)
        return AnalysisResponse(
            symbol=result["symbol"],
            market=result["market"],
            risk_level=result.get("risk_level"),
            scores=ScoreDetail(
                sentiment=result.get("sentiment_score"),
                sentiment_label=result.get("sentiment_label"),
                sentiment_reason=result.get("sentiment_reason"),
                technical=result.get("technical_score"),
                technical_signals=result.get("technical_signals"),
                fundamental=result.get("fundamental_score"),
                fundamental_signals=result.get("fundamental_signals"),
            ),
            report=result.get("final_report"),
            error=result.get("error"),
            kline_data=result.get("kline_data"),
            realtime_data=result.get("realtime_data"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))