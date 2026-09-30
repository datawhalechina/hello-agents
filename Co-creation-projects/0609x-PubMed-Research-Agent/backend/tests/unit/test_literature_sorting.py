"""Unit tests for services/literature_sorting.py and services/journal_metrics.py"""

from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.services.literature_sorting import (
    parse_pub_date,
    sort_articles,
    filter_articles,
)
from backend.services.journal_metrics import JournalMetrics


class Article:
    """Lightweight stand-in matching PubMedArticle's relevant fields."""

    def __init__(self, pmid, publish_date, journal):
        self.pmid = pmid
        self.publish_date = publish_date
        self.journal = journal


@pytest.fixture
def metrics():
    return JournalMetrics(
        data_path=os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "data", "journal_metrics.json"
        )
    )


class TestParsePubDate:
    def test_full_date(self):
        assert str(parse_pub_date("2025 Mar 12")) == "2025-03-12"

    def test_year_month(self):
        assert str(parse_pub_date("2025 Mar")) == "2025-03-01"

    def test_year_only(self):
        assert str(parse_pub_date("2025")) == "2025-01-01"

    def test_month_range(self):
        assert str(parse_pub_date("2025 Mar-Apr")) == "2025-03-01"

    def test_nov_dec(self):
        assert str(parse_pub_date("2024 Nov-Dec")) == "2024-11-01"

    def test_empty_and_invalid(self):
        assert parse_pub_date("") is None
        assert parse_pub_date("   ") is None
        assert parse_pub_date("not a date") is None


class TestSortArticles:
    def test_relevance_keeps_order(self):
        arts = [Article("1", "2020", "A"), Article("2", "2024", "B")]
        assert [a.pmid for a in sort_articles(arts, "relevance")] == ["1", "2"]

    def test_date_desc(self):
        arts = [
            Article("1", "2021 Jan", "A"),
            Article("2", "2025 Mar 12", "B"),
            Article("3", "2023", "C"),
            Article("4", "", "D"),
        ]
        out = [a.pmid for a in sort_articles(arts, "date_desc")]
        assert out == ["2", "3", "1", "4"]  # newest first, unknown last

    def test_date_asc(self):
        arts = [
            Article("1", "2025", "A"),
            Article("2", "2021 Jan", "B"),
            Article("3", "", "C"),
        ]
        out = [a.pmid for a in sort_articles(arts, "date_asc")]
        assert out == ["2", "1", "3"]

    def test_unknown_sort_falls_back(self):
        arts = [Article("1", "2020", "A"), Article("2", "2024", "B")]
        assert [a.pmid for a in sort_articles(arts, "bogus")] == ["1", "2"]

    def test_dict_articles(self):
        arts = [
            {"pmid": "1", "publish_date": "2020", "journal": "A"},
            {"pmid": "2", "publish_date": "2025", "journal": "B"},
        ]
        assert [a["pmid"] for a in sort_articles(arts, "date_desc")] == ["2", "1"]


class TestFilterArticles:
    def test_year_window(self):
        arts = [
            Article("1", "2021 Jan", "A"),
            Article("2", "2025 Mar", "B"),
            Article("3", "2023", "C"),
        ]
        kept, dropped = filter_articles(arts, min_year=2022, max_year=2025)
        assert [a.pmid for a in kept] == ["2", "3"]
        assert dropped == 1

    def test_year_keeps_unparseable(self):
        arts = [Article("1", "", "A"), Article("2", "2020", "B")]
        kept, dropped = filter_articles(arts, min_year=2021)
        assert [a.pmid for a in kept] == ["1"]
        assert dropped == 1

    def test_impact_factor_filter(self, metrics):
        arts = [
            Article("1", "2023", "Cancer Cell Int"),   # 5.3
            Article("2", "2023", "Nature"),            # 50.5
            Article("3", "2023", "Sci Rep"),           # 3.8 (below 6.0)
            Article("4", "2023", "Unknown Journal"),   # None -> kept
        ]
        kept, dropped = filter_articles(
            arts, min_impact_factor=6.0, journal_metrics=metrics
        )
        assert [a.pmid for a in kept] == ["2", "4"]
        assert dropped == 2

    def test_no_filters_keeps_all(self):
        arts = [Article("1", "2023", "A"), Article("2", "2024", "B")]
        kept, dropped = filter_articles(arts)
        assert len(kept) == 2
        assert dropped == 0

    def test_requires_journal_metrics(self):
        arts = [Article("1", "2023", "A")]
        with pytest.raises(ValueError, match="journal_metrics"):
            filter_articles(arts, min_impact_factor=5.0)


class TestJournalMetrics:
    def test_lookup_normalized(self, metrics):
        assert metrics.impact_factor("Br. J. Cancer") == 7.5
        assert metrics.impact_factor("Nature") == 50.5

    def test_unknown_journal(self, metrics):
        assert metrics.impact_factor("Some Random Journal") is None

    def test_is_known(self, metrics):
        assert metrics.is_known("Nature")
        assert not metrics.is_known("Nope Nope")
