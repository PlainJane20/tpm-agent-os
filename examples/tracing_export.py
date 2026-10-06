"""Run the pipeline in mock mode with spans exported to the console or OTLP.

    pip install -r requirements-dev.txt                    # api + sdk
    python examples/tracing_export.py

    pip install opentelemetry-exporter-otlp-proto-http     # OTLP/HTTP collector
    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 python examples/tracing_export.py

Forces TPM_AGENT_MOCK=1: no network calls, no API key.
"""

import asyncio
import os
import sys
from pathlib import Path

os.environ["TPM_AGENT_MOCK"] = "1"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from opentelemetry.sdk.resources import Resource  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter  # noqa: E402

import tracing  # noqa: E402
from orchestrator import run_program  # noqa: E402

provider = TracerProvider(resource=Resource.create({"service.name": "tpm-agent-os"}))
if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    exporter = OTLPSpanExporter()  # endpoint read from OTEL_EXPORTER_OTLP_ENDPOINT
else:
    exporter = ConsoleSpanExporter()
provider.add_span_processor(BatchSpanProcessor(exporter))
tracing.configure(provider)

brief = ROOT / "sample_programs" / "async_triage_unification.md"
result = asyncio.run(run_program(brief, ROOT / "outputs" / "_tracing_example"))
print("redirect call:", result["redirect"].call)
provider.shutdown()  # flush
