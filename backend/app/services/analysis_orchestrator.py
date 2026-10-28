from __future__ import annotations

from typing import Any

from app.observability import observe
from app.services.citation_eval import score_citation_against_chunks
from app.services.llm_report_agent import generate_report_with_llm, llm_enabled, llm_model_name
from app.services.report_builder import build_report_payload
from app.services.retrieval import requested_mode, retrieval_mode


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
    mode = retrieval_mode()

    with observe(
        "report-analysis",
        as_type="agent",
        input={"ticker": ticker, "chunks": len(chunks), "targetPrecision": target_precision, "maxRounds": max_rounds},
        metadata={"retrievalMode": mode, "requestedRetrievalMode": requested_mode(), "llmEnabled": llm_enabled()},
    ) as run_observation:
        for round_no in range(1, max_rounds + 1):
            strategy = "focused" if round_no == 1 else "broad"
            generation_mode = "heuristic"

            with observe(f"round-{round_no}", as_type="chain", input={"strategy": strategy, "retrievalMode": mode}):
                payload: dict[str, Any] | None = None
                if llm_enabled():
                    with observe(
                        "draft-llm", as_type="generation", model=llm_model_name(), input={"strategy": strategy}
                    ) as draft:
                        try:
                            payload = generate_report_with_llm(ticker=ticker, chunks=chunks, strategy=strategy)
                            generation_mode = "llm"
                            used_llm = True
                            draft.update(output={"citations": len(payload["citations"]) if payload else 0})
                        except Exception as exc:  # noqa: BLE001
                            llm_errors.append(str(exc))
                            draft.update(level="ERROR", status_message=str(exc)[:300])

                if payload is None:
                    with observe("draft-heuristic", as_type="span", input={"strategy": strategy}) as draft:
                        payload = build_report_payload(ticker=ticker, chunks=chunks, strategy=strategy)
                        draft.update(output={"citations": len(payload["citations"])})

                with observe(
                    "citation-check", as_type="evaluator", input={"citations": len(payload["citations"]), "threshold": eval_threshold}
                ) as check:
                    precision = _evaluate_precision(payload["citations"], chunks, eval_threshold)
                    check.update(output={"precision": round(precision, 4)})
                    check.score(name="citation_precision", value=round(precision, 4))

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

        final_precision = round(max(best_precision, 0.0), 4)
        run_observation.update(output={"rounds": len(trace), "finalPrecision": final_precision, "trace": trace})
        run_observation.score_trace(name="final_citation_precision", value=final_precision)
        run_observation.score_trace(name="rounds", value=len(trace))

    return {
        "payload": best_payload,
        "finalPrecision": final_precision,
        "targetPrecision": target_precision,
        "rounds": len(trace),
        "trace": trace,
        "retrievalMode": mode,
        "llmEnabled": llm_enabled(),
        "llmUsed": used_llm,
        "llmModel": llm_model_name() if llm_enabled() else None,
        "llmErrors": llm_errors,
    }
