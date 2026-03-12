from __future__ import annotations

import json
import os
from typing import Any

import httpx


def llm_enabled() -> bool:
    return os.getenv("LLM_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def llm_model_name() -> str:
    return os.getenv("LLM_MODEL", "gpt-4o-mini").strip()


def _api_base_url() -> str:
    return os.getenv("LLM_API_BASE_URL", "https://api.openai.com/v1").rstrip("/")


def _api_key() -> str:
    return os.getenv("LLM_API_KEY", "").strip()


def _max_input_chars() -> int:
    raw = os.getenv("LLM_MAX_INPUT_CHARS", "7000")
    try:
        return max(1000, int(raw))
    except ValueError:
        return 7000


def _rank_chunks(chunks: list[str], strategy: str) -> list[str]:
    if strategy == "focused":
        keywords = ["revenue", "risk", "cash flow", "margin"]
    else:
        keywords = ["operating", "liquidity", "segment", "revenue", "risk", "cash flow"]

    scored: list[tuple[int, str]] = []
    for chunk in chunks:
        lower = chunk.lower()
        score = sum(lower.count(keyword) for keyword in keywords)
        scored.append((score, chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = [chunk for _, chunk in scored[:8]]

    # Constrain prompt size.
    max_chars = _max_input_chars()
    selected: list[str] = []
    total = 0
    for chunk in top:
        if total + len(chunk) > max_chars:
            break
        selected.append(chunk)
        total += len(chunk)

    return selected or chunks[:3]


def _extract_json(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None


def _validate_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    summary = payload.get("summary")
    key_findings = payload.get("key_findings")
    citations = payload.get("citations")

    if not isinstance(summary, str):
        return None
    if not isinstance(key_findings, list) or not all(isinstance(x, str) for x in key_findings):
        return None
    if not isinstance(citations, list):
        return None

    normalized_citations: list[dict[str, str]] = []
    for item in citations:
        if not isinstance(item, dict):
            continue
        section = item.get("section")
        excerpt = item.get("excerpt")
        source_title = item.get("source_title", "SEC Filing")
        if not isinstance(section, str) or not isinstance(excerpt, str):
            continue
        normalized_citations.append(
            {
                "source_title": source_title if isinstance(source_title, str) else "SEC Filing",
                "section": section,
                "excerpt": excerpt,
            }
        )

    if not normalized_citations:
        return None

    return {
        "summary": summary,
        "key_findings": key_findings,
        "citations": normalized_citations,
    }


def generate_report_with_llm(ticker: str, chunks: list[str], strategy: str) -> dict[str, Any] | None:
    if not llm_enabled():
        return None

    api_key = _api_key()
    if not api_key:
        raise RuntimeError("LLM_ENABLED is true but LLM_API_KEY is not set")

    selected_chunks = _rank_chunks(chunks, strategy)
    context = "\n\n---\n\n".join(selected_chunks)

    prompt = (
        "You are a financial research analyst agent. "
        "Using ONLY the provided SEC filing excerpts, produce concise report JSON.\n\n"
        "Return strict JSON with keys: summary, key_findings, citations.\n"
        "- summary: string\n"
        "- key_findings: array of 3 short strings\n"
        "- citations: array of 3 objects with keys source_title, section, excerpt\n"
        "Rules:\n"
        "1) Do not invent facts; ground every finding in the provided excerpts.\n"
        "2) citation.excerpt should be copied or lightly trimmed from provided excerpts.\n"
        "3) Keep language professional and concise.\n\n"
        f"Ticker: {ticker}\n"
        f"Strategy: {strategy}\n\n"
        f"SEC Excerpts:\n{context}\n"
    )

    payload = {
        "model": llm_model_name(),
        "messages": [
            {"role": "system", "content": "You are a precise financial analysis assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=45.0) as client:
        response = client.post(f"{_api_base_url()}/chat/completions", headers=headers, json=payload)

    if response.status_code >= 400:
        raise RuntimeError(f"LLM request failed with status {response.status_code}: {response.text[:200]}")

    data = response.json()
    text = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("LLM returned empty content")

    parsed = _extract_json(text)
    if not parsed:
        raise RuntimeError("LLM output was not valid JSON")

    validated = _validate_payload(parsed)
    if not validated:
        raise RuntimeError("LLM JSON schema validation failed")

    return validated
