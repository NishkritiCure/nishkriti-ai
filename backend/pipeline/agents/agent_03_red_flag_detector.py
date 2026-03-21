import json
import os

from anthropic import Anthropic
from pydantic import ValidationError

from models.pipeline import RedFlagReport
from pipeline.state import PipelineState
from utils.logging import get_logger

logger = get_logger(__name__)

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_SYSTEM_PROMPT = """\
You are a functional medicine red flag detector working in India.

Your task: given structured clinical data from a patient consultation, identify
warning signs that require urgent attention, specialist referral, or immediate
investigation.

Red flags to always evaluate (evaluate ALL of these — mark present=False if absent):
- Unexplained significant weight loss or gain
- Fatigue with systemic features (cold intolerance, hair loss, constipation) — possible thyroid
- New onset depression or mood changes
- Chest pain or palpitations
- Unexplained anaemia symptoms (pallor, breathlessness on exertion)
- Symptoms suggesting malignancy (night sweats, unexplained lumps)
- Suicidal ideation or severe psychiatric symptoms
- Uncontrolled blood sugar symptoms (polyuria, polydipsia) with family history of diabetes
- Any symptom present for > 6 months without prior investigation

Rules:
- Evaluate every flag above against the structured data — include it even if present=False.
- Only mark present=True if the data clearly supports it.
- Do not fabricate flags not in the data.
- severity and recommended_action must be null when present=False.
"""

_TOOL_DEFINITION = {
    "name": "detect_red_flags",
    "description": (
        "Detect red flags and warning signs from structured patient clinical data. "
        "Evaluate all standard red flags and report present/absent status for each."
    ),
    "input_schema": RedFlagReport.model_json_schema(),
}


def run_agent_03(state: PipelineState) -> dict:
    """
    Agent 3 — Red Flag Detector.

    Input:  state["structured_data"] (dict — Agent 1 output)
    Output: {"red_flags": dict}

    Raises ValueError on validation failure (LangGraph retries, max 3).
    """
    call_id = state["call_id"]
    structured_data = state.get("structured_data")

    if not structured_data:
        raise ValueError("Agent 03: structured_data is empty — Agent 1 must run first")

    logger.info("agent_03_start", extra={"call_id": call_id})

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        tools=[_TOOL_DEFINITION],
        tool_choice={"type": "tool", "name": "detect_red_flags"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Evaluate red flags for this patient based on the following "
                    "structured clinical data:\n\n"
                    f"{json.dumps(structured_data)}"
                ),
            }
        ],
    )

    tool_block = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )
    if tool_block is None:
        raise ValueError("Agent 03: Claude did not return a tool_use block")

    try:
        red_flags = RedFlagReport(**tool_block.input)
    except ValidationError as e:
        raise ValueError(f"Agent 03 output validation failed: {e}") from e

    logger.info(
        "agent_03_complete",
        extra={
            "call_id": call_id,
            "flags_present": sum(1 for f in red_flags.flags if f.present),
            "any_critical": red_flags.any_critical,
        },
    )
    return {"red_flags": red_flags.model_dump()}
