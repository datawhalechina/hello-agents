# -*- coding: utf-8 -*-
"""Sorting and filtering helpers for retrieved PubMed articles.

Problem Solved:
    PubMed returns articles in relevance order. Researchers often want to
    browse by publication date (newest/oldest first) or to narrow results
    by year and journal impact factor before summarization.

Design Notes:
    - Sorting is applied locally on the final article list so the displayed
      order always matches the user's choice, regardless of the PubMed API
      order or the hybrid/rerank pipeline.
    - Year filtering keeps articles whose date cannot be parsed (rare) so a
      parsing quirk never silently drops a relevant paper.
    - Impact-factor filtering is strict: only articles with a known impact
      factor at/above the threshold are kept (see services/journal_metrics).
"""

from __future__ import annotations

import datetime as dt
import logging
import re
from typing import Optional, Sequence

logger = logging.getLogger(__name__)

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_DATE_FULL = re.compile(r"(?P<year>\d{4})\s+(?P<month>[A-Za-z]+)\s+(?P<day>\d{1,2})")
_DATE_YEAR_MONTH = re.compile(r"(?P<year>\d{4})\s+(?P<month>[A-Za-z]+)")
_DATE_YEAR_ONLY = re.compile(r"(?P<year>\d{4})")

# Recognized sort keys (API + PubMed-compatible aliases).
SORT_KEYS = {"relevance", "date_desc", "date_asc", "pub_date"}


def parse_pub_date(publish_date: str) -> Optional[dt.date]:
    """Parse a PubMed publish-date string into a date, or None if unparseable.

    Handles the common PubMed formats: "2025 Mar 12", "2025 Mar", "2025",
    "2025 Mar-Apr".
    """
    text = (publish_date or "").strip()
    if not text:
        return None
    match = _DATE_FULL.match(text)
    if match:
        year = int(match.group("year"))
        month = _MONTHS.get(match.group("month").lower()[:3])
        if month is None:
            return None
        try:
            return dt.date(year, month, int(match.group("day")))
        except ValueError:
            return None
    match = _DATE_YEAR_MONTH.match(text)
    if match:
        year = int(match.group("year"))
        month = _MONTHS.get(match.group("month").lower()[:3])
        if month is not None:
            try:
                return dt.date(year, month, 1)
            except ValueError:
                return None
    match = _DATE_YEAR_ONLY.match(text)
    if match:
        year = int(match.group("year"))
        try:
            return dt.date(year, 1, 1)
        except ValueError:
            return None
    return None


def _value(article, key: str, default=None):
    """Read a field from a PubMedArticle, a dict, or any object."""
    if isinstance(article, dict):
        return article.get(key, default)
    return getattr(article, key, default)


def sort_articles(articles: Sequence, sort_by: str) -> list:
    """Sort articles by the given key (relevance keeps the input order).

    Parameters
    ----------
    articles : sequence
        Iterable of PubMedArticle objects or dicts.
    sort_by : str
        One of ``relevance``, ``date_desc``, ``date_asc``.

    Returns
    -------
    list
        A new list in the requested order.
    """
    key = (sort_by or "relevance").lower()
    if key not in SORT_KEYS:
        logger.warning("Unknown sort_by=%r, falling back to relevance", sort_by)
        return list(articles)
    if key in ("relevance",):
        return list(articles)

    ascending = key == "date_asc"

    def _parsed(article):
        return parse_pub_date(_value(article, "publish_date", ""))

    # Articles without a parseable date always sort last, regardless of order.
    dated = [a for a in articles if _parsed(a) is not None]
    undated = [a for a in articles if _parsed(a) is None]
    dated.sort(key=_parsed, reverse=not ascending)
    ordered = dated + undated
    logger.info(
        "Sorted %d articles by %s (%s)",
        len(ordered), key, "ascending" if ascending else "descending",
    )
    return ordered


def filter_articles(
    articles: Sequence,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    min_impact_factor: Optional[float] = None,
    journal_metrics=None,
) -> tuple[list, int]:
    """Filter articles by publication year and journal impact factor.

    Parameters
    ----------
    articles : sequence
        Iterable of PubMedArticle objects or dicts.
    min_year / max_year : int, optional
        Inclusive publication-year window. Articles with an unparseable
        date are kept.
    min_impact_factor : float, optional
        Drop articles from journals with a *known* impact factor below this
        value. Journals missing from the local metrics table are kept, so a
        limited table never silently empties the result set.
    journal_metrics : JournalMetrics, optional
        Lookup table; required when min_impact_factor is set.

    Returns
    -------
    (kept, dropped) : tuple[list, int]
        Filtered list and the number of removed articles.
    """
    kept: list = []
    dropped = 0

    for article in articles:
        # --- year window ---
        if min_year is not None or max_year is not None:
            parsed = parse_pub_date(_value(article, "publish_date", ""))
            year = parsed.year if parsed else None
            if year is not None:
                if min_year is not None and year < min_year:
                    dropped += 1
                    continue
                if max_year is not None and year > max_year:
                    dropped += 1
                    continue

        # --- impact factor (lenient: unknown journals are kept) ---
        if min_impact_factor is not None:
            if journal_metrics is None:
                raise ValueError(
                    "journal_metrics is required when min_impact_factor is set"
                )
            journal = _value(article, "journal", "") or ""
            jif = journal_metrics.impact_factor(journal)
            if jif is not None and jif < min_impact_factor:
                dropped += 1
                continue

        kept.append(article)

    logger.info(
        "Filtered articles: kept=%d dropped=%d", len(kept), dropped,
    )
    return kept, dropped
