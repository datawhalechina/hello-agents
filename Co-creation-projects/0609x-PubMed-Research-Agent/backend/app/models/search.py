"""Search model: one row per user research query."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.database import Base


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, unique=True, index=True
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    pubmed_query: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(
        String(10), default="en", server_default="en"
    )
    search_mode: Mapped[str] = mapped_column(
        String(20), default="advanced", server_default="advanced"
    )
    sort_by: Mapped[str] = mapped_column(
        String(20), default="relevance", server_default="relevance"
    )
    min_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_impact_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_results: Mapped[int] = mapped_column(Integer, default=20)
    total_found: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    progress_percent: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    progress_stage: Mapped[str] = mapped_column(
        String(40), default="queued", server_default="queued", nullable=False
    )
    progress_message: Mapped[str] = mapped_column(
        String(255), default="", server_default="", nullable=False
    )
    cancel_requested: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    articles = relationship("Article", back_populates="search", cascade="all, delete-orphan")
    analysis = relationship("Analysis", back_populates="search", uselist=False, cascade="all, delete-orphan")
