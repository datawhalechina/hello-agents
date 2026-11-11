"""Offline regressions for failures during sequential plan execution.

Run with: python -m unittest discover -s code/chapter4 -p test_plan_execution.py
"""

import importlib.util
import io
import re
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


client_module = ModuleType("llm_client")
client_module.HelloAgentsLLM = object
spec = importlib.util.spec_from_file_location(
    "plan_and_solve", Path(__file__).with_name("Plan_and_solve.py")
)
plan_module = importlib.util.module_from_spec(spec)
with patch.dict("sys.modules", {"llm_client": client_module}):
    spec.loader.exec_module(plan_module)


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def think(self, messages):
        self.calls.append(messages)
        return next(self.responses)


class PlanExecutionTests(unittest.TestCase):
    def execute(self, responses, plan):
        client = FakeClient(responses)
        output = io.StringIO()
        with redirect_stdout(output):
            result = plan_module.Executor(client).execute("Calculate total", plan)
        return result, client, output.getvalue()

    def test_first_step_failure_stops_dependent_steps(self):
        for response in (None, "", " \n\t"):
            with self.subTest(response=response):
                result, client, output = self.execute(
                    [response, "Invented total"], ["Read amounts", "Sum amounts"]
                )
                self.assertEqual(result, "")
                self.assertEqual(len(client.calls), 1)
                self.assertNotIn("Invented total", output)

    def test_middle_step_failure_does_not_return_partial_success(self):
        result, client, output = self.execute(
            ["10", None, "Invented total"], ["Read first amount", "Read second amount", "Sum amounts"]
        )
        self.assertEqual(result, "")
        self.assertEqual(len(client.calls), 2)
        self.assertNotIn("Invented total", output)

    def test_final_step_whitespace_is_not_a_result(self):
        result, client, _ = self.execute(["10", " \n"], ["Read amounts", "Sum amounts"])
        self.assertEqual(result, "")
        self.assertEqual(len(client.calls), 2)

    def test_success_retains_history_and_result(self):
        result, client, _ = self.execute(["10", "20"], ["Read amounts", "Sum amounts"])
        self.assertEqual(result, "20")
        self.assertEqual(len(client.calls), 2)
        self.assertIn("10", client.calls[1][0]["content"])
        self.assertIn("Read amounts", client.calls[1][0]["content"])

    def test_empty_plan_does_not_call_client(self):
        result, client, _ = self.execute([], [])
        self.assertEqual(result, "")
        self.assertEqual(client.calls, [])

    def test_agent_does_not_report_completion_after_executor_failure(self):
        client = FakeClient(['```python\n["Read amounts", "Sum amounts"]\n```', None, "Invented total"])
        output = io.StringIO()
        with redirect_stdout(output):
            plan_module.PlanAndSolveAgent(client).run("Calculate total")
        self.assertEqual(len(client.calls), 2)
        self.assertNotIn("任务完成", output.getvalue())

    def test_agent_still_reports_completion_on_success(self):
        client = FakeClient(['```python\n["Read amounts"]\n```', "10"])
        output = io.StringIO()
        with redirect_stdout(output):
            plan_module.PlanAndSolveAgent(client).run("Calculate total")
        self.assertEqual(len(client.calls), 2)
        self.assertIn("任务完成", output.getvalue())

    def test_translated_tutorials_stop_after_a_failed_step(self):
        docs = Path(__file__).resolve().parents[2] / "docs" / "chapter4"
        for path in docs.glob("*.md"):
            namespace = {
                "EXECUTOR_PROMPT_TEMPLATE": plan_module.EXECUTOR_PROMPT_TEMPLATE,
                "Planner": plan_module.Planner,
            }
            blocks = re.findall(r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.DOTALL)
            for name in ("Executor", "PlanAndSolveAgent"):
                block = next(block for block in blocks if block.startswith(f"class {name}:"))
                exec(compile(block, str(path), "exec"), namespace)
            for response in (None, "", " \n\t"):
                with self.subTest(chapter=path.name, response=response):
                    client = FakeClient([
                        '```python\n["Read amounts", "Sum amounts"]\n```',
                        response,
                        "Invented total",
                    ])
                    output = io.StringIO()
                    with redirect_stdout(output):
                        namespace["PlanAndSolveAgent"](client).run("Calculate total")
                    self.assertEqual(len(client.calls), 2)
                    self.assertNotIn("Invented total", output.getvalue())
                    self.assertNotIn("任务完成", output.getvalue())
                    self.assertNotIn("Task Completed", output.getvalue())


if __name__ == "__main__":
    unittest.main()
