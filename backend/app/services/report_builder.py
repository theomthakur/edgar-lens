from __future__ import annotations

from typing import Any


def _first_sentence(text: str, max_chars: int = 220) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    dot = cleaned.find(".")
    if 0 < dot <= max_chars:
        return cleaned[: dot + 1]
    return cleaned[:max_chars]


def _find_chunk_by_keyword(chunks: list[str], keyword: str) -> str | None:
    keyword_lower = keyword.lower()
    for chunk in chunks:
        if keyword_lower in chunk.lower():
            return chunk
    return None


def _select_top_chunks_by_keyword_density(chunks: list[str], keywords: list[str], limit: int = 3) -> list[str]:
    scored: list[tuple[int, str]] = []
    for chunk in chunks:
        lower = chunk.lower()
        score = sum(lower.count(keyword) for keyword in keywords)
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [chunk for score, chunk in scored if score > 0][:limit]
    if not selected:
        selected = [chunk for _, chunk in scored[:limit]]
    return selected


def build_report_payload(ticker: str, chunks: list[str], strategy: str = "focused") -> dict[str, Any]:
    if strategy == "focused":
        keywords = ["revenue", "risk", "cash flow", "margin"]
    else:
        keywords = ["operating", "liquidity", "segment", "revenue", "risk", "cash flow"]

    revenue_chunk = _find_chunk_by_keyword(chunks, "revenue")
    risk_chunk = _find_chunk_by_keyword(chunks, "risk")
    cash_flow_chunk = _find_chunk_by_keyword(chunks, "cash flow")

    selected = [
        ("Item 7 - Management Discussion and Analysis", revenue_chunk),
        ("Item 1A - Risk Factors", risk_chunk),
        ("Cash Flow Discussion", cash_flow_chunk),
    ]

    citations: list[dict[str, str]] = []
    findings: list[str] = []

    for section, chunk in selected:
        if not chunk:
            continue
        excerpt = _first_sentence(chunk)
        if not excerpt:
            continue
        citations.append(
            {
                "source_title": "SEC Filing",
                "section": section,
                "excerpt": excerpt,
            }
        )
        findings.append(f"{section}: {excerpt}")

    # Ensure we always produce citation-backed output by adding top keyword-dense chunks.
    if len(citations) < 3:
        fallback_chunks = _select_top_chunks_by_keyword_density(chunks, keywords, limit=3)
        for idx, chunk in enumerate(fallback_chunks, start=1):
            excerpt = _first_sentence(chunk, max_chars=180)
            if not excerpt:
                continue
            if any(c["excerpt"] == excerpt for c in citations):
                continue
            citations.append(
                {
                    "source_title": "SEC Filing",
                    "section": f"Agent Highlight {idx}",
                    "excerpt": excerpt,
                }
            )
            findings.append(f"Agent Highlight {idx}: {excerpt}")
            if len(citations) >= 3:
                break

    if not findings:
        findings = ["No high-signal sections were found in the ingested filing chunks."]

    summary = (
        f"Automated analysis for {ticker} generated from ingested SEC filing content with "
        f"{len(citations)} citation-backed findings using {strategy} strategy."
    )

    return {
        "summary": summary,
        "key_findings": findings,
        "citations": citations,
    }
