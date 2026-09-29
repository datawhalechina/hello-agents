"""数据模型"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(kw_only=True)
class PaperSection:
    """论文章节（对标第十四章的 TodoItem）"""
    id: int
    title: str
    intent: str
    keywords: List[str] = field(default_factory=list)
    target_words: int = 800

    status: str = "pending"
    content: Optional[str] = None
    references: List[Dict[str, Any]] = field(default_factory=list)
    review_feedback: Optional[str] = None

    note_id: Optional[str] = None
    note_path: Optional[str] = None
    stream_token: Optional[str] = None


@dataclass(kw_only=True)
class PaperState:
    """论文撰写全局状态（对标第十四章的 SummaryState）"""
    research_topic: str
    paper_title: Optional[str] = None
    paper_type: str = "conference"
    citation_style: str = "gb7714"

    sections: List[PaperSection] = field(default_factory=list)
    all_references: List[Dict[str, Any]] = field(default_factory=list)
    review_notes: str = ""
    final_paper: Optional[str] = None

    report_note_id: Optional[str] = None
    report_note_path: Optional[str] = None


@dataclass(kw_only=True)
class PaperStateOutput:
    paper_markdown: str
    sections: List[PaperSection]
    references: List[Dict[str, Any]]
    review_notes: str
    library_stats: Dict[str, Any] = field(default_factory=dict)