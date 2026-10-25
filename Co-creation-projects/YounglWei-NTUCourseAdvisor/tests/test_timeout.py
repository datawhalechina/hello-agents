"""超时/异常兜底测试（不需要智谱 API key，不实际调用 LLM）。"""

import unittest
from unittest import mock

from src.team import CourseAdvisorTeam


class TestTimeoutFallback(unittest.TestCase):
    def setUp(self):
        # 绕过 __init__（避免构造 RAG/LLM），只测 run() 的兜底分支
        self.team = object.__new__(CourseAdvisorTeam)
        self.team.verbose = False
        self.team.history = []
        self.team.assumed_identity = {}
        self.team.identity = None
        self.team.max_review_rounds = 3
        self.team.retrieval = mock.Mock()
        self.team.reviewer = mock.Mock()
        self.team.retrieval.history_manager = mock.Mock()
        self.team.reviewer.history_manager = mock.Mock()

    def test_pipeline_timeout_returns_friendly_message(self):
        plan = [{"action": "search", "query": "SC2001", "level": ""}]
        with mock.patch("src.team.generate_plan", return_value=(plan, {})), \
                mock.patch.object(self.team, "_pipeline",
                                  side_effect=TimeoutError("timeout")):
            answer = self.team.run("SC2001 是几 AU？")
        self.assertIn("超时", answer)
        self.assertIn("请重试", answer)
        self.assertEqual(len(self.team.history), 2)

    def test_generic_error_returns_friendly_message(self):
        plan = [{"action": "search", "query": "SC2001", "level": ""}]
        with mock.patch("src.team.generate_plan", return_value=(plan, {})), \
                mock.patch.object(self.team, "_pipeline",
                                  side_effect=RuntimeError("boom")):
            answer = self.team.run("SC2001 是几 AU？")
        self.assertIn("处理失败", answer)
        self.assertIn("RuntimeError", answer)


if __name__ == "__main__":
    unittest.main()
