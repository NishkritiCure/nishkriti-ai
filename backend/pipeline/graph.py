from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy
from pipeline.state import PipelineState
from pipeline.agents.agent_01_data_structurer import run_agent_01
from utils.logging import get_logger

logger = get_logger(__name__)

# ─── Stub node functions ──────────────────────────────────────────────────────
# Each stub sets its output key and logs. These are replaced one-by-one starting
# in EB-004. Do not delete a stub until its real agent is implemented.

def run_agent_02(state: PipelineState) -> dict:
    """Stub: Clinical Reasoner — replaced in EB-005."""
    logger.info("agent_02_stub", extra={"call_id": state["call_id"]})
    return {"hypotheses": {"_stub": True, "agent": "02"}}


def run_agent_03(state: PipelineState) -> dict:
    """Stub: Red Flag Detector — replaced in EB-005."""
    logger.info("agent_03_stub", extra={"call_id": state["call_id"]})
    return {"red_flags": {"_stub": True, "agent": "03"}}


def run_agent_04(state: PipelineState) -> dict:
    """Stub: Protocol Generator — replaced in EB-006."""
    logger.info("agent_04_stub", extra={"call_id": state["call_id"]})
    return {"protocol": {"_stub": True, "agent": "04"}}


def run_agent_05(state: PipelineState) -> dict:
    """Stub: Plan Builder — replaced in EB-007."""
    logger.info("agent_05_stub", extra={"call_id": state["call_id"]})
    return {"plans": [{"_stub": True, "agent": "05"}]}


def run_agent_06(state: PipelineState) -> dict:
    """Stub: Doctor Queue Writer — replaced in EB-007."""
    logger.info("agent_06_stub", extra={"call_id": state["call_id"]})
    return {}


# ─── Post-call graph (Agents 1–4) ────────────────────────────────────────────
# Topology:
#   START → agent_01
#   agent_01 → agent_02  ┐ (parallel fan-out)
#   agent_01 → agent_03  ┘
#   agent_02 → agent_04  ┐ (fan-in — agent_04 waits for both)
#   agent_03 → agent_04  ┘
#   agent_04 → END

_post_call_builder = StateGraph(PipelineState)
_post_call_builder.add_node(
    "agent_01",
    run_agent_01,
    retry=RetryPolicy(max_attempts=3),
)
_post_call_builder.add_node("agent_02", run_agent_02)
_post_call_builder.add_node("agent_03", run_agent_03)
_post_call_builder.add_node("agent_04", run_agent_04)

_post_call_builder.add_edge(START, "agent_01")
_post_call_builder.add_edge("agent_01", "agent_02")
_post_call_builder.add_edge("agent_01", "agent_03")
_post_call_builder.add_edge("agent_02", "agent_04")
_post_call_builder.add_edge("agent_03", "agent_04")
_post_call_builder.add_edge("agent_04", END)

post_call_graph = _post_call_builder.compile()

# ─── Plan graph (Agents 5–6) ─────────────────────────────────────────────────
# Topology:
#   START → agent_05 → agent_06 → END
# Triggered separately after Doctor Touchpoint 1 (POST /plans/trigger/{call_id})

_plan_builder = StateGraph(PipelineState)
_plan_builder.add_node("agent_05", run_agent_05)
_plan_builder.add_node("agent_06", run_agent_06)

_plan_builder.add_edge(START, "agent_05")
_plan_builder.add_edge("agent_05", "agent_06")
_plan_builder.add_edge("agent_06", END)

plan_graph = _plan_builder.compile()
