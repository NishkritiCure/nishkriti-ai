from typing import TypedDict


class PipelineState(TypedDict):
    call_id: str
    patient_id: str
    layer: int                      # 1 | 2 | 3
    transcript_raw: str
    report_urls: list[str]          # populated in layer 2 from reports table
    structured_data: dict | None    # Agent 1 output
    hypotheses: dict | None         # Agent 2 output
    red_flags: dict | None          # Agent 3 output
    protocol: dict | None           # Agent 4 output
    plans: list[dict] | None        # Agent 5 output
    error: str | None               # set if any agent fails
