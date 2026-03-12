from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.db_models import DocumentChunkORM, FilingORM, ReportORM
from app.models.requests import CitationEvalRequest
from app.services.citation_eval import score_citation_against_chunks

router = APIRouter(prefix="/api/evals", tags=["evals"])


@router.post("/citations")
def evaluate_citations(
    payload: CitationEvalRequest, db: Session = Depends(get_db)
) -> dict[str, object]:
    report = db.get(ReportORM, payload.reportId)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    filing = None
    if payload.filingId:
        filing = db.get(FilingORM, payload.filingId)
        if not filing:
            raise HTTPException(status_code=404, detail="Filing not found")
    else:
        filing = (
            db.query(FilingORM)
            .filter(FilingORM.ticker == report.ticker)
            .order_by(desc(FilingORM.filing_date))
            .first()
        )

    if not filing:
        raise HTTPException(
            status_code=400,
            detail=(
                "No filing available for this report ticker. Ingest a filing first "
                "or pass filingId explicitly."
            ),
        )

    chunks = (
        db.query(DocumentChunkORM)
        .filter(DocumentChunkORM.filing_id == filing.filing_id)
        .all()
    )
    if not chunks:
        raise HTTPException(status_code=400, detail="No document chunks found for filing")

    chunk_texts = [c.text for c in chunks]
    items: list[dict[str, object]] = []
    supported_count = 0

    threshold = max(0.0, min(payload.supportThreshold, 1.0))

    for citation in report.citations:
        score, best_match = score_citation_against_chunks(citation.excerpt, chunk_texts)
        supported = score >= threshold
        if supported:
            supported_count += 1

        items.append(
            {
                "citationId": citation.id,
                "section": citation.section,
                "sourceTitle": citation.source_title,
                "supportScore": round(score, 4),
                "supported": supported,
                "bestMatchExcerpt": best_match,
            }
        )

    total = len(report.citations)
    precision_at_threshold = (supported_count / total) if total else 0.0

    return {
        "reportId": report.report_id,
        "ticker": report.ticker,
        "filingId": filing.filing_id,
        "supportThreshold": threshold,
        "totalCitations": total,
        "supportedCitations": supported_count,
        "precisionAtThreshold": round(precision_at_threshold, 4),
        "results": items,
    }
