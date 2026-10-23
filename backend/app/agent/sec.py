"""A small, polite client for the SEC's public data: structured facts (XBRL) and filing text.

Everything it fetches is cached on disk, so repeated runs and evaluations are fast, cheap and repeatable.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

# Friendly names the agent can ask for, mapped to us-gaap tags (first one found wins).
CONCEPTS: dict[str, list[str]] = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    "net_income": ["NetIncomeLoss"],
    "rd_expense": ["ResearchAndDevelopmentExpense"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "total_assets": ["Assets"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
}

SECTIONS = {
    "business": "1",
    "risk_factors": "1A",
    "mdna": "7",
    "market_risk": "7A",
    "financial_statements": "8",
}

_ITEM = re.compile(r"^\s*item\s+(\d{1,2}[ab]?)\s*[\.\:\-–]?\s*(.*)$", re.IGNORECASE)


class SecError(RuntimeError):
    pass


class SecClient:
    def __init__(self, user_agent: str, cache_dir: str | Path = ".cache/sec", min_interval: float = 0.25):
        if not user_agent or "example" in user_agent.lower():
            raise SecError("Set SEC_USER_AGENT to your real name and email, as the SEC requires.")
        self.user_agent = user_agent
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.min_interval = min_interval
        self._last = 0.0

    # ---------- fetching with a disk cache ----------
    def _get(self, url: str, *, as_json: bool) -> Any:
        key = self.cache / (hashlib.sha256(url.encode()).hexdigest()[:24] + (".json" if as_json else ".txt"))
        if key.exists():
            text = key.read_text(encoding="utf-8")
            return json.loads(text) if as_json else text
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        response = httpx.get(url, headers={"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}, timeout=40, follow_redirects=True)
        self._last = time.monotonic()
        if response.status_code != 200:
            raise SecError(f"The SEC returned {response.status_code} for that request.")
        key.write_text(response.text, encoding="utf-8")
        return response.json() if as_json else response.text

    # ---------- companies and structured facts ----------
    def cik_for(self, ticker: str) -> tuple[str, str]:
        data = self._get("https://www.sec.gov/files/company_tickers.json", as_json=True)
        for row in data.values():
            if row["ticker"].upper() == ticker.upper():
                return str(row["cik_str"]).zfill(10), row["title"]
        raise SecError(f"No company with ticker {ticker.upper()} was found.")

    def company_facts(self, cik: str) -> dict:
        return self._get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", as_json=True)

    def annual_facts(self, ticker: str, concept: str, years: int = 3) -> dict:
        """Annual (10-K) values for one concept, newest last. Each row carries its filing accession."""
        if concept not in CONCEPTS:
            raise SecError(f"Unknown concept '{concept}'. Choose one of: {', '.join(CONCEPTS)}.")
        cik, name = self.cik_for(ticker)
        gaap = self.company_facts(cik)["facts"].get("us-gaap", {})
        for tag in CONCEPTS[concept]:
            units = gaap.get(tag, {}).get("units", {})
            rows = units.get("USD", [])
            by_end: dict[str, dict] = {}
            for row in rows:
                if row.get("form") != "10-K" or row.get("fp") != "FY":
                    continue
                if "start" in row:  # a flow over a period must cover about a year
                    days = (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days
                    if not 340 <= days <= 380:
                        continue
                if row["end"] not in by_end or row["filed"] > by_end[row["end"]]["filed"]:
                    by_end[row["end"]] = row
            if by_end:
                chosen = [by_end[end] for end in sorted(by_end)][-max(1, min(years, 6)):]
                return {
                    "company": name,
                    "cik": cik,
                    "tag": tag,
                    "unit": "USD",
                    "rows": [{"period_end": r["end"], "value": r["val"], "accession": r["accn"], "filed": r["filed"]} for r in chosen],
                }
        raise SecError(f"{name} reports no annual '{concept}' figure in its filings.")

    # ---------- filings and their text ----------
    def filings(self, ticker: str, form: str = "10-K", limit: int = 3) -> dict:
        cik, name = self.cik_for(ticker)
        recent = self._get(f"https://data.sec.gov/submissions/CIK{cik}.json", as_json=True)["filings"]["recent"]
        found = []
        for i, f in enumerate(recent["form"]):
            if f == form:
                found.append({
                    "accession": recent["accessionNumber"][i],
                    "filed": recent["filingDate"][i],
                    "document": recent["primaryDocument"][i],
                    "period_end": recent.get("reportDate", [""] * len(recent["form"]))[i],
                })
            if len(found) >= limit:
                break
        return {"company": name, "cik": cik, "form": form, "filings": found}

    def filing_sections(self, ticker: str, accession: str) -> dict[str, str]:
        listing = self.filings(ticker, "10-K", limit=10)
        match = next((f for f in listing["filings"] if f["accession"] == accession), None)
        if match is None:
            raise SecError(f"Filing {accession} is not one of {listing['company']}'s recent 10-Ks. Call list_filings to get valid accession numbers, or use the word latest.")
        url = f"https://www.sec.gov/Archives/edgar/data/{int(listing['cik'])}/{accession.replace('-', '')}/{match['document']}"
        return split_sections(html_to_text(self._get(url, as_json=False)))


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "head"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [re.sub(r"[ \t ]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def split_sections(text: str) -> dict[str, str]:
    """Cut a 10-K into its main items. The table of contents also lists them, so the longest stretch wins."""
    lines = text.split("\n")
    marks = [(i, m.group(1).upper()) for i, line in enumerate(lines) if (m := _ITEM.match(line)) and len(line) < 140]
    best: dict[str, str] = {}
    for n, (start, item) in enumerate(marks):
        end = marks[n + 1][0] if n + 1 < len(marks) else len(lines)
        body = "\n".join(lines[start:end])
        if len(body) > len(best.get(item, "")):
            best[item] = body
    return {name: best[item] for name, item in SECTIONS.items() if item in best}
