# Tracing (optional OpenTelemetry)

The pipeline can emit OpenTelemetry spans. It is **off by default and changes
no behaviour**: with `opentelemetry-api` not installed, or installed but with
no SDK `TracerProvider` configured, every span is a no-op. The API is imported
lazily inside `tracing.py`, so the repo's Python 3.9+ support does not depend
on it.

## What is traced

```
tpm.portfolio                 run_portfolio() (only for multi-program runs)
└── tpm.program               one run_program()
    ├── tpm.stage  (x6)       framing, risk_mapper, decision_panel,
    │   │                     status_synthesizer, redirect, playbook
    │   └── tpm.agent_call    every call through agents.base.call_agent_async
    │                         (11 per program: the fan-outs and judges are separate calls)
```

| Span | Attribute | Type | Notes |
|---|---|---|---|
| `portfolio` | `programs.count` | int | |
| `program` | `brief.chars` | int | length only, never the brief |
| `program` | `risks.count` | int | |
| `program` | `decision.recommendation` | enum | `build`, `buy`, `hybrid`, `defer` |
| `program` | `decision.confidence` | enum | `low`, `medium`, `high` |
| `program` | `rag.status` | enum | `green`, `amber`, `red` |
| `program` | `redirect.call` | enum | `continue`, `redirect_resources`, `shut_down` |
| `stage` | `stage.name` | string | fixed stage identifier |
| `agent_call` | `agent.name` | string | fixed identifier, e.g. `risk_mapper.judge`, `decision_panel.build` |
| `agent_call` | `model.name` | string | `claude-opus-5` / `claude-sonnet-5` constants |
| `agent_call` | `agent.mock` | bool | true when `TPM_AGENT_MOCK=1` |
| `agent_call` | `agent.success` | bool | |
| `agent_call` | `output.schema` | string | pydantic class name |
| `agent_call` | `duration_ms` | float | |

Errors set span status `ERROR` and add an `exception` event with only
`exception.type`. In mock mode a missing fixture is recorded this way.

The "gate" decisions in this repo are model outputs (build/buy verdict, RAG
status, redirect call), so they are recorded as enum attributes on `program`.
There is no policy engine and no fallback path in this codebase, so there are
no spans for those.

## What is deliberately NOT recorded

Program briefs, charters, system prompts, user content, model output,
rationales and justifications, file names, exception messages, and API keys.
Attributes are identifiers, counts, enums, verdicts and durations only; strings
are truncated to 64 characters as a backstop. A test
(`test_no_sensitive_strings_in_span_attributes`) uses a brief and an error
message containing sentinel secrets and asserts none reach any span, event or
status.

## Enabling

```bash
pip install -r requirements-tracing.txt     # opentelemetry-api (still a no-op)
pip install opentelemetry-sdk               # needed to actually record/export
python examples/tracing_export.py           # console exporter, mock mode
```

For an OTLP collector also install `opentelemetry-exporter-otlp-proto-http` and run
`OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 python examples/tracing_export.py`.

Either call `tracing.configure(provider)` with your own `TracerProvider` (as the
example does) or set the global provider via
`opentelemetry.trace.set_tracer_provider(...)` before running. `run_demo.py` does
not configure a provider itself.

## Honest limits

- Not tested against a real collector or tracing backend; the OTLP wiring in the
  example is standard SDK usage and was not exercised. Only the console and
  in-memory exporters were run.
- No sampling configuration; use the SDK sampler on your provider.
- Tests run in mock mode. The live path is covered only with a fake async client
  (success shape and raised errors); no real Anthropic call was made.
- Which Python versions: tests ran on 3.9 and 3.14. Newer opentelemetry releases
  may drop 3.9; because the import is lazy, the pipeline still runs there
  without tracing.
- `requirements-dev.txt` now installs the API and SDK; tests in
  `tests/test_tracing.py` skip if the SDK is absent.
