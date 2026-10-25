"""Offline regression tests for the example's response and history contract.

Load only run() so these tests need neither hello-agents nor API credentials.
The string return contract is used by the chapter's pinned hello-agents 0.2.8;
the content-bearing response is supported by the example since PR #632.
"""

import ast
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


@dataclass
class Message:
    content: str
    role: str
    timestamp: datetime


def load_run():
    source = Path(__file__).resolve().parents[1] / "02_context_builder_with_agent.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    agent_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ContextAwareAgent"
    )
    run = next(node for node in agent_class.body if getattr(node, "name", None) == "run")
    namespace = {"Message": Message, "datetime": datetime}
    exec(compile(ast.Module(body=[run], type_ignores=[]), str(source), "exec"), namespace)
    return namespace["run"]


class ContextAwareAgentTests(unittest.TestCase):
    def test_response_text_and_follow_up_history(self):
        for wrapped in (False, True):
            with self.subTest(wrapped=wrapped):
                responses = ["First answer", "Follow-up answer"]
                if wrapped:
                    responses = [SimpleNamespace(content=text) for text in responses]
                snapshots = []

                def build(**kwargs):
                    snapshots.append(list(kwargs["conversation_history"]))
                    return "Optimized context"

                agent = SimpleNamespace(
                    context_builder=SimpleNamespace(build=Mock(side_effect=build)),
                    llm=SimpleNamespace(invoke=Mock(side_effect=responses)),
                    system_prompt="System instructions",
                    conversation_history=[],
                )
                run = load_run()
                self.assertEqual(run(agent, "First question"), "First answer")
                self.assertEqual(run(agent, "Follow-up question"), "Follow-up answer")
                expected = [
                    ("user", "First question"),
                    ("assistant", "First answer"),
                    ("user", "Follow-up question"),
                    ("assistant", "Follow-up answer"),
                ]
                self.assertEqual(
                    [(msg.role, msg.content) for msg in agent.conversation_history], expected
                )
                self.assertEqual(snapshots[0], [])
                self.assertEqual(
                    [(msg.role, msg.content) for msg in snapshots[1]], expected[:2]
                )
                agent.llm.invoke.assert_called_with([
                    {"role": "system", "content": "Optimized context"},
                    {"role": "user", "content": "Follow-up question"},
                ])


if __name__ == "__main__":
    unittest.main()
