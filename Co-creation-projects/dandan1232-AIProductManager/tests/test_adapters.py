"""Exercise the installed HelloAgents package without sending paid model requests."""
import importlib.util
import unittest
from unittest.mock import patch

from src.config import AppError, Settings
from src.services import HelloAgentsBackend


@unittest.skipUnless(importlib.util.find_spec("hello_agents"), "install requirements.txt for framework integration checks")
class HelloAgentsIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.backend = HelloAgentsBackend(Settings(model="test-model", api_key="test-only-key"))

    def test_real_agent_receives_role_prompt_and_isolated_context(self):
        with patch("hello_agents.HelloAgentsLLM.invoke", return_value='{"ready":false}') as invoke:
            self.assertEqual(self.backend.run("interview", {"idea": "项目 A"}), {"ready": False})
            first = invoke.call_args.args[0]
            self.assertEqual(first[0]["role"], "system")
            self.assertIn("逐步澄清需求", first[0]["content"])
            self.backend.run("interview", {"idea": "项目 B"})
            second = invoke.call_args.args[0]
            self.assertNotIn("项目 A", str(second))
            self.assertIn("项目 B", str(second))

    def test_provider_exception_is_not_returned_to_user(self):
        with patch("hello_agents.HelloAgentsLLM.invoke", side_effect=RuntimeError("Authorization: private-test-secret")):
            with self.assertRaises(AppError) as raised:
                self.backend.run("interview", {})
            self.assertNotIn("private-test-secret", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
