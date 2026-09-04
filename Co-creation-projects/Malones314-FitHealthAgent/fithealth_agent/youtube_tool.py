"""youtube_tool.py — YouTubeSearchTool：hello_agents 原生工具包装

将 ``fithealth_agent.youtube_search`` 中的搜索逻辑包装为符合
``hello_agents.tools.Tool`` 接口的工具类，直接注册到 Agent 的
``ToolRegistry``，**完全不依赖 MCPTool 或任何框架扩展**。

设计说明：
    - ``run()`` 返回 ``str``，与 hello_agents 1.0.0 的 Tool 基类签名一致。
    - 所有外部异常由 ``youtube_search.search_videos()`` 内部捕获并
      序列化到返回 JSON 中，本层不会抛出裸异常。
    - ``get_parameters()`` 严格遵循 ``ToolParameter`` 规范，确保
      ``to_openai_schema()`` 能生成正确的 function-calling schema。
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from typing import Any

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse

from .youtube_search import _normalise_channel, channel_names_match, search_videos

logger = logging.getLogger(__name__)


class YouTubeSearchTool(Tool):
    """在 YouTube 上搜索健身动作教学视频。

    Agent 在推荐具体健身动作或用户询问动作执行方式时，应调用此工具
    获取官方教学视频链接，帮助用户掌握正确动作，预防运动损伤。

    Attributes:
        name:        工具名称，固定为 ``"search_youtube_video"``。
        description: 工具描述，用于生成 LLM 的 function-calling schema。
    """

    def __init__(self, *, avoid_channels: Any = None) -> None:
        """初始化 YouTubeSearchTool。"""
        super().__init__(
            name="search_youtube_video",
            description=(
                "Search YouTube for fitness exercise tutorial videos. "
                "For a training plan, search only 1-3 unique core lifts; do not search "
                "warm-ups, cool-downs, or repeated exercises individually. "
                "Use it when explaining how to perform a specific exercise correctly. "
                "Use English query format: '<exercise name> proper form tutorial'. "
                "Returns a JSON string with ranked video titles and URLs."
            ),
        )
        self.avoid_channels = {
            _normalise_channel(channel)
            for channel in (avoid_channels or [])
            if isinstance(channel, str) and channel.strip()
        }
        self._query_cache: dict[tuple[str, int], dict[str, Any]] = {}

    def get_parameters(self) -> list[ToolParameter]:
        """返回工具参数定义列表，供框架生成 OpenAI function-calling schema。

        Returns:
            包含 ``query`` 和 ``max_results`` 两个参数定义的列表。
        """
        return [
            ToolParameter(
                name="query",
                type="string",
                description=(
                    "Search keyword in English. "
                    "Recommended format: '<exercise name> proper form tutorial', "
                    "e.g. 'barbell bench press proper form tutorial'."
                ),
                required=True,
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="Number of videos to return. Range [1, 5]. Defaults to 2.",
                required=False,
                default=2,
            ),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        """执行 YouTube 视频搜索。

        从 ``parameters`` 字典中提取 ``query`` 和 ``max_results``，
        调用 ``youtube_search.search_videos()`` 完成实际搜索，
        并将结果封装在 ToolResponse 中返回。

        Args:
            parameters: 由 Agent 框架传入的参数字典，期望包含：
                - ``query``       (str, 必填): 搜索关键词。
                - ``max_results`` (int, 可选): 结果数量，默认 2。

        Returns:
            ToolResponse 对象，包含成功或失败信息以及搜索结果。
        """
        # ── 参数提取与防御性校验 ──────────────────────────────────────────
        query: str = str(parameters.get("query") or "").strip()
        if not query:
            logger.warning("YouTubeSearchTool 收到空 query，直接返回错误")
            return ToolResponse.error(
                code="INVALID_PARAM",
                message="参数 query 不能为空",
            )

        # max_results 允许字符串类型传入（部分 LLM 可能输出字符串数字）
        raw_max: Any = parameters.get("max_results", 2)
        try:
            max_results: int = int(raw_max)
        except (TypeError, ValueError):
            logger.warning("max_results 类型异常(%r)，回退到默认值 2", raw_max)
            max_results = 2

        # ── 委托核心搜索模块执行 ─────────────────────────────────────────
        logger.info(
            "YouTubeSearchTool.run: query=%r  max_results=%d", query, max_results
        )
        requested_results = max(1, min(max_results, 5))
        cache_key = (" ".join(query.casefold().split()), requested_results)
        cached = self._query_cache.get(cache_key)
        if cached is not None:
            logger.info("YouTubeSearchTool cache hit: query=%r", query)
            cached_data = deepcopy(cached)
            return ToolResponse.success(
                text=json.dumps(cached_data, ensure_ascii=False, indent=2), data=cached_data
            )
        search_limit = min(5, requested_results * 3) if self.avoid_channels else requested_results
        json_result = search_videos(query=query, max_results=search_limit)
        
        # 将 JSON 字符串解析回字典以放入 ToolResponse.data 中
        try:
            data = json.loads(json_result)
            if "error" in data:
                return ToolResponse.error(
                    code="SEARCH_FAILED",
                    message=data["error"]
                )
            
            results = data.get("results")
            if isinstance(results, list) and self.avoid_channels:
                allowed = [
                    item for item in results
                    if isinstance(item, dict)
                    and not any(
                        channel_names_match(item.get("channel"), avoided)
                        for avoided in self.avoid_channels
                    )
                ]
                if allowed:
                    data["results"] = allowed[:requested_results]
                    data["total_found"] = len(data["results"])
                    data["excluded_channels"] = sorted(self.avoid_channels)
                else:
                    data["results"] = results[:requested_results]
                    data["total_found"] = len(data["results"])
                    data["avoidance_fallback"] = True
            text = json.dumps(data, ensure_ascii=False, indent=2)
            self._query_cache[cache_key] = deepcopy(data)
            return ToolResponse.success(
                text=text,
                data=data
            )
        except json.JSONDecodeError:
            return ToolResponse.error(
                code="JSON_PARSE_ERROR",
                message="无法解析 YouTube 搜索返回的 JSON 结果"
            )
