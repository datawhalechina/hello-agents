import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import MagicMock, patch

from hello_agents import SimpleAgent

from app.agent.agent import ModeratorAgent, ParticipantAgent, run_simple_agent
from demo_helloagents import run_demo


def _configure_llm(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("BASE_URL", "https://example.test/v1/")


def test_one_shot_task_is_driven_by_helloagents(monkeypatch):
    _configure_llm(monkeypatch)
    framework_agent = MagicMock()
    framework_agent.run.return_value = "framework response"

    with patch("app.agent.agent.HelloAgentsLLM") as llm_class, patch(
        "app.agent.agent.SimpleAgent", return_value=framework_agent
    ) as agent_class:
        response = run_simple_agent("TestAgent", "system", "hello")

    llm_class.assert_called_once()
    agent_class.assert_called_once()
    framework_agent.run.assert_called_once_with("hello")
    assert response == "framework response"


def test_participant_reuses_helloagents_agent_for_multiple_turns(monkeypatch):
    _configure_llm(monkeypatch)
    framework_agent = MagicMock()
    framework_agent.run.return_value = '{"decision":"LISTEN","inner_monologue":"观察"}'
    framework_agent.stream_run.return_value = iter(["第一段", "第二段"])
    persona = {
        "name": "测试嘉宾",
        "bio": "测试生平",
        "title": "研究者",
        "theories": ["测试理论"],
        "stance": "审慎",
        "system_prompt": "保持审慎。",
    }

    with patch("app.agent.agent.HelloAgentsLLM"):
        participant = ParticipantAgent("测试嘉宾", persona, 2, "测试议题")
        with patch.object(participant, "run", return_value=framework_agent.run.return_value), patch.object(
            participant, "stream_run", return_value=framework_agent.stream_run.return_value
        ):
            thought = participant.think("当前讨论")
            chunks = list(participant.speak(thought, "当前讨论"))

    assert isinstance(participant, SimpleAgent)
    assert thought["action"] == "listen"
    assert chunks == ["第一段", "第二段"]


def test_end_to_end_discussion_uses_helloagents_agents(monkeypatch):
    _configure_llm(monkeypatch)
    streams = iter([iter(["主持人开场"]), iter(["嘉宾发言"]), iter(["阶段总结"]), iter(["主持人闭幕"])])
    with patch("app.agent.agent.HelloAgentsLLM"), patch.object(
        SimpleAgent, "run", return_value='{"decision":"APPLY_SPEAK","inner_monologue":"回应议题"}'
    ), patch.object(SimpleAgent, "stream_run", side_effect=lambda *args, **kwargs: next(streams)):
        transcript = run_demo("测试议题")

    assert transcript["opening"] == "主持人开场"
    assert transcript["thought"]["action"] == "apply_to_speak"
    assert transcript["speech"] == "嘉宾发言"
    assert transcript["summary"] == "阶段总结"
    assert transcript["closing"] == "主持人闭幕"


def test_madf_agents_are_native_helloagents_subclasses(monkeypatch):
    _configure_llm(monkeypatch)
    persona = {"system_prompt": "persona", "name": "P"}
    with patch("app.agent.agent.HelloAgentsLLM"):
        moderator = ModeratorAgent("topic")
        participant = ParticipantAgent("P", persona, 1, "topic")

    assert isinstance(moderator, SimpleAgent)
    assert isinstance(participant, SimpleAgent)
    assert not hasattr(participant, "_hello_agent")


def test_end_to_end_discussion_through_real_helloagents_runtime(monkeypatch):
    responses = iter(
        [
            "真实框架开场",
            '{"decision":"APPLY_SPEAK","inner_monologue":"真实框架思考"}',
            "真实框架发言",
            "真实框架总结",
            "真实框架闭幕",
        ]
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_POST(self):
            size = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(size))
            content = next(responses)
            if request.get("stream"):
                payload = {
                    "id": "chatcmpl-madf",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "test-model",
                    "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
                }
                body = f"data: {json.dumps(payload, ensure_ascii=False)}\n\ndata: [DONE]\n\n".encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            body = json.dumps(
                {
                    "id": "chatcmpl-madf",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": "test-model",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": content},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
                ensure_ascii=False,
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    try:
        transcript = run_demo("真实 HelloAgents 链路测试")
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert transcript["opening"] == "真实框架开场"
    assert transcript["thought"]["action"] == "apply_to_speak"
    assert transcript["speech"] == "真实框架发言"
    assert transcript["summary"] == "真实框架总结"
    assert transcript["closing"] == "真实框架闭幕"
