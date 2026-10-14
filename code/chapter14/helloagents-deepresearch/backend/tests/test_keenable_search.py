"""Tests for the Keenable search backend.

Run from ``backend/`` with ``python -m unittest discover tests`` (pytest also
picks these up). No network access is needed; ``requests`` is mocked.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services import keenable_search  # noqa: E402


def _response(status: int, payload=None, text: str = "") -> mock.Mock:
    response = mock.Mock()
    response.status_code = status
    response.text = text
    response.json.return_value = payload
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(str(status))
    else:
        response.raise_for_status.return_value = None
    return response


SEARCH_PAYLOAD = {
    "results": [
        {
            "url": "https://example.com/a",
            "title": "Page A",
            "snippet": "Snippet A",
            "description": "",
        },
        {
            "url": "https://example.com/b",
            "title": "",
            "snippet": "",
            "description": "Description B",
        },
        {"title": "no url"},
    ]
}


class KeenableSearchTests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop("KEENABLE_API_KEY", None)

    def tearDown(self):
        self.env.stop()

    def test_keyless_call_uses_public_endpoint_and_title_header(self):
        with mock.patch.object(requests, "post", return_value=_response(200, SEARCH_PAYLOAD)) as post:
            payload = keenable_search.search_keenable("hello agents", max_results=3)

        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.keenable.ai/v1/search/public")
        self.assertEqual(kwargs["headers"]["X-Keenable-Title"], "hello-agents-deepresearch")
        self.assertNotIn("X-API-Key", kwargs["headers"])
        self.assertEqual(kwargs["json"]["query"], "hello agents")
        self.assertEqual(kwargs["json"]["max_results"], 3)

        self.assertEqual(payload["backend"], "keenable")
        self.assertIsNone(payload["answer"])
        self.assertEqual([r["url"] for r in payload["results"]], ["https://example.com/a", "https://example.com/b"])
        self.assertEqual(payload["results"][0]["content"], "Snippet A")
        self.assertEqual(payload["results"][1]["content"], "Description B")
        self.assertEqual(payload["results"][1]["title"], "https://example.com/b")
        self.assertEqual(len(payload["notices"]), 1)

    def test_api_key_switches_to_keyed_endpoint(self):
        os.environ["KEENABLE_API_KEY"] = "kn-test"
        with mock.patch.object(requests, "post", return_value=_response(200, {"results": []})) as post:
            keenable_search.search_keenable("q")

        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.keenable.ai/v1/search")
        self.assertEqual(kwargs["headers"]["X-API-Key"], "kn-test")
        self.assertEqual(kwargs["headers"]["X-Keenable-Title"], "hello-agents-deepresearch")

    def test_blank_api_key_is_treated_as_keyless(self):
        os.environ["KEENABLE_API_KEY"] = "   "
        with mock.patch.object(requests, "post", return_value=_response(200, {"results": []})) as post:
            keenable_search.search_keenable("q")

        self.assertEqual(post.call_args[0][0], "https://api.keenable.ai/v1/search/public")

    def test_rate_limit_returns_notice_not_results(self):
        with mock.patch.object(requests, "post", return_value=_response(429, text="rate limited")):
            payload = keenable_search.search_keenable("q")

        self.assertEqual(payload["results"], [])
        self.assertEqual(len(payload["notices"]), 1)
        self.assertIn("429", payload["notices"][0])
        self.assertIn("KEENABLE_API_KEY", payload["notices"][0])

    def test_other_http_errors_raise(self):
        with mock.patch.object(requests, "post", return_value=_response(400, text="missing title")):
            with self.assertRaises(RuntimeError) as ctx:
                keenable_search.search_keenable("q")
        self.assertIn("400", str(ctx.exception))

    def test_fetch_full_page_fills_raw_content_and_falls_back_to_snippet(self):
        fetch_ok = _response(200, {"url": "https://example.com/a", "content": "x" * 100})
        fetch_bad = _response(404, text="not indexed")

        with mock.patch.object(requests, "post", return_value=_response(200, SEARCH_PAYLOAD)):
            with mock.patch.object(requests, "get", side_effect=[fetch_ok, fetch_bad]) as get:
                payload = keenable_search.search_keenable("q", fetch_full_page=True, max_tokens=10)

        self.assertEqual(get.call_count, 2)
        args, kwargs = get.call_args_list[0]
        self.assertEqual(args[0], "https://api.keenable.ai/v1/fetch/public")
        self.assertEqual(kwargs["params"], {"url": "https://example.com/a"})
        self.assertEqual(kwargs["headers"]["X-Keenable-Title"], "hello-agents-deepresearch")

        first, second = payload["results"]
        self.assertEqual(first["raw_content"], "x" * 40 + "... [truncated]")
        self.assertEqual(second["raw_content"], "Description B")

    def test_no_fetch_when_fetch_full_page_is_false(self):
        with mock.patch.object(requests, "post", return_value=_response(200, SEARCH_PAYLOAD)):
            with mock.patch.object(requests, "get") as get:
                payload = keenable_search.search_keenable("q", fetch_full_page=False)

        get.assert_not_called()
        self.assertEqual(payload["results"][0]["raw_content"], "Snippet A")


if __name__ == "__main__":
    unittest.main()
