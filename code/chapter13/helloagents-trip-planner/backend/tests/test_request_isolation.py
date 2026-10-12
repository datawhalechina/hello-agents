"""Exercise request isolation with real Agents, FastAPI and an offline model."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
from threading import Event, Lock
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hello_agents.tools import CalculatorTool, MCPTool
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with patch("dotenv.load_dotenv"):
    from app.agents import trip_planner_agent
    from app.api.routes import trip
    from app.services import llm_service


class RequestIsolationTests(unittest.TestCase):
    markers = ("PRIVATE_ALICE_8237", "PRIVATE_BOB_1946")

    def setUp(self):
        self.requests = []
        self.lock = Lock()
        self.before_response = lambda stage, marker: None
        self.invalid_plan_for = None
        self.use_calculator = False
        self.client = OpenAI(
            api_key="offline-test-key", base_url="https://offline.invalid/v1",
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(self.respond)),
        )
        self.addCleanup(self.client.close)
        for boundary in (
            patch.dict(os.environ, {
                "LLM_API_KEY": "offline-test-key", "LLM_BASE_URL": "https://offline.invalid/v1",
                "LLM_MODEL_ID": "offline-model", "LLM_PROVIDER": "openai",
            }),
            patch("hello_agents.core.llm.OpenAI", return_value=self.client),
            patch.object(MCPTool, "_discover_tools", return_value=None),
            patch.object(llm_service, "_llm_instance", None),
            patch.object(trip_planner_agent, "_multi_agent_planner", None),
        ):
            boundary.start()
            self.addCleanup(boundary.stop)
        self.planner = trip_planner_agent.get_trip_planner_agent()
        self.app = FastAPI()
        self.app.include_router(trip.router)

    def respond(self, request):
        payload = json.loads(request.content)
        messages = payload["messages"]
        prompt = messages[0]["content"]
        stage = next(name for name in ("景点搜索", "天气查询", "酒店推荐", "行程规划") if name in prompt)
        marker = next(
            marker for message in reversed(messages) for marker in self.markers
            if marker in message["content"]
        )
        with self.lock:
            self.requests.append({"stage": stage, "marker": marker, "messages": messages})
        self.before_response(stage, marker)
        if stage == "行程规划":
            content = json.dumps({
                "city": marker, "start_date": "2026-10-13", "end_date": "2026-10-13",
                "days": [], "weather_info": [], "overall_suggestions": marker,
            }) if marker != self.invalid_plan_for else "invalid offline plan"
        elif stage == "景点搜索" and self.use_calculator and "工具执行结果" not in messages[-1]["content"]:
            content = "[TOOL_CALL:python_calculator:input=2+3]"
        else:
            content = f"{stage}结果：{marker}"
        return httpx.Response(200, json={
            "id": "offline-completion", "object": "chat.completion", "created": 0,
            "model": "offline-model", "choices": [{"index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": content}}],
        })

    def request(self, marker):
        # Separate portals permit two real ASGI requests to overlap even though
        # the current async route calls its synchronous planner directly.
        with TestClient(self.app) as client:
            response = client.post("/trip/plan", json={
                "city": marker, "start_date": "2026-10-13", "end_date": "2026-10-13",
                "travel_days": 1, "transportation": "步行", "accommodation": "经济酒店",
                "preferences": [marker], "free_text_input": marker,
            })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["data"]["city"], marker)
        return response.json()["data"]

    def assert_isolated(self):
        self.assertEqual(len(self.requests), 8)
        for marker in self.markers:
            requests = [request for request in self.requests if request["marker"] == marker]
            self.assertEqual({request["stage"] for request in requests}, {"景点搜索", "天气查询", "酒店推荐", "行程规划"})
            other = next(value for value in self.markers if value != marker)
            for request in requests:
                with self.subTest(marker=marker, stage=request["stage"]):
                    self.assertFalse(any(other in message["content"] for message in request["messages"]), "Model request includes another request's private marker")

    def test_sequential_requests_have_independent_history(self):
        for marker in self.markers:
            self.request(marker)
        self.assert_isolated()

    def test_fallback_does_not_leave_history_for_the_next_request(self):
        self.invalid_plan_for = self.markers[0]
        fallback = self.request(self.markers[0])
        self.assertEqual(len(fallback["days"]), 1)
        self.request(self.markers[1])
        self.assert_isolated()

    def test_overlapping_requests_do_not_share_history(self):
        alice_paused = Event()
        bob_finished = Event()

        def pause_alice(stage, marker):
            if stage == "天气查询" and marker == self.markers[0]:
                alice_paused.set()
                if not bob_finished.wait(10):
                    raise RuntimeError("Concurrent request did not finish")

        self.before_response = pause_alice
        with ThreadPoolExecutor(max_workers=2) as pool:
            alice = pool.submit(self.request, self.markers[0])
            try:
                self.assertTrue(alice_paused.wait(10))
                bob = pool.submit(self.request, self.markers[1])
                bob.result(timeout=10)
            finally:
                bob_finished.set()
            alice.result(timeout=10)
        self.assert_isolated()

    def test_request_agent_keeps_tools_and_their_results_within_its_run(self):
        self.planner.attraction_agent.add_tool(CalculatorTool())
        self.use_calculator = True
        self.request(self.markers[0])
        attraction_calls = [request for request in self.requests if request["stage"] == "景点搜索"]
        self.assertEqual(len(self.requests), 5)
        self.assertEqual(len(attraction_calls), 2)
        self.assertIn("工具执行结果", attraction_calls[1]["messages"][-1]["content"])
        self.assertIn("5", attraction_calls[1]["messages"][-1]["content"])
        self.assertTrue(any(self.markers[0] in message["content"] for message in attraction_calls[1]["messages"]))


if __name__ == "__main__":
    unittest.main()
