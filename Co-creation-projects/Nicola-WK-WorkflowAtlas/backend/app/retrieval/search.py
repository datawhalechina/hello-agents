"""Bounded lexical + entity retrieval, without claiming vector semantics."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

from app.schemas import WorkFact


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def _tokens(value: str) -> list[str]:
    normalized = _normalize(value)
    latin = re.findall(r"[a-z0-9_]+", normalized)
    chinese = re.findall(r"[\u3400-\u9fff]+", normalized)
    # Character bigrams find Chinese terms without an external tokenizer/model.
    return latin + [word for segment in chinese for word in
                    ([segment] if len(segment) == 1 else [segment[index:index + 2] for index in range(len(segment) - 1)])]


def search_facts(query: str, facts: list[WorkFact], limit: int = 20) -> list[WorkFact]:
    if limit <= 0:
        return []
    limit = min(limit, 1000)
    normalized_query = _normalize(query)
    if not normalized_query:
        return sorted(facts, key=lambda item: (item.occurred_at.isoformat(), item.id), reverse=True)[:limit]
    query_tokens = set(_tokens(query))
    corpus = [_tokens(" ".join([fact.summary, fact.project_hint or "", fact.entity_key or "", fact.actor or ""])) for fact in facts]
    frequency = Counter(token for document in corpus for token in set(document))
    total = max(len(facts), 1)
    scored: list[tuple[float, WorkFact]] = []
    for fact, document in zip(facts, corpus):
        overlap = query_tokens.intersection(document)
        score = sum(math.log(1 + total / (1 + frequency[token])) for token in overlap)
        summary = _normalize(fact.summary)
        if normalized_query in summary:
            score += 3
        for value, weight in [(fact.entity_key, 5), (fact.project_hint, 4), (fact.project_id, 4), (fact.actor, 2)]:
            if value and normalized_query == _normalize(value):
                score += weight
        if score > 0:
            scored.append((score, fact))
    scored.sort(key=lambda pair: (-pair[0], pair[1].id))
    return [fact for _, fact in scored[:limit]]
