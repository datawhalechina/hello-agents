"""Unit tests for services/literature_summary.py"""

from __future__ import annotations

import json
import sys
import os
from unittest.mock import MagicMock, patch, ANY

import pytest
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.services.literature_summary import (
    LiteratureSummarizer,
    LiteratureSummary,
    LiteratureSummaryError,
    ResearchHotspot,
    FutureDirection,
    ExperimentalMethod,
    MODEL_PRESETS,
)


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_ARTICLES = [
    {
        "pmid": "12345",
        "title": "SEC61G promotes lung cancer invasion via ER stress",
        "abstract": "Background: SEC61G is overexpressed in NSCLC. "
        "Methods: We used IHC, Western blot, and CRISPR knockout. "
        "Results: SEC61G knockdown inhibited migration by 60%. "
        "Conclusion: SEC61G is a potential therapeutic target.",
    },
    {
        "pmid": "67890",
        "title": "Immune microenvironment remodeling by SEC61G",
        "abstract": "This study analyzed TCGA data and performed "
        "flow cytometry on 200 patient samples. SEC61G expression "
        "correlated with CD8+ T cell infiltration and PD-L1 levels. "
        "Multivariate Cox regression confirmed prognostic value.",
    },
]

MOCK_LLM_RESPONSE = {
    "research_background": "SEC61G is a subunit of the SEC61 translocon "
    "implicated in protein translocation across the ER membrane. Recent "
    "studies have revealed its role in cancer biology.",
    "current_hotspots": [
        {
            "topic": "SEC61G as prognostic biomarker",
            "description": "Multiple studies link SEC61G expression to survival.",
            "evidence": ["PMID:12345", "PMID:67890"],
        },
        {
            "topic": "Immune microenvironment modulation",
            "description": "SEC61G affects T cell infiltration.",
            "evidence": ["PMID:67890"],
        },
    ],
    "main_findings": [
        "SEC61G is overexpressed in NSCLC tissues compared to normal lung.",
        "SEC61G knockdown reduces migration and invasion in vitro.",
        "High SEC61G correlates with poor overall survival.",
        "SEC61G modulates PD-L1 expression and CD8+ T cell infiltration.",
        "CRISPR-mediated SEC61G knockout validates its oncogenic role.",
    ],
    "experimental_methods": [
        {"method": "IHC", "purpose": "Protein expression in tissue", "frequency": 2},
        {"method": "Western blot", "purpose": "Protein quantification", "frequency": 1},
        {"method": "CRISPR/Cas9", "purpose": "Gene knockout validation", "frequency": 1},
        {"method": "Flow cytometry", "purpose": "Immune cell profiling", "frequency": 1},
    ],
    "future_directions": [
        {
            "direction": "Develop SEC61G-targeted small molecule inhibitors",
            "rationale": "Current findings show SEC61G is a driver, not just a marker.",
            "challenges": ["Selectivity over other SEC61 subunits", "Blood-brain barrier"],
        },
        {
            "direction": "Multi-center prospective validation",
            "rationale": "Current studies are retrospective with small sample sizes.",
            "challenges": ["Standardized IHC scoring", "Long follow-up required"],
        },
    ],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def summarizer():
    return LiteratureSummarizer(
        api_base="https://api.test.com/v1",
        api_key="test-key-123",
        model="gpt-4o-mini",
    )


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.Client.post to return a valid LLM response."""
    def mock_post(url, json_body=None, headers=None, **kwargs):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(MOCK_LLM_RESPONSE, ensure_ascii=False),
                    }
                }
            ],
            "usage": {"prompt_tokens": 500, "completion_tokens": 300, "total_tokens": 800},
        }
        resp.raise_for_status = MagicMock()
        return resp
    return mock_post


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestInit:
    def test_requires_api_key(self):
        with pytest.raises(ValueError, match="API key"):
            LiteratureSummarizer(api_base="http://x", api_key="")

    def test_default_values(self):
        s = LiteratureSummarizer(api_base="http://x", api_key="k")
        assert s.model == "gpt-4o"
        assert s.temperature == 0.3
        assert s.max_tokens == 4096
        assert s.timeout == 240.0
        assert s.verify_ssl is True

    def test_custom_values(self):
        s = LiteratureSummarizer(
            api_base="http://y/v1",
            api_key="k2",
            model="deepseek-chat",
            temperature=0.7,
            max_tokens=2048,
            timeout=60.0,
            verify_ssl=False,
        )
        assert s.api_base == "http://y/v1"
        assert s.model == "deepseek-chat"
        assert s.verify_ssl is False


class TestFromPreset:
    def test_gpt_preset(self):
        s = LiteratureSummarizer.from_preset("gpt-4o", api_key="k")
        assert s.api_base == "https://api.openai.com/v1"
        assert s.model == "gpt-4o"

    def test_deepseek_preset(self):
        s = LiteratureSummarizer.from_preset("deepseek-chat", api_key="k")
        assert s.api_base == "https://api.deepseek.com/v1"

    def test_qwen_preset(self):
        s = LiteratureSummarizer.from_preset("qwen-plus", api_key="k")
        assert "dashscope" in s.api_base

    def test_custom_base_override(self):
        s = LiteratureSummarizer.from_preset(
            "gpt-4o", api_key="k", api_base="http://local:8000/v1"
        )
        assert s.api_base == "http://local:8000/v1"

    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown model preset"):
            LiteratureSummarizer.from_preset("nonexistent-model", api_key="k")


# ---------------------------------------------------------------------------
# Summarize
# ---------------------------------------------------------------------------

class TestSummarize:
    def test_empty_articles_raises(self, summarizer):
        with pytest.raises(ValueError, match="At least one article"):
            summarizer.summarize([])

    def test_successful_summary(self, summarizer, mock_httpx_client):
        summarizer._client = MagicMock()
        summarizer._client.post = mock_httpx_client

        result = summarizer.summarize(SAMPLE_ARTICLES, language="en")

        assert isinstance(result, LiteratureSummary)
        assert len(result.current_hotspots) == 2
        assert result.current_hotspots[0].topic == "SEC61G as prognostic biomarker"
        assert len(result.main_findings) == 5
        assert len(result.experimental_methods) == 4
        assert result.experimental_methods[0].method == "IHC"
        assert len(result.future_directions) == 2
        assert result.future_directions[0].direction.startswith("Develop")
        assert result.model_used == "gpt-4o-mini"
        assert result.elapsed_seconds > 0
        assert "SEC61G" in result.research_background

    def test_summary_with_language_zh(self, summarizer, mock_httpx_client):
        summarizer._client = MagicMock()
        summarizer._client.post = mock_httpx_client

        result = summarizer.summarize(SAMPLE_ARTICLES, language="zh")
        assert isinstance(result, LiteratureSummary)

    def test_llm_returns_invalid_json(self, summarizer):
        summarizer._client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "not valid json!!!"}}]
        }
        mock_resp.raise_for_status = MagicMock()
        summarizer._client.post = MagicMock(return_value=mock_resp)

        with pytest.raises(LiteratureSummaryError, match="after 2 attempts"):
            summarizer.summarize(SAMPLE_ARTICLES)

    def test_llm_json_with_markdown_fence(self, summarizer):
        summarizer._client = MagicMock()
        json_str = json.dumps(MOCK_LLM_RESPONSE)
        fenced = f"```json\n{json_str}\n```"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": fenced}}]
        }
        mock_resp.raise_for_status = MagicMock()
        summarizer._client.post = MagicMock(return_value=mock_resp)

        # Should auto-repair the markdown fence
        result = summarizer.summarize(SAMPLE_ARTICLES)
        assert len(result.main_findings) == 5

    def test_llm_http_error(self, summarizer):
        summarizer._client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Unauthorized", request=MagicMock(), response=mock_resp
            )
        )
        summarizer._client.post = MagicMock(return_value=mock_resp)

        with pytest.raises(LiteratureSummaryError, match="401"):
            summarizer.summarize(SAMPLE_ARTICLES)

    def test_llm_network_error(self, summarizer):
        summarizer._client = MagicMock()
        summarizer._client.post = MagicMock(
            side_effect=httpx.RequestError("Connection refused")
        )

        with pytest.raises(LiteratureSummaryError, match="Connection refused"):
            summarizer.summarize(SAMPLE_ARTICLES)

    def test_llm_empty_choices(self, summarizer):
        summarizer._client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": []}
        mock_resp.raise_for_status = MagicMock()
        summarizer._client.post = MagicMock(return_value=mock_resp)

        with pytest.raises(LiteratureSummaryError, match="empty choices"):
            summarizer.summarize(SAMPLE_ARTICLES)

    def test_llm_empty_content(self, summarizer):
        summarizer._client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": ""}}]
        }
        mock_resp.raise_for_status = MagicMock()
        summarizer._client.post = MagicMock(return_value=mock_resp)

        with pytest.raises(LiteratureSummaryError, match="empty content"):
            summarizer.summarize(SAMPLE_ARTICLES)


# ---------------------------------------------------------------------------
# Article formatting
# ---------------------------------------------------------------------------

class TestFormatArticles:
    def test_basic_formatting(self, summarizer):
        text = summarizer._format_articles(SAMPLE_ARTICLES)
        assert "PMID:12345" in text
        assert "Title: SEC61G promotes" in text
        assert "Abstract: Background:" in text
        assert "[1]" in text
        assert "[2]" in text

    def test_missing_pmid_generates_placeholder(self, summarizer):
        text = summarizer._format_articles([{"title": "T", "abstract": "A"}])
        assert "PMID:UNKNOWN_1" in text

    def test_long_abstract_truncation(self, summarizer):
        text = summarizer._format_articles([
            {"pmid": "1", "title": "T", "abstract": "A" * 2000}
        ])
        assert "..." in text
        # 1500 chars + "..." = should end with ...
        assert text.rstrip().endswith("...")


# ---------------------------------------------------------------------------
# JSON repair
# ---------------------------------------------------------------------------

class TestRepairJson:
    def test_removes_markdown_fence(self):
        raw = '```json\n{"a": 1}\n```'
        fixed = LiteratureSummarizer._repair_json(raw)
        assert fixed == '{"a": 1}'

    def test_fixes_trailing_comma(self):
        raw = '{"a": 1, "b": 2,}'
        fixed = LiteratureSummarizer._repair_json(raw)
        assert '"b": 2' in fixed
        assert fixed.endswith("}")


# ---------------------------------------------------------------------------
# Output Models
# ---------------------------------------------------------------------------

class TestOutputModels:
    def test_literature_summary_construction(self):
        ls = LiteratureSummary(
            research_background="Background text.",
            current_hotspots=[
                ResearchHotspot(
                    topic="Hotspot 1",
                    description="Desc 1",
                    evidence=["PMID:1"],
                )
            ],
            main_findings=["Finding A", "Finding B"],
            experimental_methods=[
                ExperimentalMethod(method="WB", purpose="Quantification", frequency=3)
            ],
            future_directions=[
                FutureDirection(
                    direction="Direction X",
                    rationale="Rationale X",
                    challenges=["Challenge 1"],
                )
            ],
        )
        assert len(ls.current_hotspots) == 1
        assert len(ls.main_findings) == 2
        assert ls.experimental_methods[0].method == "WB"
        assert ls.future_directions[0].direction == "Direction X"

    def test_default_values(self):
        ls = LiteratureSummary(
            research_background="",
            current_hotspots=[],
            main_findings=[],
            experimental_methods=[],
            future_directions=[],
        )
        assert ls.model_used == ""
        assert ls.token_usage == {}
        assert ls.elapsed_seconds == 0.0


# ---------------------------------------------------------------------------
# Truncated / invalid JSON handling
# ---------------------------------------------------------------------------

class TestTruncatedJsonHandling:
    def test_salvage_drops_unterminated_tail_string(self):
        raw = '{"research_background": "this string is truncated'
        salvaged = LiteratureSummarizer._salvage_truncated_json(raw)
        assert salvaged == raw  # nothing recoverable -> unchanged

    def test_salvage_recovers_valid_prefix_before_truncation(self):
        raw = '{"research_background": "bg", "main_findings": ["a", "b"'
        salvaged = LiteratureSummarizer._salvage_truncated_json(raw)
        data = json.loads(salvaged)
        assert data == {
            "research_background": "bg",
            "main_findings": ["a", "b"],
        }

    def test_salvage_autocloses_missing_braces(self):
        raw = '{"research_background": "bg", "nested": {"key": "val"'
        salvaged = LiteratureSummarizer._salvage_truncated_json(raw)
        data = json.loads(salvaged)
        assert data == {"research_background": "bg", "nested": {"key": "val"}}

    def test_parse_llm_json_salvages_truncated(self, summarizer):
        raw = '{"research_background": "bg", "current_hotspots": [], "main_findings": ["x"'
        data = summarizer._parse_llm_json(raw)
        assert data is not None
        assert data["research_background"] == "bg"

    def test_parse_llm_json_returns_none_on_garbage(self, summarizer):
        assert summarizer._parse_llm_json("not json at all") is None

    def test_retries_once_then_succeeds(self, summarizer):
        summarizer._client = MagicMock()
        calls = []

        def mock_post(url, headers=None, **kwargs):
            calls.append(kwargs.get("json"))
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            if len(calls) == 1:
                content = '{"research_background": "trunc'
            else:
                content = json.dumps(MOCK_LLM_RESPONSE, ensure_ascii=False)
            resp.json.return_value = {
                "choices": [{"message": {"content": content}}]
            }
            return resp

        summarizer._client.post = MagicMock(side_effect=mock_post)
        summary = summarizer.summarize(SAMPLE_ARTICLES)
        assert len(calls) == 2
        assert calls[1]["max_tokens"] > calls[0]["max_tokens"]
        assert summary.research_background == MOCK_LLM_RESPONSE["research_background"]

    def test_invalid_json_twice_raises(self, summarizer):
        summarizer._client = MagicMock()
        calls = []

        def mock_post(url, json_body=None, headers=None, **kwargs):
            calls.append(json_body)
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {
                "choices": [{"message": {"content": "broken"}}]
            }
            return resp

        summarizer._client.post = MagicMock(side_effect=mock_post)
        with pytest.raises(LiteratureSummaryError, match="after 2 attempts"):
            summarizer.summarize(SAMPLE_ARTICLES)
        assert len(calls) == 2

    def test_schema_missing_field_retries(self, summarizer):
        summarizer._client = MagicMock()
        calls = []

        def mock_post(url, json_body=None, headers=None, **kwargs):
            calls.append(json_body)
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            if len(calls) == 1:
                content = '{"research_background": "only bg"}'
            else:
                content = json.dumps(MOCK_LLM_RESPONSE, ensure_ascii=False)
            resp.json.return_value = {
                "choices": [{"message": {"content": content}}]
            }
            return resp

        summarizer._client.post = MagicMock(side_effect=mock_post)
        summary = summarizer.summarize(SAMPLE_ARTICLES)
        assert len(calls) == 2
        assert summary.model_used == summarizer.model

    def test_retries_once_on_timeout(self, summarizer):
        summarizer._client = MagicMock()
        calls = []

        def mock_post(url, headers=None, **kwargs):
            calls.append(kwargs.get("json"))
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            if len(calls) == 1:
                raise httpx.ReadTimeout("read timed out")
            resp.json.return_value = {
                "choices": [
                    {"message": {"content": json.dumps(MOCK_LLM_RESPONSE, ensure_ascii=False)}}
                ]
            }
            return resp

        summarizer._client.post = MagicMock(side_effect=mock_post)
        summary = summarizer.summarize(SAMPLE_ARTICLES)
        assert len(calls) == 2
        assert calls[1]["max_tokens"] > calls[0]["max_tokens"]
        assert summary.research_background == MOCK_LLM_RESPONSE["research_background"]

    def test_timeout_twice_raises(self, summarizer):
        summarizer._client = MagicMock()
        calls = []

        def mock_post(url, headers=None, **kwargs):
            calls.append(1)
            raise httpx.ReadTimeout("read timed out")

        summarizer._client.post = MagicMock(side_effect=mock_post)
        with pytest.raises(LiteratureSummaryError, match="after 2 attempts"):
            summarizer.summarize(SAMPLE_ARTICLES)
        assert len(calls) == 2
