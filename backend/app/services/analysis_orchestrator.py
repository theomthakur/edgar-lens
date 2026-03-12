from __future__ import annotations

from typing import Any

from app.services.citation_eval import score_citation_against_chunks
from app.services.llm_report_agent import generate_report_with_llm, llm_enabled, llm_model_name
from app.services.report_builder import build_report_payload


def _evaluate_precision(citations: list[dict[str, str]], chunks: list[str], threshold: float) -> float:
    if not citations:
        return 0.0

    supported = 0
    for citation in citations:
        score, _ = score_citation_against_chunks(citation["excerpt"], chunks)
        if score >= threshold:
            supported += 1
    return supported / len(citations)


def run_analysis_agent_loop(
    ticker: str,
    chunks: list[str],
    target_precision: float = 0.8,
    eval_threshold: float = 0.2,
    max_rounds: int = 2,
) -> dict[str, Any]:
    trace: list[dict[str, Any]] = []
    best_payload: dict[str, Any] | None = None
    best_precision = -1.0
    used_llm = False
    llm_errors: list[str] = []

    for round_no in range(1, max_rounds + 1):
        strategy = "focused" if round_no == 1 else "broad"
        generation_mode = "heuristic"

        payload: dict[str, Any] | None = None
        if llm_enabled():
            try:
                payload = generate_report_with_llm(ticker=ticker, chunks=chunks, strategy=strategy)
                generation_mode = "llm"
                used_llm = True
            except Exception as exc:  # noqa: BLE001
                llm_errors.append(str(exc))

        if payload is None:
            payload = build_report_payload(ticker=ticker, chunks=chunks, strategy=strategy)

        precision = _evaluate_precision(payload["citations"], chunks, eval_threshold)

        trace.append(
            {
                "round": round_no,
                "strategy": strategy,
                "generationMode": generation_mode,
                "citationCount": len(payload["citations"]),
                "precision": round(precision, 4),
            }
        )

        if precision > best_precision:
            best_precision = precision
            best_payload = payload

        if precision >= target_precision:
            break

    if best_payload is None:
        best_payload = {
            "summary": f"Analysis generated for {ticker}.",
            "key_findings": ["No findings generated."],
            "citations": [],
        }

    best_payload["summary"] = (
        f"{best_payload['summary']} Agent loop rounds: {len(trace)}; "
        f"final precision: {round(best_precision, 4)}."
    )

    return {
        "payload": best_payload,
        "finalPrecision": round(max(best_precision, 0.0), 4),
        "targetPrecision": target_precision,
        "rounds": len(trace),
        "trace": trace,
        "llmEnabled": llm_enabled(),
        "llmUsed": used_llm,
        "llmModel": llm_model_name() if llm_enabled() else None,
        "llmErrors": llm_errors,
    }
