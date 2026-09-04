"""
信号留痕与历史胜率统计

商业化的第一块基石: 可验证的效果记录。
每次分析自动归档 (币种、方向判断、当时价格、报告摘要)，
到期后用真实历史价格核算信号对错，输出可对外展示的胜率统计。

存储: JSONL 追加写 (outputs/signals.jsonl)，每行一条信号:
{
  "id": "...", "ts": 1718000000.0, "symbol": "BTC",
  "bias": "看多", "price_at_signal": 67200.0,
  "report_excerpt": "...",
  "outcomes": {"24h": {"price": ..., "return_pct": ..., "hit": true}, ...}
}
"""

import json
import os
import re
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

DEFAULT_LEDGER = "outputs/signals.jsonl"

# 核算周期: 信号发出后多久检验一次
HORIZONS = {"24h": 24 * 3600, "7d": 7 * 24 * 3600}

# 中性信号的"判对"标准: 周期内涨跌幅不超过该阈值
NEUTRAL_BAND_PCT = 3.0

_BIAS_RE = re.compile(r"整体偏向\s*[:：]?\s*\**\s*(看多|看空|中性)")


def extract_bias(report: str) -> Optional[str]:
    """从综合报告中提取方向判断 (优先匹配模板字段，其次统计词频)"""
    match = _BIAS_RE.search(report)
    if match:
        return match.group(1)
    bull, bear = report.count("看多"), report.count("看空")
    if bull > bear:
        return "看多"
    if bear > bull:
        return "看空"
    return "中性" if ("中性" in report or bull) else None


def record_signal(symbol: str, report: str,
                  ledger_path: str = DEFAULT_LEDGER,
                  price: Optional[float] = None,
                  bias: Optional[str] = None,
                  now: Optional[float] = None) -> Dict[str, Any]:
    """
    归档一条分析信号。

    Args:
        symbol: 币种，如 BTC
        report: 综合分析报告全文
        price: 信号时刻价格 (不传则实时查询)
        bias: 方向判断 (不传则从报告自动提取)
        now: 时间戳 (测试用)
    """
    symbol = symbol.upper().replace("USDT", "")
    if bias is None:
        bias = extract_bias(report) or "中性"
    if price is None:
        from ..tools.market_data import get_ticker_24h
        price = float(get_ticker_24h(symbol)["lastPrice"])

    entry = {
        "id": uuid.uuid4().hex[:12],
        "ts": now if now is not None else time.time(),
        "symbol": symbol,
        "bias": bias,
        "price_at_signal": price,
        "report_excerpt": report.strip()[:300],
        "outcomes": {},
    }
    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _load(ledger_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(ledger_path):
        return []
    entries = []
    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _save(entries: List[Dict[str, Any]], ledger_path: str) -> None:
    tmp = ledger_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.replace(tmp, ledger_path)


def _judge(bias: str, return_pct: float) -> bool:
    if bias == "看多":
        return return_pct > 0
    if bias == "看空":
        return return_pct < 0
    return abs(return_pct) <= NEUTRAL_BAND_PCT


def update_outcomes(ledger_path: str = DEFAULT_LEDGER,
                    price_fn: Optional[Callable[[str, float], Optional[float]]] = None,
                    now: Optional[float] = None) -> int:
    """
    核算所有到期且未核算的信号，回写结果。返回本次新核算的条数。

    Args:
        price_fn: (symbol, timestamp) -> price，默认用 Binance 历史 K 线
    """
    if price_fn is None:
        from ..tools.market_data import get_price_at
        price_fn = get_price_at
    current_time = now if now is not None else time.time()

    entries = _load(ledger_path)
    updated = 0
    for entry in entries:
        for horizon, seconds in HORIZONS.items():
            if horizon in entry["outcomes"]:
                continue
            due_at = entry["ts"] + seconds
            if current_time < due_at:
                continue
            price = price_fn(entry["symbol"], due_at)
            if price is None:
                continue
            return_pct = (price - entry["price_at_signal"]) / entry["price_at_signal"] * 100
            entry["outcomes"][horizon] = {
                "price": price,
                "return_pct": round(return_pct, 2),
                "hit": _judge(entry["bias"], return_pct),
            }
            updated += 1

    if updated:
        _save(entries, ledger_path)
    return updated


def summarize(ledger_path: str = DEFAULT_LEDGER) -> Dict[str, Any]:
    """统计各周期/各币种的信号胜率 (可对外展示的 track record)"""
    entries = _load(ledger_path)
    stats: Dict[str, Any] = {
        "total_signals": len(entries),
        "by_horizon": {},
        "by_symbol": {},
    }
    for horizon in HORIZONS:
        judged = [e["outcomes"][horizon] for e in entries if horizon in e["outcomes"]]
        if not judged:
            continue
        hits = sum(1 for o in judged if o["hit"])
        stats["by_horizon"][horizon] = {
            "judged": len(judged),
            "hits": hits,
            "win_rate": round(hits / len(judged), 3),
            "avg_return_pct": round(sum(o["return_pct"] for o in judged) / len(judged), 2),
        }
    for e in entries:
        s = stats["by_symbol"].setdefault(
            e["symbol"], {"signals": 0, "judged": 0, "hits": 0})
        s["signals"] += 1
        for o in e["outcomes"].values():
            s["judged"] += 1
            s["hits"] += 1 if o["hit"] else 0
    for s in stats["by_symbol"].values():
        s["win_rate"] = round(s["hits"] / s["judged"], 3) if s["judged"] else None
    return stats


def format_summary(stats: Dict[str, Any]) -> str:
    """渲染胜率统计为 Markdown"""
    lines = ["## 信号历史表现", "", f"- 累计信号: {stats['total_signals']} 条"]
    for horizon, s in stats["by_horizon"].items():
        lines.append(
            f"- {horizon} 胜率: {s['win_rate']:.0%} "
            f"({s['hits']}/{s['judged']}), 平均涨跌 {s['avg_return_pct']:+.2f}%"
        )
    if stats["by_symbol"]:
        lines.append("")
        lines.append("| 币种 | 信号数 | 已核算 | 胜率 |")
        lines.append("|---|---|---|---|")
        for sym, s in sorted(stats["by_symbol"].items()):
            rate = f"{s['win_rate']:.0%}" if s["win_rate"] is not None else "-"
            lines.append(f"| {sym} | {s['signals']} | {s['judged']} | {rate} |")
    if not stats["by_horizon"]:
        lines.append("- 暂无已到期的信号 (24h 后运行 update_outcomes() 核算)")
    return "\n".join(lines)
