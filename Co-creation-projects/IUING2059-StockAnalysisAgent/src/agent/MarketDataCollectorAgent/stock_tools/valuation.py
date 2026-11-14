# stock_tools/valuation.py
import akshare as ak

from ..schemas import ValuationSchema
from ._common import _safe_float


def fetch_valuation(stock_code: str) -> ValuationSchema:
    result = ValuationSchema()
    try:
        df = ak.stock_zh_valuation_comparison_em(symbol=stock_code)
        if df.empty:
            return result

        # 该接口返回多行：行业平均、行业中值、个股。优先筛出个股行。
        row = None
        if "代码" in df.columns:
            match = df[df["代码"].astype(str).str.zfill(6) == stock_code.zfill(6)]
            if len(match) > 0:
                row = match.iloc[0]
        if row is None:
            row = df.iloc[-1]  # 兜底：最后一行通常是个股

        result.pe_ttm = _safe_float(row, "市盈率-TTM", "PE(TTM)")
        result.pb = _safe_float(row, "市净率-MRQ", "PB")
        result.ps_ttm = _safe_float(row, "市销率-TTM", "PS(TTM)")
        result.peg = _safe_float(row, "PEG")
        result.ev_ebitda = _safe_float(row, "EV/EBITDA", "企业价值倍数")
    except Exception:
        pass
    return result