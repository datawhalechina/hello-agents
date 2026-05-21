
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime

from .author import Author

@dataclass
class Paper:
    title: str
    authors: list[Author] = field(default_factory=list)
    abstract: str | None = None
    doi: str | None = None
    pmid: str | None = None
    arxiv_id: str | None = None
    pmc_id: str | None = None
    journal: str | None = None
    venue_type: str | None = None
    year: int | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    publisher: str | None = None
    pdf_url: str | None = None
    source_url: str | None = None
    local_pdf_path: str | None = None
    keywords: list[str] = field(default_factory=list)
    mesh_terms: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    citations: int = 0
    source: str = "unknown"
    relevance_score: int = 0
    notes: str | None = None
    tags: list[str] = field(default_factory=list)
    category: str | None = None
    rating: int | None = None
    read_status: str = "unread"
    importance: str = "normal"
    id: int | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "authors": [a.to_dict() if hasattr(a, "to_dict") else {"name": str(a)} for a in self.authors],
            "abstract": self.abstract,
            "doi": self.doi,
            "pmid": self.pmid,
            "arxiv_id": self.arxiv_id,
            "pmc_id": self.pmc_id,
            "journal": self.journal,
            "venue_type": self.venue_type,
            "year": self.year,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "publisher": self.publisher,
            "pdf_url": self.pdf_url,
            "source_url": self.source_url,
            "local_pdf_path": self.local_pdf_path,
            "keywords": self.keywords,
            "mesh_terms": self.mesh_terms,
            "references": self.references,
            "citations": self.citations,
            "source": self.source,
            "relevance_score": self.relevance_score,
            "notes": self.notes,
            "tags": self.tags,
            "category": self.category,
            "rating": self.rating,
            "read_status": self.read_status,
            "importance": self.importance,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Paper":
        def _parse_dt(val: Any) -> datetime | None:
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            if isinstance(val, str):
                s = val.strip()
                if not s:
                    return None
                try:
                    if s.endswith("Z"):
                        s = s[:-1] + "+00:00"
                    return datetime.fromisoformat(s)
                except ValueError:
                    return None
            return None

        def _safe_int(val: Any, default: int = 0) -> int:
            if val is None:
                return default
            if isinstance(val, bool):
                return int(val)
            if isinstance(val, int):
                return val
            try:
                return int(float(val))
            except (TypeError, ValueError):
                return default

        def _safe_year(val: Any) -> int | None:
            if val is None or val == "":
                return None
            y = _safe_int(val, -1)
            return y if 1000 <= y <= 3000 else None

        def _str_list(val: Any) -> list[str]:
            if not isinstance(val, list):
                return []
            out: list[str] = []
            for x in val:
                if x is None:
                    continue
                if isinstance(x, str):
                    t = x.strip()
                    if t:
                        out.append(t)
                else:
                    out.append(str(x).strip())
            return out

        def _safe_id(val: Any) -> int | None:
            if val is None or val == "":
                return None
            i = _safe_int(val, -1)
            return i if i >= 0 else None

        created_at = _parse_dt(data.get("created_at"))
        updated_at = _parse_dt(data.get("updated_at"))

        return cls(
            title=data.get("title", ""),
            authors=[Author.from_dict(a) if isinstance(a, dict) else Author(name=str(a)) for a in data.get("authors", [])],
            abstract=data.get("abstract"),
            doi=data.get("doi"),
            pmid=data.get("pmid"),
            arxiv_id=data.get("arxiv_id"),
            pmc_id=data.get("pmc_id"),
            journal=data.get("journal"),
            venue_type=data.get("venue_type"),
            year=_safe_year(data.get("year")),
            volume=data.get("volume"),
            issue=data.get("issue"),
            pages=data.get("pages"),
            publisher=data.get("publisher"),
            pdf_url=data.get("pdf_url"),
            source_url=data.get("source_url"),
            local_pdf_path=data.get("local_pdf_path"),
            keywords=_str_list(data.get("keywords")),
            mesh_terms=_str_list(data.get("mesh_terms")),
            references=_str_list(data.get("references")),
            citations=_safe_int(data.get("citations"), 0),
            source=data.get("source", "unknown"),
            relevance_score=_safe_int(data.get("relevance_score"), 0),
            notes=data.get("notes"),
            tags=_str_list(data.get("tags")),
            category=data.get("category"),
            rating=_safe_int(data.get("rating"), 0) if data.get("rating") is not None else None,
            read_status=data.get("read_status", "unread"),
            importance=data.get("importance", "normal"),
            id=_safe_id(data.get("id")),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
        )
