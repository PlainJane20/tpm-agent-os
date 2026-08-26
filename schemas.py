"""Structured-output contracts shared across every agent in the pipeline.

Every agent returns one of these Pydantic models (via `client.messages.parse`),
never free text. That's a deliberate choice: a Staff Technical Program
Manager's (TPM's) operating model lives or dies on whether artifacts
compose -- a risk map that's just a paragraph
can't be fed into a status report or a kill/redirect decision without a human
re-typing it. Schemas make every stage's output the next stage's input.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ProgramCharter(BaseModel):
    """Output of the Framing agent: turns an ambiguous brief into something
    a program review board could actually act on."""

    problem_statement: str
    in_scope: List[str]
    out_of_scope: List[str]
    key_stakeholders: List[str]
    success_metrics: List[str]
    open_questions: List[str] = Field(
        description="Real unresolved questions. An empty list here is a red "
        "flag that the brief was rubber-stamped, not framed."
    )
    ambiguity_level: Literal["low", "medium", "high"]
    initial_risk_call: str


class DomainRisk(BaseModel):
    risk_area: str
    affected_domains: List[str]
    impact_level: Literal["low", "medium", "high", "critical"]
    description: str
    recommended_owner: str = Field(
        description="Must name a team or role. If none exists yet, say "
        "'unowned -- needs assignment' rather than omitting this field."
    )
    recommended_mitigation: str


class RiskMap(BaseModel):
    """Output of the Risk Mapper: the synthesized architectural-risk matrix,
    produced by a judge agent from two independent parallel lenses
    (dependency/SPOF -- single point of failure -- and compliance-boundary)."""

    risks: List[DomainRisk]
    single_points_of_failure: List[str]
    phi_pii_flags: List[str] = Field(
        description="Any data flow that touches or plausibly touches PHI "
        "(Protected Health Information) or PII (Personally Identifiable "
        "Information). Bias toward flagging when ambiguous -- a false "
        "positive costs a review, a false negative costs a compliance "
        "incident."
    )
    architectural_notes: str


class DecisionLens(BaseModel):
    """One independent argument in the build-vs-buy panel."""

    stance: Literal["build", "buy", "tco_skeptic"]
    argument: str
    key_risks: List[str]
    estimated_time_to_value_weeks: int


class BuildVsBuyRecommendation(BaseModel):
    """Output of the Decision Judge, synthesized from three DecisionLens
    arguments it did not generate itself."""

    recommendation: Literal["build", "buy", "hybrid", "defer"]
    justification: str
    confidence: Literal["low", "medium", "high"]
    dissenting_view: Optional[str] = Field(
        default=None,
        description="If any lens strongly disagreed with the final call, "
        "summarize it here rather than silently dropping it.",
    )


class ProgramStatus(BaseModel):
    rag_status: Literal["green", "amber", "red"]
    exec_summary: str
    okr_alignment: str
    misaligned_okrs: List[str]
    top_risks: List[str]


class RedirectDecision(BaseModel):
    """The 'shut it down or keep going' call -- a Staff-level judgment call
    in its own right, not just an execution task."""

    call: Literal["continue", "redirect_resources", "shut_down"]
    justification: str
    what_changes: List[str]
    who_needs_to_know: List[str]


class PlaybookEntry(BaseModel):
    """Every pipeline run auto-generates one of these -- the mentoring
    artifact a new TPM could read to learn the operating model without a
    1:1. Turns 'I mentor TPMs' from a resume line into a growing corpus."""

    title: str
    situation: str
    what_we_did: List[str]
    what_id_do_differently: str
    reusable_lesson: str
