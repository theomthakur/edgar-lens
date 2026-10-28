"""Compare keyword retrieval with LangChain hybrid retrieval on real 10-K filings.

Both modes run the same report loop and are graded by the same deterministic citation check, so the
only thing that changes is which chunks the draft is written from.

    SEC_USER_AGENT="EDGARLens/1.0 (you@domain)" LLM_ENABLED=true LLM_API_KEY=... \
    LLM_API_BASE_URL=https://openrouter.ai/api/v1 LLM_MODEL=openai/gpt-4o-mini \
    python -m scripts.compare_retrieval --tickers AAPL,MSFT

With LANGFUSE_* set, every run is also a Langfuse trace tagged with its retrieval mode.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from datetime import datetime
from pathlib import Path

from app.observability import flush
from app.services import retrieval
from app.services.analysis_orchestrator import run_analysis_agent_loop
from app.services.sec_edgar import chunk_text, fetch_filing_text, fetch_latest_filing, resolve_cik_for_ticker

DEFAULT_TICKERS = "AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,JPM,V,JNJ,WMT,PG,XOM,UNH,HD,KO,PFE,INTC,CSCO"
MODES = (retrieval.LEXICAL, retrieval.HYBRID)


def _load_chunks(ticker: str) -> tuple[dict, list[str]]:
    filing = fetch_latest_filing(resolve_cik_for_ticker(ticker), "10-K")
    return filing, chunk_text(fetch_filing_text(filing["source_url"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", default=DEFAULT_TICKERS)
    parser.add_argument("--out", default="eval/results")
    args = parser.parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    rows: list[dict] = []
    for ticker in tickers:
        try:
            filing, chunks = _load_chunks(ticker)
        except Exception as error:  # noqa: BLE001
            print(f"{ticker:<6} skipped: {error}", flush=True)
            continue
        for mode in MODES:
            os.environ["RETRIEVAL_MODE"] = mode
            started = time.monotonic()
            result = run_analysis_agent_loop(ticker, chunks)
            seconds = round(time.monotonic() - started, 2)
            row = {
                "ticker": ticker, "filing_date": filing["filing_date"], "chunks": len(chunks), "mode": result["retrievalMode"],
                "round1_precision": result["trace"][0]["precision"], "final_precision": result["finalPrecision"],
                "rounds": result["rounds"], "llm_used": result["llmUsed"], "llm_errors": len(result["llmErrors"]), "seconds": seconds,
            }
            rows.append(row)
            print(f"{ticker:<6} {row['mode']:<17} r1={row['round1_precision']:.2f} final={row['final_precision']:.2f} "
                  f"rounds={row['rounds']} llm={row['llm_used']} {seconds}s", flush=True)

    summary = {}
    for mode in MODES:
        mine = [r for r in rows if r["mode"] == mode and r["llm_used"]]
        if not mine:
            continue
        summary[mode] = {
            "filings": len(mine),
            "mean_round1_precision": round(statistics.mean(r["round1_precision"] for r in mine), 3),
            "mean_final_precision": round(statistics.mean(r["final_precision"] for r in mine), 3),
            "first_round_pass_pct": round(100 * sum(r["rounds"] == 1 for r in mine) / len(mine), 1),
            "median_seconds": statistics.median(r["seconds"] for r in mine),
        }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    meta = {"llm_model": os.getenv("LLM_MODEL"), "embedding_model": os.getenv("RETRIEVAL_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"),
            "bm25_weight": os.getenv("RETRIEVAL_BM25_WEIGHT", "0.5")}
    (out / f"retrieval-comparison-{stamp}.json").write_text(json.dumps({"meta": meta, "summary": summary, "rows": rows}, indent=2))
    print("\n" + json.dumps({"meta": meta, "summary": summary}, indent=2))
    flush()


if __name__ == "__main__":
    main()
