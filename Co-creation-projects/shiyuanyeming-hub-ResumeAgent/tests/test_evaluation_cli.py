import json

from resume_agent.agents.runtime import (
    AgentCapabilityStatus,
    MentorRuntime,
)
from resume_agent.domain.models import FactProposal, FactValue
from resume_agent.evaluation import cli


class PassingWriter:
    def write(self, plan, experience, target):
        return "这项工作产生了什么结果？"


class FailingWriter:
    def write(self, plan, experience, target):
        return "请提供身份证？"


class PassingAuditor:
    def propose(self, message, session, base):
        return FactProposal(
            fact_base_revision=base.revision,
            experience_id=session.active_experience_id,
            dimension="action",
            values=[
                FactValue(
                    text="自动化看板",
                    specificity="concrete",
                    source_message_ids=[session.messages[-1].id],
                )
            ],
        )


def write_dataset(path):
    cases = [
        {
            "id": "q-result",
            "kind": "question",
            "target": {"role": "数据分析师"},
            "experience": {"organization": "云数科技", "role": "分析师"},
            "dimension": "result",
            "escalation": "direct",
            "must_include_any": ["结果"],
            "must_not_include": ["身份证"],
        },
        {
            "id": "a-action",
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
        },
    ]
    path.write_text(
        "\n".join(json.dumps(case, ensure_ascii=False) for case in cases) + "\n",
        encoding="utf-8",
    )


def ready_runtime(writer=None):
    return MentorRuntime(
        fact_auditor=PassingAuditor(),
        question_writer=writer or PassingWriter(),
        capabilities=AgentCapabilityStatus.ready("fixture-model"),
    )


def test_cli_runs_ready_runtime_and_prints_report_paths(tmp_path, monkeypatch, capsys):
    dataset = tmp_path / "tiny_v1.jsonl"
    reports = tmp_path / "reports"
    write_dataset(dataset)
    received = []
    monkeypatch.setattr(
        cli,
        "build_mentor_runtime",
        lambda environ: received.append(environ) or ready_runtime(),
    )

    exit_code = cli.main(
        [
            "--dataset",
            str(dataset),
            "--output-dir",
            str(reports),
            "--repeats",
            "2",
            "--fail-under",
            "1.0",
        ],
        environ={"LLM_MODEL_ID": "fixture-model"},
    )

    assert exit_code == 0
    assert received == [{"LLM_MODEL_ID": "fixture-model"}]
    assert len(list(reports.glob("*.json"))) == 1
    assert len(list(reports.glob("*.md"))) == 1
    output = capsys.readouterr().out
    assert str(next(reports.glob("*.json"))) in output
    assert "strict_pass_rate=100.00%" in output


def test_cli_writes_report_but_returns_one_below_threshold(
    tmp_path, monkeypatch, capsys
):
    dataset = tmp_path / "tiny_v1.jsonl"
    reports = tmp_path / "reports"
    write_dataset(dataset)
    monkeypatch.setattr(
        cli,
        "build_mentor_runtime",
        lambda environ: ready_runtime(FailingWriter()),
    )

    exit_code = cli.main(
        ["--dataset", str(dataset), "--output-dir", str(reports), "--fail-under", "1"],
        environ={},
    )

    assert exit_code == 1
    assert list(reports.glob("*.json"))
    assert "below required 100.00%" in capsys.readouterr().err


def test_cli_degraded_runtime_returns_two_without_report(tmp_path, monkeypatch, capsys):
    reports = tmp_path / "reports"
    monkeypatch.setattr(
        cli,
        "build_mentor_runtime",
        lambda environ: MentorRuntime(
            fact_auditor=None,
            question_writer=None,
            capabilities=AgentCapabilityStatus.offline("LLM_API_KEY is required"),
        ),
    )

    exit_code = cli.main(["--output-dir", str(reports)], environ={})

    assert exit_code == 2
    assert not reports.exists()
    assert "LLM_API_KEY is required" in capsys.readouterr().err


def test_cli_invalid_numeric_arguments_return_two_without_building_runtime(
    monkeypatch, capsys
):
    monkeypatch.setattr(
        cli,
        "build_mentor_runtime",
        lambda environ: (_ for _ in ()).throw(AssertionError("must not build")),
    )

    assert cli.main(["--repeats", "0"], environ={}) == 2
    assert cli.main(["--fail-under", "1.1"], environ={}) == 2
    assert "error" in capsys.readouterr().err.lower()


def test_dotenv_does_not_override_exported_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "LLM_MODEL_ID=file-model\nLLM_API_KEY=file-key\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LLM_MODEL_ID", "exported-model")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    values = cli._load_environment()

    assert values["LLM_MODEL_ID"] == "exported-model"
    assert values["LLM_API_KEY"] == "file-key"
