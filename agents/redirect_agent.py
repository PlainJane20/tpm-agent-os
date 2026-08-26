"""Redirect/Kill Agent.

Staff TPM competency: having the judgment and authority to shut down a
program or redirect resources when that's the right call for the business,
instead of defaulting to "continue." This is a distinct judgment call, not
an execution task -- so it gets its own agent and its own schema, instead
of being a footnote on the status report.
"""

from agents.base import MODEL_JUDGMENT, call_agent_async
from fixtures import REDIRECT
from schemas import (
    BuildVsBuyRecommendation,
    ProgramCharter,
    ProgramStatus,
    RedirectDecision,
    RiskMap,
)

SYSTEM = """You are the Redirect/Kill agent in a Staff TPM's operating \
model -- the one that makes the unpopular call when it's the right one for \
the business. Given the full picture of a program (charter, risk map, \
build-vs-buy decision, RAG status) and the current resourcing context, \
decide: continue as-is, redirect resources, or shut down.

Do not default to 'continue' out of social comfort. A redirect or shut-down \
call is correct exactly when the risk or opportunity cost outweighs sunk \
progress -- name that tradeoff explicitly in justification. what_changes \
must be concrete enough that someone could act on it Monday morning."""


async def run(
    charter: ProgramCharter,
    risk_map: RiskMap,
    decision: BuildVsBuyRecommendation,
    status: ProgramStatus,
    resourcing_context: str,
) -> RedirectDecision:
    user_content = (
        f"Program charter:\n{charter.model_dump_json(indent=2)}\n\n"
        f"Architectural risk map:\n{risk_map.model_dump_json(indent=2)}\n\n"
        f"Build-vs-buy decision:\n{decision.model_dump_json(indent=2)}\n\n"
        f"Current status:\n{status.model_dump_json(indent=2)}\n\n"
        f"Resourcing context:\n{resourcing_context}"
    )
    return await call_agent_async(
        system=SYSTEM,
        user_content=user_content,
        output_model=RedirectDecision,
        model=MODEL_JUDGMENT,
        mock_fixture=REDIRECT,
    )
