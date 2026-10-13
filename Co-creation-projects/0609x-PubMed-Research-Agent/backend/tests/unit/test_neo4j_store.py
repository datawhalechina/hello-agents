# -*- coding: utf-8 -*-
"""Unit tests for services/neo4j_store.py (Neo4jGraphStore).

A fake neo4j package is injected into sys.modules and the module flag is
flipped inside a fixture so the tests run without the real driver or
network access, regardless of import order.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest

from backend.services import neo4j_store as ns
from backend.services.neo4j_store import Neo4jGraphStore, Neo4jStoreError


# ---------------------------------------------------------------------------
# Fake neo4j driver package
# ---------------------------------------------------------------------------

class FakeTx:
    def __init__(self, driver):
        self.driver = driver

    def run(self, cypher, **params):
        self.driver.queries.append((cypher, dict(params)))


class FakeSession:
    def __init__(self, driver):
        self.driver = driver

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute_write(self, fn, **kwargs):
        tx = FakeTx(self.driver)
        fn(tx, **kwargs)

    def run(self, cypher, **params):
        self.driver.queries.append((cypher, dict(params)))
        return FakeResult(self.driver)


class FakeResult:
    def __init__(self, driver):
        self.driver = driver

    def __iter__(self):
        return iter(self.driver.result_records)

    def single(self):
        if self.driver.result_records:
            return self.driver.result_records.pop(0)
        return None


class FakeDriver:
    def __init__(self):
        self.queries = []
        self.ready = True
        self.result_records = []
        self.stats = {"papers": 3, "authors": 5, "journals": 2}

    def verify_connectivity(self):
        if not self.ready:
            raise RuntimeError("neo4j down")

    def session(self, database=None):
        return FakeSession(self)

    def close(self):
        self.ready = False


class FakeGraphDatabase:
    last_driver = None

    @classmethod
    def driver(cls, uri, auth):
        cls.last_driver = FakeDriver()
        cls.last_driver.uri = uri
        cls.last_driver.auth = auth
        return cls.last_driver


def _build_fake_module():
    fake = types.ModuleType("neo4j")
    fake.GraphDatabase = FakeGraphDatabase
    return fake


@pytest.fixture(scope="module", autouse=True)
def _fake_neo4j_env():
    fake = _build_fake_module()
    orig_mod = sys.modules.get("neo4j")
    sys.modules["neo4j"] = fake

    orig_available = ns._NEO4J_AVAILABLE
    orig_db = ns.GraphDatabase
    ns._NEO4J_AVAILABLE = True
    ns.GraphDatabase = FakeGraphDatabase

    yield

    ns._NEO4J_AVAILABLE = orig_available
    ns.GraphDatabase = orig_db
    if orig_mod is not None:
        sys.modules["neo4j"] = orig_mod
    else:
        sys.modules.pop("neo4j", None)


def _article_dict(pmid="1", title="T", abstract="A", journal="Cancer Res", publish_date="2024 May"):
    return {
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
        "doi": "",
        "authors": [{"last_name": "Smith", "fore_name": "J"}],
        "journal": journal,
        "publish_date": publish_date,
        "publication_type": "",
    }


@pytest.fixture
def store():
    return Neo4jGraphStore(
        uri="neo4j+s://test.databases.neo4j.io",
        username="neo4j",
        password="secret",
        database="neo4j",
    )


def test_driver_created_lazily(store):
    assert store._driver is None
    driver = store.driver
    assert driver is not None
    assert store._driver is driver


def test_upsert_articles_writes_paper_author_journal(store):
    n = store.upsert_articles([_article_dict("1")])
    assert n == 1
    queries = "".join(q[0] for q in store.driver.queries)
    assert "MERGE (p:Paper {pmid: $pmid})" in queries
    assert "AUTHORED" in queries
    assert "PUBLISHED_IN" in queries


def test_upsert_empty_returns_zero(store):
    assert store.upsert_articles([]) == 0


def test_upsert_article_without_journal_skips_journal(store):
    article = _article_dict("2", journal="")
    store.upsert_articles([article])
    queries = "".join(q[0] for q in store.driver.queries)
    assert "AUTHORED" in queries
    assert "PUBLISHED_IN" not in queries


def test_related_papers_uses_undirected_pattern(store):
    store.driver.result_records = []
    store.related_papers("1", limit=5)
    query = store.driver.queries[-1][0]
    assert "-[:AUTHORED|PUBLISHED_IN]-" in query
    assert "]->(shared)" not in query
    assert "<-[:AUTHORED|PUBLISHED_IN]-(other" not in query


def test_related_papers_returns_rows(store):
    store.driver.result_records = [
        {
            "pmid": "200",
            "title": "Other paper",
            "overlap": 2,
            "shared_authors": ["Smith J"],
            "shared_journals": ["Cancer Res"],
        },
        {
            "pmid": "300",
            "title": "Third paper",
            "overlap": 1,
            "shared_authors": [],
            "shared_journals": ["Cancer Res"],
        },
    ]
    rows = store.related_papers("1", limit=5)
    assert len(rows) == 2
    assert rows[0]["pmid"] == "200"
    assert rows[0]["overlap"] == 2
    assert rows[0]["shared_authors"] == ["Smith J"]


def test_stats_returns_counts(store):
    store.driver.result_records = [
        {"n": 3},
        {"n": 5},
        {"n": 2},
    ]
    stats = store.stats()
    assert stats == {"papers": 3, "authors": 5, "journals": 2}


def test_subgraph_builds_nodes_and_links(monkeypatch, store):
    store.driver.result_records = []
    monkeypatch.setattr(
        store,
        "related_papers",
        lambda pmid, limit=10: [
            {
                "pmid": "200",
                "title": "Other paper",
                "overlap": 2,
                "shared_authors": ["Wang"],
                "shared_journals": [],
            },
            {
                "pmid": "300",
                "title": "Third paper",
                "overlap": 1,
                "shared_authors": ["Li"],
                "shared_journals": ["Cancer Res"],
            },
        ],
    )

    class _One:
        def __init__(self, rec):
            self.rec = rec

        def single(self):
            return self.rec

    class _ScriptedSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def run(self, cypher, **params):
            if "collect(DISTINCT a.name)" in cypher:
                return _One(
                    {
                        "title": "Center paper",
                        "authors": ["Wang", "Li"],
                        "journals": ["Cancer Res"],
                    }
                )
            raise AssertionError("subgraph should reuse related_papers relationship reasons")

    class _Driver:
        def session(self, database=None):
            return _ScriptedSession()

        def close(self):
            pass

    store._driver = _Driver()
    out = store.subgraph("1", limit=10)

    assert out["pmid"] == "1"
    node_ids = {n["id"] for n in out["nodes"]}
    assert "paper:1" in node_ids
    assert "paper:200" in node_ids
    assert "paper:300" in node_ids
    assert "author:Wang" in node_ids
    assert "author:Li" in node_ids
    assert "journal:Cancer Res" in node_ids

    link_types = {(l["source"], l["target"], l["type"]) for l in out["links"]}
    assert ("paper:1", "author:Wang", "AUTHORED") in link_types
    assert ("paper:1", "journal:Cancer Res", "PUBLISHED_IN") in link_types
    assert ("paper:1", "paper:200", "RELATED") in link_types
    assert ("author:Wang", "paper:200", "AUTHORED") in link_types
    assert ("journal:Cancer Res", "paper:300", "PUBLISHED_IN") in link_types


def test_paper_details_returns_metadata(store):
    store.driver.result_records = [
        {
            "pmid": "100",
            "title": "Paper title",
            "abstract": "Paper abstract",
            "doi": "10.1/test",
            "year": "2025",
            "journal": "Cancer Res",
            "authors": ["Smith John", "Wang Li"],
        }
    ]
    detail = store.paper_details("100")
    assert detail is not None
    assert detail["pmid"] == "100"
    assert detail["authors"] == ["Smith John", "Wang Li"]
    assert detail["publish_date"] == "2025"


def test_author_name_keeps_given_name():
    assert Neo4jGraphStore._author_name(
        {"last_name": "Smith", "fore_name": "John", "initials": "J"}
    ) == "Smith John"


def test_list_papers_returns_recent_entry_points(store):
    store.driver.result_records = [
        {
            "pmid": "100",
            "title": "Recent paper",
            "journal": "Cancer Res",
            "publish_date": "2025",
        }
    ]
    papers = store.list_papers(limit=10)
    assert papers == [
        {
            "pmid": "100",
            "title": "Recent paper",
            "journal": "Cancer Res",
            "publish_date": "2025",
        }
    ]


def test_is_ready(store):
    assert store.is_ready() is True
    store.driver.ready = False
    assert store.is_ready() is False


def test_missing_driver_raises_informative_error(monkeypatch, store):
    monkeypatch.setattr(ns, "_NEO4J_AVAILABLE", False)
    monkeypatch.setattr(ns, "GraphDatabase", None)
    with pytest.raises(Neo4jStoreError, match="neo4j driver is not installed"):
        _ = store.driver


def test_year_extracted_from_publish_date():
    assert ns._extract_year("2024 May 12") == "2024"
    assert ns._extract_year("2024") == "2024"
    assert ns._extract_year("unknown") == ""


def test_diagnose_reports_connection_error(store):
    assert store.diagnose() == (True, "")
    store.driver.ready = False
    ready, error = store.diagnose()
    assert ready is False
    assert "RuntimeError" in error
    assert "neo4j down" in error


def test_diagnose_reports_missing_driver(monkeypatch, store):
    monkeypatch.setattr(ns, "_NEO4J_AVAILABLE", False)
    monkeypatch.setattr(ns, "GraphDatabase", None)
    ready, error = store.diagnose()
    assert ready is False
    assert "not installed" in error
