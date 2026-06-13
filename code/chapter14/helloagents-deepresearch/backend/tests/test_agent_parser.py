from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services.agent_parser import parse_agent_output


class AgentParserTests(unittest.TestCase):
    def test_parse_thought_action_and_final(self) -> None:
        parsed = parse_agent_output(
            'Thought: 需要搜索岗位\n'
            'Action: search\n'
            'Action Input: {"query": "Java 实习"}\n'
            'Final: 完成'
        )

        self.assertEqual(parsed["thought"], "需要搜索岗位")
        self.assertEqual(parsed["action"], "search")
        self.assertEqual(parsed["action_input"], {"query": "Java 实习"})
        self.assertEqual(parsed["final"], "完成")

    def test_parse_tool_call_expression(self) -> None:
        parsed = parse_agent_output('[TOOL_CALL:note:{"action": "create", "task_id": 1}]')

        self.assertEqual(parsed["action"], "note")
        self.assertEqual(parsed["action_input"], {"action": "create", "task_id": 1})

    def test_plain_text_has_no_action(self) -> None:
        parsed = parse_agent_output("普通 Markdown 输出")

        self.assertIsNone(parsed["action"])
        self.assertIsNone(parsed["action_input"])
        self.assertIsNone(parsed["final"])


if __name__ == "__main__":
    unittest.main()
