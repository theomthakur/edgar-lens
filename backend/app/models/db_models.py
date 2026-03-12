from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class FilingORM(Base):
    __tablename__ = "filings"

    filing_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    filing_type: Mapped[str] = mapped_column(String(16), index=True)
    filing_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_url: Mapped[str] = mapped_column(Text)

    chunks: Mapped[list[DocumentChunkORM]] = relationship(
        back_populates="filing", cascade="all, delete-orphan"
    )


class DocumentChunkORM(Base):
    __tablename__ = "document_chunks"

    chunk_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filing_id: Mapped[str] = mapped_column(ForeignKey("filings.filing_id", ondelete="CASCADE"), index=True)
    section: Mapped[str] = mapped_column(String(128))
    text: Mapped[str] = mapped_column(Text)

    filing: Mapped[FilingORM] = relationship(back_populates="chunks")


class AnalysisJobORM(Base):
    __tablename__ = "analysis_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ReportORM(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    summary: Mapped[str] = mapped_column(Text)
    key_findings: Mapped[list[Any]] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    citations: Mapped[list[ReportCitationORM]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class ReportCitationORM(Base):
    __tablename__ = "report_citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.report_id", ondelete="CASCADE"), index=True)
    source_title: Mapped[str] = mapped_column(String(256))
    section: Mapped[str] = mapped_column(String(256))
    excerpt: Mapped[str] = mapped_column(Text)

    report: Mapped[ReportORM] = relationship(back_populates="citations")
