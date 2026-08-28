"""
性能埋点: 端到端延迟、工具调用次数、HTTP 请求与缓存命中统计

对应考核指标:
- 端到端延迟 (Response Time)
- 步数效率 (一轮分析触发了多少次工具调用)
- 工具调用效率 (HTTP 请求数 / 缓存命中率，由 market_data 模块统计)
"""

import threading
import time
from typing import Any, Dict, List, Tuple

from ..tools import market_data


class ToolCallCounter:
    """工具调用计数器 - 给工具实例打补丁，统计调用次数并记录原始返回

    记录的 outputs 可直接传给 report_checks.check_grounding 做数字溯源。
    """

    def __init__(self):
        self.counts: Dict[str, int] = {}
        self.outputs: List[str] = []
        self._lock = threading.Lock()  # 子 Agent 并行执行时从多线程调用

    def instrument(self, *tools) -> None:
        """包装工具的 run 方法以计数 (对同一实例重复调用是幂等的)"""
        for tool in tools:
            if getattr(tool, "_telemetry_instrumented", False):
                continue
            original_run = tool.run

            def wrapper(parameters, _name=tool.name, _run=original_run):
                with self._lock:
                    self.counts[_name] = self.counts.get(_name, 0) + 1
                result = _run(parameters)
                if isinstance(result, str):
                    with self._lock:
                        self.outputs.append(result)
                return result

            tool.run = wrapper
            tool._telemetry_instrumented = True

    def reset(self) -> None:
        with self._lock:
            self.counts.clear()
            self.outputs.clear()

    @property
    def total_calls(self) -> int:
        return sum(self.counts.values())


def timed_run(agent, query: str) -> Tuple[str, Dict[str, Any]]:
    """
    运行 Agent 并采集性能指标。

    Returns:
        (agent输出, 指标字典)，指标包含:
        - elapsed_seconds: 端到端耗时
        - http_requests: 本次运行发出的真实 HTTP 请求数
        - cache_hits: 缓存命中数
        - cache_hit_rate: 命中率
    """
    before = market_data.get_stats()
    start = time.perf_counter()
    result = agent.run(query)
    elapsed = time.perf_counter() - start
    after = market_data.get_stats()

    requests_made = after["http_requests"] - before["http_requests"]
    hits = after["cache_hits"] - before["cache_hits"]
    total = requests_made + hits
    metrics = {
        "elapsed_seconds": round(elapsed, 2),
        "http_requests": requests_made,
        "cache_hits": hits,
        "cache_hit_rate": round(hits / total, 3) if total else 0.0,
    }
    return result, metrics


def format_metrics(metrics: Dict[str, Any],
                   counter: ToolCallCounter = None) -> str:
    """将性能指标渲染为可读摘要"""
    lines = [
        "## 性能指标",
        f"- 端到端耗时: {metrics['elapsed_seconds']:.1f}s",
        f"- HTTP 请求数: {metrics['http_requests']}",
        f"- 缓存命中: {metrics['cache_hits']} (命中率 {metrics['cache_hit_rate']:.0%})",
    ]
    if counter and counter.counts:
        lines.append(f"- 工具调用总数: {counter.total_calls}")
        for name, n in sorted(counter.counts.items(), key=lambda x: -x[1]):
            lines.append(f"  - {name}: {n} 次")
    return "\n".join(lines)
