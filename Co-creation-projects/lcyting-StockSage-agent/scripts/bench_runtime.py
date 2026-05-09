"""
本地运行时稳定性 / 时效性自测脚本（不落盘密钥）。

用法（后端已启动在默认端口时）：
  py -3 scripts/bench_runtime.py
"""

from __future__ import annotations

import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
BACKEND = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5173"


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def bench_urls(name: str, urls: list[str], rounds: int, concurrent: int) -> dict:
    """对多个 URL 轮流请求 rounds 轮；每轮并发 concurrent 个线程。"""
    latencies_ms: list[float] = []
    errors = 0

    def one_get(url: str) -> tuple[float, bool]:
        t0 = time.perf_counter()
        try:
            r = httpx.get(url, timeout=120.0)
            ok = r.status_code < 500
            return (time.perf_counter() - t0) * 1000.0, ok
        except Exception:
            return (time.perf_counter() - t0) * 1000.0, False

    with ThreadPoolExecutor(max_workers=max(concurrent, 1)) as ex:
        for _ in range(rounds):
            futs = []
            for _i in range(concurrent):
                url = urls[_ % len(urls)]
                futs.append(ex.submit(one_get, url))
            for fu in as_completed(futs):
                ms, ok = fu.result()
                latencies_ms.append(ms)
                if not ok:
                    errors += 1

    latencies_ms.sort()
    return {
        "name": name,
        "requests": len(latencies_ms),
        "errors": errors,
        "min_ms": min(latencies_ms) if latencies_ms else None,
        "p50_ms": _percentile(latencies_ms, 50),
        "p95_ms": _percentile(latencies_ms, 95),
        "max_ms": max(latencies_ms) if latencies_ms else None,
        "mean_ms": statistics.mean(latencies_ms) if latencies_ms else None,
    }


def main() -> int:
    sys.path  # noqa: satisfy linters if any

    health = f"{BACKEND}/api/v1/system/health"
    config = f"{BACKEND}/api/v1/system/config"
    quote = f"{BACKEND}/api/v1/market/quote/600519"

    print("=== 智能股票分析器 — 运行时压测（本机） ===\n")

    # 1) 纯本地路由：高并发短时稳定性
    r1 = bench_urls(
        "health+config 交错 GET（并发10 × 30轮 = 300次）",
        [health, config],
        rounds=30,
        concurrent=10,
    )

    # 2) 依赖外部 MX 的行情接口：样本较小，看长尾延迟
    r2 = bench_urls(
        "行情 quote/600519（并发3 × 5轮 = 15次，含外部API）",
        [quote],
        rounds=5,
        concurrent=3,
    )

    # 3) 前端 dev server 首页
    r3 = bench_urls(
        "Vite 首页 GET（并发5 × 10轮 = 50次）",
        [FRONTEND + "/"],
        rounds=10,
        concurrent=5,
    )

    def fmt(d: dict) -> None:
        print(f"[{d['name']}]")
        print(f"  请求数={d['requests']} 失败={d['errors']}")
        print(
            f"  延迟 ms: min={d['min_ms']:.2f}  mean={d['mean_ms']:.2f}  "
            f"p50={d['p50_ms']:.2f}  p95={d['p95_ms']:.2f}  max={d['max_ms']:.2f}"
        )
        print()

    fmt(r1)
    fmt(r2)
    fmt(r3)

    if r1["errors"] > 0 or r3["errors"] > 0:
        print("结论: 本地路由或前端出现异常响应，请查看后端/Vite 日志。")
        return 1
    if r2["errors"] > 0:
        print("结论: 行情接口存在失败（可能与 MX 网络或配额有关），本地服务进程仍可用。")
        return 0
    print("结论: 本地进程响应稳定；行情接口本轮全部成功（长尾请看 p95/max）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
