# tpm-agent-os

**A multi-agent operating model for technical program management.**
Feed it one ambiguous, high-risk program brief. It runs the same operating
model a Staff TPM runs by hand — frame it, map the cross-domain risk, force
a build-vs-buy call, synthesize a status report, decide whether to keep
going or pull the plug — and it can run several of those concurrently,
because real programs don't queue up one at a time.

```
python run_demo.py sample_programs/async_triage_unification.md
```

## Why this exists

Every Staff/Principal TPM role is, underneath the title, asking for the
same operating model: take something ambiguous, impose structure on it
fast, catch the cross-team risk before it becomes an incident, make the
build-vs-buy and kill/redirect calls explicitly instead of by default, and
teach the next TPM how you did it. That operating model shows up, in some
form, in almost every Staff-level TPM posting across tech and healthtech —
it's specific enough to encode as software, and I wanted a way to show it
rather than describe it in a bullet point.

Each agent below exists because it maps to a specific, recurring Staff TPM
competency — not because it made a tidy demo:

| Agent | Staff TPM competency it demonstrates |
|---|---|
| **Framing** | Owning ambiguous, high-risk programs end-to-end — from initial framing through delivery — rather than starting from a scope someone else already defined. |
| **Risk Mapper** (Lead Architectural Risk Orchestrator) | Acting as a **technical integrator**: surfacing architectural misalignments and cross-domain/platform risk before they become incidents, not just tracking status. |
| **Decision Panel** | Shaping technical roadmap and **build-vs-buy decisions** by weighing engineering, product, and business constraints together — one of the clearest signals of Staff-level technical judgment. |
| **Status Synthesizer** | Designing execution frameworks — planning cadences, program reviews, cross-team operating rhythms — that keep **roadmap and OKR alignment** intact across multiple teams. |
| **Redirect/Kill** | Having the judgment and authority to **shut down a program or redirect resources** when that's the right call, instead of defaulting to "continue." |
| **Playbook** | **Mentoring other TPMs** and building durable onboarding material — growing the practice, not just running your own programs. |

That last row matters more than it looks. A resume can say "I mentor TPMs";
it can't produce evidence of it. Every run of this pipeline emits a
[playbook entry](sample_programs/) — a teachable case study a new TPM could
actually read. That turns mentoring from a claim into a growing, inspectable
corpus.

## Architecture

```
brief.md
   │
   ▼
┌─────────────┐
│   Framing   │  ambiguous brief -> structured charter
└──────┬──────┘  (surfaces open questions, doesn't paper over them)
       │
       ▼
┌───────────────────────────────────────────┐
│  Risk Mapper (Lead Architectural Risk      │
│  Orchestrator)                             │
│   ┌────────────────┐  ┌──────────────────┐ │
│   │ Dependency/SPOF │  │ Compliance/PHI   │ │  ← run in PARALLEL,
│   │ lens             │  │ boundary lens    │ │    no shared context
│   └────────┬───────┘  └────────┬─────────┘ │
│            └──────────┬────────┘            │
│                       ▼                     │
│                Synthesis judge  ────────────┼──▶ risk matrix
└───────────────────────────────────────────┘
       │
       ▼
┌───────────────────────────────────────────┐
│  Build-vs-Buy Decision Panel               │
│   ┌───────┐  ┌───────┐  ┌───────────────┐ │
│   │ Build │  │  Buy  │  │  TCO skeptic  │ │  ← 3 independent lenses,
│   └───┬───┘  └───┬───┘  └───────┬───────┘ │    argue in PARALLEL
│       └──────────┼──────────────┘          │
│                   ▼                        │
│                 Judge  ────────────────────┼──▶ build/buy/hybrid/defer
└───────────────────────────────────────────┘
       │
       ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ Status Synthesizer│ ──▶  │  Redirect/Kill   │ ──▶  │    Playbook      │
│  (RAG + OKR check) │      │  agent           │      │  (mentoring doc)  │
└──────────────────┘      └──────────────────┘      └──────────────────┘
```

Two design choices this diagram is trying to make visible:

**Fan-out, then judge — not one big prompt.** An earlier draft of the risk
mapper asked one model call to do dependency mapping *and* compliance
analysis *and* synthesis in a single pass. That's three unrelated
analytical jobs sharing one context window, each getting less attention
than it would alone. Splitting into independent lenses that run
concurrently and a judge that sees both, without redoing their work, is the
same total work at lower latency and higher depth per dimension. The same
pattern repeats in the build-vs-buy panel: three committed stances beat one
model quietly averaging toward the middle.

**Model tiering is a build-vs-buy call applied to itself.** Judgment-critical
steps — framing, risk synthesis, the build-vs-buy verdict, the RAG status,
the kill/redirect call — run on `claude-opus-5`. The parallelizable lenses
and the playbook write-up (distillation, not judgment) run on
`claude-sonnet-5`. That's not a cost shortcut; it's the same "where does
investment actually change the outcome" judgment call a Staff TPM is asked
to make about engineering effort, applied to model spend. See
[`agents/base.py`](agents/base.py) for where that's decided.

Full design rationale, agent-by-agent: [ARCHITECTURE.md](ARCHITECTURE.md).

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Live mode -- calls Claude, needs an API key
export ANTHROPIC_API_KEY=sk-ant-...
python run_demo.py sample_programs/async_triage_unification.md

# Run two ambiguous programs concurrently
python run_demo.py sample_programs/*.md

# Fully offline -- no API key, no network, deterministic fixtures.
# This is what the test suite and CI run.
TPM_AGENT_MOCK=1 python run_demo.py sample_programs/async_triage_unification.md
```

Every run writes its full artifact trail to `outputs/<program-name>/`:
the charter, the risk matrix, the build-vs-buy verdict, the RAG status, the
redirect decision, and the playbook entry — each one the schema-validated
input to the next stage, not a paragraph a human has to re-type.

Run the tests (offline, no API key needed):

```bash
pip install -r requirements-dev.txt
TPM_AGENT_MOCK=1 pytest tests/ -v
```

## Sample programs included

- **`async_triage_unification.md`** — a fictional but representative
  healthtech scenario: three teams, no named end-to-end owner, an unwritten
  PHI handling boundary, a "sometime in Q4" deadline. This is the primary
  demo.
- **`vendor_tooling_consolidation.md`** — an operational-tooling
  consolidation program, shaped after the kind of vendor/contract cleanup
  work that's easy to describe on a resume as a single number ("$1.2M
  saved") and hard to show as a repeatable process. This is that process.

## What I'd add next

- A real Jira/Linear connector so the Framing agent reads an actual backlog
  instead of a markdown file — the schema layer is already the seam for it.
- An adversarial verify pass on the Risk Mapper's judge output (a second
  model instance trying to refute each flagged risk before it's trusted),
  the same pattern used to keep this repo's own review tooling honest.
- A memory store across runs so the Playbook agent can say "this is the
  third time an unnamed owner showed up in a Q4 program" instead of treating
  every run as the first.

## License

MIT — see [LICENSE](LICENSE).
