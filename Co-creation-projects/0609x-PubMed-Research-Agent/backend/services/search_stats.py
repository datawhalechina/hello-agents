# -*- coding: utf-8 -*-
"""Dashboard aggregations for GET /api/v1/search/stats.

Aggregates stored searches and articles into the stats shape consumed by
the research dashboard. Trending keywords are extracted from both the
rewritten PubMed query (English terms inside quoted phrases) and the
original query (Chinese phrases), then filtered against a user-managed
exclusion list persisted in data/excluded_keywords.json.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Optional, Sequence, Set, Tuple

from backend.services.journal_metrics import JournalMetrics

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_EXCLUDED_PATH = _DATA_DIR / "excluded_keywords.json"

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")
_CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff]+")

# Low-signal English terms (generic biomedical words) dropped from keywords.
_EN_STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was",
    "were", "has", "have", "had", "not", "but", "can", "you", "what",
    "how", "why", "who", "which", "when", "where", "into", "its", "his",
    "her", "our", "their", "your", "via", "per", "using", "based", "role",
    "study", "studies", "effect", "effects", "impact", "level", "levels",
    "cell", "cells", "gene", "genes", "protein", "proteins", "patient",
    "patients", "analysis", "expression", "human", "related", "associated",
    "treatment", "therapy", "therapies", "mechanism", "mechanisms",
    "clinical", "review", "current", "novel", "disease", "diseases",
    "cancer", "tumor", "tumour", "tumors", "lung", "breast", "liver",
    "kidney", "colon", "gastric", "pancreatic", "prostate", "ovarian",
    "neoplasms", "neoplasm", "carcinoma", "carcinomas", "malignant",
    "malignancy", "biology", "molecular", "research", "function",
    "functions", "potential", "important", "significant",
}

# Function characters stripped from Chinese query runs.
_CJK_STOP_CHARS = set("在的中了与和等是及为对从到之者或其个和")
# Generic Chinese suffixes/words removed so the remaining run is the topic.
_CJK_STOP_WORDS = (
    "作用", "机制", "研究", "分析", "影响", "表达", "相关", "临床",
    "水平", "患者", "治疗", "预后", "分子", "进行", "通过", "可以",
    "显示", "发现", "表明", "意义", "价值",
)

_IF_BUCKET_ORDER = ["<3", "3-5", "5-10", ">=10", "未知"]


def extract_year(publish_date: str) -> Optional[int]:
    """Best-effort extraction of a 4-digit year from a PubMed date string."""
    match = _YEAR_RE.search(publish_date or "")
    return int(match.group(0)) if match else None


def impact_factor_bucket(impact_factor: Optional[float]) -> str:
    """Bucket an impact factor (None -> unknown)."""
    if impact_factor is None:
        return "未知"
    if impact_factor < 3:
        return "<3"
    if impact_factor < 5:
        return "3-5"
    if impact_factor < 10:
        return "5-10"
    return ">=10"


def _cjk_phrases(text: str) -> list[str]:
    """Extract clean Chinese topic phrases from a query.

    Removes function characters and generic suffixes so that
    "SEC61G在肺癌中的作用" yields "肺癌" instead of character bigrams.
    """
    phrases: list[str] = []
    for run in _CJK_RUN_RE.findall(text or ""):
        cleaned = "".join(ch for ch in run if ch not in _CJK_STOP_CHARS)
        for word in _CJK_STOP_WORDS:
            cleaned = cleaned.replace(word, "")
        if len(cleaned) >= 2:
            phrases.append(cleaned)
    return phrases


def _rewritten_terms(rewritten: str) -> list[str]:
    """Extract English keywords from a rewritten PubMed query.

    Prefers the semantic phrases the LLM wrapped in quotes; falls back to
    plain tokenization for rewrites without quotes.
    """
    rewritten = rewritten or ""
    quoted = re.findall(r'"([^"]+)"', rewritten)
    sources = quoted if quoted else [rewritten]
    terms: list[str] = []
    for source in sources:
        for tok in _TOKEN_RE.findall(source):
            tok = tok.lower()
            if len(tok) >= 3 and tok not in _EN_STOP_WORDS:
                terms.append(tok)
    return terms


def _query_keywords(raw: str, rewritten: str) -> list[str]:
    """Combine English terms (rewritten query) and Chinese phrases (raw query)."""
    terms: Set[str] = set()
    terms.update(_rewritten_terms(rewritten))
    terms.update(_cjk_phrases(raw))
    return list(terms)


def build_dashboard_stats(
    articles: Sequence[Tuple[str, str]],
    queries: Sequence[str],
    rewritten_queries: Optional[Sequence[str]] = None,
    metrics: Optional[JournalMetrics] = None,
    excluded_keywords: Optional[Set[str]] = None,
    top_n: int = 10,
) -> dict:
    """Aggregate article (journal, publish_date) rows and query texts.

    Parameters
    ----------
    articles :
        Sequence of (journal, publish_date) tuples.
    queries :
        Original research question texts, one per stored search.
    rewritten_queries :
        Rewritten PubMed query per stored search (aligned with ``queries``).
    excluded_keywords :
        Keywords to hide from the trending list.

    Returns a plain dict matching ``DashboardStatsOut``.
    """
    metrics = metrics if metrics is not None else JournalMetrics()
    excluded = set(excluded_keywords or [])
    rewrites = rewritten_queries if rewritten_queries is not None else [""] * len(queries)

    journals: Counter[str] = Counter()
    years: Counter[int] = Counter()
    if_buckets: Counter[str] = Counter()

    for journal, publish_date in articles:
        if_buckets[impact_factor_bucket(metrics.impact_factor(journal))] += 1
        if journal:
            journals[journal] += 1
        year = extract_year(publish_date)
        if year is not None:
            years[year] += 1

    keywords: Counter[str] = Counter()
    for raw, rewritten in zip(queries, rewrites):
        for term in _query_keywords(raw, rewritten):
            if term not in excluded:
                keywords[term] += 1

    return {
        "total_searches": len(queries),
        "total_articles": len(articles),
        "journals": [
            {"name": name, "count": count}
            for name, count in journals.most_common(top_n)
        ],
        "years": [
            {"year": year, "count": count}
            for year, count in sorted(years.items())
        ],
        "impact_factor_buckets": [
            {"bucket": bucket, "count": if_buckets.get(bucket, 0)}
            for bucket in _IF_BUCKET_ORDER
        ],
        "top_keywords": [
            {"keyword": keyword, "count": count}
            for keyword, count in keywords.most_common(top_n)
        ],
        "excluded_keywords": sorted(excluded),
    }


def load_excluded_keywords() -> Set[str]:
    """Load the persisted keyword exclusion list (empty set on any failure)."""
    try:
        data = json.loads(_EXCLUDED_PATH.read_text(encoding="utf-8"))
        return set(data.get("keywords", []))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return set()


def save_excluded_keywords(keywords: Set[str]) -> None:
    """Persist the keyword exclusion list to data/excluded_keywords.json."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _EXCLUDED_PATH.write_text(
        json.dumps({"keywords": sorted(keywords)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
