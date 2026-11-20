"""Shared prompt-response cache with Redis and local-disk backends."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Optional

import redis as redis_lib

logger = logging.getLogger(__name__)


class PromptCache:
    """TTL cache for LLM results.

    Redis is the production backend and is shared by every API/worker process.
    The disk backend remains available only when ``redis_url`` is omitted,
    which keeps local tests and offline development self-contained.
    """

    def __init__(
        self,
        cache_dir: str = "./data/cache",
        ttl_hours: int = 24,
        max_entries: int = 1000,
        *,
        redis_url: str | None = None,
        namespace: str = "pubmed-agent:prompt-cache",
        socket_connect_timeout: float = 2.0,
        socket_timeout: float = 5.0,
        lock_timeout: int = 300,
        lock_wait_timeout: int = 30,
    ) -> None:
        self.cache_dir = cache_dir
        self.ttl_seconds = max(1, int(ttl_hours * 3600))
        self.max_entries = max_entries
        self.namespace = namespace.rstrip(":")
        self.lock_timeout = lock_timeout
        self.lock_wait_timeout = lock_wait_timeout
        self._redis = None
        self._hot: dict[str, dict] = {}

        if redis_url:
            self._redis = redis_lib.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=socket_connect_timeout,
                socket_timeout=socket_timeout,
            )
            logger.info(
                "PromptCache ready (backend=redis, namespace=%s, ttl=%dh)",
                self.namespace,
                ttl_hours,
            )
        else:
            os.makedirs(cache_dir, exist_ok=True)
            self._load_index()
            logger.info(
                "PromptCache ready (backend=disk, dir=%s, ttl=%dh, entries=%d)",
                cache_dir,
                ttl_hours,
                len(self._hot),
            )

    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        metadata: Optional[dict] = None,
    ) -> tuple[Any, bool]:
        """Return a cached value or compute it once across worker processes."""
        cache_key = self._cache_key(key, metadata)
        cached = self._get_by_hash(cache_key)
        if cached is not None:
            logger.info("Cache HIT: %s", cache_key[:12])
            return cached, True

        logger.info("Cache MISS: %s", cache_key[:12])
        if self._redis is None:
            value = compute_fn()
            self._set_by_hash(cache_key, value, key)
            return value, False

        lock = self._redis.lock(
            self._redis_lock_key(cache_key),
            timeout=self.lock_timeout,
            blocking_timeout=self.lock_wait_timeout,
        )
        acquired = False
        try:
            acquired = bool(lock.acquire(blocking=True))
        except redis_lib.RedisError as exc:
            logger.warning("Cache lock unavailable; computing without lock: %s", exc)

        if not acquired:
            value = compute_fn()
            self._set_by_hash(cache_key, value, key)
            return value, False

        try:
            # Another worker may have populated the value while this worker waited.
            cached = self._get_by_hash(cache_key)
            if cached is not None:
                logger.info("Cache HIT after lock: %s", cache_key[:12])
                return cached, True
            value = compute_fn()
            self._set_by_hash(cache_key, value, key)
            return value, False
        finally:
            try:
                lock.release()
            except redis_lib.RedisError:
                logger.warning("Cache lock release failed: %s", cache_key[:12])

    def get(self, key: str, metadata: Optional[dict] = None) -> Optional[Any]:
        return self._get_by_hash(self._cache_key(key, metadata))

    def set(
        self,
        key: str,
        value: Any,
        metadata: Optional[dict] = None,
    ) -> None:
        cache_key = self._cache_key(key, metadata)
        self._set_by_hash(cache_key, value, key)

    def invalidate(self, key: str, metadata: Optional[dict] = None) -> None:
        cache_key = self._cache_key(key, metadata)
        if self._redis is not None:
            try:
                self._redis.delete(self._redis_value_key(cache_key))
            except redis_lib.RedisError as exc:
                logger.warning("Redis cache invalidation failed: %s", exc)
            return
        self._hot.pop(cache_key, None)
        fpath = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(fpath):
            os.remove(fpath)

    def stats(self) -> dict:
        if self._redis is not None:
            try:
                total = sum(
                    1
                    for _ in self._redis.scan_iter(
                        match=f"{self.namespace}:value:*", count=200
                    )
                )
            except redis_lib.RedisError as exc:
                logger.warning("Redis cache stats failed: %s", exc)
                total = 0
            return {
                "backend": "redis",
                "total_entries": total,
                "fresh_entries": total,
                "ttl_hours": self.ttl_seconds / 3600,
            }
        fresh = sum(1 for entry in self._hot.values() if self._is_fresh(entry))
        return {
            "backend": "disk",
            "total_entries": len(self._hot),
            "fresh_entries": fresh,
            "ttl_hours": self.ttl_seconds / 3600,
        }

    def _cache_key(self, key: str, metadata: Optional[dict]) -> str:
        raw = key
        if metadata:
            raw += json.dumps(metadata, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def _redis_value_key(self, cache_key: str) -> str:
        return f"{self.namespace}:value:{cache_key}"

    def _redis_lock_key(self, cache_key: str) -> str:
        return f"{self.namespace}:lock:{cache_key}"

    def _get_by_hash(self, cache_key: str) -> Optional[Any]:
        if self._redis is not None:
            try:
                raw = self._redis.get(self._redis_value_key(cache_key))
                if not raw:
                    return None
                entry = json.loads(raw)
                return entry.get("value")
            except (redis_lib.RedisError, json.JSONDecodeError, TypeError) as exc:
                logger.warning("Redis cache read failed: %s", exc)
                return None
        entry = self._hot.get(cache_key)
        if entry and self._is_fresh(entry):
            return entry["value"]
        return None

    def _is_fresh(self, entry: dict) -> bool:
        return (time.time() - entry["cached_at"]) < self.ttl_seconds

    def _set_by_hash(self, cache_key: str, value: Any, raw_key: str) -> None:
        entry = {
            "value": self._to_jsonable(value),
            "raw_key": raw_key[:200],
            "cached_at": time.time(),
        }
        if self._redis is not None:
            try:
                self._redis.set(
                    self._redis_value_key(cache_key),
                    json.dumps(entry, ensure_ascii=False),
                    ex=self.ttl_seconds,
                )
            except redis_lib.RedisError as exc:
                logger.warning("Redis cache write failed: %s", exc)
            return

        self._hot[cache_key] = entry
        if len(self._hot) > self.max_entries:
            oldest = min(self._hot, key=lambda item: self._hot[item]["cached_at"])
            del self._hot[oldest]
        try:
            fpath = os.path.join(self.cache_dir, f"{cache_key}.json")
            with open(fpath, "w", encoding="utf-8") as handle:
                json.dump(entry, handle, ensure_ascii=False)
        except OSError as exc:
            logger.warning("Cache persist failed: %s", exc)

    def _load_index(self) -> None:
        try:
            for fname in os.listdir(self.cache_dir):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(self.cache_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as handle:
                        entry = json.load(handle)
                    if self._is_fresh(entry):
                        self._hot[fname[:-5]] = entry
                except (OSError, json.JSONDecodeError, KeyError, TypeError):
                    try:
                        os.remove(fpath)
                    except OSError:
                        pass
        except FileNotFoundError:
            pass

    @classmethod
    def _to_jsonable(cls, value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return cls._to_jsonable(value.model_dump(mode="json"))
        if is_dataclass(value) and not isinstance(value, type):
            return cls._to_jsonable(asdict(value))
        if isinstance(value, dict):
            return {str(key): cls._to_jsonable(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [cls._to_jsonable(item) for item in value]
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        raise TypeError(f"Unsupported cache value type: {type(value).__name__}")
