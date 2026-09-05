# backend/data/sources/stock_list.py
import csv
from collections import defaultdict
from pathlib import Path
from typing import Optional

from pypinyin import lazy_pinyin, Style

# 项目根目录（stock-agent/）：backend/data/sources/stock_list.py → 上溯 3 级
_PROJECT_ROOT = Path(__file__).resolve().parents[3]

_CSV_PATHS = {
    "A股": _PROJECT_ROOT / "A-stock.csv",
    "港股": _PROJECT_ROOT / "G-stock.csv",
    "美股": _PROJECT_ROOT / "U-stock.csv",
}

_stocks_by_market: dict[str, list[dict]] = {"A股": [], "港股": [], "美股": []}
# 倒排索引：键统一小写，值为 (market_index, stock_index) 列表
_index_by_market: dict[str, dict[str, list[int]]] = {
    "A股": defaultdict(list),
    "港股": defaultdict(list),
    "美股": defaultdict(list),
}
_loaded = False


def _pinyin_keys(name: str) -> tuple[str, str]:
    """返回 (全拼, 首字母拼) — 输入纯英文时返回 ('', '')"""
    if not any("一" <= c <= "鿿" for c in name):
        return "", ""
    full = "".join(lazy_pinyin(name, style=Style.NORMAL))
    initials = "".join(lazy_pinyin(name, style=Style.FIRST_LETTER))
    return full.lower(), initials.lower()


def _add_to_index(market: str, idx: int, *keys: str) -> None:
    bucket = _index_by_market[market]
    for k in keys:
        if k:
            bucket[k.lower()].append(idx)


def _load_a_share(path: Path) -> list[dict]:
    """A-stock.csv 列：dm（如 000001.SZ）, mc, jys"""
    result = []
    with path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            dm = (row.get("dm") or "").strip()
            name = (row.get("mc") or "").strip().replace(" ", "")
            if not dm or not name:
                continue
            symbol = dm.split(".")[0]  # 600519.SH → 600519
            if not (symbol.isdigit() and len(symbol) == 6):
                continue
            result.append({"symbol": symbol, "name": name})
    return result


def _load_hk(path: Path) -> list[dict]:
    """G-stock.csv 列：股票代码（5位）, 股票简称"""
    result = []
    with path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            symbol = (row.get("股票代码") or "").strip()
            name = (row.get("股票简称") or "").strip()
            if not symbol or not name:
                continue
            symbol = symbol.zfill(5)  # 港股统一 5 位
            result.append({"symbol": symbol, "name": name})
    return result


def _load_us(path: Path) -> list[dict]:
    """U-stock.csv 列：股票代码, 股票名称"""
    result = []
    with path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            symbol = (row.get("股票代码") or "").strip().upper()
            name = (row.get("股票名称") or "").strip()
            if not symbol or not name:
                continue
            if any(c in symbol for c in [" ", "(", ")", "/"]):
                continue
            result.append({"symbol": symbol, "name": name})
    return result


def _build_index(market: str, stocks: list[dict]) -> None:
    bucket = _index_by_market[market]
    bucket.clear()
    for idx, s in enumerate(stocks):
        full, initials = _pinyin_keys(s["name"])
        _add_to_index(market, idx, s["symbol"], s["name"], full, initials)


def load_stock_list() -> None:
    """同步加载三市股票列表 + 构建索引。冷启动 < 1s。"""
    global _loaded
    if _loaded:
        return

    loaders = {
        "A股": _load_a_share,
        "港股": _load_hk,
        "美股": _load_us,
    }

    for market, loader in loaders.items():
        path = _CSV_PATHS[market]
        if not path.exists():
            print(f"[WARN] {market} CSV 不存在: {path}")
            _stocks_by_market[market] = []
            continue
        try:
            stocks = loader(path)
            _stocks_by_market[market] = stocks
            _build_index(market, stocks)
            print(f"[OK] {market} 加载 {len(stocks)} 只")
        except Exception as e:
            print(f"[ERR] {market} 加载失败: {e}")
            _stocks_by_market[market] = []

    _loaded = True


async def ensure_stock_list() -> None:
    """异步入口，保持与原接口兼容。当前实现是同步加载（CSV 很快）。"""
    load_stock_list()


def _score(symbol: str, name: str, kw: str, kw_lower: str, kw_upper: str,
           full_pinyin: str, initials: str) -> Optional[int]:
    if symbol == kw_upper or symbol == kw:
        return 0
    if name == kw:
        return 1
    if symbol.startswith(kw_upper):
        return 2
    if name.startswith(kw):
        return 3
    if initials and initials.startswith(kw_lower):
        return 4
    if full_pinyin and full_pinyin.startswith(kw_lower):
        return 5
    if kw in name or kw_lower in name.lower():
        return 6
    if kw_upper in symbol:
        return 7
    if initials and kw_lower in initials:
        return 8
    if full_pinyin and kw_lower in full_pinyin:
        return 9
    return None


def search_stocks(
    keyword: str,
    market: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """支持代码 / 中文名 / 拼音首字母 / 全拼 多路匹配"""
    if not _loaded:
        load_stock_list()

    keyword = keyword.strip()
    if not keyword:
        return []

    kw_lower = keyword.lower()
    kw_upper = keyword.upper()

    target_markets = [market] if market in _stocks_by_market else list(_stocks_by_market.keys())

    # 用倒排索引快速收集候选
    candidates: dict[tuple[str, int], None] = {}
    for mkt in target_markets:
        bucket = _index_by_market[mkt]
        for key in bucket:
            if kw_lower in key or kw_upper in key.upper():
                for idx in bucket[key]:
                    candidates[(mkt, idx)] = None

    scored: list[tuple[int, dict]] = []
    for (mkt, idx) in candidates:
        s = _stocks_by_market[mkt][idx]
        full, initials = _pinyin_keys(s["name"])
        p = _score(s["symbol"], s["name"], keyword, kw_lower, kw_upper, full, initials)
        if p is not None:
            scored.append((p, {**s, "market": mkt}))

    scored.sort(key=lambda x: (x[0], len(x[1]["symbol"])))

    seen = set()
    unique = []
    for _, item in scored:
        key = (item["market"], item["symbol"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
        if len(unique) >= limit:
            break
    return unique


def resolve_symbol(keyword: str, market: str) -> str:
    """名称/关键词 → 股票代码"""
    keyword = keyword.strip()
    if market == "A股" and keyword.isdigit() and len(keyword) == 6:
        return keyword
    if market == "港股" and keyword.isdigit() and 1 <= len(keyword) <= 5:
        return keyword.zfill(5)
    if market == "美股" and keyword.isascii() and keyword.replace("-", "").replace(".", "").isalpha() and len(keyword) <= 6:
        return keyword.upper()

    results = search_stocks(keyword, market=market, limit=1)
    if results:
        return results[0]["symbol"]
    return keyword
