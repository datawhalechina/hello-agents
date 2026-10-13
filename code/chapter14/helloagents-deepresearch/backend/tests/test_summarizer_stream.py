"""Exercise streamed summaries without external model or search requests."""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Configuration
from models import SummaryState, TodoItem
from services.summarizer import SummarizationService


class SummarizerStreamTests(unittest.TestCase):
    def make_stream(self, chunks, *, strip_thinking=True):
        agent = Mock()
        agent.stream_run.return_value = iter(chunks)
        service = SummarizationService(
            lambda: agent,
            Configuration(strip_thinking_tokens=strip_thinking, enable_notes=False),
        )
        stream, summary = service.stream_task_summary(
            SummaryState(research_topic="Offline research"),
            TodoItem(id=1, title="Evidence", intent="Summarize", query="offline"),
            "Verified context",
        )
        return stream, summary, agent

    def test_filters_thinking_at_every_chunk_boundary(self):
        text = "Before <think>internal-only</think>after<think>more-hidden</think>!"
        expected = "Before after!"
        partitions = [[text[:i], text[i:]] for i in range(len(text) + 1)]
        partitions.append(list(text))
        for chunks in partitions:
            with self.subTest(chunks=chunks):
                stream, summary, agent = self.make_stream(chunks)
                visible = ""
                for chunk in stream:
                    visible += chunk
                    self.assertTrue(expected.startswith(visible), visible)
                self.assertEqual(visible, expected)
                self.assertEqual(summary(), expected)
                agent.clear_history.assert_called_once()

    def test_streams_safe_text_before_model_completion(self):
        consumed = []

        def chunks():
            for chunk in ["First <thi", "nk>hidden</thi", "nk> second"]:
                consumed.append(chunk)
                yield chunk

        stream, summary, agent = self.make_stream(chunks())
        self.assertEqual(next(stream), "First ")
        self.assertEqual(consumed, ["First <thi"])
        self.assertEqual("".join(stream), " second")
        self.assertEqual(summary(), "First  second")
        agent.clear_history.assert_called_once()

    def test_preserves_plain_angle_brackets_and_incomplete_prefixes(self):
        for chunks in (["Value <", " 5"], ["a<thi", "mble>"], ["ending <thi"], ["", "<", ""]):
            with self.subTest(chunks=chunks):
                stream, summary, agent = self.make_stream(chunks)
                self.assertEqual("".join(stream), "".join(chunks))
                self.assertEqual(summary(), "".join(chunks).strip())
                agent.clear_history.assert_called_once()

    def test_drops_unclosed_thinking_section(self):
        stream, summary, agent = self.make_stream(["Public <thi", "nk>hidden", "</thi"])
        self.assertEqual("".join(stream), "Public ")
        self.assertEqual(summary(), "Public")
        agent.clear_history.assert_called_once()

    def test_disabled_filter_preserves_model_chunks(self):
        chunks = ["<thi", "nk>thought</think>", "Answer"]
        stream, summary, agent = self.make_stream(chunks, strip_thinking=False)
        self.assertEqual(list(stream), chunks)
        self.assertEqual(summary(), "".join(chunks))
        agent.clear_history.assert_called_once()

    def test_closing_stream_clears_history_without_flushing_a_partial_tag(self):
        stream, summary, agent = self.make_stream(["Visible<thi", "nk>hidden</think> tail"])
        self.assertEqual(next(stream), "Visible")
        stream.close()
        agent.clear_history.assert_called_once()
        self.assertEqual(summary(), "Visible")

    def test_model_failure_clears_history_and_propagates(self):
        def chunks():
            yield "Visible<thi"
            raise RuntimeError("model stream failed")

        stream, summary, agent = self.make_stream(chunks())
        self.assertEqual(next(stream), "Visible")
        with self.assertRaisesRegex(RuntimeError, "model stream failed"):
            next(stream)
        agent.clear_history.assert_called_once()
        self.assertEqual(summary(), "Visible")


if __name__ == "__main__":
    unittest.main()
