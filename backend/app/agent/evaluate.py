"""Measure the agent. Answers are graded against the SEC's structured numbers, not against the model's own opinion.

    python -m app.agent.evaluate --model qwen2.5:7b --limit 8
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import model_from_env, sec_from_env
from .loop import Budget, RunResult, run_agent
from .sec import SecClient
from .verifier import SCALES

COMPANIES = {"AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon", "GOOGL": "Alphabet", "META": "Meta"}
LABELS = {"revenue": "revenue", "net_income": "net income", "rd_expense": "research and development expense"}


@dataclass
class Task:
    id: str
    kind: str            # lookup, ratio, growth, refuse, quote
    question: str
    truth: float | None = None
    tolerance: float = 0.005     # relative for money, absolute for ratios
    absolute: bool = False


def build_tasks(sec: SecClient, tickers: list[str] | None = None) -> list[Task]:
    tickers = tickers or list(COMPANIES)
    tasks: list[Task] = []
    for t in tickers:
        name = COMPANIES.get(t, t)
        latest = {c: sec.annual_facts(t, c, 2)["rows"] for c in ("revenue", "net_income", "rd_expense")}
        for concept in ("revenue", "net_income"):
            tasks.append(Task(f"{t}-{concept}", "lookup", f"What was {name}'s {LABELS[concept]} in its most recent fiscal year?", float(latest[concept][-1]["value"])))
        tasks.append(Task(f"{t}-margin", "ratio", f"What share of {name}'s revenue was net income in its most recent fiscal year? Give it as a percent.",
                          latest["net_income"][-1]["value"] / latest["revenue"][-1]["value"], 0.001, True))
        rev = latest["revenue"]
        tasks.append(Task(f"{t}-growth", "growth", f"By what percent did {name}'s revenue change from the previous fiscal year to the most recent one?",
                          rev[-1]["value"] / rev[-2]["value"] - 1, 0.001, True))
    first = tickers[0]
    first_name = COMPANIES.get(first, first)
    tasks += [
        Task(f"{first}-future", "refuse", f"What will {first_name}'s revenue be in 2030?"),
        Task(f"{first}-price", "refuse", f"What is {first_name}'s stock price right now?"),
        Task(f"{first}-quote", "quote", f"Find one sentence in {first_name}'s latest 10-K risk factors about competition, and quote it exactly."),
    ]
    return tasks


def score(task: Task, result: RunResult) -> dict:
    """Did the agent do the right thing? 'wrong_but_answered' is the failure that matters most."""
    correct = False
    if task.kind == "refuse":
        correct = result.status == "insufficient_evidence"
    elif task.kind == "quote":
        correct = result.status == "answered" and any(c.get("type") == "quote" for c in result.verified_claims)
    elif result.status == "answered" and task.truth is not None:
        for claim in result.verified_claims:
            if claim.get("type") != "number":
                continue
            stated = float(claim["value"]) * SCALES.get(str(claim.get("scale", "units")), 1.0)
            gap = abs(stated - task.truth) if task.absolute else abs(stated - task.truth) / max(abs(task.truth), 1e-12)
            if gap <= task.tolerance:
                correct = True
                break
    return {
        "id": task.id, "kind": task.kind, "status": result.status, "correct": correct,
        "wrong_but_answered": result.status == "answered" and not correct,
        "model_calls": result.model_calls, "tool_calls": result.tool_calls, "repairs": result.repairs,
        "cost_usd": result.cost_usd, "seconds": result.seconds,
    }


def summarize(rows: list[dict]) -> dict:
    n = len(rows) or 1
    answerable = [r for r in rows if r["kind"] != "refuse"]
    refusals = [r for r in rows if r["kind"] == "refuse"]
    return {
        "tasks": len(rows),
        "correct_pct": round(100 * sum(r["correct"] for r in rows) / n, 1),
        "answerable_correct_pct": round(100 * sum(r["correct"] for r in answerable) / max(len(answerable), 1), 1),
        "refused_correctly_pct": round(100 * sum(r["correct"] for r in refusals) / max(len(refusals), 1), 1),
        "wrong_but_answered_pct": round(100 * sum(r["wrong_but_answered"] for r in rows) / n, 1),
        "needed_a_fix_pct": round(100 * sum(r["repairs"] > 0 for r in rows) / n, 1),
        "median_model_calls": statistics.median(r["model_calls"] for r in rows) if rows else 0,
        "median_seconds": round(statistics.median(r["seconds"] for r in rows), 1) if rows else 0,
        "avg_cost_usd": round(sum(r["cost_usd"] for r in rows) / n, 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model")
    parser.add_argument("--limit", type=int, default=0, help="run only the first N tasks (0 = all)")
    parser.add_argument("--tickers", default="", help="comma separated, default all")
    parser.add_argument("--out", default="eval/results")
    args = parser.parse_args()
    sec = sec_from_env()
    model = model_from_env(args.model)
    tasks = build_tasks(sec, [t.strip().upper() for t in args.tickers.split(",") if t.strip()] or None)
    if args.limit:
        tasks = tasks[: args.limit]
    rows, runs = [], []
    for i, task in enumerate(tasks, 1):
        result = run_agent(task.question, model, sec, Budget())
        row = score(task, result)
        rows.append(row)
        runs.append({"task": task.__dict__, "score": row, "result": result.as_dict()})
        print(f"{i:>2}/{len(tasks)} {task.id:<14} {row['status']:<22} {'OK ' if row['correct'] else 'BAD'} {row['model_calls']:>2} calls  {row['seconds']:>5}s  ${row['cost_usd']:.4f}", flush=True)
    summary = summarize(rows)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{model.name.replace('/', '_').replace(':', '_')}-{stamp}.json"
    path.write_text(json.dumps({"model": model.name, "summary": summary, "runs": runs}, indent=2, default=str), encoding="utf-8")
    print("\n" + json.dumps({"model": model.name, **summary}, indent=2))
    print(f"saved {path}")


if __name__ == "__main__":
    main()
