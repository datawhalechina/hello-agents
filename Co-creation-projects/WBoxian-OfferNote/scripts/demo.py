"""调用真实 API 业务流程的离线演示，全部使用虚构材料与临时数据库。"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def run_demo() -> dict:
    from fastapi.testclient import TestClient

    from app.main import create_app

    with tempfile.TemporaryDirectory(prefix="offernote-demo-") as directory:
        with TestClient(create_app(str(Path(directory) / "demo.sqlite3"))) as client:

            def request(method, url, **kwargs):
                response = client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()

            workspace = request("POST", "/api/workspaces/demo")
            base = f"/api/workspaces/{workspace['id']}"
            workspace = request("POST", base + "/analyze", json={"mode": "demo"})
            workspace = request(
                "POST", base + "/sessions", json={"mode": "demo", "count": 4}
            )
            session = workspace["sessions"][-1]
            for index in range(4):
                question = session["questions"][index]
                workspace = request(
                    "POST",
                    base + f"/sessions/{session['id']}/answers",
                    json={
                        "question_id": question["id"],
                        "request_id": f"notebook-demo-{index}",
                        "answer": "我负责后端接口，用 pytest 验证无效输入不会推进状态。还需要补充真实模型与人工评测记录。",
                    },
                )
                session = workspace["sessions"][-1]
                if session["status"] != "active":
                    break
            workspace = request("GET", base)
            session = workspace["sessions"][-1]
            retrained = request(
                "POST",
                base + "/sessions",
                json={
                    "mode": "demo",
                    "count": 2,
                    "focus": "weak",
                    "source_session_id": session["id"],
                },
            )
            assert session["status"] == "completed"
            assert retrained["sessions"][-1]["focus"] == "weak"
            return {
                "mode": "demo",
                "notice": "固定规则演示，非真实模型效果。",
                "requirements": len(workspace["analysis"]["requirements"]),
                "claims": len(workspace["analysis"]["claims"]),
                "answered": len(session["turns"]),
                "report": session["report"],
                "retraining_created": True,
            }
