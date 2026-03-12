from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.db_models import AnalysisJobORM
from app.models.requests import CompareRequest, CreateJobRequest
from app.persistence import create_completed_job_with_report, get_latest_filing_chunks_for_ticker
from app.services.analysis_orchestrator import run_analysis_agent_loop

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/jobs")
def create_job(payload: CreateJobRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    ticker = payload.ticker.upper()
    filing_data = get_latest_filing_chunks_for_ticker(db, ticker)
    if not filing_data:
        raise HTTPException(
            status_code=400,
            detail="No ingested filing found for ticker. Ingest a filing first.",
        )

    _, chunks = filing_data
    agent_run = run_analysis_agent_loop(
        ticker=ticker,
        chunks=chunks,
        target_precision=0.8,
        eval_threshold=0.2,
        max_rounds=2,
    )
    generated = agent_run["payload"]

    job, report = create_completed_job_with_report(
        db=db,
        ticker=ticker,
        summary=generated["summary"],
        key_findings=generated["key_findings"],
        citations=generated["citations"],
    )
    return {
        "jobId": job.job_id,
        "status": job.status,
        "reportId": report.report_id,
        "agentMode": "multi-step-orchestrator",
        "rounds": agent_run["rounds"],
        "finalPrecision": agent_run["finalPrecision"],
        "targetPrecision": agent_run["targetPrecision"],
        "trace": agent_run["trace"],
        "llmEnabled": agent_run["llmEnabled"],
        "llmUsed": agent_run["llmUsed"],
        "llmModel": agent_run["llmModel"],
        "llmErrors": agent_run["llmErrors"],
    }


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    job = db.get(AnalysisJobORM, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"jobId": job.job_id, "status": job.status}


@router.post("/compare")
def compare_filings(payload: CompareRequest) -> dict[str, object]:
    highlights = [
        "Risk factor language increased emphasis on geopolitical supply risk.",
        "Operating margin declined 80 bps year-over-year.",
        "Management raised capex guidance for AI infrastructure investments.",
    ]
    return {"ticker": payload.ticker.upper(), "highlights": highlights}
