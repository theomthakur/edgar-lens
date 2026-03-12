from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class FilingMetadata(BaseModel):
    filing_id: str
    ticker: str
    filing_type: str
    filing_date: datetime
    source_url: str


class DocumentChunk(BaseModel):
    chunk_id: str
    filing_id: str
    section: str
    text: str


class Citation(BaseModel):
    source_title: str
    section: str
    excerpt: str


class AnalysisJob(BaseModel):
    job_id: str
    ticker: str
    status: str = Field(default="queued")
    created_at: datetime


class GeneratedReport(BaseModel):
    report_id: str
    ticker: str
    summary: str
    key_findings: List[str]
    citations: List[Citation]
    generated_at: datetime
