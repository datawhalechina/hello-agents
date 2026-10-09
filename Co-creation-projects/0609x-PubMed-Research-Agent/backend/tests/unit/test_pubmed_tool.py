"""
Unit tests for tools/pubmed_tool.py
"""

from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Ensure tools/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.tools.pubmed_tool import (
    Author,
    PubMedArticle,
    PubMedSearchResult,
    PubMedSearchTool,
    PubMedAPIError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tool_no_key():
    """Return a PubMedSearchTool without an API key."""
    return PubMedSearchTool(email="test@example.com")


@pytest.fixture
def tool_with_key():
    """Return a PubMedSearchTool with an API key."""
    return PubMedSearchTool(email="test@example.com", api_key="fake-key-123")


@pytest.fixture
def mock_esearch_response():
    """Minimal ESearch response dict as returned by Entrez.read."""
    return {"Count": "3", "IdList": ["12345", "67890", "11111"]}


@pytest.fixture
def mock_efetch_xml():
    """Return realistic but minimal EFetch XML for Entrez.read to parse."""
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        "<PubmedArticleSet>"
        "<PubmedArticle>"
        "<MedlineCitation>"
        "<PMID>12345</PMID>"
        "<Article>"
        '<ArticleTitle>SEC61G promotes lung cancer invasion</ArticleTitle>'
        "<Abstract>"
        '<AbstractText Label="BACKGROUND">Background text here.</AbstractText>'
        '<AbstractText Label="METHODS">Methods text here.</AbstractText>'
        '<AbstractText Label="RESULTS">Results text here.</AbstractText>'
        "</Abstract>"
        "<AuthorList>"
        "<Author>"
        "<LastName>Zhang</LastName>"
        "<ForeName>Wei</ForeName>"
        "<Initials>W</Initials>"
        "<AffiliationInfo>"
        "<Affiliation>Peking University</Affiliation>"
        "</AffiliationInfo>"
        "</Author>"
        "<Author>"
        "<LastName>Li</LastName>"
        "<ForeName>Min</ForeName>"
        "<Initials>M</Initials>"
        "</Author>"
        "</AuthorList>"
        "<Journal>"
        "<Title>Cancer Res</Title>"
        "<JournalIssue>"
        '<PubDate><Year>2024</Year><Month>Mar</Month><Day>15</Day></PubDate>'
        "</JournalIssue>"
        "</Journal>"
        "<ELocationID EIdType=\"doi\" ValidYN=\"Y\">10.1000/j.canres.2024.0001</ELocationID>"
        "<PublicationTypeList><PublicationType>Journal Article</PublicationType></PublicationTypeList>"
        "</Article>"
        "</MedlineCitation>"
        "</PubmedArticle>"
        "</PubmedArticleSet>"
    )


# ---------------------------------------------------------------------------
# Author dataclass
# ---------------------------------------------------------------------------

class TestAuthor:
    def test_author_full_name_with_both(self):
        a = Author(last_name="Zhang", fore_name="Wei")
        assert a.full_name == "Zhang Wei"

    def test_author_full_name_initials_fallback(self):
        a = Author(last_name="Zhang", initials="W")
        assert a.full_name == "Zhang W"

    def test_author_full_name_last_only(self):
        a = Author(last_name="Zhang")
        assert a.full_name == "Zhang"

    def test_author_full_name_unknown(self):
        a = Author()
        assert a.full_name == "Unknown"


# ---------------------------------------------------------------------------
# PubMedArticle dataclass
# ---------------------------------------------------------------------------

class TestPubMedArticle:
    def test_pubmed_url(self):
        article = PubMedArticle(pmid="12345")
        assert article.pubmed_url == "https://pubmed.ncbi.nlm.nih.gov/12345/"

    def test_author_names(self):
        article = PubMedArticle(
            pmid="1",
            authors=[
                Author(last_name="Zhang", fore_name="Wei"),
                Author(last_name="Li", fore_name="Min"),
            ],
        )
        assert article.author_names == ["Zhang Wei", "Li Min"]

    def test_to_dict(self):
        article = PubMedArticle(
            pmid="12345",
            title="Test Title",
            abstract="Test abstract.",
            doi="10.1000/test",
            authors=[Author(last_name="Zhang", fore_name="Wei", affiliation="PKU")],
            journal="Nature",
            publish_date="2024 Jan 01",
            publication_type="Journal Article",
        )
        d = article.to_dict()
        assert d["pmid"] == "12345"
        assert d["title"] == "Test Title"
        assert d["doi"] == "10.1000/test"
        assert len(d["authors"]) == 1
        assert d["authors"][0]["last_name"] == "Zhang"
        assert d["authors"][0]["affiliation"] == "PKU"
        assert d["journal"] == "Nature"

    def test_to_dict_empty_article(self):
        article = PubMedArticle(pmid="0")
        d = article.to_dict()
        assert d["abstract"] == ""
        assert d["authors"] == []


# ---------------------------------------------------------------------------
# PubMedSearchResult dataclass
# ---------------------------------------------------------------------------

class TestPubMedSearchResult:
    def test_bool_true(self):
        r = PubMedSearchResult(query="q", total_count=1, articles=[PubMedArticle(pmid="1")])
        assert bool(r) is True

    def test_bool_false(self):
        r = PubMedSearchResult(query="q", total_count=0, articles=[])
        assert bool(r) is False

    def test_len(self):
        r = PubMedSearchResult(
            query="q",
            total_count=3,
            articles=[
                PubMedArticle(pmid="1"),
                PubMedArticle(pmid="2"),
                PubMedArticle(pmid="3"),
            ],
        )
        assert len(r) == 3


# ---------------------------------------------------------------------------
# PubMedSearchTool — construction & rate limiting
# ---------------------------------------------------------------------------

class TestPubMedSearchToolInit:
    def test_requires_valid_email(self):
        with pytest.raises(ValueError, match="email"):
            PubMedSearchTool(email="")

    def test_requires_at_sign(self):
        with pytest.raises(ValueError, match="email"):
            PubMedSearchTool(email="no-at-sign")

    def test_default_values(self):
        tool = PubMedSearchTool(email="test@example.com")
        assert tool.email == "test@example.com"
        assert tool.api_key is None
        assert tool.tool_name == "PubMed-Research-Agent"

    def test_with_api_key(self):
        tool = PubMedSearchTool(email="x@y.com", api_key="abc")
        assert tool.api_key == "abc"


# ---------------------------------------------------------------------------
# PubMedSearchTool — search (mocked)
# ---------------------------------------------------------------------------

class TestPubMedSearchToolSearch:
    def test_search_returns_result(self, tool_no_key, mock_efetch_xml):
        with patch("backend.tools.pubmed_tool.Entrez.esearch") as mock_es, \
             patch("backend.tools.pubmed_tool.Entrez.efetch") as mock_ef, \
             patch("backend.tools.pubmed_tool.Entrez.read") as mock_read:
            # ESearch returns PMIDs
            mock_read.side_effect = [
                {"Count": "3", "IdList": ["12345", "67890", "11111"]},
                self._build_parsed_efetch(),
            ]
            mock_es.return_value = MagicMock()
            mock_ef.return_value = MagicMock()

            result = tool_no_key.search("lung cancer", max_results=3)

            assert isinstance(result, PubMedSearchResult)
            assert result.query == "lung cancer"
            assert len(result.articles) == 1
            assert result.articles[0].pmid == "12345"
            assert "SEC61G" in result.articles[0].title
            assert result.articles[0].doi == "10.1000/j.canres.2024.0001"
            assert result.articles[0].journal == "Cancer Res"
            assert result.articles[0].publish_date == "2024 Mar 15"
            assert len(result.articles[0].authors) == 2
            assert result.articles[0].authors[0].full_name == "Zhang Wei"
            assert result.articles[0].publication_type == "Journal Article"

    def test_search_no_results(self, tool_no_key):
        with patch("backend.tools.pubmed_tool.Entrez.esearch") as mock_es, \
             patch("backend.tools.pubmed_tool.Entrez.read") as mock_read:
            mock_read.return_value = {"Count": "0", "IdList": []}
            mock_es.return_value = MagicMock()

            result = tool_no_key.search("xyznonexistent")

            assert result.total_count == 0
            assert len(result.articles) == 0
            assert result.query == "xyznonexistent"

    def test_search_raises_on_http_error(self, tool_no_key):
        with patch("backend.tools.pubmed_tool.Entrez.esearch") as mock_es:
            from Bio.Entrez import HTTPError
            mock_es.side_effect = HTTPError("http://fake", 500, "Internal Server Error", {}, None)

            with pytest.raises(PubMedAPIError, match="ESearch failed"):
                tool_no_key.search("query")

    def test_search_raises_on_unexpected_error(self, tool_no_key):
        with patch("backend.tools.pubmed_tool.Entrez.esearch") as mock_es:
            mock_es.side_effect = OSError("network down")

            with pytest.raises(PubMedAPIError, match="ESearch failed"):
                tool_no_key.search("query")

    @staticmethod
    def _build_parsed_efetch():
        """Build a minimal parsed EFetch record dict."""
        return {
            "PubmedArticle": [
                {
                    "MedlineCitation": {
                        "PMID": "12345",
                        "Article": {
                            "ArticleTitle": "SEC61G promotes lung cancer invasion",
                            "Abstract": {
                                "AbstractText": [
                                    "Background text here.",
                                    "Methods text here.",
                                    "Results text here.",
                                ]
                            },
                            "AuthorList": [
                                {
                                    "LastName": "Zhang",
                                    "ForeName": "Wei",
                                    "Initials": "W",
                                    "AffiliationInfo": [
                                        {"Affiliation": "Peking University"}
                                    ],
                                },
                                {
                                    "LastName": "Li",
                                    "ForeName": "Min",
                                    "Initials": "M",
                                    "AffiliationInfo": [],
                                },
                            ],
                            "Journal": {
                                "Title": "Cancer Res",
                                "JournalIssue": {
                                    "PubDate": {
                                        "Year": "2024",
                                        "Month": "Mar",
                                        "Day": "15",
                                    }
                                },
                            },
                            "ELocationID": [
                                "10.1000/j.canres.2024.0001",
                            ],
                            "PublicationTypeList": ["Journal Article"],
                        },
                    }
                }
            ]
        }


# ---------------------------------------------------------------------------
# PubMedSearchTool — DOI extraction
# ---------------------------------------------------------------------------

class TestDOIExtraction:
    def test_extract_doi_from_string_eid(self):
        article_data = {"ELocationID": ["10.1000/test doi review-article"]}
        doi = PubMedSearchTool._extract_doi(article_data)
        assert doi == "10.1000/test"

    def test_extract_doi_none(self):
        article_data = {}
        doi = PubMedSearchTool._extract_doi(article_data)
        assert doi == ""


# ---------------------------------------------------------------------------
# PubMedSearchTool — publish date parsing
# ---------------------------------------------------------------------------

class TestParsePubDate:
    def test_full_date(self):
        pd = PubMedSearchTool._parse_pub_date({
            "JournalIssue": {
                "PubDate": {"Year": "2024", "Month": "Mar", "Day": "15"}
            }
        })
        assert pd == "2024 Mar 15"

    def test_year_month_only(self):
        pd = PubMedSearchTool._parse_pub_date({
            "JournalIssue": {
                "PubDate": {"Year": "2023", "Month": "Jan"}
            }
        })
        assert pd == "2023 Jan"

    def test_year_only(self):
        pd = PubMedSearchTool._parse_pub_date({
            "JournalIssue": {"PubDate": {"Year": "2022"}}
        })
        assert pd == "2022"

    def test_numeric_month_translation(self):
        pd = PubMedSearchTool._parse_pub_date({
            "JournalIssue": {
                "PubDate": {"Year": "2024", "Month": "06", "Day": "01"}
            }
        })
        assert pd == "2024 Jun 01"

    def test_empty_journal(self):
        pd = PubMedSearchTool._parse_pub_date({})
        assert pd == ""



