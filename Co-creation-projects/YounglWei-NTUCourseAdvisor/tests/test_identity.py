"""身份识别与 grounding 回归测试（不需要智谱 API key）。"""

import unittest

from src.identity import (explicit_level, identify, programme_code,
                          programme_mentioned)


class TestIdentity(unittest.TestCase):
    def test_cca_freshman_confirmed(self):
        r = identify("我是 CCA 新生")
        self.assertEqual(r.status, "confirmed")
        self.assertEqual(r.level, "graduate")
        self.assertIn("Computer Control", r.programme or "")

    def test_unknown_programme_declaration(self):
        r = identify("我是 SPML 新生")
        self.assertEqual(r.status, "unrecognized")
        self.assertEqual(r.claim, "SPML")

    def test_unknown_major_mention(self):
        r = identify("AAI专业课程有哪些？")
        self.assertEqual(r.status, "unrecognized")

    def test_course_code_attribute_query_is_unknown(self):
        r = identify("EE6407 几 AU")
        self.assertEqual(r.status, "unknown")

    def test_robotics_not_mapped_to_csc(self):
        """D4 Q08 回归：Robotics 里的 "cs" 不得命中 CSC。"""
        self.assertIsNone(programme_code("MSc Robotics and Intelligent Systems"))

    def test_cca_programme_code(self):
        self.assertEqual(programme_code("CCA"), "CCA")

    def test_explicit_level(self):
        self.assertEqual(explicit_level("我是研究生"), "graduate")
        self.assertEqual(explicit_level("我是本科生"), "undergraduate")

    def test_grounding(self):
        self.assertTrue(programme_mentioned("我是 CCA 新生", "CCA"))
        self.assertFalse(programme_mentioned("我是机械工程专业", "CCA"))


if __name__ == "__main__":
    unittest.main()
