from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.db_models import ReportORM

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    report = db.get(ReportORM, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "reportId": report.report_id,
        "ticker": report.ticker,
        "summary": report.summary,
        "keyFindings": report.key_findings,
        "citations": [
            {
                "sourceTitle": c.source_title,
                "section": c.section,
                "excerpt": c.excerpt,
            }
            for c in report.citations
        ],
    }
