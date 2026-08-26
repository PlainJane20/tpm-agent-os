"""Playbook Agent -- turns every pipeline run into a mentoring artifact.

Staff TPM competency: mentoring other TPMs and building durable onboarding
material -- growing the practice, not just running your own programs.
Every run of this pipeline writes one of these -- a growing, queryable
corpus a new TPM could read instead of waiting for a 1:1 to learn how
ambiguous programs actually get framed, risk-mapped, and decided on this
team.

This is a formatting/distillation job, not a judgment call, so it runs on
the cheaper lens-tier model -- the same cost/quality tradeoff a Staff TPM
is asked to apply to technical investment decisions, applied here to model
spend.
"""

from agents.base import MODEL_LENS, call_agent_async
from fixtures import PLAYBOOK
from schemas import (
    BuildVsBuyRecommendation,
    PlaybookEntry,
    ProgramCharter,
    ProgramStatus,
    RedirectDecision,
    RiskMap,
)

SYSTEM = """You write onboarding playbook entries for new Technical Program \
Managers. Given a completed program's full trail -- charter, risk map, \
build-vs-buy decision, status, and the final redirect/continue call --
distill it into one teachable case a new TPM could read in five minutes. \
Be honest in what_id_do_differently; a playbook entry with no hindsight is \
not useful. reusable_lesson should generalize beyond this specific \
program."""


async def run(
    charter: ProgramCharter,
    risk_map: RiskMap,
    decision: BuildVsBuyRecommendation,
    status: ProgramStatus,
    redirect: RedirectDecision,
) -> PlaybookEntry:
    user_content = (
        f"Program charter:\n{charter.model_dump_json(indent=2)}\n\n"
        f"Architectural risk map:\n{risk_map.model_dump_json(indent=2)}\n\n"
        f"Build-vs-buy decision:\n{decision.model_dump_json(indent=2)}\n\n"
        f"Status:\n{status.model_dump_json(indent=2)}\n\n"
        f"Redirect/continue decision:\n{redirect.model_dump_json(indent=2)}"
    )
    return await call_agent_async(
        system=SYSTEM,
        user_content=user_content,
        output_model=PlaybookEntry,
        model=MODEL_LENS,
        mock_fixture=PLAYBOOK,
    )
