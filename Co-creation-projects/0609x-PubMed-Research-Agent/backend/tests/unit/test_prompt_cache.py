from __future__ import annotations

from pydantic import BaseModel
from redis.exceptions import ConnectionError

from backend.services.prompt_cache import PromptCache


class FakeLock:
    def acquire(self, blocking=True):
        return True

    def release(self):
        return None


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex=None):
        self.values[key] = value
        self.expirations[key] = ex

    def delete(self, key):
        self.values.pop(key, None)

    def scan_iter(self, match=None, count=None):
        prefix = (match or "").rstrip("*")
        return (key for key in self.values if key.startswith(prefix))

    def lock(self, *args, **kwargs):
        return FakeLock()


class BrokenRedis(FakeRedis):
    def get(self, key):
        raise ConnectionError("redis offline")

    def set(self, key, value, ex=None):
        raise ConnectionError("redis offline")

    def lock(self, *args, **kwargs):
        class BrokenLock:
            def acquire(self, blocking=True):
                raise ConnectionError("redis offline")

        return BrokenLock()


class CachedResult(BaseModel):
    title: str
    scores: list[int]


def test_pydantic_value_survives_disk_round_trip(tmp_path):
    cache_dir = tmp_path / "cache"
    cache = PromptCache(cache_dir=str(cache_dir))
    value = CachedResult(title="result", scores=[1, 2, 3])

    computed, hit = cache.get_or_compute("key", lambda: value)

    assert computed == value
    assert hit is False

    reloaded = PromptCache(cache_dir=str(cache_dir))
    cached, hit = reloaded.get_or_compute("key", lambda: None)

    assert hit is True
    assert cached == {"title": "result", "scores": [1, 2, 3]}


def test_unsupported_value_is_not_stringified(tmp_path):
    cache = PromptCache(cache_dir=str(tmp_path / "cache"))

    class Unsupported:
        pass

    try:
        cache.get_or_compute("key", Unsupported)
    except TypeError as exc:
        assert "Unsupported cache value type" in str(exc)
    else:
        raise AssertionError("unsupported cache values must fail explicitly")


def test_redis_backend_is_shared_across_workers(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(
        "backend.services.prompt_cache.redis_lib.Redis.from_url",
        lambda *args, **kwargs: redis,
    )
    first = PromptCache(redis_url="redis://cache/1", ttl_hours=2)
    second = PromptCache(redis_url="redis://cache/1", ttl_hours=2)

    computed, hit = first.get_or_compute("shared-key", lambda: {"answer": 42})
    reused, second_hit = second.get_or_compute(
        "shared-key", lambda: {"answer": "should-not-run"}
    )

    assert hit is False
    assert second_hit is True
    assert computed == reused == {"answer": 42}
    assert set(redis.expirations.values()) == {7200}
    assert second.stats()["backend"] == "redis"


def test_redis_invalidate_removes_shared_value(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(
        "backend.services.prompt_cache.redis_lib.Redis.from_url",
        lambda *args, **kwargs: redis,
    )
    cache = PromptCache(redis_url="redis://cache/1")
    cache.set("key", [1, 2, 3])
    assert cache.get("key") == [1, 2, 3]

    cache.invalidate("key")

    assert cache.get("key") is None


def test_redis_outage_does_not_block_llm_computation(monkeypatch):
    monkeypatch.setattr(
        "backend.services.prompt_cache.redis_lib.Redis.from_url",
        lambda *args, **kwargs: BrokenRedis(),
    )
    cache = PromptCache(redis_url="redis://cache/1")

    value, hit = cache.get_or_compute("key", lambda: {"computed": True})

    assert value == {"computed": True}
    assert hit is False
