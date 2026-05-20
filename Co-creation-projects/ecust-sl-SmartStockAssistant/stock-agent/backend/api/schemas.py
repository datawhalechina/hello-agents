# backend/api/schemas.py
from pydantic import BaseModel, Field
from typing import Optional


class SearchResult(BaseModel):
    symbol: str
    name: str
    market: str   # "A股" | "港股" | "美股"


class AnalysisRequest(BaseModel):
    symbol: str = Field(..., description="股票代码")
    market: str = Field(..., description="市场：A股 | 港股 | 美股")

    model_config = {"json_schema_extra": {
        "examples": [
            {"symbol": "600519", "market": "A股"},
            {"symbol": "00700",  "market": "港股"},
            {"symbol": "AAPL",   "market": "美股"},
        ]
    }}


class ScoreDetail(BaseModel):
    sentiment: Optional[float] = None
    sentiment_label: Optional[str] = None
    sentiment_reason: Optional[str] = None
    technical: Optional[float] = None
    technical_signals: Optional[list] = None
    fundamental: Optional[float] = None
    fundamental_signals: Optional[list] = None


class AnalysisResponse(BaseModel):
    symbol: str
    market: str
    risk_level: Optional[str] = None
    scores: ScoreDetail
    report: Optional[str] = None
    error: Optional[str] = None
    kline_data: Optional[list] = None      # 新增
    realtime_data: Optional[dict] = None   # 新增


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    mock_mode: bool