from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services.search import (
    build_platform_job_query,
    build_search_diagnostics,
    build_strict_job_query,
    classify_job_source,
    is_reliable_job_source,
    prioritize_job_search_results,
)


class SearchFilterTests(unittest.TestCase):
    def test_prioritizes_jd_links_and_drops_interview_noise(self) -> None:
        payload = {
            "results": [
                {
                    "title": "Java 后端实习面经汇总",
                    "url": "https://example.com/interview",
                    "content": "面经 面试题 学习",
                },
                {
                    "title": "Java开发（26届暑期实习）招聘",
                    "url": "https://www.zhipin.com/job_detail/abc.html",
                    "content": "岗位职责 任职要求 投递",
                },
                {
                    "title": "Spring Boot 学习资源",
                    "url": "https://www.javaboy.org/springboot",
                    "content": "教程 学习资源",
                },
                {
                    "title": "Java后端开发工程师实习招聘",
                    "url": "https://www.shixiseng.com/intern/abc",
                    "content": "职位描述 任职要求 实习生",
                },
            ],
            "backend": "duckduckgo",
            "answer": None,
            "notices": [],
        }

        filtered = prioritize_job_search_results(payload)

        self.assertIsNotNone(filtered)
        results = filtered["results"]
        self.assertEqual(len(results), 2)
        self.assertIn("zhipin.com/job_detail", results[0]["url"])
        self.assertTrue(all("面经" not in item["title"] for item in results))
        self.assertTrue(all("学习资源" not in item["title"] for item in results))

    def test_no_jd_like_results_returns_empty_results(self) -> None:
        payload = {
            "results": [
                {
                    "title": "Java 后端面试题",
                    "url": "https://example.com/interview",
                    "content": "面经 面试 学习",
                }
            ]
        }

        filtered = prioritize_job_search_results(payload)

        self.assertEqual(filtered["results"], [])

    def test_strict_query_excludes_interview_and_tutorial_terms(self) -> None:
        query = build_strict_job_query("Java 后端 实习 上海")

        self.assertIn("岗位详情", query)
        self.assertIn("投递入口", query)
        self.assertIn("招聘官网", query)
        self.assertIn("任职要求", query)
        self.assertIn("-面经", query)
        self.assertIn("-教程", query)
        self.assertIn("-博客", query)
        self.assertIn("-提示词", query)

    def test_platform_query_targets_job_boards_and_career_sites(self) -> None:
        query = build_platform_job_query("AI 应用开发 实习 北京")

        self.assertIn("BOSS直聘", query)
        self.assertIn("实习僧", query)
        self.assertIn("牛客招聘", query)
        self.assertIn("校招官网", query)
        self.assertIn("投递入口", query)
        self.assertIn("site:zhipin.com/job_detail", query)
        self.assertIn("site:shixiseng.com/intern", query)

    def test_reliable_job_source_rejects_blog_and_prompt_examples(self) -> None:
        self.assertFalse(
            is_reliable_job_source(
                {
                    "title": "用 Cursor 开发 10+ 项目后整理的提示词案例",
                    "url": "https://example.com/blog/rag-prompts",
                    "content": "博客 提示词 案例",
                }
            )
        )

    def test_reliable_job_source_accepts_company_career_jd_page(self) -> None:
        self.assertTrue(
            is_reliable_job_source(
                {
                    "title": "AI 应用开发实习生招聘",
                    "url": "https://careers.example.com/jobs/ai-intern",
                    "content": "职位描述 任职要求 投递入口",
                }
            )
        )

    def test_reliable_job_source_keeps_trusted_jd_with_experience_terms(self) -> None:
        self.assertTrue(
            is_reliable_job_source(
                {
                    "title": "Java开发（26届暑期实习）招聘",
                    "url": "https://www.zhipin.com/job_detail/abc.html",
                    "content": "岗位职责：参与后端开发。任职要求：有项目经验和开发经验，支持在线投递。",
                }
            )
        )

    def test_classify_job_source_returns_reject_reasons(self) -> None:
        self.assertEqual(
            classify_job_source(
                {
                    "title": "Java 后端实习面经",
                    "url": "https://example.com/interview",
                    "content": "面试题 面经",
                }
            ),
            "interview_noise",
        )
        self.assertEqual(
            classify_job_source(
                {
                    "title": "Spring Boot 教程",
                    "url": "https://example.com/blog",
                    "content": "教程 博客",
                }
            ),
            "tutorial_or_blog",
        )

    def test_build_search_diagnostics_counts_reliable_and_rejected_results(self) -> None:
        diagnostics = build_search_diagnostics(
            task_id=1,
            task_title="岗位搜索",
            backend="duckduckgo",
            query="Java 后端 实习",
            final_query="Java 后端 实习 BOSS直聘",
            retry_query="Java 后端 实习 BOSS直聘",
            raw_results=[
                {
                    "title": "Java 后端实习面经",
                    "url": "https://example.com/interview",
                    "content": "面经 面试题",
                },
                {
                    "title": "Java开发（26届暑期实习）招聘",
                    "url": "https://www.zhipin.com/job_detail/abc.html",
                    "content": "岗位职责 任职要求 投递",
                },
            ],
        )

        self.assertEqual(diagnostics["counts"]["raw"], 2)
        self.assertEqual(diagnostics["counts"]["reliable"], 1)
        self.assertEqual(diagnostics["counts"]["filtered"], 1)
        self.assertEqual(diagnostics["reject_reasons"]["interview_noise"], 1)
        self.assertTrue(diagnostics["rejected_samples"])

    def test_diagnostics_suggestion_mentions_experience_term_for_tutorial_noise(self) -> None:
        diagnostics = build_search_diagnostics(
            task_id=1,
            task_title="岗位搜索",
            backend="duckduckgo",
            query="Java 后端 实习",
            final_query="Java 后端 实习 BOSS直聘",
            retry_query=None,
            raw_results=[
                {
                    "title": "Spring Boot 项目经验教程",
                    "url": "https://example.com/blog/spring",
                    "content": "教程 博客 项目经验",
                }
            ],
        )

        self.assertIn("经验词", diagnostics["suggestion"])

    def test_diagnostics_suggestion_for_non_job_urls_stays_generic(self) -> None:
        diagnostics = build_search_diagnostics(
            task_id=1,
            task_title="岗位搜索",
            backend="duckduckgo",
            query="Java 后端 实习",
            final_query="Java 后端 实习 BOSS直聘",
            retry_query=None,
            raw_results=[
                {
                    "title": "Java company news",
                    "url": "https://example.com/news/java",
                    "content": "company news",
                }
            ],
        )

        self.assertIn("未发现可靠岗位", diagnostics["suggestion"])


if __name__ == "__main__":
    unittest.main()
