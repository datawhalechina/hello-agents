import json

import pytest

from resume_agent.evaluation.dataset import DatasetError, load_dataset
from resume_agent.evaluation.models import AuditEvaluationCase, QuestionEvaluationCase


def write_jsonl(path, items):
    path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in items) + "\n",
        encoding="utf-8",
    )


def question_case(case_id="q-context"):
    return {
        "id": case_id,
        "kind": "question",
        "target": {"role": "数据分析师"},
        "experience": {"organization": "云数科技", "role": "分析师"},
        "dimension": "context",
        "escalation": "direct",
        "must_include_any": ["背景", "问题"],
        "must_not_include": ["请提供身份证"],
    }


def audit_case(case_id="a-action"):
    return {
        "id": case_id,
        "kind": "audit",
        "target": {"role": "数据分析师"},
        "experience": {"organization": "云数科技", "role": "分析师"},
        "message": "我搭建了自动化看板",
        "expected_dimension": "action",
        "required_fact_fragments": ["自动化看板"],
        "forbidden_fact_fragments": ["提升30%"],
        "expected_confidence": "unverified",
        "expected_specificity": "concrete",
        "expected_sensitive": False,
    }


def test_loader_validates_and_discriminates_cases(tmp_path):
    path = tmp_path / "mentor.jsonl"
    write_jsonl(path, [question_case(), audit_case()])

    dataset = load_dataset(path)

    assert dataset.version == "mentor"
    assert isinstance(dataset.cases[0], QuestionEvaluationCase)
    assert isinstance(dataset.cases[1], AuditEvaluationCase)
    assert dataset.case_ids == ["q-context", "a-action"]


def test_loader_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "mentor_v1.jsonl"
    write_jsonl(path, [question_case(), question_case()])

    with pytest.raises(DatasetError, match="duplicate case id"):
        load_dataset(path)


def test_loader_reports_malformed_json_line(tmp_path):
    path = tmp_path / "mentor_v1.jsonl"
    path.write_text('{"id":"ok"}\n{broken\n', encoding="utf-8")

    with pytest.raises(DatasetError, match="line 2"):
        load_dataset(path)


def test_loader_rejects_unknown_case_kind(tmp_path):
    path = tmp_path / "mentor_v1.jsonl"
    item = question_case()
    item["kind"] = "translation"
    write_jsonl(path, [item])

    with pytest.raises(DatasetError, match="line 1"):
        load_dataset(path)


def test_bundled_dataset_has_versioned_synthetic_coverage():
    dataset = load_dataset()

    assert dataset.version == "mentor_v1"
    assert len(dataset.cases) >= 18
    assert {case.kind for case in dataset.cases} == {"question", "audit"}
    assert {case.dimension.value for case in dataset.question_cases} == {
        "context",
        "responsibility",
        "action",
        "method",
        "result",
        "evidence",
    }
    assert {case.expected_dimension.value for case in dataset.audit_cases} >= {
        "context",
        "responsibility",
        "action",
        "method",
        "result",
        "evidence",
    }
