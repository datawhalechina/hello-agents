"""Offline regression tests for the plan passed from Planner to Executor."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock

from Plan_and_solve import PlanAndSolveAgent, Planner


def plan_response(plan):
    return f"```python\n{plan!r}\n```"


class PlannerValidationTests(unittest.TestCase):
    def test_rejects_invalid_steps(self):
        for step in (None, 123, True, {"task": "search"}, ["search"], "", " \t\n"):
            with self.subTest(step=step):
                client = Mock()
                client.think.return_value = plan_response(["valid step", step])
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(Planner(client).plan("question"), [])

    def test_invalid_plan_does_not_call_executor(self):
        client = Mock()
        client.think.return_value = plan_response([None])
        with redirect_stdout(io.StringIO()):
            PlanAndSolveAgent(client).run("question")
        self.assertEqual(client.think.call_count, 1)

    def test_preserves_valid_steps(self):
        steps = ["  search for evidence  ", "总结结果"]
        client = Mock()
        client.think.return_value = plan_response(steps)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(Planner(client).plan("question"), steps)

    def test_existing_parse_failures_still_return_empty_plan(self):
        for response in (
            None,
            "",
            "not a fenced plan",
            "```python\n[\n```",
            plan_response({"task": "search"}),
            plan_response([]),
        ):
            with self.subTest(response=response):
                client = Mock()
                client.think.return_value = response
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(Planner(client).plan("question"), [])

    def test_valid_plan_runs_steps_in_order_with_prior_results(self):
        client = Mock()
        client.think.side_effect = [
            plan_response(["find evidence", "summarize"]),
            "evidence found",
            "summary",
        ]
        with redirect_stdout(io.StringIO()):
            PlanAndSolveAgent(client).run("question")
        self.assertEqual(client.think.call_count, 3)
        execution_prompts = [
            call.kwargs["messages"][0]["content"]
            for call in client.think.call_args_list[1:]
        ]
        self.assertIn("当前步骤:\nfind evidence", execution_prompts[0])
        self.assertIn("当前步骤:\nsummarize", execution_prompts[1])
        self.assertIn("结果: evidence found", execution_prompts[1])


if __name__ == "__main__":
    unittest.main()
