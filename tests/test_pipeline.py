"""Smoke test: the full six-agent pipeline, run entirely offline.

Sets TPM_AGENT_MOCK=1 before importing anything that touches agents.base,
so no network call and no API key is required to run this. This is what CI
runs on every commit -- it proves the orchestration, schema contracts, and
artifact writing are correct independent of what the live model actually
says.
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path

os.environ["TPM_AGENT_MOCK"] = "1"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import run_program, run_portfolio  # noqa: E402
from schemas import (  # noqa: E402
    BuildVsBuyRecommendation,
    PlaybookEntry,
    ProgramCharter,
    ProgramStatus,
    RedirectDecision,
    RiskMap,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_BRIEF = REPO_ROOT / "sample_programs" / "async_triage_unification.md"
TEST_OUT_DIR = REPO_ROOT / "outputs" / "_test_run"


def test_single_program_produces_all_artifacts():
    if TEST_OUT_DIR.exists():
        shutil.rmtree(TEST_OUT_DIR)

    result = asyncio.run(run_program(SAMPLE_BRIEF, TEST_OUT_DIR))

    assert isinstance(result["charter"], ProgramCharter)
    assert isinstance(result["risk_map"], RiskMap)
    assert isinstance(result["decision"], BuildVsBuyRecommendation)
    assert isinstance(result["status"], ProgramStatus)
    assert isinstance(result["redirect"], RedirectDecision)
    assert isinstance(result["playbook"], PlaybookEntry)

    for filename in (
        "01_charter.json",
        "02_risk_map.json",
        "03_build_vs_buy.json",
        "04_status.json",
        "05_redirect_decision.json",
        "06_playbook_entry.md",
    ):
        assert (TEST_OUT_DIR / filename).exists(), f"missing artifact: {filename}"

    shutil.rmtree(TEST_OUT_DIR)


def test_portfolio_runs_programs_concurrently():
    briefs = sorted((REPO_ROOT / "sample_programs").glob("*.md"))
    assert len(briefs) >= 2, "expected at least two sample program briefs"

    out_root = REPO_ROOT / "outputs" / "_test_portfolio"
    if out_root.exists():
        shutil.rmtree(out_root)

    results = asyncio.run(run_portfolio(briefs, out_root=out_root))

    assert len(results) == len(briefs)
    for result in results:
        assert isinstance(result["redirect"], RedirectDecision)

    shutil.rmtree(out_root)


def test_risk_map_never_hides_a_missing_owner():
    """The mock fixture models the exact failure mode we care about most:
    a risk with no named owner should say so explicitly, not disappear."""
    result = asyncio.run(run_program(SAMPLE_BRIEF, REPO_ROOT / "outputs" / "_test_owner_check"))
    shutil.rmtree(REPO_ROOT / "outputs" / "_test_owner_check")

    owners = [r.recommended_owner for r in result["risk_map"].risks]
    assert any("unowned" in o.lower() for o in owners), (
        "expected at least one explicitly-unowned risk in the fixture data"
    )


if __name__ == "__main__":
    test_single_program_produces_all_artifacts()
    test_portfolio_runs_programs_concurrently()
    test_risk_map_never_hides_a_missing_owner()
    print("All tests passed.")
