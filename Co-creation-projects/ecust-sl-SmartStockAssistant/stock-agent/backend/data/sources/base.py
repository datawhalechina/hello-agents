# backend/data/sources/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StockQuote:
    """实时行情数据结构"""
    symbol: str
    price: float
    volume: int
    change_pct: float      # 涨跌幅，如 1.5 表示 +1.5%
    open: float
    high: float
    low: float
    timestamp: str


@dataclass
class KlineBar:
    """单根 K 线数据结构"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class FundamentalData:
    """基本面数据结构"""
    symbol: str
    pe_ratio: float        # 市盈率
    pb_ratio: float        # 市净率
    market_cap: float      # 市值（亿）
    revenue_growth: float  # 营收同比增长率 %
    profit_growth: float   # 净利润同比增长率 %


class BaseDataSource(ABC):
    """
    所有数据源适配器的统一接口。
    新增数据源（如富途、同花顺）只需继承此类并实现三个方法。
    测试时用 MockDataSource 替换，无需真实网络。
    """

    @abstractmethod
    async def get_realtime_quote(self, symbol: str) -> StockQuote:
        """获取实时行情"""
        ...

    @abstractmethod
    async def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        limit: int = 30,
    ) -> list[KlineBar]:
        """
        获取 K 线数据
        period: "daily" | "weekly" | "60min" | "30min"
        limit:  返回最近 N 根 K 线
        """
        ...

    @abstractmethod
    async def get_fundamental(self, symbol: str) -> FundamentalData:
        """获取基本面数据"""
        ...