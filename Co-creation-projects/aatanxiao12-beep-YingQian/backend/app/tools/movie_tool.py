"""TMDB MovieTool — 可展开为 movies_discover / movies_search，供检索 Agent 调用。

内部复用 MovieService，与 /api/movies/* 同一数据源（双通道同源）。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from hello_agents.tools import Tool, ToolParameter, ToolResponse, tool_action
from hello_agents.tools.errors import ToolErrorCode

from ..services.movie_service import MovieServiceError, get_movie_service, normalize_tmdb_language
from ..utils.logger import get_logger

logger = get_logger("app.movie_tool")


def _movies_to_payload(movies: list) -> Dict[str, Any]:
    items = [m.model_dump() for m in movies]
    text = json.dumps({"count": len(items), "movies": items}, ensure_ascii=False)
    return {"text": text, "data": {"movies": items, "count": len(items)}}


class MovieTool(Tool):
    """可展开电影工具：注册后变成 movies_discover / movies_search 两个子工具。"""

    def __init__(self) -> None:
        super().__init__(
            name="movies",
            description="TMDB 电影检索：discover 条件发现、search 文本搜索",
            expandable=True,  # True → Agent.add_tool 时自动展开子工具
        )
        self._service = get_movie_service()  # 与 /api/movies 共用同一服务
        # 编排器可按次 run 设置上限，防止 LLM 一轮内并行狂打 discover
        self._discover_calls = 0
        self._discover_call_limit: Optional[int] = None

    def begin_search_run(self, discover_limit: int = 1) -> None:
        """检索阶段开始：重置计数并设置 movies_discover 调用上限。"""
        self._discover_calls = 0
        self._discover_call_limit = discover_limit

    def end_search_run(self) -> None:
        """检索阶段结束：取消调用上限。"""
        self._discover_call_limit = None
        self._discover_calls = 0

    @tool_action("movies_discover", "按类型/年份/时长/语言等条件发现电影")
    def discover(
        self,
        with_genres: str = "",
        year: int = 0,
        year_gte: int = 0,
        year_lte: int = 0,
        max_runtime: int = 0,
        with_original_language: str = "",
        sort_by: str = "popularity.desc",
        page: int = 1,
    ) -> ToolResponse:
        """条件发现电影（主路径）。

        Args:
            with_genres: 类型名或 id，逗号分隔，如 剧情,科幻
            year: 精确上映年，0 表示不限
            year_gte: 上映年起，0 表示不限
            year_lte: 上映年止，0 表示不限
            max_runtime: 最大片长分钟，0 表示不限
            with_original_language: 原始语言代码，如 zh/en/ja/ko
            sort_by: 排序，默认 popularity.desc
            page: 页码
        """
        if self._discover_call_limit is not None:
            self._discover_calls += 1
            if self._discover_calls > self._discover_call_limit:
                logger.warning(
                    "movies_discover 已达上限 %d，拒绝第 %d 次调用",
                    self._discover_call_limit,
                    self._discover_calls,
                )
                return ToolResponse.error(
                    code=ToolErrorCode.INTERNAL_ERROR,
                    message=(
                        f"movies_discover 本轮最多调用 {self._discover_call_limit} 次；"
                        "请基于已有工具结果直接输出含 movies 的 JSON，"
                        "并保留工具返回的 poster_url 等字段。"
                    ),
                )
        try:
            raw_lang = with_original_language or None
            lang = normalize_tmdb_language(raw_lang)
            if raw_lang and not lang:
                logger.warning(
                    "movies_discover 丢弃非法 language=%r，将按无语言过滤查询",
                    raw_lang,
                )

            logger.info(
                "movies_discover 请求 genres=%r lang=%r(raw=%r) year=%s gte=%s lte=%s "
                "runtime_lte=%s sort=%s page=%s",
                with_genres or None,
                lang,
                raw_lang,
                year or None,
                year_gte or None,
                year_lte or None,
                max_runtime or None,
                sort_by or "popularity.desc",
                page or 1,
            )

            # 空结果时自动放宽条件，避免 Agent 一次非法/过严参数直接失败
            movies = self._service.discover_with_relax(
                with_genres=with_genres or None,
                year=year or None,
                year_gte=year_gte or None,
                year_lte=year_lte or None,
                max_runtime=max_runtime or None,
                with_original_language=raw_lang,
                sort_by=sort_by or "popularity.desc",
                page=page or 1,
            )
            payload = _movies_to_payload(movies)
            logger.info("movies_discover -> %d", payload["data"]["count"])
            return ToolResponse.success(text=payload["text"], data=payload["data"])
        except MovieServiceError as e:
            return ToolResponse.error(code=ToolErrorCode.INTERNAL_ERROR, message=str(e))

    @tool_action("movies_search", "按关键词搜索电影")
    def search(self, q: str, year: int = 0, page: int = 1) -> ToolResponse:
        """文本搜索电影（已看解析 / 兜底）。

        Args:
            q: 搜索关键词
            year: 上映年，0 表示不限
            page: 页码
        """
        try:
            movies = self._service.search(q=q, year=year or None, page=page or 1)
            payload = _movies_to_payload(movies)
            logger.info("movies_search q=%r -> %d", q, payload["data"]["count"])
            return ToolResponse.success(text=payload["text"], data=payload["data"])
        except MovieServiceError as e:
            return ToolResponse.error(code=ToolErrorCode.INTERNAL_ERROR, message=str(e))

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        return ToolResponse.error(
            code=ToolErrorCode.NOT_IMPLEMENTED,
            message="请使用子工具 movies_discover 或 movies_search",
        )

    def get_parameters(self) -> List[ToolParameter]:
        return []


_movie_tool: Optional[MovieTool] = None


def get_movie_tool() -> MovieTool:
    global _movie_tool
    if _movie_tool is None:
        _movie_tool = MovieTool()
    return _movie_tool
