"""Search model: one row per user research query."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.database import Base


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    pubmed_query: Mapped[str] = mapped_column(Text, default="")
    max_results: Mapped[int] = mapped_column(Integer, default=20)
    total_found: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    articles = relationship("Article", back_populates="search", cascade="all, delete-orphan")
    analysis = relationship("Analysis", back_populates="search", uselist=False, cascade="all, delete-orphan")
