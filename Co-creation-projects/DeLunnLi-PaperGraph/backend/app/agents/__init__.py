from __future__ import annotations

from .knowledge_graph_agent import KnowledgeGraphAgent
from .paper_analysis_agent import PaperAnalysisAgent
from .search_agent import get_search_agent

__all__ = [
    "KnowledgeGraphAgent",
    "PaperAnalysisAgent",
    "get_knowledge_graph_agent",
    "get_paper_analysis_agent",
    "get_search_agent",
]

_paper_analysis_agent: PaperAnalysisAgent | None = None
_knowledge_graph_agent: KnowledgeGraphAgent | None = None


def get_paper_analysis_agent() -> PaperAnalysisAgent:
    global _paper_analysis_agent
    if _paper_analysis_agent is None:
        _paper_analysis_agent = PaperAnalysisAgent()
    return _paper_analysis_agent


def get_knowledge_graph_agent() -> KnowledgeGraphAgent:
    global _knowledge_graph_agent
    if _knowledge_graph_agent is None:
        _knowledge_graph_agent = KnowledgeGraphAgent()
    return _knowledge_graph_agent
