"""利用 HelloAgents SearchTool 的搜索分发助手。"""

from __future__ import annotations

import logging
import threading
from typing import Any

from hello_agents.tools import SearchTool

from config import Configuration
from utils import (
    deduplicate_and_format_sources,
    format_sources,
    get_config_value,
)

logger = logging.getLogger(__name__)

MAX_TOKENS_PER_SOURCE = 2000
_GLOBAL_SEARCH_TOOL: SearchTool | None = None
_SEARCH_TOOL_LOCK = threading.Lock()


def get_global_search_tool(config: Configuration) -> SearchTool:
    """使用 API 密钥延迟初始化全局搜索工具（线程安全）。"""
    global _GLOBAL_SEARCH_TOOL
    if _GLOBAL_SEARCH_TOOL is None:
        with _SEARCH_TOOL_LOCK:
            # 双重检查锁定，避免多线程重复创建
            if _GLOBAL_SEARCH_TOOL is None:
                _GLOBAL_SEARCH_TOOL = SearchTool(
                    backend="hybrid",
                    tavily_key=config.tavily_api_key,
                    serpapi_key=config.serpapi_api_key,
                )
    return _GLOBAL_SEARCH_TOOL


def dispatch_search(
    query: str,
    config: Configuration,
    loop_count: int,
) -> tuple[dict[str, Any] | None, list[str], str | None, str]:
    """
    执行配置的搜索后端并标准化响应负载。
    
    Args:
        query: 搜索查询字符串。
        config: 包含搜索 API 配置的对象。
        loop_count: 当前研究循环计数（用于分页或深度控制）。
        
    Returns:
        元组 (原始负载, 通知列表, 答案文本, 后端标签)。
    """
    search_api = get_config_value(config.search_api)
    search_tool = get_global_search_tool(config)

    try:
        raw_response = search_tool.run(
            {
                "input": query,
                "backend": search_api,
                "mode": "structured",
                "fetch_full_page": config.fetch_full_page,
                "max_results": 5,
                "max_tokens_per_source": MAX_TOKENS_PER_SOURCE,
                "loop_count": loop_count,
            }
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Search backend %s failed: %s", search_api, exc)
        raise

    if isinstance(raw_response, str):
        notices = [raw_response]
        logger.warning("Search backend %s returned text notice: %s", search_api, raw_response)
        payload: dict[str, Any] = {
            "results": [],
            "backend": search_api,
            "answer": None,
            "notices": notices,
        }
    else:
        payload = raw_response
        notices = list(payload.get("notices") or [])

    backend_label = str(payload.get("backend") or search_api)
    answer_text = payload.get("answer")
    results = payload.get("results", [])

    if notices:
        for notice in notices:
            logger.info("Search notice (%s): %s", backend_label, notice)

    logger.info(
        "Search backend=%s resolved_backend=%s answer=%s results=%s",
        search_api,
        backend_label,
        bool(answer_text),
        len(results),
    )

    return payload, notices, answer_text, backend_label


def prepare_research_context(
    search_result: dict[str, Any] | None,
    answer_text: str | None,
    config: Configuration,
) -> tuple[str, str]:
    """
    为下游代理构建结构化上下文和来源摘要。
    
    Args:
        search_result: 搜索后端返回的原始结果字典。
        answer_text: 搜索后端直接生成的答案（如果有）。
        config: 配置对象。
        
    Returns:
        元组 (来源摘要列表, 详细上下文文本)。
    """
    sources_summary = format_sources(search_result)
    context = deduplicate_and_format_sources(
        search_result or {"results": []},
        max_tokens_per_source=MAX_TOKENS_PER_SOURCE,
        fetch_full_page=config.fetch_full_page,
    )

    if answer_text:
        context = f"AI直接答案：\n{answer_text}\n\n{context}"

    return sources_summary, context
