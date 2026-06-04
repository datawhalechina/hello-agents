from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Configuration
from models import SummaryState, TodoItem
from services.summarizer import SummarizationService


class RateLimitError(RuntimeError):
    pass


class FakeSummaryAgent:
    def __init__(
        self,
        *,
        response: str = "",
        exc: Exception | None = None,
        stream_chunks: list[str] | None = None,
        stream_exc: Exception | None = None,
    ) -> None:
        self.response = response
        self.exc = exc
        self.stream_chunks = stream_chunks or []
        self.stream_exc = stream_exc
        self.prompt = ""
        self.cleared = False

    def run(self, prompt: str) -> str:
        self.prompt = prompt
        if self.exc:
            raise self.exc
        return self.response

    def stream_run(self, prompt: str):
        self.prompt = prompt
        if self.stream_exc:
            raise self.stream_exc
        yield from self.stream_chunks

    def clear_history(self) -> None:
        self.cleared = True


def config() -> Configuration:
    return Configuration(
        llm_retry_attempts=0,
        llm_retry_base_delay=0,
        llm_retry_max_delay=0,
        llm_min_interval_seconds=0,
    )


def make_state() -> SummaryState:
    return SummaryState(
        research_topic="我想找 2026 暑期 Java 后端实习，城市上海/杭州"
    )


def make_task() -> TodoItem:
    return TodoItem(
        id=1,
        title="岗位搜索",
        intent="搜索可靠岗位/JD来源",
        query="Java 后端 实习 招聘 JD",
    )


class SummarizationServiceTests(unittest.TestCase):
    def test_sync_rate_limit_returns_fallback_summary(self) -> None:
        agent = FakeSummaryAgent(exc=RateLimitError("Error code: 429 code 1302"))
        service = SummarizationService(lambda: agent, config())  # type: ignore[arg-type]

        summary = service.summarize_task(
            make_state(),
            make_task(),
            "标题：Java 后端实习招聘\nURL：https://www.zhipin.com/job_detail/a.html",
        )

        self.assertTrue(summary.startswith("## 任务总结"))
        self.assertIn("LLM 限流", summary)
        self.assertIn("Java 后端 实习 招聘 JD", summary)
        self.assertTrue(agent.cleared)

    def test_stream_rate_limit_yields_fallback_summary(self) -> None:
        agent = FakeSummaryAgent(stream_exc=RateLimitError("您的账户已达到速率限制"))
        service = SummarizationService(lambda: agent, config())  # type: ignore[arg-type]

        stream, get_summary = service.stream_task_summary(
            make_state(),
            make_task(),
            "来源：实习僧 Java 实习\nhttps://www.shixiseng.com/intern/a",
        )
        text = "".join(stream)

        self.assertTrue(text.startswith("## 任务总结"))
        self.assertIn("LLM 限流", text)
        self.assertIn("来源线索", text)
        self.assertEqual(get_summary(), text)
        self.assertTrue(agent.cleared)

    def test_stream_normal_chunks_are_preserved(self) -> None:
        agent = FakeSummaryAgent(stream_chunks=["## 任务总结\n", "正常输出"])
        service = SummarizationService(lambda: agent, config())  # type: ignore[arg-type]

        stream, get_summary = service.stream_task_summary(make_state(), make_task(), "")
        text = "".join(stream)

        self.assertEqual(text, "## 任务总结\n正常输出")
        self.assertEqual(get_summary(), text)


if __name__ == "__main__":
    unittest.main()
