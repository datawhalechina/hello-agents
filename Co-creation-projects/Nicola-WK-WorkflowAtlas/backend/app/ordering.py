"""Preserve observed chronology and clause order without claiming causality."""
from .schemas import WorkFact


def fact_order_key(fact: WorkFact) -> tuple[float, str, str, int, str]:
    occurred = fact.occurred_at.timestamp() if fact.occurred_at.tzinfo is not None else float("inf")
    primary = fact.evidence[0] if fact.evidence else None
    span = fact.attributes.get("source_span")
    start = span.get("start", -1) if isinstance(span, dict) else -1
    return (occurred, primary.source_id if primary else "", primary.message_id if primary else "", start if isinstance(start, int) else -1, fact.id)
