import json
import os

from anthropic import Anthropic
from pydantic import ValidationError

from models.pipeline import ClinicalHypotheses
from pipeline.state import PipelineState
from utils.logging import get_logger

logger = get_logger(__name__)

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_SYSTEM_PROMPT = """\
You are a functional medicine clinical reasoner working in India.

Your task: given structured clinical data from a patient consultation, generate
a ranked list of root cause hypotheses. Think beyond symptom management —
identify the underlying physiological drivers.

Rules:
- Generate only hypotheses that are supported by specific evidence in the data.
- Order hypotheses by likelihood (rank 1 = most likely).
- For each hypothesis, cite the exact facts from the data that support it.
- Consider Indian epidemiology and dietary patterns when relevant.
- Do not list more than 5 hypotheses.
- Do not recommend investigations or treatments — that is Agent 4's job.
"""

_TOOL_DEFINITION = {
    "name": "extract_clinical_hypotheses",
    "description": (
        "Generate ranked root cause hypotheses from structured patient clinical data. "
        "Call this tool with all hypotheses and their supporting evidence."
    ),
    "input_schema": ClinicalHypotheses.model_json_schema(),
}


def run_agent_02(state: PipelineState) -> dict:
    """
    Agent 2 — Clinical Reasoner.

    Input:  state["structured_data"] (dict — Agent 1 output)
    Output: {"hypotheses": dict}

    Raises ValueError on validation failure (LangGraph retries, max 3).
    """
    call_id = state["call_id"]
    structured_data = state.get("structured_data")

    if not structured_data:
        raise ValueError("Agent 02: structured_data is empty — Agent 1 must run first")

    logger.info("agent_02_start", extra={"call_id": call_id})

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        tools=[_TOOL_DEFINITION],
        tool_choice={"type": "tool", "name": "extract_clinical_hypotheses"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Generate ranked root cause hypotheses for this patient based on "
                    "the following structured clinical data:\n\n"
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
        raise ValueError("Agent 02: Claude did not return a tool_use block")

    try:
        hypotheses = ClinicalHypotheses(**tool_block.input)
    except ValidationError as e:
        raise ValueError(f"Agent 02 output validation failed: {e}") from e

    logger.info(
        "agent_02_complete",
        extra={"call_id": call_id, "hypothesis_count": len(hypotheses.hypotheses)},
    )
    return {"hypotheses": hypotheses.model_dump()}
