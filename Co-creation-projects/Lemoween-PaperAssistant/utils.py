"""通用工具函数"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def strip_thinking_tokens(text: str) -> str:
    """移除 <think>...</think> 段"""
    while "<think>" in text and "</think>" in text:
        start = text.find("<think>")
        end = text.find("</think>") + len("</think>")
        text = text[:start] + text[end:]
    return text


def strip_tool_calls(text: str) -> str:
    """移除残留的 [TOOL_CALL:...] 标记"""
    if not text:
        return text
    return re.sub(r"\[TOOL_CALL:[^\]]+\]", "", text)


def normalize_title(title: str) -> str:
    """标题归一化，用于去重"""
    return re.sub(r"\s+", " ", (title or "").strip().lower())