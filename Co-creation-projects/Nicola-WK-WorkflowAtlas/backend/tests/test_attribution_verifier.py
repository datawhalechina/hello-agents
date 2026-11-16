"""Project context claims require their own source evidence, not just a task quote."""
from datetime import datetime, timedelta, timezone

from app.schemas import EvidenceReference, StandardMessage, WorkFact
from app.workflow.verifier import fact_verification_errors, message_index


def context_case():
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    parent = StandardMessage(id="parent", source_id="invented", chat_id="room", text="青禾项目", timestamp=timestamp)
    child = StandardMessage(id="child", source_id="invented", chat_id="room", text="开始测试设备", timestamp=timestamp + timedelta(minutes=1))
    support = EvidenceReference(message_id=parent.id, source_id=parent.source_id, quote=parent.text)
    fact = WorkFact(id="f", kind="task", summary=child.text, project_hint="青禾项目", occurred_at=child.timestamp,
                    evidence=[EvidenceReference(message_id=child.id, source_id=child.source_id, quote=child.text), support],
                    attributes={"project_attribution": {"method": "reply", "support": [support.model_dump()], "review_required": True}})
    return parent, child, fact


def test_attribution_verifier_accepts_literal_same_chat_past_support():
    parent, child, fact = context_case()
    assert not fact_verification_errors(fact, message_index([parent, child]))


def test_attribution_verifier_rejects_unbound_or_unrelated_support():
    parent, child, fact = context_case()
    for claim in ("虚构另一个项目", "完全不存在项目"):
        changed = fact.model_copy(deep=True)
        changed.project_hint = claim
        assert fact_verification_errors(changed, message_index([parent, child]))
    changed = fact.model_copy(deep=True)
    changed.evidence = changed.evidence[:1]
    assert fact_verification_errors(changed, message_index([parent, child]))


def test_attribution_verifier_rejects_cross_chat_and_future_context():
    parent, child, fact = context_case()
    for changed in (parent.model_copy(update={"chat_id": "another-room"}), parent.model_copy(update={"timestamp": child.timestamp + timedelta(days=1)})):
        assert fact_verification_errors(fact, message_index([changed, child]))
