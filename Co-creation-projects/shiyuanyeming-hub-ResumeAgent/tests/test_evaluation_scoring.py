from uuid import uuid4

from resume_agent.domain.models import (
    ConfidenceStatus,
    FactProposal,
    FactValue,
    QualityDimension,
    Specificity,
)
from resume_agent.evaluation.models import AuditEvaluationCase, QuestionEvaluationCase
from resume_agent.evaluation.scoring import score_proposal, score_question


def make_question_case(**updates):
    payload = {
        "id": "q-result",
        "kind": "question",
        "target": {"role": "数据分析师"},
        "experience": {"organization": "云数科技", "role": "分析师"},
        "dimension": "result",
        "escalation": "direct",
        "must_include_any": ["结果", "变化"],
        "must_not_include": ["身份证", "一定提升"],
        "expected_question_marks": 1,
    }
    payload.update(updates)
    return QuestionEvaluationCase.model_validate(payload)


def make_audit_case(**updates):
    payload = {
        "id": "a-evidence",
        "kind": "audit",
        "target": {"role": "数据分析师"},
        "experience": {"organization": "云数科技", "role": "分析师"},
        "message": "大约覆盖500名用户，这个数字需要保密",
        "expected_dimension": "evidence",
        "required_fact_fragments": ["500", "用户"],
        "forbidden_fact_fragments": ["营收", "1000"],
        "expected_confidence": "estimated",
        "expected_specificity": "concrete",
        "expected_sensitive": True,
    }
    payload.update(updates)
    return AuditEvaluationCase.model_validate(payload)


def make_proposal(**value_updates):
    value = FactValue(
        text="大约覆盖500名用户，这个数字需要保密",
        confidence=ConfidenceStatus.ESTIMATED,
        specificity=Specificity.CONCRETE,
        sensitive=True,
        source_message_ids=[uuid4()],
    ).model_copy(update=value_updates)
    return FactProposal(
        fact_base_revision=0,
        experience_id=uuid4(),
        dimension=QualityDimension.EVIDENCE,
        values=[value],
    )


def test_question_score_names_each_independent_contract_check():
    score = score_question(make_question_case(), "这项工作最终产生了什么结果或变化？")

    assert score.passed is True
    assert score.checks == {
        "runtime_success": True,
        "single_question": True,
        "required_language": True,
        "forbidden_language_absent": True,
    }


def test_question_multiple_or_coercive_question_fails_only_relevant_checks():
    score = score_question(
        make_question_case(),
        "结果是什么？请提供身份证？",
    )

    assert score.checks["single_question"] is False
    assert score.checks["required_language"] is True
    assert score.checks["forbidden_language_absent"] is False
    assert score.passed is False


def test_audit_score_accepts_grounded_estimated_sensitive_fact():
    score = score_proposal(make_audit_case(), make_proposal())

    assert score.passed is True
    assert all(score.checks.values())


def test_audit_wrong_dimension_and_hallucination_fail_independently():
    proposal = make_proposal(text="大约覆盖500名用户并带来1000万元营收")
    proposal.dimension = QualityDimension.RESULT

    score = score_proposal(make_audit_case(), proposal)

    assert score.checks["dimension_exact"] is False
    assert score.checks["required_evidence_retained"] is True
    assert score.checks["hallucination_free"] is False


def test_audit_label_and_source_failures_are_visible():
    proposal = make_proposal(
        confidence=ConfidenceStatus.CONFIRMED,
        specificity=Specificity.PRESENT,
        sensitive=False,
        source_message_ids=[],
    )

    score = score_proposal(make_audit_case(), proposal)

    assert score.checks["confidence_exact"] is False
    assert score.checks["specificity_exact"] is False
    assert score.checks["sensitivity_exact"] is False
    assert score.checks["source_linked"] is False
    assert score.checks["unconfirmed_only"] is False


def test_runtime_error_score_contains_safe_category_not_raw_output():
    score = score_question(
        make_question_case(),
        None,
        error=RuntimeError("secret provider response"),
    )

    assert score.passed is False
    assert score.error_category == "RuntimeError"
    assert "secret" not in score.model_dump_json()
