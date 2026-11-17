"""Offline regression tests for the chapter 7 multi-provider search example.

Run with: python -m unittest discover -s code/chapter7 -p test_advanced_search_fallback.py
"""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


class AdvancedSearchFallbackTests(unittest.TestCase):
    def setUp(self):
        # This example only needs ToolRegistry when creating a registry; do not
        # require the agent framework or real search SDKs for provider tests.
        framework = types.ModuleType("hello_agents")
        framework.ToolRegistry = Mock()
        spec = importlib.util.spec_from_file_location(
            "advanced_search_example", Path(__file__).with_name("my_advanced_search.py")
        )
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"hello_agents": framework}):
            spec.loader.exec_module(module)
        self.tool = module.MyAdvancedSearchTool.__new__(module.MyAdvancedSearchTool)
        self.tool.search_sources = ["tavily", "serpapi"]
        self.tool.tavily_client = SimpleNamespace(search=Mock())
        self.serpapi = types.ModuleType("serpapi")
        self.serpapi.GoogleSearch = Mock()

    def configure(self, tavily, serpapi):
        self.serpapi.GoogleSearch.reset_mock()
        self.tool.tavily_client.search.return_value = tavily
        self.serpapi.GoogleSearch.return_value.get_dict.return_value = serpapi

    def search(self):
        with patch.dict(sys.modules, {"serpapi": self.serpapi}):
            return self.tool.search("Python")

    def test_empty_tavily_falls_back_to_serpapi(self):
        for empty in ({}, {"results": []}, {"answer": "  ", "results": None}):
            with self.subTest(response=empty):
                self.configure(empty, {"organic_results": [{"title": "Backup", "snippet": "Found"}]})
                self.assertIn("Backup", self.search())
                self.serpapi.GoogleSearch.assert_called()

    def test_all_providers_empty(self):
        for empty in ({}, {"organic_results": []}, {"organic_results": None}):
            with self.subTest(response=empty):
                self.configure({"results": []}, empty)
                self.assertIn("所有搜索源均未返回有效结果", self.search())

    def test_answer_without_links_is_valid(self):
        self.configure({"answer": "Direct answer", "results": []}, {})
        answer = self.search()
        self.assertIn("Direct answer", answer)
        self.assertNotIn("相关结果", answer)
        self.serpapi.GoogleSearch.assert_not_called()

    def test_tavily_links_are_valid(self):
        self.configure({"results": [{"title": "Primary", "content": "Found"}]}, {})
        self.assertIn("Primary", self.search())
        self.serpapi.GoogleSearch.assert_not_called()

    def test_result_can_contain_not_found_phrase(self):
        self.configure({"answer": "解释文件未找到错误", "results": []}, {})
        self.assertIn("解释文件未找到错误", self.search())
        self.serpapi.GoogleSearch.assert_not_called()

    def test_provider_exception_falls_back(self):
        self.configure({}, {"organic_results": [{"title": "Backup", "snippet": "Found"}]})
        self.tool.tavily_client.search.side_effect = RuntimeError("Provider unavailable")
        self.assertIn("Backup", self.search())

    def test_empty_query_skips_providers(self):
        self.assertIn("搜索查询不能为空", self.tool.search("  "))
        self.tool.tavily_client.search.assert_not_called()

    def test_no_configured_providers(self):
        self.tool.search_sources = []
        self.assertIn("没有可用的搜索源", self.search())


if __name__ == "__main__":
    unittest.main()
