"""Unit tests for services/translation.py"""

from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock

import pytest
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.services.translation import LiteratureTranslator, TranslationError


@pytest.fixture
def translator():
    return LiteratureTranslator(
        api_base="https://api.test.com/v1",
        api_key="test-key-123",
        model="gpt-4o-mini",
    )


def _mock_response(content: str, status_code: int = 200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if status_code == 200:
        resp.json.return_value = {
            "choices": [{"message": {"content": content}}]
        }
    else:
        resp.text = "Unauthorized"
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Unauthorized", request=MagicMock(), response=resp
            )
        )
    if status_code == 200:
        resp.raise_for_status = MagicMock()
    return resp


class TestInit:
    def test_requires_api_key(self):
        with pytest.raises(ValueError, match="API key"):
            LiteratureTranslator(api_base="http://x", api_key="", model="gpt-4o")

    def test_default_values(self):
        t = LiteratureTranslator(api_base="http://x", api_key="k", model="gpt-4o")
        assert t.temperature == 0.2
        assert t.max_tokens == 2048
        assert t.timeout == 120.0


class TestTranslate:
    def test_translate_success(self, translator):
        translator._client = MagicMock()
        translator._client.post = MagicMock(
            return_value=_mock_response("SEC61G 在肺腺癌中高表达。")
        )
        out = translator.translate("SEC61G is overexpressed in LUAD.", "zh")
        assert out == "SEC61G 在肺腺癌中高表达。"
        # verify payload
        _, kwargs = translator._client.post.call_args
        payload = kwargs["json"]
        assert payload["model"] == "gpt-4o-mini"
        assert payload["messages"][0]["role"] == "system"
        assert "Simplified Chinese" in payload["messages"][0]["content"]

    def test_translate_empty_text(self, translator):
        assert translator.translate("", "zh") == ""
        assert translator.translate("   ", "zh") == ""
        translator._client = MagicMock()
        translator._client.post = MagicMock()
        translator.translate("", "zh")
        translator._client.post.assert_not_called()

    def test_translate_long_text_chunks(self, translator):
        translator._client = MagicMock()
        long_text = ("A sentence with enough length to force chunking. " * 60)[:4000]
        translator._client.post = MagicMock(
            return_value=_mock_response("翻译结果")
        )
        out = translator.translate(long_text, "zh")
        assert translator._client.post.call_count > 1
        assert out.count("翻译结果") == translator._client.post.call_count

    def test_translate_http_error(self, translator):
        translator._client = MagicMock()
        translator._client.post = MagicMock(return_value=_mock_response("", 401))
        with pytest.raises(TranslationError, match="401"):
            translator.translate("hello", "zh")

    def test_translate_request_error(self, translator):
        translator._client = MagicMock()
        translator._client.post = MagicMock(
            side_effect=httpx.RequestError("Connection refused")
        )
        with pytest.raises(TranslationError, match="Connection refused"):
            translator.translate("hello", "zh")

    def test_translate_empty_choices(self, translator):
        translator._client = MagicMock()
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.return_value = {"choices": []}
        resp.raise_for_status = MagicMock()
        translator._client.post = MagicMock(return_value=resp)
        with pytest.raises(TranslationError, match="empty choices"):
            translator.translate("hello", "zh")

    def test_translate_empty_content(self, translator):
        translator._client = MagicMock()
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.return_value = {"choices": [{"message": {"content": ""}}]}
        resp.raise_for_status = MagicMock()
        translator._client.post = MagicMock(return_value=resp)
        with pytest.raises(TranslationError, match="empty content"):
            translator.translate("hello", "zh")


class TestTranslateArticle:
    def test_article_zh_fields(self, translator):
        translator._client = MagicMock()
        translator._client.post = MagicMock(
            return_value=_mock_response("翻译后的摘要")
        )
        article = {
            "pmid": "123",
            "title": "SEC61G in lung cancer",
            "abstract": "Background: ...",
        }
        out = translator.translate_article(article, "zh")
        assert out["pmid"] == "123"
        assert "title_zh" in out
        assert "abstract_zh" in out
        assert out["title_zh"] == "翻译后的摘要"
        assert out["abstract_zh"] == "翻译后的摘要"


class TestChunkText:
    def test_short_text_single_chunk(self):
        assert LiteratureTranslator._chunk_text("short text") == ["short text"]

    def test_long_text_split(self):
        text = "A paragraph one. " * 200
        chunks = LiteratureTranslator._chunk_text(text)
        assert len(chunks) > 1
        assert all(len(c) <= 1800 + 2 for c in chunks)
        assert "".join(chunks).replace(" ", "").startswith(text.replace(" ", "")[:20])
