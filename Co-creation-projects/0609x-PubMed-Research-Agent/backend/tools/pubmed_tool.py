"""
PubMed Search Tool

NCBI E-utilities API wrapper for searching and fetching PubMed articles.

Usage:
    tool = PubMedSearchTool(email="user@example.com")
    results = tool.search("SEC61G in Lung Cancer", max_results=20)

Each result includes: pmid, title, abstract, doi, authors, journal, publish_date.
"""

from __future__ import annotations

import logging
import re
import ssl
import time
from dataclasses import dataclass, field
from typing import Optional

from Bio import Entrez
from Bio.Entrez import HTTPError as EntrezHTTPError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class Author:
    """Represents a single author entry."""

    last_name: str = ""
    fore_name: str = ""
    initials: str = ""
    affiliation: str = ""

    @property
    def full_name(self) -> str:
        """Return the full author name in 'LastName FN' format."""
        if self.last_name and self.fore_name:
            return f"{self.last_name} {self.fore_name}"
        if self.last_name and self.initials:
            return f"{self.last_name} {self.initials}"
        return self.last_name or self.fore_name or "Unknown"


@dataclass
class PubMedArticle:
    """Structured representation of a single PubMed article."""

    pmid: str
    title: str = ""
    abstract: str = ""
    doi: str = ""
    authors: list[Author] = field(default_factory=list)
    journal: str = ""
    publish_date: str = ""
    publication_type: str = ""

    @property
    def pubmed_url(self) -> str:
        """Return the PubMed web URL for this article."""
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"

    @property
    def author_names(self) -> list[str]:
        """Return the list of author full names."""
        return [a.full_name for a in self.authors]

    def to_dict(self) -> dict:
        """Serialize the article to a plain dict."""
        return {
            "pmid": self.pmid,
            "title": self.title,
            "abstract": self.abstract,
            "doi": self.doi,
            "authors": [
                {
                    "last_name": a.last_name,
                    "fore_name": a.fore_name,
                    "initials": a.initials,
                    "affiliation": a.affiliation,
                }
                for a in self.authors
            ],
            "journal": self.journal,
            "publish_date": self.publish_date,
            "publication_type": self.publication_type,
        }


@dataclass
class PubMedSearchResult:
    """The result of a PubMed search, including metadata and article list."""

    query: str
    total_count: int
    articles: list[PubMedArticle] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    def __len__(self) -> int:
        return len(self.articles)

    def __bool__(self) -> bool:
        return len(self.articles) > 0


# ---------------------------------------------------------------------------
# PubMedSearchTool
# ---------------------------------------------------------------------------

class PubMedSearchTool:
    """Encapsulated PubMed search tool using NCBI E-utilities.

    Rate limits (no API key: 3 req/s; with key: 10 req/s) are respected
    automatically via sleep-based throttling.

    Parameters
    ----------
    email : str
        Your email address (NCBI requirement).
    api_key : str, optional
        NCBI API key for higher rate limits.
    tool_name : str, optional
        Tool name sent to NCBI for identification.
    """

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(
        self,
        email: str,
        api_key: Optional[str] = None,
        tool_name: str = "PubMed-Research-Agent",
        verify_ssl: bool = True,
    ) -> None:
        if not email or "@" not in email:
            raise ValueError("A valid email address is required by NCBI.")

        self.email: str = email
        self.api_key: Optional[str] = api_key
        self.tool_name: str = tool_name
        self.verify_ssl: bool = verify_ssl

        # Register globals with Bio.Entrez
        Entrez.email = email
        Entrez.tool = tool_name
        if api_key:
            Entrez.api_key = api_key

        # SSL verification (disable for corporate proxy environments)
        if not verify_ssl:
            import urllib.request
            urllib.request.install_opener(
                urllib.request.build_opener(
                    urllib.request.HTTPSHandler(
                        context=ssl._create_unverified_context()
                    )
                )
            )
            logger.warning("SSL verification DISABLED")

        # Rate-limiting
        self._min_interval: float = 1.0 / 3.0  # 3 req/s default
        if api_key:
            self._min_interval = 1.0 / 10.0     # 10 req/s with key
        self._last_request_time: float = 0.0

        logger.info(
            "PubMedSearchTool initialized (email=%s, api_key=%s, rate=%.1f req/s)",
            email,
            "***" if api_key else "not set",
            1.0 / self._min_interval,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        max_results: int = 20,
        retstart: int = 0,
        sort: str = "relevance",
    ) -> PubMedSearchResult:
        """Execute a PubMed search and return structured results.

        Parameters
        ----------
        query : str
            Free-text query or PubMed query syntax.
        max_results : int
            Maximum number of articles to fetch (capped at 100 per batch).
        retstart : int
            Offset for paginated results.
        sort : str
            Sort order: `"relevance"`, `"pub_date"`, `"first_author"`.

        Returns
        -------
        PubMedSearchResult
            Object containing the query, total PubMed count, and fetched articles.
        """
        start_time = time.perf_counter()
        logger.info("Search initiated: query=%r, max=%d", query, max_results)

        # 1. ESearch - get PMID list
        pmids = self._esearch(query, max_results, retstart, sort)

        if not pmids:
            logger.info("No PMIDs returned for query=%r", query)
            return PubMedSearchResult(
                query=query,
                total_count=0,
                articles=[],
            )

        total_count = len(pmids)
        logger.info("ESearch returned %d PMIDs", total_count)

        # 2. EFetch - get full records
        articles = self._efetch(pmids)

        elapsed = time.perf_counter() - start_time
        logger.info(
            "Search completed: %d articles fetched in %.2fs",
            len(articles),
            elapsed,
        )

        return PubMedSearchResult(
            query=query,
            total_count=total_count,
            articles=articles,
            elapsed_seconds=round(elapsed, 3),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _throttle(self) -> None:
        """Enforce rate-limiting between NCBI requests."""
        now = time.perf_counter()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            sleep_for = self._min_interval - elapsed
            logger.debug("Rate-limit: sleeping %.3fs", sleep_for)
            time.sleep(sleep_for)
        self._last_request_time = time.perf_counter()

    def _esearch(
        self,
        query: str,
        max_results: int,
        retstart: int,
        sort: str,
    ) -> list[str]:
        """Run ESearch and return a list of PMID strings."""
        self._throttle()

        try:
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                retstart=retstart,
                sort=sort,
            )
            record = Entrez.read(handle)
            handle.close()
            pmids = record.get("IdList", [])
            if isinstance(pmids, list):
                return [str(p) for p in pmids]
            return []
        except EntrezHTTPError as exc:
            logger.error("ESearch HTTP error: %s", exc)
            raise PubMedAPIError(f"ESearch failed: {exc}") from exc
        except Exception as exc:
            logger.error("ESearch unexpected error: %s", exc)
            raise PubMedAPIError(f"ESearch failed unexpectedly: {exc}") from exc

    def _efetch(self, pmids: list[str]) -> list[PubMedArticle]:
        """Run EFetch for a batch of PMIDs and parse into PubMedArticle objects."""
        if not pmids:
            return []

        self._throttle()

        try:
            handle = Entrez.efetch(
                db="pubmed",
                id=",".join(pmids),
                rettype="xml",
                retmode="xml",
            )
            records = Entrez.read(handle)
            handle.close()
        except EntrezHTTPError as exc:
            logger.error("EFetch HTTP error: %s", exc)
            raise PubMedAPIError(f"EFetch failed: {exc}") from exc
        except Exception as exc:
            logger.error("EFetch unexpected error: %s", exc)
            raise PubMedAPIError(f"EFetch failed unexpectedly: {exc}") from exc

        articles: list[PubMedArticle] = []
        pubmed_articles = records.get("PubmedArticle", [])

        for record in pubmed_articles:
            try:
                article = self._parse_record(record)
                if article.pmid:
                    articles.append(article)
            except Exception as exc:
                logger.warning("Skipping malformed record: %s", exc)
                continue

        return articles

    def _parse_record(self, record: dict) -> PubMedArticle:
        """Parse a single PubmedArticle record dict into a PubMedArticle."""
        medline = record.get("MedlineCitation", {})
        article_data = medline.get("Article", {})

        # PMID
        pmid = str(medline.get("PMID", ""))

        # Title
        title = _strip_html(_safe_str(article_data.get("ArticleTitle", "")))

        # Abstract
        abstract_parts = article_data.get("Abstract", {}).get("AbstractText", [])
        if isinstance(abstract_parts, list):
            abstract = " ".join(
                _strip_html(_safe_str(p)) if isinstance(p, str) else ""
                for p in abstract_parts
            )
        elif isinstance(abstract_parts, str):
            abstract = _strip_html(abstract_parts)
        else:
            abstract = ""

        # DOI
        doi = self._extract_doi(article_data)

        # Authors
        author_list = article_data.get("AuthorList", [])
        authors = self._parse_authors(author_list)

        # Journal
        journal_data = article_data.get("Journal", {})
        journal = _safe_str(journal_data.get("Title", ""))

        # Publish date
        pub_date = self._parse_pub_date(journal_data)

        # Publication type
        pub_type_list = article_data.get("PublicationTypeList", [])
        pub_type = _safe_str(pub_type_list[0]) if pub_type_list else ""

        return PubMedArticle(
            pmid=pmid,
            title=title,
            abstract=abstract,
            doi=doi,
            authors=authors,
            journal=journal,
            publish_date=pub_date,
            publication_type=pub_type,
        )

    @staticmethod
    def _extract_doi(article_data: dict) -> str:
        """Extract DOI from Article's ELocationID list."""
        elocation_ids = article_data.get("ELocationID", [])
        if isinstance(elocation_ids, str):
            elocation_ids = [elocation_ids]
        for eid in elocation_ids:
            eid_str = _safe_str(eid)
            # Check if the entry has attributes (Bio.Entrez parsed dict)
            if hasattr(eid, "attributes"):
                valid = eid.attributes.get("EIdType", "")
            elif isinstance(eid, dict):
                valid = eid.get("attributes", {}).get("EIdType", "")
            else:
                valid = ""
            if valid == "doi" or eid_str.startswith("10."):
                # Strip trailing EIdType annotation from plain strings
                # e.g. "10.1000/abc doi" -> "10.1000/abc"
                return eid_str.split()[0]
        return ""

    @staticmethod
    def _parse_authors(author_list: list) -> list[Author]:
        """Parse AuthorList into a list of Author objects."""
        authors: list[Author] = []
        for a in author_list:
            try:
                last_name = _safe_str(a.get("LastName", ""))
                fore_name = _safe_str(a.get("ForeName", ""))
                initials = _safe_str(a.get("Initials", ""))

                affiliation = ""
                affiliations = a.get("AffiliationInfo", [])
                if affiliations and isinstance(affiliations, list):
                    affiliation = _safe_str(affiliations[0].get("Affiliation", ""))

                authors.append(
                    Author(
                        last_name=last_name,
                        fore_name=fore_name,
                        initials=initials,
                        affiliation=affiliation,
                    )
                )
            except Exception as exc:
                logger.warning("Failed to parse author entry: %s", exc)
                continue
        return authors

    @staticmethod
    def _parse_pub_date(journal_data: dict) -> str:
        """Extract and format publication date from Journal data."""
        pub_date = journal_data.get("JournalIssue", {}).get("PubDate", {})
        if not pub_date:
            return ""

        year = _safe_str(pub_date.get("Year", ""))
        month = _safe_str(pub_date.get("Month", "")).capitalize()
        day = _safe_str(pub_date.get("Day", ""))

        parts = [year]
        if month:
            month_map = {
                "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
                "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
                "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
                "1": "Jan", "2": "Feb", "3": "Mar", "4": "Apr",
                "5": "May", "6": "Jun", "7": "Jul", "8": "Aug",
                "9": "Sep",
            }
            month = month_map.get(month, month)
            parts.append(month)
        if day:
            parts.append(day)

        return " ".join(parts)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class PubMedAPIError(Exception):
    """Raised when a PubMed API call fails."""


class PubMedParseError(Exception):
    """Raised when PubMed XML parsing fails."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _strip_html(text: str) -> str:
    """Remove HTML/XML tags from text, replacing common entities."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    return text.strip()


def _safe_str(value) -> str:
    """Coerce a value to string safely, handling Bio.Entrez StringElement."""
    if value is None:
        return ""
    return str(value).strip()

