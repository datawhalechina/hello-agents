from fastapi.testclient import TestClient

from resume_agent.api.app import create_app


def test_root_serves_original_workbench_shell(tmp_path):
    with TestClient(create_app(tmp_path / "app.db")) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="primary-tabs"' in response.text
    assert all(
        label in response.text for label in ("访谈", "事实库", "JD 定制", "工具")
    )
    assert 'id="chat-composer"' in response.text
    assert 'id="preview-frame"' in response.text
    assert 'id="base-select"' in response.text
    assert 'id="new-base-button"' in response.text
    assert 'id="interview-progress"' in response.text
    assert 'aria-label="访谈证据进度"' in response.text
    assert "stSidebar" not in response.text
    assert "把做过的事，讲成有证据的职业故事" not in response.text


def test_web_assets_are_served(tmp_path):
    with TestClient(create_app(tmp_path / "app.db")) as client:
        css = client.get("/assets/styles.css")
        api = client.get("/assets/api.js")
        app = client.get("/assets/app.js")

    assert css.status_code == 200
    assert css.headers["content-type"].startswith("text/css")
    assert api.status_code == 200
    assert "javascript" in api.headers["content-type"]
    assert app.status_code == 200
    assert "javascript" in app.headers["content-type"]


def test_styles_define_required_breakpoints_without_ai_effects(tmp_path):
    with TestClient(create_app(tmp_path / "app.db")) as client:
        css = client.get("/assets/styles.css").text

    assert "400px minmax(0, 1fr)" in css
    assert "@media (max-width: 960px)" in css
    assert "@media (max-width: 640px)" in css
    assert "[hidden] { display: none !important; }" in css
    assert "linear-gradient" not in css
    assert "backdrop-filter" not in css
