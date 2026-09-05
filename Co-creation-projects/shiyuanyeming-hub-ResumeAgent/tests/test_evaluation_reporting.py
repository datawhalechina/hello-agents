import json
from datetime import datetime, timezone

from resume_agent.evaluation.models import BenchmarkReport, CaseScore
from resume_agent.evaluation.reporting import write_report


def make_report():
    return BenchmarkReport(
        dataset_version="mentor_v1",
        repeats=1,
        generated_at=datetime(2026, 8, 13, 12, 34, 56, tzinfo=timezone.utc),
        metadata={"framework": "HelloAgents", "model": "fixture-model"},
        scores=[
            CaseScore(
                case_id="q-safe",
                kind="question",
                checks={"runtime_success": True, "single_question": True},
            ),
            CaseScore(
                case_id="a-failed",
                kind="audit",
                checks={"runtime_success": True, "hallucination_free": False},
                error_category=None,
            ),
        ],
        metrics={
            "runtime_success_rate": 1.0,
            "strict_pass_rate": 0.5,
        },
    )


def test_write_report_creates_matching_json_and_markdown_files(tmp_path):
    files = write_report(make_report(), tmp_path)

    assert files.json_path.exists()
    assert files.markdown_path.exists()
    assert files.json_path.stem == files.markdown_path.stem
    assert files.json_path.name == "mentor-evaluation-20260813T123456Z.json"

    payload = json.loads(files.json_path.read_text(encoding="utf-8"))
    assert payload["dataset_version"] == "mentor_v1"
    assert payload["metrics"]["strict_pass_rate"] == 0.5
    assert payload["scores"][1]["case_id"] == "a-failed"

    markdown = files.markdown_path.read_text(encoding="utf-8")
    assert "# Mentor Evaluation Report" in markdown
    assert "50.00%" in markdown
    assert "a-failed" in markdown
    assert "hallucination_free" in markdown


def test_report_files_exclude_raw_candidate_and_model_content(tmp_path):
    files = write_report(make_report(), tmp_path)
    combined = files.json_path.read_text(encoding="utf-8") + files.markdown_path.read_text(
        encoding="utf-8"
    )

    assert "用户本轮回答" not in combined
    assert "raw model output" not in combined
    assert "api_key" not in combined
    assert "base_url" not in combined
