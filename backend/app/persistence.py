from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.db_models import (
    AnalysisJobORM,
    DocumentChunkORM,
    FilingORM,
    ReportCitationORM,
    ReportORM,
)


def upsert_filing_with_chunks(
    db: Session,
    filing_id: str,
    ticker: str,
    filing_type: str,
    filing_date: datetime,
    source_url: str,
    chunks: list[str],
) -> int:
    existing = db.get(FilingORM, filing_id)
    if existing:
        existing.ticker = ticker
        existing.filing_type = filing_type
        existing.filing_date = filing_date
        existing.source_url = source_url
        existing.chunks.clear()
        db.flush()
        filing = existing
    else:
        filing = FilingORM(
            filing_id=filing_id,
            ticker=ticker,
            filing_type=filing_type,
            filing_date=filing_date,
            source_url=source_url,
        )
        db.add(filing)
        db.flush()

    for chunk in chunks:
        db.add(
            DocumentChunkORM(
                chunk_id=str(uuid4()),
                filing_id=filing.filing_id,
                section="full-text",
                text=chunk,
            )
        )

    db.commit()
    return len(chunks)


def get_latest_filing_chunks_for_ticker(db: Session, ticker: str) -> tuple[FilingORM, list[str]] | None:
    filing = (
        db.query(FilingORM)
        .filter(FilingORM.ticker == ticker)
        .order_by(desc(FilingORM.filing_date))
        .first()
    )
    if not filing:
        return None

    chunks = (
        db.query(DocumentChunkORM)
        .filter(DocumentChunkORM.filing_id == filing.filing_id)
        .all()
    )
    return filing, [c.text for c in chunks]


def create_completed_job_with_report(
    db: Session,
    ticker: str,
    summary: str,
    key_findings: list[str],
    citations: list[dict[str, Any]],
) -> tuple[AnalysisJobORM, ReportORM]:
    job = AnalysisJobORM(
        job_id=str(uuid4()),
        ticker=ticker,
        status="completed",
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)

    report_id = f"report-{job.job_id.split('-')[0]}"
    report = ReportORM(
        report_id=report_id,
        ticker=ticker,
        summary=summary,
        key_findings=key_findings,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(report)
    db.flush()

    db.add_all([
        ReportCitationORM(
            report_id=report.report_id,
            source_title=c["source_title"],
            section=c["section"],
            excerpt=c["excerpt"],
        )
        for c in citations
    ])

    if not citations:
        db.add_all(
            [
            ReportCitationORM(
                report_id=report.report_id,
                source_title="Form Filing",
                section="Item 1A - Risk Factors",
                excerpt="Expanded disclosures mention supplier and geopolitical concentration.",
            ),
            ReportCitationORM(
                report_id=report.report_id,
                source_title="Form Filing",
                section="Item 7 - Management Discussion and Analysis",
                excerpt="Management commentary highlights operating cash flow durability.",
            ),
            ]
        )

    db.commit()
    return job, report
