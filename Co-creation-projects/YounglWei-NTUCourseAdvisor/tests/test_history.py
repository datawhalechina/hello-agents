"""每轮清理 Agent 内部历史测试。"""

import unittest
from unittest import mock

from src.team import CourseAdvisorTeam


class TestClearAgentHistory(unittest.TestCase):
    def _fake_team(self):
        team = object.__new__(CourseAdvisorTeam)
        team.verbose = False
        team.history = []
        team.assumed_identity = {}
        team.identity = None
        team.max_review_rounds = 3
        team.retrieval = mock.Mock()
        team.reviewer = mock.Mock()
        team.retrieval.history_manager = mock.Mock()
        team.reviewer.history_manager = mock.Mock()
        return team

    def test_clear_agent_history(self):
        team = self._fake_team()
        team._clear_agent_history()
        team.retrieval.history_manager.clear.assert_called_once()
        team.reviewer.history_manager.clear.assert_called_once()

    def test_run_clears_before_planning(self):
        team = self._fake_team()
        with mock.patch.object(team, "_clear_agent_history") as clear, \
                mock.patch("src.team.generate_plan",
                           side_effect=RuntimeError("stop")), \
                mock.patch.object(team, "_pipeline", return_value="answer"):
            self.assertEqual(team.run("hello"), "answer")
        clear.assert_called_once()


if __name__ == "__main__":
    unittest.main()
