"""youtube_search.py — YouTube Data API v3 搜索核心逻辑（与框架无关）

该模块封装了所有与 YouTube Data API v3 交互的代码，不依赖任何 Agent
框架。可被以下两个调用方复用：
  - ``fithealth_agent/youtube_tool.py``：注册为 hello_agents 工具
  - ``mcp_servers/youtube_server.py``：注册为 MCP 工具（供将来扩展）

环境变量（必须配置）：
    YOUTUBE_API_KEY: 从 Google Cloud Console 获取的 YouTube Data API v3 密钥。
                     获取地址：https://console.cloud.google.com/
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


def _normalise_channel(value: object) -> str:
    """Normalize a channel label while discarding conversational wrappers."""
    text = str(value or "").casefold()
    ascii_parts = re.findall(r"[a-z0-9]+", text)
    if ascii_parts:
        return "".join(ascii_parts)
    compact = "".join(ch for ch in text if ch.isalnum())
    for wrapper in ("那个", "这个", "频道", "youtube", "油管"):
        compact = compact.replace(wrapper, "")
    return compact


def channel_names_match(left: object, right: object) -> bool:
    """Use symmetric containment for decorated or abbreviated channel names."""
    normalized_left = _normalise_channel(left)
    normalized_right = _normalise_channel(right)
    return bool(
        normalized_left
        and normalized_right
        and (
            normalized_left in normalized_right
            or normalized_right in normalized_left
        )
    )

# ─────────────────────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────────────────────

_API_SERVICE: str = "youtube"
_API_VERSION: str = "v3"

# 每次搜索允许的结果数范围，防止滥用 API 配额
_MAX_RESULTS_MIN: int = 1
_MAX_RESULTS_MAX: int = 5


# ─────────────────────────────────────────────────────────────────────────────
# 公开接口
# ─────────────────────────────────────────────────────────────────────────────

def search_videos(query: str, max_results: int = 3) -> str:
    """在 YouTube 上搜索视频，返回 JSON 格式的结构化结果字符串。

    该函数是整个 YouTube 搜索功能的核心入口，所有错误均被内部捕获并
    序列化到返回的 JSON 中，调用方无需额外处理异常。

    Args:
        query:       搜索关键词。建议使用英文，格式为
                     ``"<动作英文名> proper form tutorial"``，
                     例如 ``"barbell squat proper form tutorial"``。
        max_results: 期望返回的最大视频数量，范围 [1, 5]，默认 3。
                     超出范围的值会被自动修正到边界值。

    Returns:
        JSON 字符串，成功时结构为::

            {
                "query":       "<实际搜索关键词>",
                "results": [
                    {
                        "rank":    1,
                        "title":   "<视频标题>",
                        "url":     "https://www.youtube.com/watch?v=<id>",
                        "channel": "<频道名称>"
                    },
                    ...
                ],
                "total_found": <实际返回数量>
            }

        失败时结构为::

            {
                "error":   "<错误描述>",
                "query":   "<搜索关键词>",
                "results": []
            }
    """
    query = (query or "").strip()
    if not query:
        return _err_json("搜索关键词不能为空", query)

    clamped: int = max(_MAX_RESULTS_MIN, min(int(max_results), _MAX_RESULTS_MAX))
    logger.info("YouTube 搜索: query=%r  max_results=%d", query, clamped)

    try:
        api_key: str = _require_api_key()
        items: list[dict[str, str]] = _call_api(api_key, query, clamped)
    except EnvironmentError as exc:
        logger.error("API Key 未配置: %s", exc)
        return _err_json(str(exc), query)
    except HttpError as exc:
        status: int = exc.resp.status if exc.resp else -1
        msg = (
            f"YouTube API 请求失败（HTTP {status}）。"
            f"请检查 API Key 是否有效、YouTube Data API v3 是否已启用，"
            f"以及今日配额是否耗尽。详情：{exc}"
        )
        logger.error(msg)
        return _err_json(msg, query)
    except Exception as exc:  # noqa: BLE001
        logger.exception("YouTube 搜索发生未预期异常: %s", exc)
        return _err_json(f"未预期错误：{exc}", query)

    ranked: list[dict[str, Any]] = [
        {
            "rank":    idx + 1,
            "title":   v["title"],
            "url":     v["url"],
            "channel": v["channel"],
        }
        for idx, v in enumerate(items)
    ]
    payload: dict[str, Any] = {
        "query":       query,
        "results":     ranked,
        "total_found": len(ranked),
    }
    logger.info("搜索完成，返回 %d 条结果", len(ranked))
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# 内部辅助函数
# ─────────────────────────────────────────────────────────────────────────────

def _require_api_key() -> str:
    """读取并验证 YOUTUBE_API_KEY 环境变量。

    Returns:
        非空的 API Key 字符串。

    Raises:
        EnvironmentError: 若环境变量未设置或为空/占位符值。
    """
    key: str = os.environ.get("YOUTUBE_API_KEY", "").strip()
    # 同时拦截用户未修改的占位符值
    if not key or key == "YOUR_YOUTUBE_API_KEY_HERE":
        raise EnvironmentError(
            "YOUTUBE_API_KEY 未配置。请在 .env 文件中填入真实的 API Key。\n"
            "获取步骤：https://console.cloud.google.com/ → 启用 YouTube Data API v3 → 创建凭据 → API 密钥"
        )
    return key


def _call_api(api_key: str, query: str, max_results: int) -> list[dict[str, str]]:
    """调用 YouTube Data API v3 的 search.list 接口。

    Args:
        api_key:     有效的 YouTube Data API v3 密钥。
        query:       已清洗的搜索关键词。
        max_results: 已完成范围限制的结果数量。

    Returns:
        包含视频信息字典的列表，每项具有 ``title``、``url``、``channel``
        和 ``video_id`` 四个键。

    Raises:
        HttpError: YouTube API 返回非 2xx 响应时。
    """
    youtube: Any = build(
        _API_SERVICE,
        _API_VERSION,
        developerKey=api_key,
        cache_discovery=False,   # 禁用文件缓存，避免多进程文件锁冲突
    )
    response: dict[str, Any] = (
        youtube.search()
        .list(
            q=query,
            part="id,snippet",
            maxResults=max_results,
            type="video",
            relevanceLanguage="zh",
            safeSearch="none",
        )
        .execute()
    )

    results: list[dict[str, str]] = []
    for item in response.get("items", []):
        video_id: str | None = item.get("id", {}).get("videoId")
        if not video_id:
            logger.debug("跳过无 videoId 的条目: %s", item.get("id"))
            continue
        snippet: dict[str, Any] = item.get("snippet", {})
        results.append(
            {
                "title":    snippet.get("title") or "（无标题）",
                "url":      f"https://www.youtube.com/watch?v={video_id}",
                "channel":  snippet.get("channelTitle") or "（未知频道）",
                "video_id": video_id,
            }
        )
    return results


def _err_json(message: str, query: str) -> str:
    """构造标准错误响应 JSON 字符串。

    Args:
        message: 错误描述文本。
        query:   原始搜索关键词（用于上下文追踪）。

    Returns:
        序列化后的 JSON 错误字符串。
    """
    return json.dumps(
        {"error": message, "query": query, "results": []},
        ensure_ascii=False,
    )
