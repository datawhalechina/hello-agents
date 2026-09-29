import unittest

import httpx

from d2c.figma import fetch_figma, parse_figma_url


class FigmaTests(unittest.TestCase):
    def test_parse_url_and_override(self):
        self.assertEqual(parse_figma_url("https://www.figma.com/design/AbCd9/Work?node-id=1-2"), ("AbCd9", "1:2"))
        self.assertEqual(parse_figma_url("https://figma.com/file/AbCd9", "5:9"), ("AbCd9", "5:9"))

    def test_only_figma_https_with_frame(self):
        for url in ("http://figma.com/design/abc?node-id=1-2", "https://figma.com.evil.test/design/abc?node-id=1-2",
                    "https://localhost/design/abc?node-id=1-2", "https://figma.com/design/abc",
                    "https://user@figma.com/design/abc?node-id=1-2", "https://figma.com:9000/design/abc?node-id=1-2"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse_figma_url(url)

    def test_fetch_only_fixed_api_and_header(self):
        def handler(request):
            self.assertEqual(request.url.host, "api.figma.com")
            self.assertEqual(request.url.params["ids"], "1:2")
            self.assertEqual(request.headers["X-Figma-Token"], "test-token")
            self.assertNotIn("test-token", str(request.url))
            return httpx.Response(200, json={"nodes": {"1:2": {"document": {"id": "1:2", "type": "FRAME"}}}})
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            payload, node = fetch_figma("https://figma.com/design/abc?node-id=1-2", "test-token", client=client)
        self.assertEqual(node, "1:2")
        self.assertIn(node, payload["nodes"])

    def test_null_node_and_http_errors(self):
        for status in (401, 403, 404, 429, 500, 302, 200):
            with self.subTest(status=status):
                with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(status, json={"nodes": {"1:2": None}}))) as client:
                    with self.assertRaises(ValueError):
                        fetch_figma("https://figma.com/design/abc?node-id=1-2", "test-token", client=client)

    def test_missing_token_rejected(self):
        with self.assertRaisesRegex(ValueError, "FIGMA_ACCESS_TOKEN"):
            fetch_figma("https://figma.com/design/abc?node-id=1-2", "")


if __name__ == "__main__":
    unittest.main()
