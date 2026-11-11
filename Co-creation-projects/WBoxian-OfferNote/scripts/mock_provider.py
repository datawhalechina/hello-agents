"""仅供本地协议测试的确定性模型服务，不能用于能力或效果评测。"""

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def response_for(body):
    from app import demo
    from app.rubric import RUBRIC

    messages = body["messages"]
    user = next(m["content"] for m in reversed(messages) if m["role"] == "user")
    if body.get("tools"):
        names = {t["function"]["name"] for t in body["tools"]}
        if "get_probe_nonce" in names:
            if messages[-1]["role"] == "tool":
                return {"role": "assistant", "content": messages[-1]["content"]}
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "probe-call",
                        "type": "function",
                        "function": {
                            "name": "get_probe_nonce",
                            "arguments": '{"input":"check"}',
                        },
                    }
                ],
            }
        context = json.loads(user)
        topics = context["topics"]
        current = next(
            (t for t in topics if t["id"] == context["current_topic_id"]), None
        )
        available = [t for t in topics if t["status"] == "unvisited"]
        count = context["current_topic_turns"]
        action = (
            "ask_followup"
            if current and count < 3 and "ask_followup" in context["allowed_actions"]
            else "switch_topic"
            if available
            else "finish"
        )
        target = available[0] if action == "switch_topic" else current
        if messages[-1]["role"] != "tool" and body.get("tool_choice") != "none":
            calls = [
                {
                    "id": "material-call",
                    "type": "function",
                    "function": {
                        "name": "read_material_evidence",
                        "arguments": json.dumps({"topic_id": target["id"]}),
                    },
                }
            ]
            if current:
                calls.append(
                    {
                        "id": "history-call",
                        "type": "function",
                        "function": {
                            "name": "read_topic_history",
                            "arguments": json.dumps({"topic_id": current["id"]}),
                        },
                    }
                )
            return {"role": "assistant", "content": None, "tool_calls": calls}
        material = next(
            json.loads(m["content"])
            for m in messages
            if m["role"] == "tool" and m.get("name") == "read_material_evidence"
        )
        progress = {"covered": [], "gaps": [], "contradictions": [], "evidence": []}
        if context["latest_turn"]:
            turn = context["latest_turn"]
            progress.update(
                covered=["ownership"],
                evidence=[{"turn_id": turn["id"], "quote": turn["answer"][:40]}],
            )
        question = (
            None
            if action == "finish"
            else {
                "text": f"请围绕{target['title']}说明第{count if action == 'ask_followup' else 0}层实现，具体是怎样完成和验证的？",
                "topic": target["title"],
                "source_quote": material["claims"][0]["quote"],
                "intent": "核对具体实现。",
                "criteria": ["实际个人动作", "可核验实现"],
            }
        )
        decision = {
            "action": action,
            "topic_id": target["id"],
            "reason": "根据本轮回答继续核实或切换主题。",
            "closure": None if action == "ask_followup" else "sufficient",
            "question": question,
            "progress": progress,
        }
        return {
            "role": "assistant",
            "content": json.dumps(decision, ensure_ascii=False),
        }
    context = json.loads(user)
    if "resume" in context and "rubric" not in context:
        output = demo.analyze(context["resume"], context["job"])
    elif "rubric" not in context and "turns" in context:
        output = {
            "answers": [
                {
                    "turn_id": t["turn_id"],
                    "answer": "学习示范：先明确输入输出和个人负责的边界，再说明接口实现、失败场景与测试断言。具体结果应结合真实项目补充。",
                    "key_points": ["实现步骤", "失败验证"],
                    "pitfalls": ["避免编造项目指标"],
                }
                for t in context["turns"]
            ]
        }
    else:
        assert "trace" not in context and all(
            set(t) == {"id", "title"} for t in context["topics"]
        )
        first = context["turns"][0]
        ref = {"turn_id": first["turn_id"], "quote": first["answer"][:40]}
        output = {
            "summary": "模拟服务返回的协议测试评审，不代表实际模型效果。",
            "scores": [
                {
                    "dimension": d["id"],
                    "score": 3,
                    "reason": "仅用于测试带证据评分协议。",
                    "evidence": [ref],
                }
                for d in RUBRIC["dimensions"]
            ],
            "topics": [],
            "strengths": [{"text": "模拟的证据引用观察。", "evidence": [ref]}],
            "weaknesses": [{"text": "模拟的待完善观察。", "evidence": [ref]}],
            "improvements": [
                {
                    "topic_id": first["question"]["topic_id"],
                    "priority": "high",
                    "title": "补充验证材料",
                    "detail": "模拟服务行动项。",
                    "exercise": "准备实际断言和运行记录。",
                    "evidence": [ref],
                }
            ],
        }
        for topic in context["topics"]:
            turn = next(
                t for t in context["turns"] if t["question"]["topic_id"] == topic["id"]
            )
            output["topics"].append(
                {
                    "topic_id": topic["id"],
                    "score": 2,
                    "reason": "模拟服务主题评分。",
                    "evidence": [
                        {"turn_id": turn["turn_id"], "quote": turn["answer"][:40]}
                    ],
                }
            )
    return {"role": "assistant", "content": json.dumps(output, ensure_ascii=False)}


class Handler(BaseHTTPRequestHandler):
    requests = []
    suppress_tools = False

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.requests.append(body)
        message = (
            {"role": "assistant", "content": "{}"}
            if self.suppress_tools and body.get("tools")
            else response_for(body)
        )
        result = {
            "id": "local-test",
            "object": "chat.completion",
            "created": 0,
            "model": "local-check",
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": "tool_calls"
                    if message.get("tool_calls")
                    else "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        }
        encoded = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *_args):
        pass


def verify():
    import tempfile
    from fastapi.testclient import TestClient
    from app.main import create_app

    with tempfile.TemporaryDirectory(prefix="offernote-native-") as directory:
        with TestClient(create_app(str(Path(directory) / "test.sqlite3"))) as client:

            def request(method, path, **kwargs):
                response = client.request(method, path, **kwargs)
                assert response.is_success, response.text
                return response.json()

            assert request("POST", "/api/model-check")["supported"]
            workspace = request("POST", "/api/workspaces/demo")
            base = f"/api/workspaces/{workspace['id']}"
            request("POST", base + "/analyze", json={"mode": "live"})
            workspace = request(
                "POST", base + "/sessions", json={"mode": "live", "count": 4}
            )
            session = workspace["sessions"][-1]
            assert len(session["questions"]) == 1
            for index in range(4):
                request(
                    "POST",
                    base + f"/sessions/{session['id']}/answers",
                    json={
                        "question_id": session["questions"][-1]["id"],
                        "request_id": f"native-answer-{index}",
                        "answer": "我负责接口与测试，用 pytest 核验空字段不推进状态。尚未提供独立效果评测记录。",
                    },
                )
                session = request("GET", base)["sessions"][-1]
            assert session["status"] == "completed"
            assert (
                session["report"]["total_score"] == 75
                and session["report"]["covered_weight"] == 100
            )
            assert len(session["report"]["reference_answers"]) == 4
            events = request("GET", base + "/events")
            assert all(
                e["tokens"] > 0 and e["usage_complete"]
                for e in events
                if e["stage"] != "tool"
            )
            assert any(e["stage"] == "reference_answers" for e in events)
            assert session["questions"][2]["follow_up_depth"] == 2
            assert (
                session["questions"][3]["topic_id"]
                != session["questions"][0]["topic_id"]
            )
            assert all(entry["tools"] for entry in session["trace"][:-1])
            assert any(
                m["role"] == "tool"
                for body in Handler.requests
                for m in body["messages"]
            )
            assert all(
                len([m for m in body["messages"] if m["role"] == "user"]) == 1
                for body in Handler.requests
            )
            Handler.suppress_tools = True
            try:
                assert client.post("/api/model-check").status_code == 502
                before = request("GET", base)
                assert (
                    client.post(
                        base + "/sessions", json={"mode": "live", "count": 4}
                    ).status_code
                    == 502
                )
                assert request("GET", base)["revision"] == before["revision"]
            finally:
                Handler.suppress_tools = False
            print(
                "PASS: actual HelloAgents native tool loop, three rounds in one topic, topic switch, independent judge and weighted score."
            )
