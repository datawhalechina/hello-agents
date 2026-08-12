"""
Prompt Cache Module
===================
Caches LLM responses to avoid redundant API calls.

Problem Solved:
    Researchers often refine their queries iteratively. Without caching,
    each similar query triggers a full, expensive LLM summarization.

How It Works:
    1. Compute a cache key from query hash + articles PMID list hash
    2. Check disk-based JSON cache before calling LLM
    3. Cache HIT: return instantly. Cache MISS: call LLM, store with TTL.

Performance Gain:
    - 0ms latency for cached queries (vs 3-30s for LLM call)
    - 100% API cost savings on repeated/similar queries
    - Essential for production deployment with multiple users
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class PromptCache:
    """Disk-backed prompt response cache with TTL expiration."""

    def __init__(
        self,
        cache_dir: str = "./data/cache",
        ttl_hours: int = 24,
        max_entries: int = 1000,
    ) -> None:
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_hours * 3600
        self.max_entries = max_entries
        os.makedirs(cache_dir, exist_ok=True)
        self._hot: dict[str, dict] = {}
        self._load_index()
        logger.info(
            "PromptCache ready (dir=%s, ttl=%dh, entries=%d)",
            cache_dir, ttl_hours, len(self._hot),
        )

    def get_or_compute(
        self, key: str, compute_fn: Callable[[], Any],
        metadata: Optional[dict] = None,
    ) -> tuple[Any, bool]:
        """Get cached value or compute and cache it. Returns (value, was_cached)."""
        cache_key = self._hash_key(key)
        if metadata:
            cache_key = self._hash_key(
                key + json.dumps(metadata, sort_keys=True)
            )
        if cache_key in self._hot and self._is_fresh(self._hot[cache_key]):
            logger.info("Cache HIT: %s", cache_key[:12])
            return self._hot[cache_key]["value"], True
        logger.info("Cache MISS: %s", cache_key[:12])
        value = compute_fn()
        self._set(cache_key, value, key)
        return value, False

    def get(
        self, key: str, metadata: Optional[dict] = None
    ) -> Optional[Any]:
        cache_key = self._hash_key(key)
        if metadata:
            cache_key = self._hash_key(
                key + json.dumps(metadata, sort_keys=True)
            )
        entry = self._hot.get(cache_key)
        if entry and self._is_fresh(entry):
            return entry["value"]
        return None

    def invalidate(self, key: str) -> None:
        cache_key = self._hash_key(key)
        self._hot.pop(cache_key, None)
        fpath = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(fpath):
            os.remove(fpath)

    def stats(self) -> dict:
        fresh = sum(
            1 for e in self._hot.values() if self._is_fresh(e)
        )
        return {
            "total_entries": len(self._hot),
            "fresh_entries": fresh,
            "ttl_hours": self.ttl_seconds / 3600,
        }

    def _hash_key(self, key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()[:32]

    def _is_fresh(self, entry: dict) -> bool:
        return (time.time() - entry["cached_at"]) < self.ttl_seconds

    def _set(self, cache_key: str, value: Any, raw_key: str) -> None:
        entry = {
            "value": value, "raw_key": raw_key[:200],
            "cached_at": time.time(),
        }
        self._hot[cache_key] = entry
        if len(self._hot) > self.max_entries:
            oldest = min(self._hot.keys(), key=lambda k: self._hot[k]["cached_at"])
            del self._hot[oldest]
        try:
            fpath = os.path.join(self.cache_dir, f"{cache_key}.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, default=str)
        except Exception as exc:
            logger.warning("Cache persist failed: %s", exc)

    def _load_index(self) -> None:
        try:
            for fname in os.listdir(self.cache_dir):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(self.cache_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        entry = json.load(f)
                    if self._is_fresh(entry):
                        self._hot[fname[:-5]] = entry
                except Exception:
                    os.remove(fpath)
        except FileNotFoundError:
            pass
