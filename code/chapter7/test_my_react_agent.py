"""Constructor regression tests for the chapter's hello-agents==0.1.1 API."""

import unittest

from hello_agents import Config, ToolRegistry

from my_react_agent import MY_REACT_PROMPT, MyReActAgent


class MyReActAgentInitializationTests(unittest.TestCase):
    def setUp(self):
        # Initialization must not call an LLM or require API credentials.
        self.llm = object()
        self.tools = ToolRegistry()

    def test_preserves_custom_system_prompt(self):
        agent = MyReActAgent(
            "test", self.llm, self.tools, system_prompt="Answer concisely."
        )

        self.assertEqual(agent.system_prompt, "Answer concisely.")
        self.assertIs(agent.tool_registry, self.tools)

    def test_preserves_custom_config_and_react_options(self):
        config = Config(temperature=0.2, max_history_length=3)
        agent = MyReActAgent(
            "test",
            self.llm,
            self.tools,
            config=config,
            max_steps=2,
            custom_prompt="Question: {question}",
        )

        self.assertIs(agent.config, config)
        self.assertIsNone(agent.system_prompt)
        self.assertEqual(agent.max_steps, 2)
        self.assertEqual(agent.prompt_template, "Question: {question}")

    def test_default_initialization(self):
        agent = MyReActAgent("test", self.llm, self.tools)

        self.assertIs(agent.llm, self.llm)
        self.assertIs(agent.tool_registry, self.tools)
        self.assertIsNone(agent.system_prompt)
        self.assertIsInstance(agent.config, Config)
        self.assertEqual(agent.max_steps, 5)
        self.assertEqual(agent.prompt_template, MY_REACT_PROMPT)


if __name__ == "__main__":
    unittest.main()
