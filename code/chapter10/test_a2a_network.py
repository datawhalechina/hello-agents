"""Offline regression tests for the chapter 10 A2A content workflow."""

import ast
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


class A2ANetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).with_name("09_A2A_Network.py")
        spec = importlib.util.spec_from_file_location("a2a_network_example", path)
        cls.example = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.example)

    def test_keeps_multiline_articles(self):
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=repr(newline)):
                article = f"# 标题{newline}{newline}第一段正文{newline}第二段正文"
                result = ast.literal_eval(self.example.edit_article(f"edit {article}"))
                self.assertEqual(result["article"], article + "\n\n[已编辑优化]")

    def test_keeps_single_line_articles(self):
        result = ast.literal_eval(self.example.edit_article("edit Short article"))
        self.assertEqual(result["article"], "Short article\n\n[已编辑优化]")

    def test_keeps_articles_without_a_command_prefix(self):
        article = "# Title\n\nArticle body"
        result = ast.literal_eval(self.example.edit_article(article))
        self.assertEqual(result["article"], article + "\n\n[已编辑优化]")

    def test_accepts_an_uppercase_command(self):
        article = "# Title\n\nArticle body"
        result = ast.literal_eval(self.example.edit_article(f"EDIT {article}"))
        self.assertEqual(result["article"], article + "\n\n[已编辑优化]")

    def test_content_workflow_preserves_the_written_article(self):
        topic = "AI在医疗领域的应用"
        research = self.example.do_research(f"research {topic}")
        written = self.example.write_article(f"write {research}")

        with (
            patch.object(
                self.example.researcher_client,
                "execute_skill",
                side_effect=lambda skill, text: {"result": self.example.do_research(text)},
            ),
            patch.object(
                self.example.writer_client,
                "execute_skill",
                side_effect=lambda skill, text: {"result": self.example.write_article(text)},
            ),
            patch.object(
                self.example.editor_client,
                "execute_skill",
                side_effect=lambda skill, text: {"result": self.example.edit_article(text)},
            ) as edit,
        ):
            result = ast.literal_eval(self.example.create_content(topic))

        edit.assert_called_once_with("edit", f"edit {written}")
        self.assertEqual(result["article"], written + "\n\n[已编辑优化]")
        self.assertTrue(result["approved"])


if __name__ == "__main__":
    unittest.main()
