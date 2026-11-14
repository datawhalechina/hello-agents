# stock_tools/__init__.py
"""
股票数据工具包 (Stock Tools)
专职负责 A 股行情、估值、技术面、基本面数据的采集。
对外暴露标准化接口 StockDataTool（含 run 方法）以及各维度 fetch 函数。
"""

# ================= 1. 导入所有底层工具函数（原路径不变） =================
from ._common import (
    trade_status,
    timeout,
    get_spot_snapshot,
    clear_spot_cache,
    _create_retry_session,
    _latest_non_null,
    _safe_float,
    _latest_report_date,
)
from .fundamental import fetch_fundamental
from .quote import fetch_quote
from .technical import fetch_technical, get_cached_kline, _fetch_hist_data
from .valuation import fetch_valuation


# ================= 2. 定义标准化工具类（对外提供 run 方法） =================
class StockDataTool:
    """
    专职子工具：个股数据采集工具
    对标 Agent 架构，对外提供标准化 run() 接口，屏蔽底层 fetch 函数细节。
    上层 Agent 只需调用 run(stock_code, dims) 即可。
    """

    def __init__(self):
        self.name = "StockDataTool"
        self.description = "负责获取单只 A 股的行情、估值、技术面、基本面数据。"
        # 维度路由表（指向底层 fetch 函数）
        self._dim_map = {
            "quote": fetch_quote,
            "valuation": fetch_valuation,
            "technical": fetch_technical,
            "fundamental": fetch_fundamental,
        }

    def run(self, stock_code: str, dims: list[str]) -> dict:
        """
        标准化调用入口。
        :param stock_code: 股票代码，如 "600519"
        :param dims: 维度列表，如 ["quote", "technical"]
        :return: 结构化字典，格式与 StockDataAgent 期望的兼容
        """
        data, errors = {}, []
        meta = {}

        for dim in dims:
            fn = self._dim_map.get(dim)
            if not fn:
                errors.append(f"unknown_dim: {dim}")
                continue
            try:
                # 调用底层 fetch 函数（逻辑完全不变）
                result = fn(stock_code)
                # 如果是 Pydantic Schema 就转 dict，否则原样返回
                if hasattr(result, 'model_dump'):
                    data[dim] = result.model_dump(exclude_none=True)
                else:
                    data[dim] = result
            except Exception as e:
                errors.append(f"{dim}: {type(e).__name__}: {e}")

        # 如果请求了行情维度，附带交易状态
        if "quote" in dims:
            try:
                meta["trade_status"] = trade_status()
            except Exception:
                pass

        return {
            "stock_code": stock_code,
            "data": data,
            "errors": errors,
            "meta": meta,
        }


# ================= 3. 统一导出列表 =================
__all__ = [
    # 核心类（标准化接口）
    "StockDataTool",
    # 各维度 fetch 函数（兼容原有直接导入方式）
    "fetch_quote",
    "fetch_valuation",
    "fetch_technical",
    "fetch_fundamental",
    # 常用公共工具
    "get_cached_kline",
    "get_spot_snapshot",
    "trade_status",
    "timeout",
]