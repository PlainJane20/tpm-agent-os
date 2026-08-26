"""Build-vs-Buy Decision Panel.

Maps to the JD line: "Shape technical roadmap and build-vs-buy decisions by
aligning engineering, product, and business constraints."

Three independent lenses argue their case in parallel without seeing each
other, then a judge -- who sees all three -- decides. This is a judge-panel
pattern, not a single model asked to "weigh the tradeoffs": one model
reasoning alone tends to average toward the middle; three models each
committed to a stance, then adjudicated, surfaces the dissenting view
explicitly instead of smoothing it away.
"""

import asyncio

from agents.base import MODEL_JUDGMENT, MODEL_LENS, call_agent_async
from fixtures import DECISION, LENS_BUILD, LENS_BUY, LENS_TCO
from schemas import BuildVsBuyRecommendation, DecisionLens, ProgramCharter, RiskMap

LENS_SYSTEMS = {
    "build": (
        "You are the BUILD advocate on a Staff TPM's build-vs-buy decision "
        "panel. Argue as strongly as the facts support for building this "
        "in-house. Do not hedge into 'it depends' -- take the position and "
        "back it with the strongest real argument available, including its "
        "real costs and risks."
    ),
    "buy": (
        "You are the BUY/BORROW advocate on a Staff TPM's build-vs-buy "
        "decision panel. Argue as strongly as the facts support for "
        "licensing, extending, or reusing an existing solution instead of "
        "building new. Take the position; name its real costs and risks."
    ),
    "tco_skeptic": (
        "You are the Total-Cost-of-Ownership skeptic on a Staff TPM's "
        "build-vs-buy decision panel. Trust neither the build nor the buy "
        "camp by default. Find the cost or risk that both sides are "
        "likely underestimating -- maintenance burden, compliance work, "
        "migration cost, org readiness -- and argue from that."
    ),
}

_MOCK_LENSES = {"build": LENS_BUILD, "buy": LENS_BUY, "tco_skeptic": LENS_TCO}

JUDGE_SYSTEM = """You are the judge on a Staff TPM's build-vs-buy decision \
panel. You will see three independent arguments -- build, buy, and a \
total-cost-of-ownership skeptic -- that were generated without seeing each \
other. Decide: build, buy, hybrid, or defer. If your call overrides a lens \
with a strong case, name that lens's view in dissenting_view rather than \
silently discarding it. Set confidence honestly -- 'high' only if the \
lenses mostly converged."""


async def run(charter: ProgramCharter, risk_map: RiskMap) -> BuildVsBuyRecommendation:
    context = (
        f"Program charter:\n{charter.model_dump_json(indent=2)}\n\n"
        f"Architectural risk map:\n{risk_map.model_dump_json(indent=2)}"
    )

    lenses = await asyncio.gather(
        *(
            call_agent_async(
                system=system_prompt,
                user_content=context,
                output_model=DecisionLens,
                model=MODEL_LENS,
                mock_fixture=_MOCK_LENSES[stance],
            )
            for stance, system_prompt in LENS_SYSTEMS.items()
        )
    )

    judge_input = context + "\n\nIndependent lens arguments:\n" + "\n\n".join(
        f"[{lens.stance}] {lens.argument}\n"
        f"  key_risks: {lens.key_risks}\n"
        f"  estimated_time_to_value_weeks: {lens.estimated_time_to_value_weeks}"
        for lens in lenses
    )
    return await call_agent_async(
        system=JUDGE_SYSTEM,
        user_content=judge_input,
        output_model=BuildVsBuyRecommendation,
        model=MODEL_JUDGMENT,
        mock_fixture=DECISION,
    )
