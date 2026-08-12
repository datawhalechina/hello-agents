"""CLI 离线模式测试。"""

from pathlib import Path

from main import main


def test_audit_only_runs_without_llm_key(tmp_path, capsys) -> None:
    requirement_file = tmp_path / "requirement.txt"
    requirement_file.write_text("面向学生做学习工具，希望两周完成。", encoding="utf-8")

    exit_code = main(["--input", str(requirement_file), "--audit-only"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"coverage_percent"' in captured.out
    assert "需求完整度初检" in captured.out


def test_cli_reports_missing_input(capsys) -> None:
    exit_code = main(["--input", "definitely-not-existing.txt", "--audit-only"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "找不到输入文件" in captured.err


def test_cli_reports_directory_as_invalid_input(tmp_path, capsys) -> None:
    exit_code = main(["--input", str(tmp_path), "--audit-only"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "无法读取输入文件" in captured.err


def test_cli_reports_missing_llm_config(monkeypatch, capsys) -> None:
    for name in ("LLM_MODEL_ID", "LLM_API_KEY", "LLM_BASE_URL"):
        monkeypatch.delenv(name, raising=False)

    exit_code = main([])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "缺少 LLM 配置" in captured.err
