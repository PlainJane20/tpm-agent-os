"""Canned outputs used only when TPM_AGENT_MOCK=1.

These are generic, not program-specific -- their job is to prove the
pipeline's plumbing (schema validation, data flow between stages, artifact
writing, concurrent execution) end to end without spending a single API
token. They are not meant to look intelligent; the live path is what
demonstrates that. See tests/test_pipeline.py, which runs the full six-agent
pipeline against these fixtures on every CI run.
"""

from schemas import (
    BuildVsBuyRecommendation,
    DecisionLens,
    DomainRisk,
    PlaybookEntry,
    ProgramCharter,
    ProgramStatus,
    RedirectDecision,
    RiskMap,
)

CHARTER = ProgramCharter(
    problem_statement="Triage state is inconsistent across two surfaces "
    "and no team owns the end-to-end flow.",
    in_scope=["Symptom intake parity", "Escalation queue contract", "Risk score access path"],
    out_of_scope=["Redesigning the risk-scoring model itself"],
    key_stakeholders=["Mobile triage team", "Clinician console team", "Risk scoring team", "Compliance"],
    success_metrics=["Single triage state machine", "Documented PHI boundary", "Zero direct risk-model bypasses"],
    open_questions=[
        "Who owns the end-to-end state machine today?",
        "Why are two teams bypassing the shared risk-scoring service?",
    ],
    ambiguity_level="high",
    initial_risk_call="High -- three teams, no named owner, undocumented PHI boundary.",
)

RISK_MAP = RiskMap(
    risks=[
        DomainRisk(
            risk_area="Undocumented PHI boundary",
            affected_domains=["Mobile app", "Clinician console", "Compliance"],
            impact_level="critical",
            description="Symptom + risk-score data crosses from consumer app to clinician console with no written handling boundary.",
            recommended_owner="unowned -- needs assignment",
            recommended_mitigation="Compliance to draft and sign off on a data-boundary spec before any shared service ships.",
        ),
        DomainRisk(
            risk_area="Risk-scoring service bypass",
            affected_domains=["Risk scoring", "Mobile app", "Clinician console"],
            impact_level="high",
            description="Two teams call the risk model directly instead of the shared service, breaking the single source of truth.",
            recommended_owner="Risk scoring team",
            recommended_mitigation="Deprecate direct access; force all callers through the shared service with a hard cutover date.",
        ),
    ],
    single_points_of_failure=["Shared risk-scoring service, once direct-call bypasses are removed"],
    phi_pii_flags=["Symptom intake payload", "Risk score value when paired with a member identifier"],
    architectural_notes="No team currently owns the end-to-end state machine; ownership must be assigned before design proceeds.",
)

LENS_BUILD = DecisionLens(
    stance="build",
    argument="A real shared triage-state service is the only way to guarantee parity long-term; patches on the escalation queue will keep breaking as new surfaces get added.",
    key_risks=["Longer time to ship", "Requires headcount neither team currently has"],
    estimated_time_to_value_weeks=10,
)

LENS_BUY = DecisionLens(
    stance="buy",
    argument="Extend the existing escalation queue to accept web-originated intake; it already does 80% of what's needed.",
    key_risks=["Extends a system built on a mobile-only assumption", "Technical debt compounds"],
    estimated_time_to_value_weeks=4,
)

LENS_TCO = DecisionLens(
    stance="tco_skeptic",
    argument="Neither camp has priced the PHI-boundary work, which is required either way and is the actual long pole.",
    key_risks=["Compliance sign-off timeline is unbounded until scoped", "Estimates above likely understate total cost"],
    estimated_time_to_value_weeks=14,
)

DECISION = BuildVsBuyRecommendation(
    recommendation="hybrid",
    justification="Extend the escalation queue now to unblock Q4 while scoping the PHI boundary in parallel; commit to the real shared service only once that boundary is signed off.",
    confidence="medium",
    dissenting_view="The build lens holds that patching now guarantees a second migration later and would rather absorb the delay upfront.",
)

STATUS = ProgramStatus(
    rag_status="amber",
    exec_summary="Scope is real and worth doing, but shipping before the PHI boundary is signed off is the primary risk to the Q4 date, not engineering capacity.",
    okr_alignment="Supports the cross-surface parity OKR; at risk against the compliance-readiness OKR.",
    misaligned_okrs=["Compliance-readiness OKR (no signed boundary spec yet)"],
    top_risks=["Undocumented PHI boundary", "No named end-to-end owner"],
)

REDIRECT = RedirectDecision(
    call="redirect_resources",
    justification="Continue the technical work, but redirect one PM-week immediately to force a named owner and a compliance sign-off date -- without that, the Q4 date is fiction regardless of engineering progress.",
    what_changes=["Assign a single end-to-end owner this week", "Compliance sign-off gate added to the plan with a hard date"],
    who_needs_to_know=["Mobile lead", "Clinician console lead", "Compliance", "Program sponsor"],
)

PLAYBOOK = PlaybookEntry(
    title="When three teams each think someone else owns the state machine",
    situation="An ambiguous cross-surface program with no named end-to-end owner and an unwritten compliance boundary.",
    what_we_did=[
        "Framed the charter explicitly listing 'who owns this' as an open question instead of assuming an answer",
        "Ran dependency and compliance-boundary analysis as parallel independent lenses, not one combined pass",
        "Chose hybrid build/buy rather than picking a side, and named the dissenting view instead of hiding it",
        "Redirected resourcing toward the ownership gap before letting engineering effort continue unblocked",
    ],
    what_id_do_differently="Force the ownership question in week one of intake, not after framing -- it drives every downstream estimate.",
    reusable_lesson="An unnamed owner is itself a P0 risk, not a footnote -- treat 'no one owns this yet' as a blocking finding, not an open question to revisit later.",
)
