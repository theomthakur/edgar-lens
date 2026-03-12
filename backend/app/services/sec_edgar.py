from __future__ import annotations

import os
import re
import threading
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import httpx
from bs4 import BeautifulSoup

SEC_BASE = "https://www.sec.gov"
SEC_DATA_BASE = "https://data.sec.gov"


class SecIngestionError(Exception):
    pass


_SEC_LOCK = threading.Lock()
_LAST_SEC_REQUEST_TS = 0.0


def _validate_sec_user_agent(user_agent: str) -> None:
    normalized = user_agent.strip().lower()
    blocked_tokens = [
        "example.com",
        "student-project",
        "your-email",
        "test",
    ]
    if not user_agent.strip() or any(token in normalized for token in blocked_tokens):
        raise SecIngestionError(
            "Set SEC_USER_AGENT to a real identifier with contact email, "
            "for example: FinanceResearchAgent/1.0 (you@nyu.edu)"
        )


def _min_request_interval_seconds() -> float:
    value = os.getenv("SEC_MIN_REQUEST_INTERVAL_SECONDS", "0.2")
    try:
        parsed = float(value)
    except ValueError as exc:
        raise SecIngestionError("SEC_MIN_REQUEST_INTERVAL_SECONDS must be a number") from exc
    return max(parsed, 0.05)


def _throttle_sec_requests() -> None:
    global _LAST_SEC_REQUEST_TS

    interval = _min_request_interval_seconds()
    with _SEC_LOCK:
        now = time.monotonic()
        elapsed = now - _LAST_SEC_REQUEST_TS
        if elapsed < interval:
            time.sleep(interval - elapsed)
        _LAST_SEC_REQUEST_TS = time.monotonic()


def _sec_headers() -> dict[str, str]:
    user_agent = os.getenv("SEC_USER_AGENT", "").strip()
    _validate_sec_user_agent(user_agent)
    return {
        "User-Agent": user_agent,
        "Accept": "application/json, text/html, */*",
        "Accept-Encoding": "gzip, deflate",
    }


def _sec_get(client: httpx.Client, url: str) -> httpx.Response:
    _throttle_sec_requests()
    response = client.get(url)

    if response.status_code == 429:
        raise SecIngestionError(
            "SEC rate limit reached. Retry later or increase SEC_MIN_REQUEST_INTERVAL_SECONDS."
        )

    if response.status_code >= 400:
        raise SecIngestionError(
            f"SEC request failed with status {response.status_code} for {url}"
        )

    return response


@lru_cache(maxsize=1)
def _load_company_tickers() -> list[dict[str, Any]]:
    url = f"{SEC_BASE}/files/company_tickers.json"
    with httpx.Client(timeout=20.0, headers=_sec_headers()) as client:
        response = _sec_get(client, url)

    payload = response.json()
    return list(payload.values())


def resolve_cik_for_ticker(ticker: str) -> str:
    normalized = ticker.upper().strip()
    for item in _load_company_tickers():
        if item.get("ticker", "").upper() == normalized:
            return str(item["cik_str"]).zfill(10)
    raise SecIngestionError(f"Ticker not found in SEC mapping: {normalized}")


def fetch_latest_filing(cik: str, filing_type: str) -> dict[str, str]:
    submissions_url = f"{SEC_DATA_BASE}/submissions/CIK{cik}.json"
    with httpx.Client(timeout=20.0, headers=_sec_headers()) as client:
        response = _sec_get(client, submissions_url)

    payload = response.json()
    recent = payload.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accession_numbers = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])

    for idx, form in enumerate(forms):
        if form == filing_type:
            accession = accession_numbers[idx]
            accession_no_dashes = accession.replace("-", "")
            primary_document = primary_docs[idx]
            filing_date = filing_dates[idx]
            source_url = (
                f"{SEC_BASE}/Archives/edgar/data/{int(cik)}/{accession_no_dashes}/{primary_document}"
            )
            return {
                "cik": cik,
                "form": form,
                "accession_number": accession,
                "accession_no_dashes": accession_no_dashes,
                "filing_date": filing_date,
                "primary_document": primary_document,
                "source_url": source_url,
            }

    raise SecIngestionError(f"No {filing_type} filing found for CIK {cik}")


def fetch_filing_text(source_url: str) -> str:
    with httpx.Client(timeout=30.0, headers=_sec_headers()) as client:
        response = _sec_get(client, source_url)

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunks.append(text[start:end])
        if end == text_length:
            break
        start = max(0, end - overlap)
    return chunks


def parse_filing_date(date_value: str) -> datetime:
    return datetime.fromisoformat(date_value).replace(tzinfo=timezone.utc)
