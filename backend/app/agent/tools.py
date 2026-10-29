"""The tools the agent may call. It can reach the SEC's public data and do arithmetic, and nothing else."""
from __future__ import annotations

import re
from typing import Any, Callable

from .evidence import CalcError, Evidence
from .sec import CONCEPTS, SECTIONS, SecClient, SecError

WINDOW = 4500  # characters of filing text shown at once

TOOL_SPECS: list[dict] = [
    {"type": "function", "function": {
        "name": "get_financial_facts",
        "description": "Get annual figures (from 10-K filings) for a company from the SEC's structured data. Each row gets an id like F1 that you can cite and use in calculate.",
        "parameters": {"type": "object", "properties": {
            "ticker": {"type": "string", "description": "Stock ticker, for example AAPL"},
            "concept": {"type": "string", "enum": list(CONCEPTS)},
            "years": {"type": "integer", "description": "How many recent fiscal years, 1 to 6", "default": 3}},
            "required": ["ticker", "concept"]}}},
    {"type": "function", "function": {
        "name": "list_filings",
        "description": "List a company's recent filings of one form, newest first, with accession numbers.",
        "parameters": {"type": "object", "properties": {
            "ticker": {"type": "string"}, "form": {"type": "string", "default": "10-K"}, "limit": {"type": "integer", "default": 3}},
            "required": ["ticker"]}}},
    {"type": "function", "function": {
        "name": "read_filing_section",
        "description": "Read part of a 10-K, in windows. The text you are shown gets an id like T1 that you can quote from.",
        "parameters": {"type": "object", "properties": {
            "ticker": {"type": "string"}, "accession": {"type": "string", "description": "Accession number from list_filings, or the word latest"},
            "section": {"type": "string", "enum": list(SECTIONS)},
            "offset": {"type": "integer", "description": "Character offset to start from", "default": 0}},
            "required": ["ticker", "accession", "section"]}}},
    {"type": "function", "function": {
        "name": "search_filing",
        "description": "Find the passages of a 10-K that best match some words. Each passage you are shown gets an id like T2.",
        "parameters": {"type": "object", "properties": {
            "ticker": {"type": "string"}, "accession": {"type": "string", "description": "Accession number from list_filings, or the word latest"}, "query": {"type": "string"},
            "section": {"type": "string", "enum": list(SECTIONS), "description": "Optional: only search this section"}},
            "required": ["ticker", "accession", "query"]}}},
    {"type": "function", "function": {
        "name": "calculate",
        "description": "Do arithmetic on figures you have retrieved. Use ids like F1 and K1 and + - * / ( ). Returns a result with an id like K1.",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string", "description": "For example: F3 / F1"}}, "required": ["expression"]}}},
    {"type": "function", "function": {
        "name": "final_answer",
        "description": "Give your final answer. Every number and quote you state must appear as a claim that points to evidence you retrieved. If the evidence is not enough, set status to insufficient_evidence and say what is missing.",
        "parameters": {"type": "object", "properties": {
            "status": {"type": "string", "enum": ["answered", "insufficient_evidence"]},
            "answer": {"type": "string", "description": "Plain-language answer for a non-expert"},
            "claims": {"type": "array", "items": {"type": "object", "properties": {
                "type": {"type": "string", "enum": ["number", "quote"]},
                "text": {"type": "string", "description": "The statement this claim supports"},
                "ref": {"type": "string", "description": "F#, K# for a number; T# for a quote"},
                "value": {"type": "number", "description": "For a number claim: the number as you wrote it"},
                "scale": {"type": "string", "enum": ["units", "thousands", "millions", "billions", "percent"]},
                "quote": {"type": "string", "description": "For a quote claim: the exact words copied from the text"}},
                "required": ["type", "text", "ref"]}}},
            "required": ["status", "answer", "claims"]}}},
]


def _passages(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n{1,}", text) if len(p.strip()) > 40]
    merged, buffer = [], ""
    for part in parts:  # glue short neighbours so a passage reads as a thought
        buffer = f"{buffer} {part}".strip()
        if len(buffer) >= 400:
            merged.append(buffer)
            buffer = ""
    if buffer:
        merged.append(buffer)
    return merged


def _score(passage: str, words: set[str]) -> float:
    tokens = re.findall(r"[a-z0-9]+", passage.lower())
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in words)
    return hits / (len(tokens) ** 0.5)


class Toolbox:
    """Runs tool calls for one agent run and remembers what the agent has been shown."""

    def __init__(self, sec: SecClient, evidence: Evidence):
        self.sec = sec
        self.evidence = evidence
        self._sections: dict[tuple[str, str], dict[str, str]] = {}
        self.handlers: dict[str, Callable[..., Any]] = {
            "get_financial_facts": self.get_financial_facts,
            "list_filings": self.list_filings,
            "read_filing_section": self.read_filing_section,
            "search_filing": self.search_filing,
            "calculate": self.calculate,
        }

    def call(self, name: str, args: dict) -> dict:
        handler = self.handlers.get(name)
        if handler is None:
            return {"error": f"Unknown tool '{name}'. Available: {', '.join(self.handlers)}, final_answer."}
        try:
            return handler(**args)
        except (SecError, CalcError) as error:
            return {"error": str(error)}
        except TypeError as error:
            return {"error": f"Those arguments do not fit the tool: {error}"}

    # ---- tools ----
    def get_financial_facts(self, ticker: str, concept: str, years: int = 3) -> dict:
        data = self.sec.annual_facts(ticker, concept, int(years))
        rows = []
        for row in data["rows"]:
            fact_id = self.evidence.add_fact({"ticker": ticker.upper(), "concept": concept, "unit": data["unit"], **row})
            rows.append({"id": fact_id, "fiscal_year_ended": row["period_end"], "value": row["value"], "unit": data["unit"], "accession": row["accession"]})
        return {"company": data["company"], "concept": concept, "rows": rows}

    def list_filings(self, ticker: str, form: str = "10-K", limit: int = 3) -> dict:
        return self.sec.filings(ticker, form, int(limit))

    def _load(self, ticker: str, accession: str) -> dict[str, str]:
        if str(accession).strip().lower() in ("", "latest", "none", "null", "most recent"):
            newest = self.sec.filings(ticker, "10-K", 1)["filings"]
            if not newest:
                raise SecError(f"No 10-K filings were found for {ticker.upper()}.")
            accession = newest[0]["accession"]
        key = (ticker.upper(), accession)
        if key not in self._sections:
            self._sections[key] = self.sec.filing_sections(ticker, accession)
        return self._sections[key]

    def read_filing_section(self, ticker: str, accession: str, section: str, offset: int = 0) -> dict:
        sections = self._load(ticker, accession)
        if section not in sections:
            return {"error": f"That filing has no '{section}' section I could find. Found: {', '.join(sections) or 'none'}."}
        body = sections[section]
        offset = max(0, int(offset))
        window = body[offset: offset + WINDOW]
        text_id = self.evidence.add_text(window)
        end = offset + len(window)
        return {"id": text_id, "section": section, "offset": offset, "text": window, "has_more": end < len(body), "next_offset": end if end < len(body) else None}

    def search_filing(self, ticker: str, accession: str, query: str, section: str = "") -> dict:
        sections = self._load(ticker, accession)
        pool = {section: sections[section]} if section in sections else sections
        words = set(re.findall(r"[a-z0-9]+", query.lower())) - {"the", "a", "of", "and", "to", "in", "for", "is", "are", "what", "how"}
        scored = []
        for name, body in pool.items():
            for passage in _passages(body):
                scored.append((_score(passage, words), name, passage))
        scored.sort(key=lambda item: item[0], reverse=True)
        hits = []
        for score, name, passage in scored[:4]:
            if score <= 0:
                break
            hits.append({"id": self.evidence.add_text(passage[:900]), "section": name, "text": passage[:900]})
        return {"query": query, "results": hits} if hits else {"query": query, "results": [], "note": "No passage matched. Try different words."}

    def calculate(self, expression: str) -> dict:
        key, result = self.evidence.calculate(expression)
        return {"id": key, "expression": expression, "result": result}
