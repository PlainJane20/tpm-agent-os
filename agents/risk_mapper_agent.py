"""Risk Mapper -- the Lead Architectural Risk Orchestrator.

Staff TPM competency: acting as a technical integrator -- surfacing
architectural misalignments and system-/platform-level risk across domains
before they become incidents, rather than only tracking status after the
fact.

This agent is a fan-out/synthesize pattern, not one large prompt. An earlier
draft of this agent asked a single model call to do dependency mapping *and*
compliance-boundary analysis *and* synthesis in one pass -- three unrelated
analytical jobs sharing one context. The two analysis jobs don't depend on
each other's output, so they run as independent lenses in parallel, and a
judge agent -- which sees both -- synthesizes the matrix. Same total work,
lower latency, and each lens gets a full context window for its own job
instead of splitting attention across three.
"""

import asyncio

from agents.base import MODEL_JUDGMENT, MODEL_LENS, call_agent_async
from fixtures import RISK_MAP
from schemas import ProgramCharter, RiskMap

DEPENDENCY_LENS_SYSTEM = """You are the Dependency & Single-Point-of-Failure \
lens on a Staff TPM's architectural risk review. Given a program charter, \
identify every cross-service or cross-team dependency implied by it, and \
mark which ones are single points of failure. Be concrete: name the teams \
or services involved, not abstractions. If the charter doesn't name an \
owner for a dependency, that absence is itself a finding -- say so."""

COMPLIANCE_LENS_SYSTEM = """You are the Compliance-Boundary lens on a Staff \
TPM's architectural risk review. Given a program charter for a healthtech \
platform, identify every point where data could cross a compliance \
boundary -- especially where clinical/patient data (PHI) or personal data \
(PII) might mix with non-clinical systems (analytics, marketing, general \
telemetry). When it's unclear whether a data flow touches PHI/PII, flag it \
as if it does: a false positive costs a review, a false negative costs a \
compliance incident."""

JUDGE_SYSTEM = """You are the synthesis judge for a Staff TPM's \
architectural risk review. You will be given a program charter plus two \
independent analyses -- a dependency/single-point-of-failure lens and a \
compliance-boundary lens -- that were produced without seeing each other's \
work. Synthesize both into one risk matrix. Do not silently drop a finding \
from either lens because it doesn't fit neatly; if a risk area doesn't have \
a clear owner, set recommended_owner to 'unowned -- needs assignment' \
rather than inventing one. Remain strictly analytical and concise."""


async def run(charter: ProgramCharter) -> RiskMap:
    charter_text = charter.model_dump_json(indent=2)

    dependency_analysis, compliance_analysis = await asyncio.gather(
        call_agent_async(
            system=DEPENDENCY_LENS_SYSTEM,
            user_content=f"Program charter:\n{charter_text}",
            output_model=RiskMap,
            model=MODEL_LENS,
            mock_fixture=RISK_MAP,
        ),
        call_agent_async(
            system=COMPLIANCE_LENS_SYSTEM,
            user_content=f"Program charter:\n{charter_text}",
            output_model=RiskMap,
            model=MODEL_LENS,
            mock_fixture=RISK_MAP,
        ),
    )

    judge_input = (
        f"Program charter:\n{charter_text}\n\n"
        f"Dependency/SPOF lens findings:\n{dependency_analysis.model_dump_json(indent=2)}\n\n"
        f"Compliance-boundary lens findings:\n{compliance_analysis.model_dump_json(indent=2)}"
    )
    return await call_agent_async(
        system=JUDGE_SYSTEM,
        user_content=judge_input,
        output_model=RiskMap,
        model=MODEL_JUDGMENT,
        mock_fixture=RISK_MAP,
    )
