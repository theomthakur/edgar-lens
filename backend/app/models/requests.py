from pydantic import BaseModel


class IngestRequest(BaseModel):
    ticker: str
    filingType: str


class CreateJobRequest(BaseModel):
    ticker: str


class CompareRequest(BaseModel):
    ticker: str
    currentFilingId: str
    previousFilingId: str


class CitationEvalRequest(BaseModel):
    reportId: str
    filingId: str | None = None
    supportThreshold: float = 0.35
