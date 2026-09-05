"""Port-based benchmark execution with per-case failure isolation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from resume_agent.application.ports import FactAuditAgent, QuestionWriterAgent
from resume_agent.application.question_planner import QuestionPlan
from resume_agent.domain.models import (
    CareerFactBase,
    InterviewMessage,
    InterviewSession,
)
from resume_agent.evaluation.models import (
    AuditEvaluationCase,
    BenchmarkReport,
    CaseScore,
    MentorDataset,
    QuestionEvaluationCase,
)
from resume_agent.evaluation.scoring import score_proposal, score_question


_SAFE_METADATA_KEYS = ("framework", "model")


class MentorBenchmark:
    def __init__(
        self,
        question_writer: QuestionWriterAgent,
        fact_auditor: FactAuditAgent,
    ) -> None:
        self.question_writer = question_writer
        self.fact_auditor = fact_auditor

    def run(
        self,
        dataset: MentorDataset,
        *,
        repeats: int = 1,
        metadata: Mapping[str, object] | None = None,
    ) -> BenchmarkReport:
        if repeats < 1:
            raise ValueError("repeats must be at least 1")

        scores: list[CaseScore] = []
        for _ in range(repeats):
            for case in dataset.cases:
                if isinstance(case, QuestionEvaluationCase):
                    scores.append(self._run_question(case))
                else:
                    scores.append(self._run_audit(case))

        return BenchmarkReport(
            dataset_version=dataset.version,
            repeats=repeats,
            metadata=self._safe_metadata(metadata),
            scores=scores,
            metrics=_aggregate_metrics(scores),
        )

    def _run_question(self, case: QuestionEvaluationCase) -> CaseScore:
        attempts = {
            "direct": 0,
            "recall_anchors": 1,
            "alternative_evidence": 2,
        }
        plan = QuestionPlan(
            dimension=case.dimension,
            priority=1.0,
            attempt=attempts[case.escalation],
            escalation=case.escalation,
        )
        try:
            question = self.question_writer.write(
                plan,
                case.experience.model_copy(deep=True),
                case.target.model_copy(deep=True),
            )
        except Exception as error:
            return score_question(case, None, error=error)
        return score_question(case, question)

    def _run_audit(self, case: AuditEvaluationCase) -> CaseScore:
        experience = case.experience.model_copy(deep=True)
        base = CareerFactBase(
            target=case.target.model_copy(deep=True),
            experiences=[experience],
        )
        session = InterviewSession(
            fact_base_id=base.id,
            active_experience_id=experience.id,
            messages=[InterviewMessage(role="user", content=case.message)],
        )
        try:
            proposal = self.fact_auditor.propose(case.message, session, base)
        except Exception as error:
            return score_proposal(case, None, error=error)
        return score_proposal(case, proposal)

    @staticmethod
    def _safe_metadata(metadata: Mapping[str, object] | None) -> dict[str, str]:
        values = metadata or {}
        return {
            key: str(values[key])
            for key in _SAFE_METADATA_KEYS
            if key in values and values[key] is not None
        }


def _rate(scores: Sequence[CaseScore], check: str | None = None) -> float:
    if not scores:
        return 1.0
    if check is None:
        passed = sum(score.passed for score in scores)
    else:
        passed = sum(score.checks.get(check, False) for score in scores)
    return passed / len(scores)


def _aggregate_metrics(scores: Sequence[CaseScore]) -> dict[str, float]:
    question_scores = [score for score in scores if score.kind == "question"]
    audit_scores = [score for score in scores if score.kind == "audit"]
    return {
        "runtime_success_rate": _rate(scores, "runtime_success"),
        "question_contract_pass_rate": _rate(question_scores),
        "audit_dimension_accuracy": _rate(audit_scores, "dimension_exact"),
        "evidence_recall_rate": _rate(audit_scores, "required_evidence_retained"),
        "hallucination_free_rate": _rate(audit_scores, "hallucination_free"),
        "confidence_label_accuracy": _rate(audit_scores, "confidence_exact"),
        "sensitivity_label_accuracy": _rate(audit_scores, "sensitivity_exact"),
        "strict_pass_rate": _rate(scores),
    }
