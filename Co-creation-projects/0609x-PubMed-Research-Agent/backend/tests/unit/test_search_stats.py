# -*- coding: utf-8 -*-
"""Unit tests for the dashboard aggregation service and /search/stats endpoint."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import backend.app.models.analysis  # noqa: F401  (register tables)
import backend.app.models.article  # noqa: F401
import backend.app.models.search  # noqa: F401
from backend.app.main import app
from backend.app.models.article import Article
from backend.app.models.database import Base, get_db
from backend.app.models.search import Search
from backend.services.search_stats import build_dashboard_stats
from backend.services.journal_metrics import JournalMetrics

test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _fresh_db():
    async def _reset():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_reset())

    async def override_get_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    asyncio.run(_reset())


def _metrics(tmp_path) -> JournalMetrics:
    data = tmp_path / "metrics.json"
    data.write_text(
        json.dumps({"journals": {"Cancer Res": 8.5, "J Clin Oncol": 20.1}}),
        encoding="utf-8",
    )
    return JournalMetrics(data_path=data)


def test_build_dashboard_stats_aggregates(tmp_path):
    metrics = _metrics(tmp_path)
    articles = [
        ("Cancer Res", "2023 Jan"),
        ("Cancer Res", "2023 Feb"),
        ("J Clin Oncol", "2024"),
        ("Unknown Journal", "2024 May"),
        ("", "2022"),
    ]
    queries = ["SEC61G in lung cancer", "肺癌中 SEC61G 的作用", "SEC61G lung cancer 2024"]
    rewrites = [
        '"SEC61G"[Title/Abstract]',
        "SEC61G",
        '"SEC61G" AND "lung adenocarcinoma"',
    ]

    stats = build_dashboard_stats(
        articles,
        queries,
        rewritten_queries=rewrites,
        metrics=metrics,
    )

    assert stats["total_searches"] == 3
    assert stats["total_articles"] == 5
    assert stats["journals"][0] == {"name": "Cancer Res", "count": 2}
    assert {"year": 2022, "count": 1} in stats["years"]
    assert {"year": 2023, "count": 2} in stats["years"]
    assert {"year": 2024, "count": 2} in stats["years"]
    buckets = {b["bucket"]: b["count"] for b in stats["impact_factor_buckets"]}
    assert buckets["5-10"] == 2  # Cancer Res (8.5)
    assert buckets[">=10"] == 1  # J Clin Oncol (20.1)
    assert buckets["未知"] == 2  # unknown journal + empty journal
    keywords = {k["keyword"]: k["count"] for k in stats["top_keywords"]}
    assert keywords["sec61g"] == 3  # English term from rewritten queries
    assert keywords["肺癌"] == 1  # clean Chinese phrase from raw query
    assert keywords["adenocarcinoma"] == 1  # from quoted phrase in rewrite
    assert "lung" not in keywords and "cancer" not in keywords  # generic terms dropped


def test_build_dashboard_stats_empty():
    stats = build_dashboard_stats(
        [],
        [],
        rewritten_queries=[],
        metrics=JournalMetrics(data_path=__import__("pathlib").Path("nope.json")),
    )
    assert stats == {
        "total_searches": 0,
        "total_articles": 0,
        "journals": [],
        "years": [],
        "impact_factor_buckets": [
            {"bucket": "<3", "count": 0},
            {"bucket": "3-5", "count": 0},
            {"bucket": "5-10", "count": 0},
            {"bucket": ">=10", "count": 0},
            {"bucket": "未知", "count": 0},
        ],
        "top_keywords": [],
        "excluded_keywords": [],
    }


def test_search_stats_endpoint_empty_db(monkeypatch, tmp_path):
    # Isolate from real data/excluded_keywords.json (user-managed runtime state).
    import backend.services.search_stats as search_stats_mod
    monkeypatch.setattr(
        search_stats_mod,
        "_EXCLUDED_PATH",
        tmp_path / "excluded_keywords.json",
    )
    with TestClient(app) as client:
        resp = client.get("/api/v1/search/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_searches"] == 0
    assert body["total_articles"] == 0
    assert body["journals"] == []
    assert body["years"] == []
    assert body["top_keywords"] == []
    assert body["excluded_keywords"] == []


def test_build_dashboard_stats_filters_excluded_keywords(tmp_path):
    metrics = _metrics(tmp_path)
    queries = ["SEC61G in lung cancer", "肺癌中 SEC61G 的作用"]
    rewrites = ['"SEC61G"[Title/Abstract]', "SEC61G"]
    stats = build_dashboard_stats(
        [],
        queries,
        rewritten_queries=rewrites,
        metrics=metrics,
        excluded_keywords={"sec61g"},
    )
    keywords = [k["keyword"] for k in stats["top_keywords"]]
    assert "sec61g" not in keywords
    assert "肺癌" in keywords
    assert stats["excluded_keywords"] == ["sec61g"]


def test_search_stats_endpoint_returns_aggregates():
    async def _seed():
        async with TestSession() as session:
            session.add(Search(query_text="SEC61G lung cancer", status="completed"))
            await session.flush()
            search_id = (await session.execute(select(Search))).scalars().first().id
            session.add(
                Article(
                    search_id=search_id,
                    pmid="1",
                    title="t",
                    journal="Cancer Res",
                    publish_date="2024",
                )
            )
            await session.commit()

    asyncio.run(_seed())
    with TestClient(app) as client:
        resp = client.get("/api/v1/search/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_searches"] == 1
    assert body["total_articles"] == 1
    assert body["journals"] == [{"name": "Cancer Res", "count": 1}]
    assert body["years"] == [{"year": 2024, "count": 1}]
