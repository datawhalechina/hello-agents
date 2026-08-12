"""Analysis model: LLM structured summary for a search."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.database import Base


class Analysis(Base):
    __tablename__ = "analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(
        ForeignKey("searches.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    summary: Mapped[str] = mapped_column(Text, default="")
    research_background: Mapped[str] = mapped_column(Text, default="")
    current_hotspots: Mapped[str] = mapped_column(Text, default="[]")  # JSON string
    main_findings: Mapped[str] = mapped_column(Text, default="[]")  # JSON string
    experimental_methods: Mapped[str] = mapped_column(Text, default="[]")  # JSON string
    future_directions: Mapped[str] = mapped_column(Text, default="[]")  # JSON string
    model_used: Mapped[str] = mapped_column(Text, default="")
    token_usage: Mapped[str] = mapped_column(Text, default="{}")  # JSON string
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    search = relationship("Search", back_populates="analysis")
