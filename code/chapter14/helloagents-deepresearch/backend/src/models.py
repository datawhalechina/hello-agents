"""State models used by the deep research workflow."""

import operator
from dataclasses import dataclass, field
from typing import List, Optional

from typing_extensions import Annotated


@dataclass(kw_only=True)
class TodoItem:
    """单个待办任务项。"""

    id: int
    title: str
    intent: str
    query: str
    status: str = field(default="pending")
    summary: Optional[str] = field(default=None)
    sources_summary: Optional[str] = field(default=None)
    notices: list[str] = field(default_factory=list)
    note_id: Optional[str] = field(default=None)
    note_path: Optional[str] = field(default=None)
    stream_token: Optional[str] = field(default=None)


@dataclass(kw_only=True)
class JobItem:
    """Structured internship/job item extracted from search results."""

    id: str
    company: str = field(default="未确认")
    title: str = field(default="未确认")
    location: str = field(default="未确认")
    source_url: str = field(default="未确认")
    source_title: str = field(default="未确认")
    requirements: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    tech_stack: list[str] = field(default_factory=list)
    duration: str = field(default="未确认")
    deadline: str = field(default="未确认")
    match_score: Optional[int] = field(default=None)
    match_reason: str = field(default="信息不足，需点开来源确认")
    resume_advice: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class SummaryState:
    run_id: str = field(default=None)
    research_topic: str = field(default=None)  # Report topic
    search_query: str = field(default=None)  # Deprecated placeholder
    web_research_results: Annotated[list, operator.add] = field(default_factory=list)
    sources_gathered: Annotated[list, operator.add] = field(default_factory=list)
    research_loop_count: int = field(default=0)  # Research loop count
    running_summary: str = field(default=None)  # Legacy summary field
    todo_items: Annotated[list, operator.add] = field(default_factory=list)
    structured_report: Optional[str] = field(default=None)
    report_note_id: Optional[str] = field(default=None)
    report_note_path: Optional[str] = field(default=None)
    job_items: Annotated[list, operator.add] = field(default_factory=list)
    search_diagnostics: Annotated[list, operator.add] = field(default_factory=list)
    search_diagnostics_path: Optional[str] = field(default=None)


@dataclass(kw_only=True)
class SummaryStateInput:
    research_topic: str = field(default=None)  # Report topic


@dataclass(kw_only=True)
class SummaryStateOutput:
    running_summary: str = field(default=None)  # Backward-compatible文本
    report_markdown: Optional[str] = field(default=None)
    todo_items: List[TodoItem] = field(default_factory=list)
    job_items: List[JobItem] = field(default_factory=list)
    search_diagnostics: List[dict] = field(default_factory=list)

