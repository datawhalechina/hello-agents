import contextlib
import io
import unittest
from unittest.mock import Mock

from Reflection import ReflectionAgent


class ReflectionAgentTest(unittest.TestCase):
    def run_agent(self, responses, max_iterations=3):
        client = Mock()
        client.think.side_effect = responses
        agent = ReflectionAgent(client, max_iterations=max_iterations)
        with contextlib.redirect_stdout(io.StringIO()):
            result = agent.run("Generate a function")
        return agent, client, result

    def test_empty_refinement_preserves_last_execution(self):
        initial_code = "def answer(): return 42"
        for refinement in (None, "", " \n\t"):
            with self.subTest(refinement=refinement):
                agent, client, result = self.run_agent(
                    [initial_code, "Improve the algorithm", refinement]
                )
                self.assertEqual(result, initial_code)
                self.assertEqual(client.think.call_count, 3)
                self.assertEqual(
                    agent.memory.records,
                    [
                        {"type": "execution", "content": initial_code},
                        {"type": "reflection", "content": "Improve the algorithm"},
                    ],
                )

    def test_failed_refinement_keeps_most_recent_success(self):
        improved_code = "def answer(): return 42"
        agent, client, result = self.run_agent(
            ["initial code", "Improve it", improved_code, "Improve it again", None]
        )
        self.assertEqual(result, improved_code)
        self.assertEqual(client.think.call_count, 5)
        self.assertEqual(
            [
                record["content"]
                for record in agent.memory.records
                if record["type"] == "execution"
            ],
            ["initial code", improved_code],
        )

    def test_successful_refinements_are_recorded(self):
        agent, client, result = self.run_agent(
            [
                "initial code",
                "First feedback",
                "first revision",
                "Second feedback",
                "  final revision\n",
            ],
            max_iterations=2,
        )
        self.assertEqual(result, "  final revision\n")
        self.assertEqual(client.think.call_count, 5)
        self.assertEqual(len(agent.memory.records), 5)

    def test_satisfied_reflection_skips_refinement(self):
        for feedback in ("无需改进", "No Need For Improvement"):
            with self.subTest(feedback=feedback):
                agent, client, result = self.run_agent(["initial code", feedback])
                self.assertEqual(result, "initial code")
                self.assertEqual(client.think.call_count, 2)
                self.assertEqual(len(agent.memory.records), 2)

    def test_zero_iterations_returns_initial_code(self):
        agent, client, result = self.run_agent(["initial code"], max_iterations=0)
        self.assertEqual(result, "initial code")
        self.assertEqual(client.think.call_count, 1)
        self.assertEqual(len(agent.memory.records), 1)


if __name__ == "__main__":
    unittest.main()
