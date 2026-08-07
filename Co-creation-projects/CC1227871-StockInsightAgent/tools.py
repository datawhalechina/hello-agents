"""Step 2: 股票分析工具 — akshare (Sina/Tencent 源) 真实数据 + 技术指标"""
import time
import numpy as np
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from typing import Dict, Any


class ToolExecutor:
    """工具注册与执行中心"""
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def registerTool(self, name: str, description: str, func: callable):
        self.tools[name] = {"description": description, "func": func}
        print(f"  [工具] {name} 已注册")

    def getTool(self, name: str) -> callable:
        return self.tools.get(name, {}).get("func")

    def getAvailableTools(self) -> str:
        return "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.tools.items()
        ])


# ==================== 辅助函数 ====================

def _to_sina_code(code: str) -> str:
    """将纯数字代码转换为 Sina 格式 (sh600519 / sz000001)"""
    code = code.strip()
    if code.startswith("6"):
        return f"sh{code}"
    elif code.startswith(("0", "3")):
        return f"sz{code}"
    return code


def _resolve_symbol(query: str) -> str:
    """解析股票代码：支持名称搜索，返回纯数字代码"""
    query = query.strip()
    if query.isdigit() and len(query) == 6:
        return query

    # 尝试使用 akshare stock_info_a_code_name 映射
    try:
        import akshare as ak
        stock_info = ak.stock_info_a_code_name()

        # 匹配名称
        match = stock_info[stock_info["name"] == query]
        if not match.empty:
            return match["code"].values[0]

        # 模糊匹配名称
        fuzzy_match = stock_info[stock_info["name"].str.contains(query, na=False)]
        if not fuzzy_match.empty:
            return fuzzy_match["code"].values[0]
    except Exception:
        pass

    # 尝试通过新闻接口反查（间接方式）
    try:
        time.sleep(1)
        info = ak.stock_individual_info_em(symbol=query) if query.isdigit() else None
        if info is not None and len(info) > 0:
            return query
    except Exception:
        pass
    return query


def _safe_fetch(func, *args, **kwargs):
    """带重试的数据获取"""
    import random
    for attempt in range(3):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < 2:
                time.sleep(4 + random.random() * 2)
            else:
                return None


# ==================== 工具函数 ====================

def get_realtime_quote(query: str) -> str:
    """
    获取A股最新行情。输入: 股票代码(如"600519")或部分名称。
    数据源: 东方财富个股信息 + Sina 日线最新一条。
    """
    print(f"  [查询实时行情] {query}")
    symbol = _resolve_symbol(query)

    # 使用 Sina 日线获取最新价格
    try:
        sina_code = _to_sina_code(symbol)
        df = _safe_fetch(ak.stock_zh_a_daily,
                         symbol=sina_code,
                         start_date=(datetime.now() - timedelta(days=10)).strftime("%Y%m%d"),
                         end_date=datetime.now().strftime("%Y%m%d"),
                         adjust="qfq")
        if df is None or df.empty:
            df = _safe_fetch(ak.stock_zh_a_hist, symbol=symbol, period="daily", start_date=(datetime.now() - timedelta(days=10)).strftime("%Y%m%d"), end_date=datetime.now().strftime("%Y%m%d"), adjust="qfq")

        if df is None or df.empty:
            return f"未找到 {symbol} 的行情数据"

        if df is not None and not df.empty:
            # 统一列名为英文以适配下游逻辑
            rename_map = {
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume", "成交额": "amount"
            }
            df = df.rename(columns=rename_map)
    except Exception as e:
        return f"获取行情失败: {e}"

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    # 尝试获取个股信息（名称、PE等）
    name = symbol
    pe = "N/A"
    try:
        time.sleep(2)
        info = ak.stock_individual_info_em(symbol=symbol)
        name_row = info[info["item"] == "股票简称"]
        if not name_row.empty:
            name = name_row["value"].values[0]
        pe_row = info[info["item"] == "市盈率-动态"]
        if not pe_row.empty:
            pe = pe_row["value"].values[0]
    except Exception:
        pass

    chg_pct = (latest["close"] - prev["close"]) / prev["close"] * 100

    return (
        f"{name}({symbol})\n"
        f"  最新价: {latest['close']:.2f}  涨跌幅: {chg_pct:+.2f}%\n"
        f"  今开: {latest['open']:.2f}  最高: {latest['high']:.2f}  最低: {latest['low']:.2f}\n"
        f"  成交量: {latest.get('volume', 'N/A')}手  成交额: {latest.get('amount', 'N/A')}元\n"
        f"  市盈率(动态): {pe}"
    )


def get_historical_data(query: str) -> str:
    """
    获取历史K线数据。输入格式: "symbol|period|days"
    period: daily/weekly/monthly(日/周/月), days: 最近多少个周期(默认60)
    示例: "600519|daily|30"
    数据源: Sina
    """
    print(f"  [查询历史数据] {query}")

    parts = query.strip().split("|")
    symbol = _resolve_symbol(parts[0].strip())
    period = parts[1].strip() if len(parts) > 1 else "daily"
    try:
        days = int(parts[2]) if len(parts) > 2 else 60
    except ValueError:
        days = 60

    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=days * 30)).strftime("%Y%m%d") if period != "daily" else (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

    try:
        sina_code = _to_sina_code(symbol)
        period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
        ak_period = period_map.get(period, "daily")
        hist = _safe_fetch(ak.stock_zh_a_hist,
                           symbol=symbol, period=ak_period, start_date=start,
                           end_date=end, adjust="qfq")
        if hist is None or hist.empty:
            hist = _safe_fetch(ak.stock_zh_a_daily,
                           symbol=sina_code, start_date=start,
                           end_date=end, adjust="qfq")
        if hist is None or hist.empty:
            # 尝试 Tencent 源
            time.sleep(2)
            hist = ak.stock_zh_a_hist_tx(symbol=sina_code,
                                         start_date=start, end_date=end)
            if hist is None or hist.empty:
                return f"未找到 {symbol} 的历史数据"
            # Tencent 列名映射
            hist = hist.rename(columns={
                "date": "date", "open": "open", "close": "close",
                "high": "high", "low": "low", "amount": "volume"
            })
        elif hist is not None and not hist.empty:
            # 统一列名为英文以适配下游逻辑
            rename_map = {
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume", "成交额": "amount"
            }
            hist = hist.rename(columns=rename_map)
    except Exception as e:
        return f"获取历史数据失败: {e}"

    if hist is None or hist.empty:
        return f"未找到 {symbol} 的历史数据"

    hist = hist.tail(days)
    latest = hist.iloc[-1]
    first = hist.iloc[0]
    change = (latest["close"] - first["close"]) / first["close"] * 100
    date_col = "date" if "date" in hist.columns else hist.columns[0]
    close_col = "close"

    lines = [f"{symbol} daily K线 (近{len(hist)}条, {hist.iloc[0][date_col]} ~ {hist.iloc[-1][date_col]})"]
    lines.append(f"  区间涨跌: {change:.2f}%")
    lines.append(f"  最新: O={latest['open']:.2f} H={latest['high']:.2f} L={latest['low']:.2f} C={latest[close_col]:.2f}")
    lines.append(f"  区间最高: {hist['high'].max():.2f}  区间最低: {hist['low'].min():.2f}")
    closes = [f"{x:.2f}" for x in hist[close_col].tail(5).tolist()]
    lines.append(f"  近5日收盘: {' -> '.join(closes)}")

    return "\n".join(lines)


def get_financial_data(symbol: str) -> str:
    """
    获取核心财务指标。输入: 股票代码(如"600519")
    数据源: akshare stock_financial_abstract (Sina)
    返回: 净利润、营收、ROE、毛利率、增长率等关键指标。
    """
    print(f"  [查询财务数据] {symbol}")
    symbol = symbol.strip()

    try:
        df = _safe_fetch(ak.stock_financial_abstract, symbol=symbol)
        if df is None or df.empty:
            return f"未找到 {symbol} 的财务数据"
    except Exception as e:
        return f"获取财务数据失败: {e}"

    # 取最近两期季度数据列
    date_cols = [c for c in df.columns if c.isdigit() and len(c) == 8]
    if len(date_cols) < 2:
        return f"{symbol} 财务数据不足"
    latest_col = date_cols[0]
    prev_col = date_cols[1]

    lines = [f"{symbol} 核心财务数据 (最新: {latest_col} vs 上期: {prev_col})"]

    # 关键指标映射
    key_metrics = [
        ("归母净利润", "归母净利润", "元"),
        ("营业总收入", "营业总收入", "元"),
        ("净利润", "净利润", "元"),
        ("扣非净利润", "扣非净利润", "元"),
        ("基本每股收益", "基本每股收益", "元"),
        ("每股净资产", "每股净资产", "元"),
        ("净资产收益率", "净资产收益率", "%"),
        ("总资产收益率", "总资产收益率", "%"),
        ("销售毛利率", "销售毛利率", "%"),
        ("销售净利率", "销售净利率", "%"),
        ("营收同比增长", "营业总收入同比增长", "%"),
        ("归母净利润同比增长", "归属母公司股东的净利润同比增长", "%"),
        ("资产负债率", "资产负债率", "%"),
        ("流动比率", "流动比率", ""),
        ("速动比率", "速动比率", ""),
    ]

    for label, metric_name, unit in key_metrics:
        row = df[df["指标"] == metric_name]
        if row.empty:
            continue
        val = row[latest_col].values[0]
        prev_val = row[prev_col].values[0] if prev_col in row.columns else None

        if pd.isna(val):
            continue

        try:
            if unit == "元" and abs(float(val)) > 1e8:
                val_str = f"{float(val)/1e8:.2f}亿"
                if prev_val is not None and not pd.isna(prev_val) and abs(float(prev_val)) > 1e8:
                    prev_str = f"{float(prev_val)/1e8:.2f}亿"
                else:
                    prev_str = None
            elif unit == "%":
                val_str = f"{float(val):.2f}%"
                prev_str = f"{float(prev_val):.2f}%" if prev_val is not None and not pd.isna(prev_val) else None
            else:
                val_str = f"{float(val):.4f}"
                prev_str = f"{float(prev_val):.4f}" if prev_val is not None and not pd.isna(prev_val) else None
        except (ValueError, TypeError):
            val_str = str(val)
            prev_str = str(prev_val) if prev_val is not None else None

        line = f"  {label}: {val_str}"
        if prev_str:
            try:
                trend = "[+]" if float(val) > float(prev_val) else "[-]"
                line += f" {trend} (上期: {prev_str})"
            except (ValueError, TypeError):
                line += f" (上期: {prev_str})"
        lines.append(line)

    return "\n".join(lines)


def calc_indicators(query: str) -> str:
    """
    计算技术指标。输入格式: "symbol|daily|days"
    返回: MA5/10/20/60, MACD(DIF/DEA/柱), RSI14, 布林带, 支撑压力位。
    数据源: Sina
    """
    print(f"  [计算技术指标] {query}")

    parts = query.strip().split("|")
    symbol = parts[0].strip()
    try:
        days = min(int(parts[2]), 365) if len(parts) > 2 else 120
    except ValueError:
        days = 120

    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

    try:
        sina_code = _to_sina_code(symbol)
        df = _safe_fetch(ak.stock_zh_a_daily,
                         symbol=sina_code, start_date=start,
                         end_date=end, adjust="qfq")
        if df is None or df.empty:
            # 尝试新版 API fallback
            df = _safe_fetch(ak.stock_zh_a_hist, symbol=symbol, period="daily", start_date=start, end_date=end, adjust="qfq")

        if df is None or df.empty:
            return f"未找到 {symbol} 的数据"

        if df is not None and not df.empty:
            # 统一列名为英文以适配下游逻辑
            rename_map = {
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume", "成交额": "amount"
            }
            df = df.rename(columns=rename_map)
    except Exception as e:
        return f"获取数据失败: {e}"

    df = df.tail(days).reset_index(drop=True)
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    latest_close = close.iloc[-1]

    lines = [f"{symbol} 技术指标分析 (基于近{len(df)}条日K线)"]
    lines.append(f"  最新收盘价: {latest_close:.2f}")
    lines.append("")

    # --- 移动均线 ---
    lines.append("--- 移动均线 ---")
    ma_signals = []
    for ma in [5, 10, 20, 60]:
        if len(close) >= ma:
            ma_val = close.rolling(window=ma).mean().iloc[-1]
            relation = "[+]多头" if latest_close > ma_val else "[-]空头"
            lines.append(f"  MA{ma:>2}: {ma_val:.2f}  ({relation})")
            ma_signals.append(latest_close > ma_val)
    if ma_signals:
        bullish = sum(ma_signals)
        lines.append(f"  均线综合: {bullish}/{len(ma_signals)} 条支撑  "
                      f"({'偏多' if bullish >= 3 else '偏空' if bullish <= 1 else '震荡'})")

    # --- MACD ---
    lines.append("")
    lines.append("--- MACD (12,26,9) ---")
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9).mean()
    macd_bar = 2 * (dif - dea)

    lines.append(f"  DIF: {dif.iloc[-1]:.3f}  DEA: {dea.iloc[-1]:.3f}")
    bar_color = "红柱" if macd_bar.iloc[-1] > 0 else "绿柱"
    lines.append(f"  MACD柱: {macd_bar.iloc[-1]:.3f}  ({bar_color})")

    if len(dif) >= 2:
        if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]:
            lines.append("  [!] 信号: 金叉(买入信号)")
        elif dif.iloc[-1] < dea.iloc[-1] and dif.iloc[-2] >= dea.iloc[-2]:
            lines.append("  [!] 信号: 死叉(卖出信号)")
        else:
            trend = "多头" if dif.iloc[-1] > dea.iloc[-1] else "空头"
            lines.append(f"  趋势: {trend}持续")
    else:
        trend = "多头" if dif.iloc[-1] > dea.iloc[-1] else "空头"
        lines.append(f"  趋势: {trend}持续")

    # --- RSI ---
    lines.append("")
    lines.append("--- RSI (14) ---")
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14).mean()
    avg_loss = loss.ewm(alpha=1/14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi_val = rsi.iloc[-1]

    if rsi_val > 80:
        rsi_status = "严重超买"
    elif rsi_val > 70:
        rsi_status = "超买区域"
    elif rsi_val < 20:
        rsi_status = "严重超卖"
    elif rsi_val < 30:
        rsi_status = "超卖区域"
    else:
        rsi_status = "中性"
    lines.append(f"  RSI: {rsi_val:.1f} ({rsi_status})")

    # --- 布林带 ---
    lines.append("")
    lines.append("--- 布林带 (20,2) ---")
    bb_mid = close.rolling(window=20).mean()
    bb_std = close.rolling(window=20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    lines.append(f"  上轨: {bb_upper.iloc[-1]:.2f}")
    lines.append(f"  中轨: {bb_mid.iloc[-1]:.2f}")
    lines.append(f"  下轨: {bb_lower.iloc[-1]:.2f}")
    bb_pos = (latest_close - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
    if bb_pos > 0.9:
        lines.append(f"  价格位于布林带上沿附近，注意压力")
    elif bb_pos < 0.1:
        lines.append(f"  价格位于布林带下沿附近，关注支撑")
    else:
        lines.append(f"  价格位于布林带中轨附近")

    # --- 支撑/压力位 ---
    lines.append("")
    lines.append("--- 关键价位 ---")
    recent_high = high.tail(20).max()
    recent_low = low.tail(20).min()
    lines.append(f"  近20日最高: {recent_high:.2f} (压力位)")
    lines.append(f"  近20日最低: {recent_low:.2f} (支撑位)")
    if len(close) >= 60:
        ma60 = close.rolling(60).mean().iloc[-1]
        lines.append(f"  MA60: {ma60:.2f} (长期支撑/压力)")

    return "\n".join(lines)


def get_news(symbol: str) -> str:
    """
    获取近期新闻。输入: 股票代码(如"600519")
    返回最新5条新闻标题。
    """
    print(f"  [查询新闻] {symbol}")
    symbol = symbol.strip()

    try:
        news_df = _safe_fetch(ak.stock_news_em, symbol=symbol)
        if news_df is None or news_df.empty:
            return f"未找到 {symbol} 的相关新闻"
    except Exception as e:
        return f"获取新闻失败: {e}"

    recent = news_df.head(5)
    lines = [f"{symbol} 近期新闻:"]
    for i, (_, row) in enumerate(recent.iterrows(), 1):
        title = row.get("新闻标题", "N/A")
        dt = row.get("发布时间", "")
        content = row.get("新闻内容", "")
        summary = content[:80] + "..." if isinstance(content, str) and len(content) > 80 else str(content or "")
        lines.append(f"  {i}. [{dt}] {title}")
        if summary:
            lines.append(f"     {summary}")

    return "\n".join(lines)
