import pytest

from resume_agent.domain.models import (
    ConfidenceStatus,
    FactProposal,
    FactValue,
    Specificity,
)
from resume_agent.evaluation.models import MentorDataset
from resume_agent.evaluation.runner import MentorBenchmark


class RecordingQuestionWriter:
    def __init__(self):
        self.calls = []

    def write(self, plan, experience, target):
        self.calls.append((plan, experience, target))
        return "这项工作最终产生了什么结果？"


class RecordingFactAuditor:
    def __init__(self):
        self.calls = []

    def propose(self, message, session, base):
        self.calls.append((message, session, base))
        return FactProposal(
            fact_base_revision=base.revision,
            experience_id=session.active_experience_id,
            dimension="evidence",
            values=[
                FactValue(
                    text="大约覆盖500名用户",
                    confidence=ConfidenceStatus.ESTIMATED,
                    specificity=Specificity.CONCRETE,
                    source_message_ids=[session.messages[-1].id],
                )
            ],
        )


def make_dataset():
    return MentorDataset.model_validate(
        {
            "version": "tiny_v1",
            "cases": [
                {
                    "id": "q-result",
                    "kind": "question",
                    "target": {"role": "数据分析师"},
                    "experience": {"organization": "云数科技", "role": "分析师"},
                    "dimension": "result",
                    "escalation": "recall_anchors",
                    "must_include_any": ["结果"],
                    "must_not_include": ["身份证"],
                },
                {
                    "id": "a-evidence",
                    "kind": "audit",
                    "target": {"role": "数据分析师"},
                    "experience": {"organization": "云数科技", "role": "分析师"},
                    "message": "大约覆盖500名用户",
                    "expected_dimension": "evidence",
                    "required_fact_fragments": ["500", "用户"],
                    "forbidden_fact_fragments": ["营收"],
                    "expected_confidence": "estimated",
                    "expected_specificity": "concrete",
                    "expected_sensitive": False,
                },
            ],
        }
    )


def test_runner_builds_fresh_case_state_and_counts_repeats():
    writer = RecordingQuestionWriter()
    auditor = RecordingFactAuditor()

    report = MentorBenchmark(writer, auditor).run(
        make_dataset(),
        repeats=2,
        metadata={"framework": "fake", "model": "fixture-model"},
    )

    assert len(report.scores) == 4
    assert report.total_runs == 4
    assert report.strict_pass_rate == 1.0
    assert len(writer.calls) == 2
    assert writer.calls[0][0].dimension.value == "result"
    assert writer.calls[0][0].escalation == "recall_anchors"
    assert len(auditor.calls) == 2
    assert auditor.calls[0][0] == "大约覆盖500名用户"
    assert auditor.calls[0][1] is not auditor.calls[1][1]
    assert auditor.calls[0][1].messages[-1].role == "user"


def test_runner_aggregates_named_metrics_exactly():
    report = MentorBenchmark(
        RecordingQuestionWriter(), RecordingFactAuditor()
    ).run(make_dataset(), repeats=1)

    assert report.metrics == {
        "runtime_success_rate": 1.0,
        "question_contract_pass_rate": 1.0,
        "audit_dimension_accuracy": 1.0,
        "evidence_recall_rate": 1.0,
        "hallucination_free_rate": 1.0,
        "confidence_label_accuracy": 1.0,
        "sensitivity_label_accuracy": 1.0,
        "strict_pass_rate": 1.0,
    }


class BrokenQuestionWriter:
    def write(self, plan, experience, target):
        raise RuntimeError("raw secret model output")


def test_runner_isolates_case_errors_and_keeps_only_safe_error_category():
    report = MentorBenchmark(BrokenQuestionWriter(), RecordingFactAuditor()).run(
        make_dataset(), repeats=1
    )

    assert report.total_runs == 2
    assert report.strict_pass_rate == 0.5
    failed = report.failed_scores
    assert [score.case_id for score in failed] == ["q-result"]
    assert failed[0].error_category == "RuntimeError"
    assert "raw secret" not in report.model_dump_json()


def test_runner_rejects_invalid_repeats():
    with pytest.raises(ValueError, match="repeats"):
        MentorBenchmark(RecordingQuestionWriter(), RecordingFactAuditor()).run(
            make_dataset(), repeats=0
        )


def test_runner_whitelists_safe_metadata_only():
    report = MentorBenchmark(
        RecordingQuestionWriter(), RecordingFactAuditor()
    ).run(
        make_dataset(),
        repeats=1,
        metadata={
            "framework": "HelloAgents",
            "model": "fixture-model",
            "api_key": "super-secret",
            "base_url": "https://private.example/v1",
        },
    )

    assert report.metadata == {
        "framework": "HelloAgents",
        "model": "fixture-model",
    }
    assert "super-secret" not in report.model_dump_json()
    assert "private.example" not in report.model_dump_json()
