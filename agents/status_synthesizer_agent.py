"""Status Synthesizer -- RAG status + OKR alignment check.

Maps to the JD lines: "Design execution frameworks and operating models --
planning cadences, program reviews..." and "...keep roadmap and OKR
alignment intact across the organization."
"""

from agents.base import MODEL_JUDGMENT, call_agent_async
from fixtures import STATUS
from schemas import BuildVsBuyRecommendation, ProgramCharter, ProgramStatus, RiskMap

SYSTEM = """You are the Status Synthesizer in a Staff TPM's operating model. \
Given a program's charter, architectural risk map, and build-vs-buy \
decision, plus a list of the org's current OKRs, produce an executive-ready \
RAG status.

Rules:
- RAG status reflects real risk, not effort expended. A program can be red \
  even if the team is working hard, if an unresolved risk threatens the \
  outcome.
- exec_summary must be one paragraph a VP could read in 20 seconds and \
  understand what's actually at stake -- no status-report throat-clearing.
- Call out every OKR this program is at risk of missing, even ones that are \
  inconvenient to mention."""

DEFAULT_ORG_OKRS = [
    "Ship cross-surface parity for the top 3 member journeys this half",
    "Zero unresolved PHI/PII compliance findings entering any launch review",
    "Reduce time-to-decision on build-vs-buy calls across the platform org",
]


async def run(
    charter: ProgramCharter,
    risk_map: RiskMap,
    decision: BuildVsBuyRecommendation,
    org_okrs: list = None,
) -> ProgramStatus:
    org_okrs = org_okrs or DEFAULT_ORG_OKRS
    user_content = (
        f"Program charter:\n{charter.model_dump_json(indent=2)}\n\n"
        f"Architectural risk map:\n{risk_map.model_dump_json(indent=2)}\n\n"
        f"Build-vs-buy decision:\n{decision.model_dump_json(indent=2)}\n\n"
        f"Org OKRs this program should align to:\n" + "\n".join(f"- {o}" for o in org_okrs)
    )
    return await call_agent_async(
        system=SYSTEM,
        user_content=user_content,
        output_model=ProgramStatus,
        model=MODEL_JUDGMENT,
        mock_fixture=STATUS,
    )
