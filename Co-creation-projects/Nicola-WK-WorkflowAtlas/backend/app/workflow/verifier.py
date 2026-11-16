"""Literal evidence verification, distinct from semantic truth or human review."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from pydantic import ValidationError

from app.connectors.context import display_text
from app.resolution.projects import canonical_name
from app.schemas import EvidenceReference, StandardMessage, WorkFact


def message_index(messages: Sequence[StandardMessage]) -> dict[tuple[str, str], StandardMessage]:
    """Exclude conflicting identities instead of resolving them by input ordering."""
    index: dict[tuple[str, str], StandardMessage] = {}
    conflicts: set[tuple[str, str]] = set()
    for message in messages:
        key = (message.source_id, message.id)
        if key in index and index[key] != message:
            conflicts.add(key)
        else:
            index[key] = message
    return {key: value for key, value in index.items() if key not in conflicts}


def verify_evidence(
    evidence: EvidenceReference | Sequence[EvidenceReference],
    messages: Sequence[StandardMessage],
) -> bool:
    """True iff every nonempty quote is in its exact source/message.

    Empty collections, conflicting message identities, wrong sources and invented
    quotes fail closed. Passing means source support exists; it does not establish
    that an interpretation is true or that a human has approved it.
    """
    references = [evidence] if isinstance(evidence, EvidenceReference) else list(evidence)
    return verify_references(references, message_index(messages))


def verify_references(
    evidence: Sequence[EvidenceReference],
    index: dict[tuple[str, str], StandardMessage],
) -> bool:
    if not evidence:
        return False
    return all(
        bool(reference.quote.strip())
        and (message := index.get((reference.source_id, reference.message_id))) is not None
        and reference.quote in message.text
        for reference in evidence
    )


def fact_verification_errors(
    fact: WorkFact, index: dict[tuple[str, str], StandardMessage]
) -> list[str]:
    errors: list[str] = []
    if not verify_references(fact.evidence, index):
        errors.append("missing, conflicting or nonliteral source evidence")
    if not fact.summary.strip():
        errors.append("empty fact summary")
    if fact.confidence < 0.5:
        errors.append("fact confidence below conservative graph threshold 0.5")
    if not _aware(fact.occurred_at):
        errors.append("fact timestamp lacks timezone")
    elif verify_references(fact.evidence, index):
        latest = max(index[(item.source_id, item.message_id)].timestamp for item in fact.evidence)
        # Plans can describe the future. Other occurrences cannot be established
        # by evidence that predates the claimed occurrence.
        if fact.kind != "plan" and fact.occurred_at > latest:
            errors.append("fact occurrence follows all source evidence")
    errors.extend(_project_attribution_errors(fact, index))
    return errors


def _project_attribution_errors(fact: WorkFact, index: dict[tuple[str, str], StandardMessage]) -> list[str]:
    attribution = fact.attributes.get("project_attribution")
    if attribution is None:
        return []  # Compatibility for previous providers without contextual attribution.
    if not isinstance(attribution, dict):
        return ["malformed project attribution"]
    method = attribution.get("method")
    if method == "unassigned":
        return ["unassigned attribution conflicts with project hint"] if fact.project_hint else []
    if method not in {"explicit", "section", "catalog", "reply"} or not fact.project_hint:
        return ["unsupported project attribution method or missing project hint"]
    raw = attribution.get("support", attribution.get("evidence"))
    if not isinstance(raw, list) or not raw:
        return ["project attribution lacks supporting evidence"]
    try:
        support = [EvidenceReference.model_validate(item) for item in raw]
    except (ValidationError, TypeError, ValueError):
        return ["project attribution has invalid supporting references"]
    if not verify_references(support, index) or any(ref not in fact.evidence for ref in support):
        return ["project attribution evidence is not bound to the fact's literal evidence"]
    primary = index.get((fact.evidence[0].source_id, fact.evidence[0].message_id))
    if primary is None:
        return ["project attribution has no primary observation"]
    for ref in support:
        origin = index[(ref.source_id, ref.message_id)]
        if origin.source_id != primary.source_id or origin.chat_id != primary.chat_id or origin.timestamp > primary.timestamp:
            return ["project attribution context crosses source/chat or follows the observation"]
    hint = canonical_name(fact.project_hint)
    if not any(hint in canonical_name(display_text(ref.quote)) for ref in support):
        return ["project name is absent from attribution evidence"]
    return []


def _aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
