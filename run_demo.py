#!/usr/bin/env python3
"""CLI entrypoint.

    # one program, live Claude calls (needs ANTHROPIC_API_KEY)
    python run_demo.py sample_programs/async_triage_unification.md

    # two programs concurrently -- mirrors owning several programs at once
    python run_demo.py sample_programs/*.md

    # fully offline, no API key needed (what CI runs)
    TPM_AGENT_MOCK=1 python run_demo.py sample_programs/async_triage_unification.md
"""

import argparse
import asyncio
import sys
from pathlib import Path

from orchestrator import run_portfolio

RAG_EMOJI = {"green": "🟢", "amber": "🟡", "red": "🔴"}


def _print_summary(name: str, result: dict) -> None:
    status = result["status"]
    redirect = result["redirect"]
    decision = result["decision"]
    print(f"\n{'=' * 70}")
    print(f"PROGRAM: {name}")
    print(f"{'=' * 70}")
    print(f"RAG status:      {RAG_EMOJI.get(status.rag_status, '')} {status.rag_status.upper()}")
    print(f"Exec summary:    {status.exec_summary}")
    print(f"Build vs buy:    {decision.recommendation.upper()} ({decision.confidence} confidence)")
    print(f"Redirect call:   {redirect.call.replace('_', ' ').upper()}")
    print(f"Justification:   {redirect.justification}")
    print(f"Full artifacts:  outputs/{name}/")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "programs", nargs="+", type=Path, help="Path(s) to program brief markdown files"
    )
    args = parser.parse_args()

    missing = [p for p in args.programs if not p.exists()]
    if missing:
        print(f"Error: file(s) not found: {', '.join(str(p) for p in missing)}", file=sys.stderr)
        return 1

    results = asyncio.run(run_portfolio(args.programs))
    for path, result in zip(args.programs, results):
        _print_summary(path.stem, result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
