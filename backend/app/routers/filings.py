from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.requests import IngestRequest
from app.persistence import upsert_filing_with_chunks
from app.services.sec_edgar import (
    SecIngestionError,
    chunk_text,
    fetch_filing_text,
    fetch_latest_filing,
    parse_filing_date,
    resolve_cik_for_ticker,
)

router = APIRouter(prefix="/api/filings", tags=["filings"])


@router.post("/ingest")
def ingest_latest_filing(
    payload: IngestRequest, db: Session = Depends(get_db)
) -> dict[str, str | int]:
    ticker = payload.ticker.upper().strip()
    filing_type = payload.filingType.strip().upper()

    try:
        cik = resolve_cik_for_ticker(ticker)
        filing = fetch_latest_filing(cik, filing_type)
        filing_text = fetch_filing_text(filing["source_url"])
        text_chunks = chunk_text(filing_text)
    except SecIngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filing_id = f"filing-{filing['accession_no_dashes']}"
    chunk_count = upsert_filing_with_chunks(
        db=db,
        filing_id=filing_id,
        ticker=ticker,
        filing_type=filing_type,
        filing_date=parse_filing_date(filing["filing_date"]),
        source_url=filing["source_url"],
        chunks=text_chunks,
    )

    return {
        "ticker": ticker,
        "filingType": filing_type,
        "filingDate": filing["filing_date"],
        "status": "ingested",
        "filingId": filing_id,
        "chunkCount": chunk_count,
    }
