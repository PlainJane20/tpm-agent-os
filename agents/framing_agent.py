"""Framing agent -- turns an ambiguous brief into an actionable charter.

Staff TPM competency: owning an ambiguous, high-risk program end-to-end --
from initial framing through delivery -- rather than starting from a scope
someone else already defined.
"""

from agents.base import MODEL_JUDGMENT, call_agent_async
from fixtures import CHARTER
from schemas import ProgramCharter

SYSTEM = """You are the Framing agent in a Staff Technical Program Manager's \
operating model. You take an ambiguous, underspecified program brief and \
turn it into a structured charter a program review board could act on: a \
clear problem statement, explicit scope boundaries, the real stakeholders, \
and the open questions nobody has answered yet.

Bias toward surfacing ambiguity, not hiding it. A charter that pretends the \
scope is clear when it isn't will make every downstream decision -- risk \
mapping, build-vs-buy, kill/redirect -- wrong in a way that looks confident. \
If the brief doesn't name an owner for something, say so in open_questions \
rather than inventing one."""


async def run(program_brief: str) -> ProgramCharter:
    return await call_agent_async(
        system=SYSTEM,
        user_content=f"Program brief:\n\n{program_brief}",
        output_model=ProgramCharter,
        model=MODEL_JUDGMENT,
        mock_fixture=CHARTER,
    )
