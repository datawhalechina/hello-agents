from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_entrypoint_renders_actionable_offline_state(monkeypatch):
    monkeypatch.setenv("RESUME_AGENT_API_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("RESUME_AGENT_API_TIMEOUT", "0.1")
    entrypoint = Path(__file__).parents[1] / "streamlit_app.py"

    test = AppTest.from_file(entrypoint, default_timeout=3).run()

    assert not test.exception
    assert test.title[0].value == "ResumeAgent"
    assert any("无法连接" in item.value for item in test.error)
