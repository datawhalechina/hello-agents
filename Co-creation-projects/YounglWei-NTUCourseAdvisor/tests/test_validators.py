"""学位校验回归测试（不需要智谱 API key）。

运行：python -m unittest discover -s tests -t . -v
"""

import unittest

from src.validators import DegreeAuditTool


class TestCcaAuLimit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = DegreeAuditTool()

    def test_robotics_course_not_counted_as_cca_general(self):
        """MA6210 是 Robotics 核心课，不能计入 CCA 通选 AU。"""
        resp = self.tool.check_au_limit(["MA6210", "EE6203"], option=1)
        self.assertEqual(resp.status.value, "success")
        self.assertEqual(resp.data["general_count"], 0)
        self.assertEqual(resp.data["specialized_count"], 1)
        self.assertIn("MA6210", resp.data["not_ruled"])
        self.assertIn("通选：0 门", resp.text)

    def test_cca_general_and_specialized_still_counted(self):
        resp = self.tool.check_au_limit(["EE6203", "EE6008"], option=1)
        self.assertEqual(resp.data["specialized_count"], 1)
        self.assertEqual(resp.data["general_count"], 1)

    def test_option1_scope_note(self):
        """工具只校验 AU 分布，必须明确不校验总门数/论文。"""
        resp = self.tool.check_au_limit(
            ["EE6203", "EE6204", "EE6221", "EE6225"], option=1)
        self.assertIn("不校验总门数", resp.text)


if __name__ == "__main__":
    unittest.main()
