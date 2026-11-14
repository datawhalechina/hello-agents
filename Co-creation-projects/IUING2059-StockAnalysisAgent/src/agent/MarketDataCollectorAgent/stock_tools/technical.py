# stock_tools/technical.py
import os
from datetime import datetime, timedelta

import akshare as ak
import pandas as pd

from ..schemas import TechnicalIndicatorSchema


def _fetch_hist_data(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """尝试不同的数据源获取历史K线，规避单一接口的风控。"""
    df = pd.DataFrame()

    # 1. 尝试东方财富
    try:
        df = ak.stock_zh_a_hist(
            symbol=stock_code, period="daily",
            start_date=start_date, end_date=end_date, adjust="qfq"
        )
    except Exception as e:
        print(f"[Warning] 东财历史数据获取失败，尝试腾讯接口: {e}")

    # 2. 尝试腾讯 (如果东财没拿到数据)
    if df.empty:
        try:
            prefix = "sh" if stock_code.startswith(("6", "5")) else "sz"
            tx_symbol = f"{prefix}{stock_code}"
            df = ak.stock_zh_a_hist_tx(
                symbol=tx_symbol,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            if not df.empty:
                # 【修复】腾讯的 amount 通常是成交额，vol/volume 是成交量
                df = df.rename(columns={
                    "date": "日期", "open": "开盘", "close": "收盘",
                    "high": "最高", "low": "最低", "amount": "成交额",
                    "vol": "成交量", "volume": "成交量"
                })
                if "成交量" not in df.columns:
                    df["成交量"] = 0.0
        except Exception as e:
            print(f"[Warning] 腾讯历史数据获取失败: {e}")

    # 3. 尝试新浪 (如果前面都没拿到数据)
    if df.empty:
        try:
            prefix = "sh" if stock_code.startswith(("6", "5")) else "sz"
            sz_symbol = f"{prefix}{stock_code}"
            df = ak.stock_zh_a_daily(symbol=sz_symbol, adjust="qfq")
            if not df.empty:
                df = df.rename(columns={
                    "date": "日期", "open": "开盘", "close": "收盘",
                    "high": "最高", "low": "最低", "volume": "成交量"
                })
                if "成交量" not in df.columns:
                    df["成交量"] = 0.0
                # 过滤日期范围
                df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
                start_fmt = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
                df = df[df["日期"] >= start_fmt]
        except Exception as e:
            print(f"[Warning] 新浪历史数据获取失败: {e}")

    # ================= 核心修复：统一日期格式 =================
    # 无论数据来自哪个接口，一律把“日期”列转为标准的 YYYY-MM-DD 字符串
    if not df.empty and "日期" in df.columns:
        df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
    # ==========================================================

    return df


def get_cached_kline(stock_code: str) -> pd.DataFrame:
    cache_dir = "./stock_data_cache"
    os.makedirs(cache_dir, exist_ok=True)
    file_path = os.path.join(cache_dir, f"{stock_code}_kline.csv")

    today_str = datetime.today().strftime("%Y-%m-%d")
    need_update = True

    if os.path.exists(file_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d")
        if mtime == today_str:
            need_update = False

    if need_update:
        end = datetime.today().strftime("%Y%m%d")
        start = (datetime.today() - timedelta(days=30)).strftime("%Y%m%d") if os.path.exists(file_path) else (
                datetime.today() - timedelta(days=365)).strftime("%Y%m%d")

        new_df = _fetch_hist_data(stock_code, start, end)

        if not new_df.empty:
            if os.path.exists(file_path):
                old_df = pd.read_csv(file_path)
                old_df = old_df.loc[:, ~old_df.columns.str.contains('^Unnamed')]

                # 【修复】读取旧数据后，强制确保旧数据的日期也是字符串，防止旧文件里有脏数据
                old_df["日期"] = pd.to_datetime(old_df["日期"]).dt.strftime("%Y-%m-%d")

                df = pd.concat([old_df, new_df], ignore_index=True)
                df = df.drop_duplicates(subset=["日期"], keep="last").sort_values("日期").reset_index(drop=True)
            else:
                df = new_df
            df.to_csv(file_path, index=False)
        else:
            if not os.path.exists(file_path):
                raise ValueError(f"所有数据源均无法获取 {stock_code} 的历史数据，且本地无缓存。")
            print(f"[Warning] 更新失败，使用本地旧缓存: {stock_code}")

    df = pd.read_csv(file_path)
    # 【修复】最终兜底：确保返回给指标计算的数据，日期绝对是字符串
    df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
    return df.sort_values("日期").reset_index(drop=True)


def fetch_technical(stock_code: str) -> TechnicalIndicatorSchema:
    result = TechnicalIndicatorSchema()
    df = get_cached_kline(stock_code)

    if len(df) < 30:
        return result

    close = pd.to_numeric(df["收盘"], errors="coerce")
    high = pd.to_numeric(df["最高"], errors="coerce")
    low = pd.to_numeric(df["最低"], errors="coerce")
    # 容错处理：如果没有成交量列，默认填 0
    volume = pd.to_numeric(df.get("成交量", 0), errors="coerce").fillna(0)

    if len(close) >= 20:
        result.ma20 = float(close.rolling(20).mean().iloc[-1])
    if len(close) >= 60:
        result.ma60 = float(close.rolling(60).mean().iloc[-1])

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    result.macd_dif = float(dif.iloc[-1])
    result.macd_dea = float(dea.iloc[-1])
    result.macd_bar = float(2 * (dif.iloc[-1] - dea.iloc[-1]))

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, float("nan"))
    result.rsi_14 = float((100 - 100 / (1 + rs)).iloc[-1])

    low9 = low.rolling(9).min()
    high9 = high.rolling(9).max()
    rsv = (close - low9) / (high9 - low9).replace(0, float("nan")) * 100
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    result.kdj_k = float(k.iloc[-1])
    result.kdj_d = float(d.iloc[-1])
    result.kdj_j = float(3 * k.iloc[-1] - 2 * d.iloc[-1])

    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    result.boll_mid = float(mid.iloc[-1])
    result.boll_upper = float((mid + 2 * std).iloc[-1])
    result.boll_lower = float((mid - 2 * std).iloc[-1])

    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    result.obv = float((volume * direction).cumsum().iloc[-1])

    return result