"""Behavioral tests for tool-call event tracking."""

from __future__ import annotations

import sys
import threading
import unittest
from pathlib import Path


SRC_DIRECTORY = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))

from services.tool_events import ToolCallTracker


class ToolCallTrackerTests(unittest.TestCase):
    def test_record_assigns_unique_ids_for_concurrent_calls(self) -> None:
        """Every recorded tool call receives a unique sequential event ID."""

        tracker = ToolCallTracker(notes_workspace=None)
        worker_count = 32
        events_per_worker = 500
        start_barrier = threading.Barrier(worker_count)

        def record_events() -> None:
            start_barrier.wait()
            for _ in range(events_per_worker):
                tracker.record(
                    {
                        "agent_name": "test-agent",
                        "tool_name": "test-tool",
                        "parsed_parameters": {},
                    }
                )

        previous_switch_interval = sys.getswitchinterval()
        sys.setswitchinterval(0.000001)
        try:
            threads = [threading.Thread(target=record_events) for _ in range(worker_count)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        finally:
            sys.setswitchinterval(previous_switch_interval)

        event_ids = [event["id"] for event in tracker.as_dicts()]
        expected_count = worker_count * events_per_worker

        self.assertEqual(len(event_ids), expected_count)
        self.assertEqual(sorted(event_ids), list(range(1, expected_count + 1)))


if __name__ == "__main__":
    unittest.main()
