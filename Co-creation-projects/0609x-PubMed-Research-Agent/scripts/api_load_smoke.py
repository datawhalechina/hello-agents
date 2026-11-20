"""Run a small concurrent HTTP smoke test against a deployed API endpoint."""

from __future__ import annotations

import argparse
import asyncio
import math
import statistics
import sys
from time import perf_counter

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--path", default="/api/v1/health/live")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--p95-budget-ms", type=float, default=500.0)
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1:
        parser.error("--requests and --concurrency must be positive")
    return args


async def run(args: argparse.Namespace) -> int:
    url = f"{args.base_url.rstrip('/')}/{args.path.lstrip('/')}"
    semaphore = asyncio.Semaphore(args.concurrency)
    latencies_ms: list[float] = []
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=args.timeout) as client:
        try:
            for _ in range(min(3, args.requests)):
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            print(f"FAIL {url}: warm-up request failed ({type(exc).__name__})")
            return 1

        async def request_once() -> None:
            async with semaphore:
                started = perf_counter()
                try:
                    response = await client.get(url)
                    elapsed_ms = (perf_counter() - started) * 1000
                    if response.is_success:
                        latencies_ms.append(elapsed_ms)
                    else:
                        errors.append(f"HTTP {response.status_code}")
                except httpx.HTTPError as exc:
                    errors.append(type(exc).__name__)

        started = perf_counter()
        await asyncio.gather(*(request_once() for _ in range(args.requests)))
        duration = perf_counter() - started

    if not latencies_ms:
        print(f"FAIL {url}: all {args.requests} requests failed")
        return 1

    ordered = sorted(latencies_ms)
    p50 = statistics.median(ordered)
    p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    p95 = ordered[p95_index]
    rate = len(latencies_ms) / duration if duration else float("inf")
    passed = not errors and p95 <= args.p95_budget_ms

    print(
        f"{'PASS' if passed else 'FAIL'} {url} | "
        f"ok={len(latencies_ms)} errors={len(errors)} "
        f"p50={p50:.1f}ms p95={p95:.1f}ms rate={rate:.1f}req/s"
    )
    if errors:
        print(f"errors: {', '.join(errors[:5])}")
    if p95 > args.p95_budget_ms:
        print(f"p95 budget exceeded: {p95:.1f}ms > {args.p95_budget_ms:.1f}ms")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run(parse_args())))
