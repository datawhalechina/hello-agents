"""Exercise the context-aware example without external model requests."""

import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from hello_agents import HelloAgentsLLM
from openai import OpenAI

example_path = Path(__file__).resolve().parents[1] / "02_context_builder_with_agent.py"
spec = importlib.util.spec_from_file_location("context_aware_example", example_path)
example = importlib.util.module_from_spec(spec)
with patch("dotenv.load_dotenv"):
    spec.loader.exec_module(example)


class ContextAwareAgentTests(unittest.TestCase):
    def test_real_llm_text_response_is_returned_and_retained_across_turns(self):
        requests = []
        answers = ["Use categorical columns.", "Convert with astype('category')."]

        def respond(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={
                "id": "offline-completion",
                "object": "chat.completion",
                "created": 0,
                "model": "offline-model",
                "choices": [{"index": 0, "finish_reason": "stop", "message": {
                    "role": "assistant", "content": answers[len(requests) - 1],
                }}],
            })

        client = OpenAI(
            api_key="offline-test-key", base_url="https://offline.invalid/v1",
            http_client=httpx.Client(transport=httpx.MockTransport(respond)),
        )
        self.addCleanup(client.close)
        with patch("hello_agents.core.llm.OpenAI", return_value=client):
            llm = HelloAgentsLLM(
                model="offline-model", api_key="offline-test-key",
                base_url="https://offline.invalid/v1", provider="openai",
            )
        agent = example.ContextAwareAgent(name="Offline agent", llm=llm, system_prompt="Give practical advice.")

        self.assertEqual(agent.run("Reduce memory usage."), answers[0])
        self.assertEqual(agent.run("Show an example."), answers[1])
        self.assertEqual(
            [(message.role, message.content) for message in agent.conversation_history],
            [("user", "Reduce memory usage."), ("assistant", answers[0]),
             ("user", "Show an example."), ("assistant", answers[1])],
        )
        self.assertIn("Give practical advice.", requests[1]["messages"][0]["content"])
        self.assertEqual(requests[1]["messages"][1]["content"], "Show an example.")

    def test_response_object_still_contributes_its_text_to_history(self):
        llm = Mock()
        llm.invoke.return_value = SimpleNamespace(content="Structured response text.")
        agent = example.ContextAwareAgent(name="Offline agent", llm=llm)
        self.assertEqual(agent.run("Question"), "Structured response text.")
        self.assertEqual(agent.conversation_history[-1].content, "Structured response text.")

    def test_failed_call_does_not_add_an_incomplete_turn(self):
        llm = Mock()
        llm.invoke.side_effect = RuntimeError("model unavailable")
        agent = example.ContextAwareAgent(name="Offline agent", llm=llm)
        with self.assertRaisesRegex(RuntimeError, "model unavailable"):
            agent.run("Question")
        self.assertEqual(agent.conversation_history, [])


if __name__ == "__main__":
    unittest.main()
