import os

from anthropic import Anthropic
from pydantic import ValidationError

from models.pipeline import StructuredClinicalData
from pipeline.state import PipelineState
from utils.logging import get_logger

logger = get_logger(__name__)

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_SYSTEM_PROMPT = """\
You are a clinical data extraction assistant for a functional medicine clinic in India.

Your task: extract structured clinical information from a doctor-patient consultation
transcript. You must call the extract_clinical_data tool with all fields populated.

Rules:
- Extract only what is explicitly stated in the transcript. Do not infer or hallucinate.
- If a field is not mentioned, set it to null or an empty list — never fabricate data.
- Preserve the patient's own words for chief_complaint.
- For symptoms, capture duration and severity only if mentioned.
- For review_of_systems, use lowercase system names as keys
  (e.g. "digestive", "musculoskeletal", "endocrine", "dermatological").
- Indian medication brand names are valid — include them as stated.
"""

_TOOL_DEFINITION = {
    "name": "extract_clinical_data",
    "description": (
        "Extract structured clinical data from a doctor-patient consultation transcript. "
        "Call this tool with all information mentioned in the transcript."
    ),
    "input_schema": StructuredClinicalData.model_json_schema(),
}


def run_agent_01(state: PipelineState) -> dict:
    """
    Agent 1 — Data Structurer.

    Input:  state["transcript_raw"]
    Output: {"structured_data": dict}

    Raises ValueError on Claude API error or Pydantic validation failure.
    LangGraph retries at the node level (max 3 attempts, configured in graph.py).
    """
    call_id = state["call_id"]
    transcript = state.get("transcript_raw", "")

    if not transcript:
        raise ValueError("Agent 01: transcript_raw is empty — cannot extract clinical data")

    logger.info("agent_01_start", extra={"call_id": call_id})

    response = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        tools=[_TOOL_DEFINITION],
        tool_choice={"type": "tool", "name": "extract_clinical_data"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract structured clinical data from this consultation transcript:\n\n"
                    f"{transcript}"
                ),
            }
        ],
    )

    # Extract tool_use block
    tool_block = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )
    if tool_block is None:
        raise ValueError("Agent 01: Claude did not return a tool_use block")

    # Validate with Pydantic — raises ValueError for LangGraph retry
    try:
        structured = StructuredClinicalData(**tool_block.input)
    except ValidationError as e:
        raise ValueError(f"Agent 01 output validation failed: {e}") from e

    logger.info("agent_01_complete", extra={"call_id": call_id})
    return {"structured_data": structured.model_dump()}
