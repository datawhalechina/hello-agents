import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock


llm_client = types.ModuleType("llm_client")
llm_client.HelloAgentsLLM = object
sys.modules.setdefault("llm_client", llm_client)

dotenv = types.ModuleType("dotenv")
dotenv.load_dotenv = lambda: None
sys.modules.setdefault("dotenv", dotenv)

module_path = Path(__file__).with_name("Plan_and_solve.py")
spec = importlib.util.spec_from_file_location("plan_and_solve", module_path)
plan_and_solve = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan_and_solve)


class PlanAndSolveAgentTest(unittest.TestCase):
    def test_run_returns_executor_final_answer(self):
        agent = object.__new__(plan_and_solve.PlanAndSolveAgent)
        agent.planner = Mock()
        agent.executor = Mock()
        agent.planner.plan.return_value = ["solve the problem"]
        agent.executor.execute.return_value = "the final answer"

        result = agent.run("test question")

        self.assertEqual(result, "the final answer")
        agent.executor.execute.assert_called_once_with(
            "test question", ["solve the problem"]
        )

    def test_run_returns_none_when_plan_is_empty(self):
        agent = object.__new__(plan_and_solve.PlanAndSolveAgent)
        agent.planner = Mock()
        agent.executor = Mock()
        agent.planner.plan.return_value = []

        result = agent.run("test question")

        self.assertIsNone(result)
        agent.executor.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
