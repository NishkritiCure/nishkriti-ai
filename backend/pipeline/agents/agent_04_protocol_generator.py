import json
import os

from anthropic import Anthropic
from pydantic import ValidationError

from models.pipeline import ProtocolSummary
from pipeline.state import PipelineState
from utils.logging import get_logger

logger = get_logger(__name__)

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_SYSTEM_PROMPT = """\
You are a functional medicine protocol generator working in India.

You receive:
1. Root cause hypotheses (ranked by likelihood) from a clinical reasoning agent
2. Red flag findings (flagged warnings) from a red flag detection agent

Your task: synthesise both into a single, actionable clinical protocol for the
treating doctor to review before building a patient plan.

Rules:
- Base all recommendations on the provided hypotheses and red flags — do not add
  findings not present in the inputs.
- Order recommended_investigations by urgency: urgent items first.
- urgent = required before next consultation or within 48 hours
- routine = standard workup, within 1-2 weeks
- optional = nice-to-have or confirmatory
- If a red flag is present, its recommended_action must appear in red_flag_actions.
- investigation_keywords should be usable as PubMed or Google Scholar search terms.
- Keep clinical_summary factual and concise — 2-3 sentences maximum.
- Consider Indian lab availability and cost when selecting investigations.
"""

_TOOL_DEFINITION = {
    "name": "generate_protocol",
    "description": (
        "Generate an actionable clinical protocol by synthesising hypotheses and "
        "red flag findings into a prioritised investigation plan for the doctor."
    ),
    "input_schema": ProtocolSummary.model_json_schema(),
}


def run_agent_04(state: PipelineState) -> dict:
    """
    Agent 4 — Protocol Generator.

    Input:  state["hypotheses"] (dict — Agent 2 output)
            state["red_flags"]  (dict — Agent 3 output)
    Output: {"protocol": dict}

    Raises ValueError on validation failure (LangGraph retries, max 3).
    """
    call_id = state["call_id"]
    hypotheses = state.get("hypotheses")
    red_flags = state.get("red_flags")

    if not hypotheses:
        raise ValueError("Agent 04: hypotheses is empty — Agent 2 must run first")
    if not red_flags:
        raise ValueError("Agent 04: red_flags is empty — Agent 3 must run first")

    logger.info("agent_04_start", extra={"call_id": call_id})

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=_SYSTEM_PROMPT,
        tools=[_TOOL_DEFINITION],
        tool_choice={"type": "tool", "name": "generate_protocol"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Generate a clinical protocol for this patient.\n\n"
                    "## Root cause hypotheses (Agent 2 output):\n"
                    f"{json.dumps(hypotheses)}\n\n"
                    "## Red flag findings (Agent 3 output):\n"
                    f"{json.dumps(red_flags)}"
                ),
            }
        ],
    )

    tool_block = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )
    if tool_block is None:
        raise ValueError("Agent 04: Claude did not return a tool_use block")

    try:
        protocol = ProtocolSummary(**tool_block.input)
    except ValidationError as e:
        raise ValueError(f"Agent 04 output validation failed: {e}") from e

    logger.info(
        "agent_04_complete",
        extra={
            "call_id": call_id,
            "investigation_count": len(protocol.recommended_investigations),
            "red_flag_actions_count": len(protocol.red_flag_actions),
        },
    )
    return {"protocol": protocol.model_dump()}
