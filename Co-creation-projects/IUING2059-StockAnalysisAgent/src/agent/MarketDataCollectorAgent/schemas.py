# src/agent/MarketDataCollectorAgent/schemas.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

from src.common.agent_result import BaseAgentOutput, SafeFloat


class StockQuoteSchema(BaseModel):
    """行情快照（已删除 time_range，时间区间统一放在顶层 CompleteStockAnalysisSchema）"""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True, validate_assignment=True)

    stock_code: str = Field(description="股票代码，如 600519.SH")
    stock_name: str = Field(description="股票名称")
    open_price: SafeFloat = None
    close_price: SafeFloat = None
    high_price: SafeFloat = None
    low_price: SafeFloat = None
    volume: SafeFloat = Field(default=None, description="成交量")
    amount: SafeFloat = None
    turnover_rate: SafeFloat = None


class FundamentalQualitySchema(BaseModel):
    """基本面质量（全部改为 SafeFloat，自动清洗 akshare 的 'xx%' 字符串）"""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True, validate_assignment=True)

    roe: SafeFloat = None
    roic: SafeFloat = None
    gross_margin: SafeFloat = None
    net_margin: SafeFloat = None
    adjusted_net_profit: SafeFloat = None
    revenue_yoy: SafeFloat = None
    adjusted_profit_yoy: SafeFloat = None
    debt_ratio: SafeFloat = None
    interest_coverage: SafeFloat = None
    goodwill_to_equity: SafeFloat = None
    ocf_to_net_profit: SafeFloat = None
    free_cash_flow: SafeFloat = None


class ValuationSchema(BaseModel):
    """估值"""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True, validate_assignment=True)

    pe_ttm: SafeFloat = None
    pb: SafeFloat = None
    ps_ttm: SafeFloat = None
    peg: SafeFloat = None
    ev_ebitda: SafeFloat = None


class TechnicalIndicatorSchema(BaseModel):
    """技术指标"""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True, validate_assignment=True)

    ma20: SafeFloat = None
    ma60: SafeFloat = None
    macd_dif: SafeFloat = None
    macd_dea: SafeFloat = None
    macd_bar: SafeFloat = None
    obv: SafeFloat = None
    rsi_14: SafeFloat = None
    kdj_k: SafeFloat = None
    kdj_d: SafeFloat = None
    kdj_j: SafeFloat = None
    boll_upper: SafeFloat = None
    boll_mid: SafeFloat = None
    boll_lower: SafeFloat = None


class CompleteStockAnalysisSchema(BaseAgentOutput):
    """行情采集 Agent 的最终输出（继承 BaseAgentOutput，统一 to_json）。"""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True, validate_assignment=True)

    time_range: Optional[str] = Field(default=None, description="数据统计时间区间")
    trade_status: Optional[str] = Field(
        default=None, description="normal / suspended / not_trading_day"
    )

    quote: Optional[StockQuoteSchema] = None
    fundamental: Optional[FundamentalQualitySchema] = None
    valuation: Optional[ValuationSchema] = None
    technical: Optional[TechnicalIndicatorSchema] = None
    summary_score: SafeFloat = None