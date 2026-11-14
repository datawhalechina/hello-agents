# stock_tools/fundamental.py
import akshare as ak
import pandas as pd

from ..schemas import FundamentalQualitySchema
from ._common import _latest_non_null, _latest_report_date


def fetch_fundamental(stock_code: str) -> FundamentalQualitySchema:
    result = FundamentalQualitySchema()

    # ---- 指标类 ----
    try:
        ind_df = ak.stock_financial_analysis_indicator_em(symbol=stock_code)
        # 长表：指标名称 | 报告期 | 指标值
        ind_pivot = ind_df.pivot_table(
            index="报告期", columns="指标名称", values="指标值", aggfunc="first"
        ).sort_index(ascending=False)

        def get_ind(*keys):
            for k in keys:
                if k in ind_pivot.columns:
                    return _latest_non_null(ind_pivot[k])
            return None

        result.roe = get_ind("净资产收益率", "ROE")
        result.gross_margin = get_ind("销售毛利率", "毛利率")
        result.net_margin = get_ind("销售净利率", "净利率")
        result.debt_ratio = get_ind("资产负债率")
        result.revenue_yoy = get_ind("营业收入同比增长率")
    except Exception:
        pass

    # ---- 扣非净利润 & 同比 ----
    try:
        abs_df = ak.stock_financial_abstract_ths(symbol=stock_code, indicator="按报告期")
        abs_df = abs_df.sort_values("报告期", ascending=False)
        if "扣非净利润" in abs_df.columns:
            v = _latest_non_null(abs_df["扣非净利润"])
            if v is not None:
                try:
                    result.adjusted_net_profit = round(float(v) / 1e8, 2)
                except (TypeError, ValueError):
                    pass
        if "扣非净利润同比增长率" in abs_df.columns:
            result.adjusted_profit_yoy = _latest_non_null(abs_df["扣非净利润同比增长率"])
    except Exception:
        pass

    # ---- 现金流 ----
    try:
        report_date = _latest_report_date(stock_code)
        if report_date:
            cf_df = ak.stock_xjll_em(date=report_date)
            cf_row = cf_df[cf_df["股票代码"].astype(str).str.zfill(6) == stock_code.zfill(6)]
            if len(cf_row) > 0:
                r = cf_row.iloc[0]
                ocf = r.get("经营活动产生的现金流量净额")
                capex = r.get("购建固定资产、无形资产和其他长期资产支付的现金")
                if pd.notna(ocf):
                    capex_val = float(capex) if pd.notna(capex) else 0.0
                    result.free_cash_flow = round((float(ocf) - capex_val) / 1e8, 2)
                if pd.notna(ocf) and result.adjusted_net_profit:
                    result.ocf_to_net_profit = round(
                        float(ocf) / (result.adjusted_net_profit * 1e8), 2
                    )
    except Exception:
        pass

    return result