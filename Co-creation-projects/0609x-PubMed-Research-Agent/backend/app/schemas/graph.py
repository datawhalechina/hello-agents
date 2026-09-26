# -*- coding: utf-8 -*-
"""Graph API schemas (Neo4j knowledge graph)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GraphStatsOut(BaseModel):
    ready: bool = False
    papers: int = 0
    authors: int = 0
    journals: int = 0
    error: str = ""


class RelatedPaper(BaseModel):
    pmid: str
    title: str = ""
    overlap: int = 0
    shared_authors: list[str] = Field(default_factory=list)
    shared_journals: list[str] = Field(default_factory=list)


class RelatedPapersOut(BaseModel):
    pmid: str
    related: list[RelatedPaper] = Field(default_factory=list)



class GraphNodeOut(BaseModel):
    id: str
    type: str  # paper | author | journal
    label: str = ""
    pmid: str = ""


class GraphLinkOut(BaseModel):
    source: str
    target: str
    type: str  # AUTHORED | PUBLISHED_IN | RELATED


class GraphSubgraphOut(BaseModel):
    pmid: str
    nodes: list[GraphNodeOut] = Field(default_factory=list)
    links: list[GraphLinkOut] = Field(default_factory=list)


class GraphPaperOut(BaseModel):
    pmid: str
    title: str = ""
    abstract: str = ""
    doi: str = ""
    authors: list[str] = Field(default_factory=list)
    journal: str = ""
    publish_date: str = ""


class GraphPaperSummaryOut(BaseModel):
    pmid: str
    title: str = ""
    journal: str = ""
    publish_date: str = ""


class GraphPapersOut(BaseModel):
    papers: list[GraphPaperSummaryOut] = Field(default_factory=list)
