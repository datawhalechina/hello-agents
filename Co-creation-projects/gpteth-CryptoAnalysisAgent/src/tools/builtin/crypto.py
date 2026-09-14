"""Wrap the existing multi-agent analysis pipeline as a chat tool."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from hello_agents.tools import Tool, ToolParameter

from ...compat import first_text, tool_text


class CryptoAnalysisTool(Tool):
    def __init__(self, get_coordinator: Callable[[], Any]):
        super().__init__(
            name="crypto_analysis",
            description=(
                "调用技术/链上/情绪分析师做加密货币分析。"
                "focus=full 并行三维综合分析；也可取 technical / onchain / sentiment。"
            ),
        )
        self._get_coordinator = get_coordinator

    def run(self, parameters: Dict[str, Any]) -> str:
        symbol = first_text(parameters, "symbol", "query")
        focus = str(parameters.get("focus") or "full").strip().lower() or "full"
        if not symbol:
            return "错误: 请提供 symbol，例如 BTC"
        if "分析" in symbol or "行情" in symbol:
            query = symbol
        elif focus == "technical":
            query = f"只从技术面分析 {symbol}"
        elif focus == "onchain":
            query = f"只从链上面分析 {symbol}"
        elif focus == "sentiment":
            query = f"只从情绪面分析 {symbol}"
        else:
            query = f"分析 {symbol} 当前的市场状况，给出条件化建议"
        try:
            coordinator = self._get_coordinator()
            return tool_text(coordinator.run(query))
        except Exception as exc:
            return f"分析失败: {exc}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="symbol", type="string", description="币种，如 BTC、ETH、SOL", required=True),
            ToolParameter(
                name="focus",
                type="string",
                description="full / technical / onchain / sentiment，默认 full",
                required=False,
            ),
        ]
