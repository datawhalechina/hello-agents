"""ReporterAgent 统计与报告生成的单元测试"""
from src.agents.reporter_agent import ReporterAgent


def _make_result(passed, name="用例", case_type="normal", status_code=200):
    return {
        "case": {"name": name, "case_type": case_type, "expected_status": 200},
        "result": {"success": True, "status_code": status_code, "body": None, "elapsed": 0.1, "error": None},
        "passed": passed,
        "errors": [] if passed else ["状态码不符：期望 200，实际 %s" % status_code],
    }


# --- summarize ---

def test_summarize_basic():
    results = [_make_result(True), _make_result(True), _make_result(False)]
    s = ReporterAgent().summarize(results)
    assert s == {"total": 3, "passed": 2, "failed": 1, "pass_rate": 66.7}


def test_summarize_empty():
    s = ReporterAgent().summarize([])
    assert s == {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0}


# --- generate_markdown ---

def test_generate_markdown_summary():
    md = ReporterAgent().generate_markdown([_make_result(True), _make_result(False)])
    assert "通过率：**50.0%**" in md
    assert "| 用例名称 | 类型 | 状态码 |" in md


def test_generate_markdown_failed_request_no_none():
    # 请求失败时 status_code 是 None，报告里应显示 "-" 而不是 "None"
    results = [
        {
            "case": {"name": "失败用例", "case_type": "error"},
            "result": {"success": False, "status_code": None, "body": None, "elapsed": 0.0, "error": "请求超时"},
            "passed": False,
            "errors": ["请求失败：请求超时"],
        }
    ]
    md = ReporterAgent().generate_markdown(results)
    assert "None" not in md
    assert "| 失败用例 | error | - |" in md


# --- generate_html ---

def test_generate_html_basic():
    html = ReporterAgent().generate_html([_make_result(True)])
    assert "API 测试报告" in html
    assert "100.0%" in html


def test_generate_html_no_crash_on_empty():
    html = ReporterAgent().generate_html([])
    assert "API 测试报告" in html
