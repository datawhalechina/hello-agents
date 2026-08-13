"""Deterministic, privacy-safe hard gates for mentor agent outputs."""

from __future__ import annotations

from resume_agent.domain.models import ConfidenceStatus, FactProposal
from resume_agent.evaluation.models import (
    AuditEvaluationCase,
    CaseScore,
    QuestionEvaluationCase,
)


def _contains(text: str, fragment: str) -> bool:
    return fragment.casefold() in text.casefold()


def _safe_error_category(error: BaseException | None) -> str | None:
    return type(error).__name__ if error is not None else None


def score_question(
    case: QuestionEvaluationCase,
    output: str | None,
    *,
    error: BaseException | None = None,
) -> CaseScore:
    runtime_success = error is None and output is not None
    text = output or ""
    question_marks = text.count("?") + text.count("？")
    checks = {
        "runtime_success": runtime_success,
        "single_question": runtime_success
        and question_marks == case.expected_question_marks,
        "required_language": runtime_success
        and any(_contains(text, fragment) for fragment in case.must_include_any),
        "forbidden_language_absent": runtime_success
        and all(not _contains(text, fragment) for fragment in case.must_not_include),
    }
    return CaseScore(
        case_id=case.id,
        kind=case.kind,
        checks=checks,
        error_category=_safe_error_category(error),
    )


def score_proposal(
    case: AuditEvaluationCase,
    proposal: FactProposal | None,
    *,
    error: BaseException | None = None,
) -> CaseScore:
    runtime_success = error is None and proposal is not None
    values = proposal.values if proposal is not None else []
    fact_text = "\n".join(value.text for value in values)

    def labels_match(attribute: str, expected: object | None) -> bool:
        return expected is None or (
            bool(values) and all(getattr(value, attribute) == expected for value in values)
        )

    checks = {
        "runtime_success": runtime_success,
        "dimension_exact": runtime_success
        and proposal.dimension == case.expected_dimension,
        "required_evidence_retained": runtime_success
        and all(
            _contains(fact_text, fragment) for fragment in case.required_fact_fragments
        ),
        "hallucination_free": runtime_success
        and all(
            not _contains(fact_text, fragment)
            for fragment in case.forbidden_fact_fragments
        ),
        "confidence_exact": runtime_success
        and labels_match("confidence", case.expected_confidence),
        "specificity_exact": runtime_success
        and labels_match("specificity", case.expected_specificity),
        "sensitivity_exact": runtime_success
        and labels_match("sensitive", case.expected_sensitive),
        "source_linked": runtime_success
        and bool(values)
        and all(value.source_message_ids for value in values),
        "unconfirmed_only": runtime_success
        and bool(values)
        and all(value.confidence is not ConfidenceStatus.CONFIRMED for value in values),
    }
    return CaseScore(
        case_id=case.id,
        kind=case.kind,
        checks=checks,
        error_category=_safe_error_category(error),
    )
