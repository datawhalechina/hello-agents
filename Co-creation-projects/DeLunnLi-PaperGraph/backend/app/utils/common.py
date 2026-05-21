
from __future__ import annotations

import asyncio
import functools
import sqlite3
import logging
import re
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger(__name__)

def safe_http_500(op_name: str, exc: Exception) -> HTTPException:
    logger.exception("%s failed", op_name, exc_info=exc)
    return HTTPException(status_code=500, detail="服务暂时不可用，请稍后重试")

def normalize_arxiv_id(arxiv_id: str | None) -> str | None:
    if not arxiv_id:
        return None
    s = str(arxiv_id).strip()
    if not s:
        return None
    if "v" in s and s.rsplit("v", 1)[-1].isdigit():
        s = s.rsplit("v", 1)[0]
    return s.lower()

def parse_llm_json(text: str) -> dict[str, Any | None]:
    from app.services.search_intent.parsing import extract_json_object

    return extract_json_object(text)

def truncate_text(text: str, max_length: int, suffix: str = "…") -> str:
    t = (text or "").strip()
    if len(t) <= max_length:
        return t
    return t[: max_length - len(suffix)] + suffix

def tokenize_for_keywords(text: str, min_len: int = 3, max_len: int = 26) -> set[str]:
    t = (text or "").lower()
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
    out: set[str] = set()
    for x in t.split():
        s = x.strip()
        if min_len <= len(s) <= max_len:
            out.add(s)
    return out

def text_has_cjk(s: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in s)

def dedupe_strings_preserve_order(items: list[str | None], *, max_n: int) -> list[str]:
    if not items:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        t = str(raw).strip()
        if not t:
            continue
        k = t.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(t)
        if len(out) >= max_n:
            break
    return out

def suppress_exceptions(default_return=None, log_level="debug", log_message=None):
    """Catch sync/async exceptions and return a default value."""
    def decorator(func):
        is_async = asyncio.iscoroutinefunction(func)
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception:
                if log_level == "warning":
                    logger.warning(log_message or f"{func.__name__} failed", exc_info=True)
                else:
                    logger.debug(log_message or f"{func.__name__} failed", exc_info=True)
                return default_return

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                if log_level == "warning":
                    logger.warning(log_message or f"{func.__name__} failed", exc_info=True)
                else:
                    logger.debug(log_message or f"{func.__name__} failed", exc_info=True)
                return default_return

        return async_wrapper if is_async else sync_wrapper
    return decorator

suppress_exceptions_async = suppress_exceptions

def exec_sql(db_path: str, *statements: str) -> None:
    conn = sqlite3.connect(db_path)
    for stmt in statements:
        conn.execute(stmt)
    conn.commit()
    conn.close()

def build_in_clause(column: str, values: list[Any]) -> tuple[str, tuple[Any, ...]]:
    if not values:
        return f"{column} IN (NULL)", ()
    placeholders = ",".join(["?"] * len(values))
    return f"{column} IN ({placeholders})", tuple(values)
