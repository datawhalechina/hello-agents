"""Bounded working memory assembled from persisted facts on demand."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.schemas import WorkFact
from app.ordering import fact_order_key


def build_working_memory(facts: list[WorkFact], *, recent_limit: int = 12, entity_limit: int = 20,
                         text_budget: int = 6000) -> dict[str, Any]:
    """Return counts, latest entity states and recent facts within a text budget.

    This is an ephemeral projection, not a second source of truth. Callers must
    prefilter facts to the relevant project/permission scope.
    """
    recent_limit = max(0, min(recent_limit, 100))
    entity_limit = max(0, min(entity_limit, 100))
    budget = max(0, min(text_budget, 50000))
    ordered = sorted(facts, key=fact_order_key, reverse=True)
    counts: dict[str, int] = defaultdict(int)
    for fact in facts:
        counts[str(fact.kind)] += 1
    entity_states: list[dict[str, str]] = []
    recent: list[dict[str, Any]] = []
    seen_entities: set[tuple[str | None, str]] = set()
    remaining = budget
    for fact in ordered:
        if fact.entity_key:
            key = (fact.project_id, fact.entity_key)
            if key not in seen_entities and len(entity_states) < entity_limit:
                cost = len(fact.entity_key) + len(fact.status) + len(fact.id)
                if cost <= remaining:
                    entity_states.append({"entity": fact.entity_key, "status": fact.status, "fact_id": fact.id})
                    remaining -= cost
                    seen_entities.add(key)
        if len(recent) < recent_limit:
            cost = len(fact.summary) + len(fact.id)
            if cost <= remaining:
                recent.append({"id": fact.id, "summary": fact.summary, "verified": fact.verified,
                               "review_status": fact.review_status, "evidence_count": len(fact.evidence)})
                remaining -= cost
    return {"fact_count": len(facts), "kind_counts": dict(sorted(counts.items())),
            "entity_states": entity_states, "recent_facts": recent,
            "text_budget": budget, "text_used": budget - remaining}
