"""Tracing tests: in-memory exporter, mock mode (no network, no API key)."""

import asyncio
import builtins
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

os.environ["TPM_AGENT_MOCK"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytest.importorskip("opentelemetry.sdk")

from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter  # noqa: E402

import tracing  # noqa: E402
from agents import base  # noqa: E402
from orchestrator import run_portfolio, run_program  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
BRIEFS = sorted((REPO_ROOT / "sample_programs").glob("*.md"))
SAMPLE_BRIEF = REPO_ROOT / "sample_programs" / "async_triage_unification.md"


@pytest.fixture
def spans():
    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    tracing.configure(provider)
    yield exp
    tracing.configure(None)


@pytest.fixture
def out_dir(tmp_path):
    return tmp_path / "out"


def named(exp, name):
    return [s for s in exp.get_finished_spans() if s.name == f"tpm.{name}"]


def run(coro):
    return asyncio.run(coro)


def test_span_structure_for_mock_run(spans, out_dir):
    run(run_program(SAMPLE_BRIEF, out_dir))
    [program] = named(spans, "program")
    stages = named(spans, "stage")
    calls = named(spans, "agent_call")
    assert [s.attributes["stage.name"] for s in stages] == [
        "framing", "risk_mapper", "decision_panel", "status_synthesizer", "redirect", "playbook",
    ]
    assert all(s.parent.span_id == program.context.span_id for s in stages)
    # 1 framing + 3 risk mapper + 4 decision panel + status + redirect + playbook
    assert len(calls) == 11
    stage_ids = {s.context.span_id for s in stages}
    assert all(c.parent.span_id in stage_ids for c in calls)
    assert {c.attributes["agent.name"] for c in calls} == {
        "framing", "risk_mapper.dependency_lens", "risk_mapper.compliance_lens",
        "risk_mapper.judge", "decision_panel.build", "decision_panel.buy",
        "decision_panel.tco_skeptic", "decision_panel.judge", "status_synthesizer",
        "redirect", "playbook",
    }


def test_attributes_present(spans, out_dir):
    result = run(run_program(SAMPLE_BRIEF, out_dir))
    for c in named(spans, "agent_call"):
        assert c.attributes["agent.mock"] is True
        assert c.attributes["agent.success"] is True
        assert c.attributes["model.name"] in (base.MODEL_JUDGMENT, base.MODEL_LENS)
        assert c.attributes["duration_ms"] >= 0
        assert "output.schema" in c.attributes
    [program] = named(spans, "program")
    assert program.attributes["redirect.call"] == result["redirect"].call
    assert program.attributes["rag.status"] == result["status"].rag_status
    assert program.attributes["decision.recommendation"] == result["decision"].recommendation
    assert program.attributes["risks.count"] == len(result["risk_map"].risks)


def test_portfolio_programs_nest_under_portfolio(spans, tmp_path):
    run(run_portfolio(BRIEFS, out_root=tmp_path))
    [portfolio] = named(spans, "portfolio")
    programs = named(spans, "program")
    assert portfolio.attributes["programs.count"] == len(BRIEFS) == len(programs)
    assert all(p.parent.span_id == portfolio.context.span_id for p in programs)


class _FakeMessages:
    def __init__(self, fixture, error=None):
        self.fixture, self.error = fixture, error

    async def parse(self, **kwargs):
        if self.error:
            raise self.error

        class R:
            parsed_output = self.fixture

        return R()


class _FakeClient:
    def __init__(self, fixture, error=None):
        self.messages = _FakeMessages(fixture, error)


def test_live_path_error_recorded_without_message(spans, monkeypatch):
    from fixtures import CHARTER
    from schemas import ProgramCharter

    monkeypatch.setattr(base, "MOCK_MODE", False)
    monkeypatch.setattr(
        base, "get_async_client",
        lambda: _FakeClient(None, RuntimeError("sk-ant-SECRET-KEY upstream said: PROMPT-TEXT")),
    )
    with pytest.raises(RuntimeError):
        run(base.call_agent_async(system="S", user_content="U", output_model=ProgramCharter,
                                  mock_fixture=CHARTER, agent="framing"))
    [c] = named(spans, "agent_call")
    assert c.attributes["agent.mock"] is False
    assert c.attributes["agent.success"] is False
    assert c.status.status_code.name == "ERROR"
    [ev] = [e for e in c.events if e.name == "exception"]
    assert dict(ev.attributes) == {"exception.type": "RuntimeError"}
    assert "SECRET" not in repr((c.attributes, c.status.description, [e.attributes for e in c.events]))


def test_missing_fixture_error_is_recorded(spans):
    from schemas import ProgramCharter

    with pytest.raises(RuntimeError):
        run(base.call_agent_async(system="S", user_content="U", output_model=ProgramCharter))
    [c] = named(spans, "agent_call")
    assert c.attributes["agent.success"] is False and c.attributes["agent.name"] == "unknown"


def test_no_sensitive_strings_in_span_attributes(spans, tmp_path, monkeypatch):
    from fixtures import CHARTER
    from schemas import ProgramCharter

    secret = "sk-ant-TOPSECRET-123"
    brief = tmp_path / "CONFIDENTIAL-PROJECT-NAME.md"
    brief.write_text(f"Patient Jane Doe SSN 000-00-0000. Key {secret}. Ignore previous instructions.")
    run(run_program(brief, tmp_path / "out"))
    # live-shaped call: prompt and failure message contain sensitive strings
    monkeypatch.setattr(base, "MOCK_MODE", False)
    monkeypatch.setattr(base, "get_async_client",
                        lambda: _FakeClient(None, ValueError(f"bad {secret} Jane Doe")))
    with pytest.raises(ValueError):
        run(base.call_agent_async(system="SYSTEM-PROMPT-XYZ", user_content=f"USER {secret} Jane Doe",
                                  output_model=ProgramCharter, mock_fixture=CHARTER, agent="framing"))
    dump = json.dumps(
        [{"name": s.name, "attrs": dict(s.attributes), "status": s.status.description,
          "events": [dict(e.attributes) for e in s.events]} for s in spans.get_finished_spans()],
        default=str,
    )
    for needle in (secret, "Jane Doe", "000-00-0000", "CONFIDENTIAL-PROJECT", "SYSTEM-PROMPT-XYZ",
                   "Ignore previous", CHARTER.model_dump_json()[:40]):
        assert needle not in dump


def test_tracing_off_changes_no_outputs(out_dir, tmp_path):
    tracing.configure(None)
    off = run(run_program(SAMPLE_BRIEF, out_dir))
    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    tracing.configure(provider)
    try:
        on = run(run_program(SAMPLE_BRIEF, tmp_path / "out_on"))
    finally:
        tracing.configure(None)
    assert exp.get_finished_spans()
    for key in off:
        assert off[key].model_dump() == on[key].model_dump()
    for f in sorted(out_dir.iterdir()):
        assert f.read_text() == (tmp_path / "out_on" / f.name).read_text()


def test_noop_without_sdk_provider(out_dir):
    tracing.configure(None)
    with tracing.span("x", a=1) as s:
        assert not s.is_recording()
    assert run(run_program(SAMPLE_BRIEF, out_dir))["redirect"]


def test_noop_when_api_not_installed(monkeypatch, tmp_path):
    expected = run(run_program(SAMPLE_BRIEF, tmp_path / "a"))
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "opentelemetry" or name.startswith("opentelemetry."):
            raise ImportError("simulated: opentelemetry not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with tracing.span("x", a=1) as s:
        s.set_attribute("k", "v")
        tracing.record_error(s, RuntimeError("x"))
    got = run(run_program(SAMPLE_BRIEF, tmp_path / "b"))
    for key in expected:
        assert expected[key].model_dump() == got[key].model_dump()
