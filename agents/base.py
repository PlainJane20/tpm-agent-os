"""Shared Claude client + the one call-site every agent goes through.

Model tiering here is a deliberate cost/quality tradeoff, not a blanket
default -- the same kind of tradeoff a build-vs-buy call is:

- MODEL_JUDGMENT (Opus) runs the steps where a wrong call is expensive to
  unwind: framing an ambiguous program, synthesizing cross-domain risk,
  the build-vs-buy verdict, the RAG status, the kill/redirect decision.
- MODEL_LENS (Sonnet) runs the parallelizable "argue one side" work: each
  independent lens in the decision panel, and the playbook write-up, which
  is distillation, not judgment.

TPM_AGENT_MOCK=1 short-circuits every call to a canned fixture so the full
pipeline -- orchestration, schema validation, artifact writing -- can be
exercised in tests and demos with zero API spend and zero network dependency.
Live mode is the real path; mock mode is what let this get built and tested
without burning credits on every iteration.
"""

import os
from typing import Optional, Type, TypeVar

from pydantic import BaseModel

MODEL_JUDGMENT = "claude-opus-5"
MODEL_LENS = "claude-sonnet-5"

MOCK_MODE = os.environ.get("TPM_AGENT_MOCK") == "1"

T = TypeVar("T", bound=BaseModel)

_client = None
_async_client = None


def get_client():
    """Lazy sync client -- not needed in mock mode, so importing this module
    never requires an API key."""
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic()
    return _client


def get_async_client():
    global _async_client
    if _async_client is None:
        import anthropic

        _async_client = anthropic.AsyncAnthropic()
    return _async_client


async def call_agent_async(
    *,
    system: str,
    user_content: str,
    output_model: Type[T],
    model: str = MODEL_JUDGMENT,
    mock_fixture: Optional[T] = None,
) -> T:
    """Call Claude with a system prompt and a structured-output contract.

    Every agent in this repo calls through here rather than the SDK
    directly, for one reason: a single choke point for mock mode, model
    tiering, and (later) retry/observability, instead of each agent file
    re-implementing all three.
    """
    if MOCK_MODE:
        if mock_fixture is None:
            raise RuntimeError(
                f"TPM_AGENT_MOCK=1 but no fixture was supplied for "
                f"output_model={output_model.__name__}."
            )
        return mock_fixture

    client = get_async_client()
    response = await client.messages.parse(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_content}],
        output_format=output_model,
    )
    return response.parsed_output
