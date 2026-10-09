"""论文撰写助手配置

LLM 由 HelloAgentsLLM 自动检测；Qdrant/Neo4j/Embedding 由 RAGTool/MemoryTool 内部读取。
本模块只管理应用层配置。
"""
import os
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel


class PaperType(str, Enum):
    CONFERENCE = "conference"
    JOURNAL = "journal"
    THESIS = "thesis"


class CitationStyle(str, Enum):
    GB7714 = "gb7714"
    APA = "apa"


class Configuration(BaseModel):
    """应用层配置"""

    # ---------- 论文设置 ----------
    paper_type: PaperType = PaperType.CONFERENCE
    citation_style: CitationStyle = CitationStyle.GB7714
    target_sections: int = 5
    target_words_per_section: int = 1000
    max_references_per_section: int = 5
    max_review_rounds: int = 2

    # ---------- Paper Search MCP ----------
    paper_search_mcp_command: str = "uvx,paper-search-mcp"
    paper_search_mcp_prefix: str = "papersearch"

    # ---------- 论文库 ----------
    pdf_download_enabled: bool = True
    max_pdf_size_mb: int = 50
    paper_library_path: str = "./workspace/paper_library"
    paper_library_rag_namespace: Optional[str] = None

    # ---------- 笔记与记忆 ----------
    enable_notes: bool = True
    notes_workspace: str = "./workspace/paper_notes"
    enable_memory: bool = True
    memory_user_id: str = "paper_author"

    # ---------- 其他 ----------
    strip_thinking_tokens: bool = True

    @classmethod
    def from_env(cls, overrides: Optional[dict] = None) -> "Configuration":
        raw: dict[str, Any] = {}

        for name in cls.model_fields.keys():
            key = name.upper()
            if key in os.environ:
                raw[name] = os.environ[key]

        aliases = {
            "paper_type": os.getenv("PAPER_TYPE"),
            "citation_style": os.getenv("CITATION_STYLE"),
            "target_sections": os.getenv("TARGET_SECTIONS"),
            "target_words_per_section": os.getenv("TARGET_WORDS_PER_SECTION"),
            "max_references_per_section": os.getenv("MAX_REFERENCES_PER_SECTION"),
            "max_review_rounds": os.getenv("MAX_REVIEW_ROUNDS"),
            "paper_search_mcp_command": os.getenv("PAPER_SEARCH_MCP_COMMAND"),
            "paper_search_mcp_prefix": os.getenv("PAPER_SEARCH_MCP_PREFIX"),
            "pdf_download_enabled": os.getenv("PDF_DOWNLOAD_ENABLED"),
            "max_pdf_size_mb": os.getenv("MAX_PDF_SIZE_MB"),
            "paper_library_path": os.getenv("PAPER_LIBRARY_PATH"),
            "paper_library_rag_namespace": os.getenv("PAPER_LIBRARY_RAG_NAMESPACE"),
            "enable_notes": os.getenv("ENABLE_NOTES"),
            "notes_workspace": os.getenv("NOTES_WORKSPACE"),
            "enable_memory": os.getenv("ENABLE_MEMORY"),
            "memory_user_id": os.getenv("MEMORY_USER_ID"),
            "strip_thinking_tokens": os.getenv("STRIP_THINKING_TOKENS"),
        }
        for key, value in aliases.items():
            if value is not None:
                raw.setdefault(key, value)

        if overrides:
            for key, value in overrides.items():
                if value is not None:
                    raw[key] = value

        return cls(**raw)

    def resolve_paper_search_mcp_command(self) -> Optional[List[str]]:
        """把逗号分隔的命令字符串解析为列表"""
        raw = (self.paper_search_mcp_command or "").strip()
        if not raw:
            return None
        return [p.strip() for p in raw.split(",") if p.strip()]