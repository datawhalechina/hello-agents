"""Offline regressions for ReAct's reserved Finish action."""

import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

llm = ModuleType("llm_client")
llm.HelloAgentsLLM = object
tools = ModuleType("tools")
tools.ToolExecutor = object
tools.search = None
spec = importlib.util.spec_from_file_location("react_example", Path(__file__).with_name("ReAct.py"))
react = importlib.util.module_from_spec(spec)
with patch.dict("sys.modules", {"llm_client": llm, "tools": tools}):
    spec.loader.exec_module(react)


class FinishDispatchTests(unittest.TestCase):
    def run_agent(self, actions, tool_name="Search"):
        client = Mock()
        client.think.side_effect = [f"Action: {action}" for action in actions]
        toolbox = Mock()
        toolbox.getAvailableTools.return_value = f"{tool_name}: look up a record"
        function = Mock(return_value="record found")
        toolbox.getTool.side_effect = lambda name: function if name == tool_name else None
        agent = react.ReActAgent(client, toolbox, max_steps=len(actions))
        with redirect_stdout(io.StringIO()):
            result = agent.run("Look up a record")
        return result, client, toolbox, function, agent

    def test_finish_prefixed_tools_are_executed(self):
        for name in ("FinishLookup", "FinishTask", "Finish_Job"):
            with self.subTest(name=name):
                result, client, toolbox, function, agent = self.run_agent(
                    [f"{name}[record-42]", "Finish[confirmed]"], name
                )
                self.assertEqual(result, "confirmed")
                self.assertEqual(client.think.call_count, 2)
                toolbox.getTool.assert_called_once_with(name)
                function.assert_called_once_with("record-42")
                self.assertIn("Observation: record found", agent.history)

    def test_ordinary_tools_still_execute(self):
        result, _, _, function, _ = self.run_agent(["Search[record-42]", "Finish[confirmed]"])
        self.assertEqual(result, "confirmed")
        function.assert_called_once_with("record-42")

    def test_finish_preserves_multiline_and_bracketed_answers(self):
        for answer in ("confirmed", "line one\nline two", "items [a, b]", ""):
            with self.subTest(answer=answer):
                result, _, toolbox, _, _ = self.run_agent([f"Finish[{answer}]"])
                self.assertEqual(result, answer)
                toolbox.getTool.assert_not_called()

    def test_incomplete_finish_does_not_end_the_run(self):
        result, client, _, _, agent = self.run_agent(["Finish[unfinished", "Finish[confirmed]"])
        self.assertEqual(result, "confirmed")
        self.assertEqual(client.think.call_count, 2)
        self.assertTrue(agent.history)


if __name__ == "__main__":
    unittest.main()
