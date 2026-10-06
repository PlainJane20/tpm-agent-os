"""Wires the six agents into one pipeline and runs N programs concurrently.

Pipeline for one program:

    brief --> Framing --> [Dependency lens, Compliance lens] --> Risk Judge
           --> [Build lens, Buy lens, TCO-skeptic lens] --> Decision Judge
           --> Status Synthesizer --> Redirect Agent --> Playbook Agent

The two bracketed steps are internal fan-outs inside risk_mapper_agent and
decision_panel_agent respectively -- see those files for why.

run_portfolio() runs multiple programs concurrently via asyncio.gather,
mirroring "own 25+ concurrent programs" rather than processing them one at a
time -- the actual point of building this as an agent pipeline instead of a
single long prompt.
"""

import json
from pathlib import Path
from typing import List

import tracing
from agents import (
    decision_panel_agent,
    framing_agent,
    playbook_agent,
    redirect_agent,
    risk_mapper_agent,
    status_synthesizer_agent,
)

DEFAULT_RESOURCING_CONTEXT = (
    "This program competes for the same two senior engineers as two other "
    "in-flight Q4 commitments. No additional headcount is available this half."
)


def _write_json(path: Path, model) -> None:
    path.write_text(json.dumps(model.model_dump(), indent=2))


async def run_program(
    brief_path: Path,
    out_dir: Path,
    resourcing_context: str = DEFAULT_RESOURCING_CONTEXT,
) -> dict:
    """Run the full six-agent pipeline against one program brief."""
    with tracing.span("program") as s:
        result = await _run_program(brief_path, out_dir, resourcing_context, s)
        tracing.set_attrs(
            s,
            **{
                "risks.count": len(result["risk_map"].risks),
                "decision.recommendation": result["decision"].recommendation,
                "decision.confidence": result["decision"].confidence,
                "rag.status": result["status"].rag_status,
                "redirect.call": result["redirect"].call,
            },
        )
        return result


async def _run_program(brief_path: Path, out_dir: Path, resourcing_context: str, program_span) -> dict:
    brief = brief_path.read_text()
    tracing.set_attrs(program_span, **{"brief.chars": len(brief)})

    with tracing.span("stage", **{"stage.name": "framing"}):
        charter = await framing_agent.run(brief)
    with tracing.span("stage", **{"stage.name": "risk_mapper"}):
        risk_map = await risk_mapper_agent.run(charter)
    with tracing.span("stage", **{"stage.name": "decision_panel"}):
        decision = await decision_panel_agent.run(charter, risk_map)
    with tracing.span("stage", **{"stage.name": "status_synthesizer"}):
        status = await status_synthesizer_agent.run(charter, risk_map, decision)
    with tracing.span("stage", **{"stage.name": "redirect"}):
        redirect = await redirect_agent.run(charter, risk_map, decision, status, resourcing_context)
    with tracing.span("stage", **{"stage.name": "playbook"}):
        playbook = await playbook_agent.run(charter, risk_map, decision, status, redirect)

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "01_charter.json", charter)
    _write_json(out_dir / "02_risk_map.json", risk_map)
    _write_json(out_dir / "03_build_vs_buy.json", decision)
    _write_json(out_dir / "04_status.json", status)
    _write_json(out_dir / "05_redirect_decision.json", redirect)
    (out_dir / "06_playbook_entry.md").write_text(
        f"# {playbook.title}\n\n"
        f"**Situation:** {playbook.situation}\n\n"
        f"**What we did:**\n" + "\n".join(f"- {item}" for item in playbook.what_we_did) + "\n\n"
        f"**What I'd do differently:** {playbook.what_id_do_differently}\n\n"
        f"**Reusable lesson:** {playbook.reusable_lesson}\n"
    )

    return {
        "charter": charter,
        "risk_map": risk_map,
        "decision": decision,
        "status": status,
        "redirect": redirect,
        "playbook": playbook,
    }


async def run_portfolio(brief_paths: List[Path], out_root: Path = Path("outputs")) -> List[dict]:
    """Run several ambiguous programs concurrently, not sequentially."""
    import asyncio

    with tracing.span("portfolio", **{"programs.count": len(brief_paths)}):
        return await asyncio.gather(
            *(run_program(p, out_root / p.stem) for p in brief_paths)
        )
