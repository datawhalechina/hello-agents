"""来源逐课校验回归测试（不需要智谱 API key）。

运行：python -m unittest discover -s tests -t . -v
"""

import unittest

from src.guards import mechanical_review


class TestSourceProvenance(unittest.TestCase):
    steps = [{"action": "search", "query": "SC2001", "level": ""}]

    def test_wrong_but_whitelisted_url_is_flagged(self):
        """引用另一门课的合法 URL 也算来源不符，不能只靠 URL 白名单。"""
        draft = (
            "SC2001 是 3 AU。\n"
            "来源：\n"
            "- EE6203 — https://www.ntu.edu.sg/education/graduate-programme/"
            "master-of-science-in-computer-control-automation"
        )
        issues = mechanical_review("SC2001 是几 AU？", None, draft, self.steps)
        self.assertTrue(any("来源" in i for i in issues), issues)

    def test_correct_card_url_passes_source_check(self):
        draft = (
            "SC2001 是 3 AU。\n"
            "来源：\n"
            "- SC2001 — https://wis.ntu.edu.sg/webexe/owa/aus_subj_cont.main"
        )
        issues = mechanical_review("SC2001 是几 AU？", None, draft, self.steps)
        self.assertFalse(any("来源" in i for i in issues), issues)

    def test_not_found_phrasing_exempts_source(self):
        """「未能找到/未找到」类表述不需要来源，不能误判为缺来源。"""
        draft = (
            "很抱歉，我未能找到关于 CS1010S 这门课程的描述信息。\n"
            "来源：\n"
            "- CS1010S 课程描述信息未找到"
        )
        issues = mechanical_review("CS1010S 这门课讲什么？", None, draft, self.steps)
        self.assertFalse(any("来源覆盖" in i for i in issues), issues)


if __name__ == "__main__":
    unittest.main()
