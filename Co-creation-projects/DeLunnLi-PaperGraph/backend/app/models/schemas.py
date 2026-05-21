
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

class PaperSource(str, Enum):
    ARXIV = "arxiv"
    OPENALEX = "openalex"
    DBLP = "dblp"
    TAVILY = "tavily"
    UNKNOWN = "unknown"

class ReadStatus(str, Enum):
    UNREAD = "unread"
    READING = "reading"
    READ = "read"

class FeedbackActionEnum(str, Enum):

    CLICK = "click"
    SAVE = "save"
    SKIP = "skip"
    IGNORE = "ignore"
    READ = "read"

class BaseAPIResponse(BaseModel):

    success: bool
    message: str | None = None

class Author(BaseModel):

    name: str
    affiliation: str | None = None
    email: str | None = None
    orcid: str | None = None
    db_id: int | None = Field(default=None, description="本地 authors 表 id，用于区分同名")

class Paper(BaseModel):

    id: int | None = None
    title: str
    authors: list[Author] = Field(default_factory=list)
    abstract: str | None = None
    doi: str | None = None
    pmid: str | None = None
    arxiv_id: str | None = None
    pmc_id: str | None = None
    journal: str | None = None
    venue_type: str | None = Field(default=None, description="会议/期刊类型：conference 或 journal")
    year: int | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    publisher: str | None = None
    pdf_url: str | None = None
    source_url: str | None = None
    local_pdf_path: str | None = Field(default=None, description="本地 PDF 相对路径")
    keywords: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    citations: int = 0
    source: PaperSource = PaperSource.UNKNOWN
    relevance_score: float = 0.0
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    category: str | None = Field(
        default=None,
        description="文献库领域（保存时由大模型或手写）",
    )
    rating: int | None = None
    read_status: ReadStatus = ReadStatus.UNREAD
    importance: str = "normal"
    created_at: datetime | None = None
    updated_at: datetime | None = None

class PapersResponse(BaseAPIResponse):
    total: int
    papers: list[Paper] = Field(default_factory=list)

class LibraryCategoryFolder(BaseModel):
    category: str
    folder: str
    count: int
    children: list[dict[str, Any]] = Field(default_factory=list)

class LibraryCategoriesResponse(BaseAPIResponse):
    store_root: str = "文献库"
    folders: list[LibraryCategoryFolder] = Field(default_factory=list)

class SavePapersRequest(BaseModel):
    papers: list[Paper]
    download_pdfs: bool = Field(default=False, description="保存后下载 PDF")
    llm_classify: bool = Field(default=True, description="大模型划分 category")

class SavePapersResponse(BaseAPIResponse):
    added: int
    updated: int = 0
    ids: list[int] = Field(default_factory=list)
    pdf_downloaded: int = 0
    llm_classified: int = 0

class DailyPaperPickHint(BaseModel):
    identity_key: str = Field(description="身份键，如 arxiv:2401.0001")
    pick_kind: str = Field(description="personalized | general")
    explanation: str = Field(default="", description="入选理由")

class DailyPapersRequest(BaseModel):
    days_back: int = Field(default=5, ge=0, le=30, description="arXiv 最近 N 天")
    arxiv_max_results: int = Field(default=20, ge=10, le=50, description="arXiv 候选数")
    arxiv_categories: list[str] | None = Field(default=None, description="arXiv 分类过滤")
    personalized_k: int = Field(default=20, ge=0, le=40, description="个性化推荐条数")
    library_limit: int = Field(default=800, ge=50, le=3000, description="库内候选上限")
    force_refresh: bool = Field(default=False, description="忽略缓存强制刷新")
    use_llm_rank: bool = Field(default=False, description="是否启用 LLM 精排")
    rerank_recall_max: int = Field(default=24, ge=8, le=60, description="精排前召回候选上限")
    use_llm_theme_keywords: bool = Field(default=True, description="LLM 生成主题标签")

class DailyPapersResponse(BaseAPIResponse):
    date_key: str
    arxiv_latest_total: int
    arxiv_selected_total: int
    personalized_total: int
    arxiv_latest: list[Paper] = Field(default_factory=list)
    arxiv_selected: list[Paper] = Field(default_factory=list)
    personalized: list[Paper] = Field(default_factory=list)
    memory_keywords_used: list[str] = Field(default_factory=list, description="偏好词摘要")
    strategy_explanation: str = Field(default="", description="推荐策略摘要（≤2 行中文）")
    personalized_theme_keywords: list[str] = Field(default_factory=list, description="个性化列表主题标签")
    general_theme_keywords: list[str] = Field(default_factory=list, description="精选列表主题标签")
    personalized_pick_hints: list[DailyPaperPickHint] = Field(default_factory=list)
    general_pick_hints: list[DailyPaperPickHint] = Field(default_factory=list)

class UpdatePaperRequest(BaseModel):
    notes: str | None = None
    tags: list[str] | None = None
    category: str | None = None
    rating: int | None = None
    read_status: ReadStatus | None = None
    importance: str | None = None

class UpdatePaperResponse(BaseAPIResponse):
    updated_fields: list[str] = Field(default_factory=list)

class DeletePaperResponse(BaseAPIResponse):
    pass

class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    paper_id: int | None = None
    year: int | None = None
    category: str | None = None
    journal: str | None = None
    venue_type: str | None = None
    weight: float = 1.0

class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    weight: float = 1.0

    evidence: str | None = None

class LibraryGraphResponse(BaseAPIResponse):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

class PaperReaderOpeningRequest(BaseModel):
    paper_id: int = Field(..., ge=1)

class PaperReaderOpeningResponse(BaseAPIResponse):
    opening: str
    pdf_parsing: bool = False

class PaperReaderChatRequest(BaseModel):
    paper_id: int = Field(..., ge=1)
    messages: list[dict[str, str]] = Field(default_factory=list)
    user_message: str = Field(..., min_length=1, max_length=12000)

class PaperReaderChatResponse(BaseAPIResponse):
    reply: str
    pdf_parsing: bool = False
    related_papers: list[Paper] = Field(default_factory=list)

    related_hints: list[dict[str, Any]] = Field(default_factory=list)

    kg_edges: list[dict[str, Any]] = Field(default_factory=list)

class PaperReaderHistoryItem(BaseModel):
    role: str
    content: str
    created_at: int

class PaperReaderHistoryResponse(BaseAPIResponse):
    paper_id: int
    turns: list[PaperReaderHistoryItem] = Field(default_factory=list)

class ReadingLogRequest(BaseModel):
    paper_id: int = Field(..., ge=1)
    duration_sec: int = Field(..., ge=1, le=60 * 60 * 24, description="本次阅读停留时长（秒）")
    client_ts: int | None = Field(default=None, description="客户端时间戳（秒）；缺省则服务端按当前时间落在当天")

class ReadingCalendarItem(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    seconds: int = 0
    sessions: int = 0

class ReadingCalendarResponse(BaseAPIResponse):
    days: int = 180
    items: list[ReadingCalendarItem] = Field(default_factory=list)

class DailyRecommendFeedbackRequest(BaseModel):

    identity_key: str = Field(..., description="论文身份标识（如 arxiv:2401.0001 / doi:xxx / title_hash:xxx）")
    title: str | None = Field(default=None, description="论文标题")
    action: FeedbackActionEnum = Field(..., description="用户动作")
    source_list: str | None = Field(default=None, description="推荐来源: personalized 或 general")
    score_at_recommend: float | None = Field(default=None, description="推荐时的匹配分数")
    keywords: list[str] | None = Field(default=None, description="论文关键词")
    category: str | None = Field(default=None, description="论文分类")
    journal: str | None = Field(default=None, description="论文期刊/会议（用于负反馈建模）")
    source: str | None = Field(default=None, description="数据源（用于负反馈建模）")

class DailyRecommendFeedbackResponse(BaseAPIResponse):
    pass
