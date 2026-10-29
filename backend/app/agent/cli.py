"""Ask the agent a question:  python -m app.agent.cli "What was Apple's R&D expense last year?" """
from __future__ import annotations

import argparse
import json
import sys

from .config import model_from_env, sec_from_env
from .loop import Budget, run_agent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--model")
    parser.add_argument("--json", action="store_true", help="print the whole run as JSON")
    args = parser.parse_args()

    def show(event: dict) -> None:
        if args.json:
            return
        kind = event["kind"]
        if kind == "model":
            print(f"[{event['t']:>6}s] model -> {', '.join(event['calls']) or 'text only'}  ({event['tokens']} tokens)")
        elif kind == "tool":
            print(f"[{event['t']:>6}s] tool  {event['name']}({json.dumps(event['args'])[:120]})\n          {event['result'][:160]}")
        elif kind == "verify":
            print(f"[{event['t']:>6}s] check {event['verified']} verified, {event['failed']} failed {event['warnings'] or ''}")

    result = run_agent(args.question, model_from_env(args.model), sec_from_env(), Budget(), on_event=show)
    if args.json:
        print(json.dumps(result.as_dict(), indent=2, default=str))
    else:
        print(f"\nSTATUS: {result.status}   steps: {result.model_calls} model / {result.tool_calls} tool   cost: ${result.cost_usd:.4f}   time: {result.seconds}s")
        print(f"ANSWER: {result.answer}")
        for claim in result.verified_claims:
            print(f"  verified  {claim['ref']}: {claim['text']}")
        for claim in result.failed_claims:
            print(f"  FAILED    {claim['ref']}: {claim['text']}  -> {claim['reason']}")
    return 0 if result.status in ("answered", "insufficient_evidence") else 1


if __name__ == "__main__":
    sys.exit(main())
