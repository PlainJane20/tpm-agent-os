# Architecture notes

This document is the "why," one agent at a time. The README is the pitch;
this is what I'd actually defend in a design review.

## Why structured outputs everywhere, not free text

Every agent returns a Pydantic model via `client.messages.parse`
(`schemas.py`), never a paragraph. A Staff TPM's actual output isn't prose —
it's a charter, a risk register, a decision record, a status doc — things
other people and other systems act on without re-parsing your intent. If
the Risk Mapper returned a paragraph, the Decision Panel would need its own
prompt to re-extract structure from it before it could use it, and that
re-extraction step is exactly where information quietly gets lost. Schemas
make each stage's output directly consumable as the next stage's input.

## Why `recommended_owner` is a required string, not optional

Early in building this, the schema allowed `recommended_owner:
Optional[str]`. That's the wrong default: an unnamed owner is a *finding*,
not a null value to skip past. Making it a required field that must contain
either a real owner or the literal string `"unowned -- needs assignment"`
forces every risk to make an explicit ownership claim, which is the exact
failure mode ("everyone thinks someone else owns this") the sample program
is built around. `tests/test_pipeline.py::test_risk_map_never_hides_a_missing_owner`
exists specifically to keep this from regressing.

## Why the Risk Mapper is two parallel lenses plus a judge, not one prompt

The first draft was a single system prompt: "identify dependencies AND
analyze compliance boundaries AND produce a matrix." Three problems with
that, in order of how expensive they are to notice:

1. **The two analysis tasks don't need each other's output.** Sequential
   execution added latency with no benefit — a classic case of imposing
   the wrong process control (sequential) on a problem shape that doesn't
   need it (parallel).
2. **One context window doing three jobs does each one shallower.** A model
   asked to map dependencies, reason about PHI boundaries, and synthesize a
   matrix in the same pass has less room to go deep on any single dimension
   than three narrowly-scoped calls would.
3. **A single pass can't surface disagreement between the two analyses,
   because there's only ever one pass.** Splitting them means the judge
   sees both independently-generated views and can flag if they conflict,
   instead of one model silently reconciling tension it never had to state.

The fix: two lens agents that never see each other's output, run
concurrently with `asyncio.gather`, and a judge agent that sees both and
produces the final matrix. Same total analytical work, lower latency,
and disagreement between lenses becomes visible instead of pre-resolved.

## Why the Decision Panel is 3 lenses + a judge, not "weigh the tradeoffs"

Asking one model call to "weigh build vs. buy" tends to produce an answer
that's hedged toward the middle, because nothing forces it to commit to
either side before averaging. Assigning three separate agents a stance each
— build, buy, and a total-cost-of-ownership skeptic whose only job is to
distrust both — and asking a fourth to judge between committed arguments
produces a sharper decision, and critically, produces a `dissenting_view`
field the judge is instructed not to discard. In practice: the recommendation
that goes out is usually not "50/50, use your judgment," it's "hybrid,
because of X, and the build lens still disagrees for reason Y" — which is
the actual shape of a real build-vs-buy call.

## Why model tiering isn't a cost hack

`agents/base.py` defines two tiers: `MODEL_JUDGMENT` (Opus) for the steps
where a wrong call is expensive to unwind — framing, risk synthesis, the
build-vs-buy verdict, RAG status, the redirect/kill decision — and
`MODEL_LENS` (Sonnet) for parallelizable single-stance arguments and the
playbook write-up, which is distillation, not judgment. This is the same
"where does technical investment actually change the outcome" judgment a
Staff TPM is asked to apply to engineering effort — applied here to model
spend instead of headcount. The tiering is a single choke point
(`call_agent_async`) specifically so it can be re-tuned in one place as
real usage data comes in, rather than scattered across six agent files.

## Why mock mode exists and what it does and doesn't prove

`TPM_AGENT_MOCK=1` short-circuits every call in `call_agent_async` to a
canned fixture from `fixtures.py`. It exists for one reason: to let the
orchestration logic, schema contracts, concurrent execution, and artifact
writing be tested and iterated on without spending API credits or requiring
network access on every change — including in CI, which has no API key.

What it proves: the plumbing is correct. Six agents wire together, run
concurrently where they should, and produce six valid artifacts.

What it does **not** prove: that the live model's actual judgment is good.
Both sample programs produce identical mock output on purpose — the
fixtures are generic scaffolding, not case-specific intelligence. Live mode,
with a real API key, is the only path that demonstrates differentiated,
per-program reasoning. The README's demo instructions lead with live mode
for exactly this reason.

## Why `asyncio` throughout instead of a sequential loop

`orchestrator.run_portfolio` runs multiple program briefs concurrently via
`asyncio.gather`. A TPM who "owns 25+ concurrent programs" processing them
one at a time in code would be modeling the job wrong. The same reasoning
applies inside each pipeline run: every fan-out (the two risk lenses, the
three decision lenses) uses `asyncio.gather` rather than sequential calls,
because nothing about those steps' inputs depends on ordering.
