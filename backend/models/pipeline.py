from pydantic import BaseModel, Field


# ─── Agent 1 — Data Structurer output ────────────────────────────────────────

class SymptomEntry(BaseModel):
    symptom: str = Field(description="Name or description of the symptom")
    duration: str | None = Field(
        None,
        description="How long the symptom has been present (e.g. '3 months', '2 weeks')"
    )
    severity: str | None = Field(
        None,
        description="Severity level: 'mild' | 'moderate' | 'severe' — null if not stated"
    )


class MedicationEntry(BaseModel):
    name: str = Field(description="Name of medication or supplement")
    dose: str | None = Field(None, description="Dosage if stated")
    frequency: str | None = Field(None, description="Frequency if stated")
    type: str = Field(
        description="Category: 'prescription' | 'supplement' | 'otc' | 'unknown'"
    )


class LifestyleData(BaseModel):
    diet: str | None = Field(None, description="Diet pattern described by patient")
    sleep_hours: str | None = Field(None, description="Hours of sleep per night")
    sleep_quality: str | None = Field(
        None,
        description="'refreshing' | 'unrefreshing' | 'unknown'"
    )
    exercise: str | None = Field(None, description="Exercise habits described")
    stress_level: str | None = Field(
        None,
        description="'low' | 'moderate' | 'high' — null if not stated"
    )
    alcohol: str | None = Field(None, description="Alcohol consumption described")
    smoking: str | None = Field(None, description="Smoking status described")


class StructuredClinicalData(BaseModel):
    chief_complaint: str = Field(
        description="Primary reason for the visit, in the patient's own words"
    )
    symptoms: list[SymptomEntry] = Field(
        description="All symptoms mentioned by the patient during the consultation"
    )
    medical_history: list[str] = Field(
        description="Past diagnoses, surgeries, hospitalizations mentioned"
    )
    current_medications: list[MedicationEntry] = Field(
        description="All medications and supplements currently taken"
    )
    family_history: list[str] = Field(
        description="Relevant family medical history mentioned"
    )
    allergies: list[str] = Field(
        description="Known allergies mentioned by the patient"
    )
    lifestyle: LifestyleData
    review_of_systems: dict[str, str] = Field(
        description=(
            "System-by-system notes on anything mentioned. "
            "Keys are system names (e.g. 'digestive', 'musculoskeletal', 'endocrine', "
            "'dermatological', 'cardiovascular'). "
            "Values are brief notes from the transcript."
        )
    )


# ─── Agent 2 — Clinical Reasoner output ──────────────────────────────────────

class HypothesisEntry(BaseModel):
    hypothesis: str = Field(
        description="Name of the root cause hypothesis (e.g. 'Hypothyroidism', 'Iron deficiency anaemia')"
    )
    confidence: str = Field(
        description="Confidence level: 'high' | 'medium' | 'low'"
    )
    supporting_evidence: list[str] = Field(
        description="Specific facts from the structured clinical data that support this hypothesis"
    )
    rank: int = Field(
        description="Rank by likelihood — 1 = most likely, higher numbers = less likely"
    )


class ClinicalHypotheses(BaseModel):
    hypotheses: list[HypothesisEntry] = Field(
        description="All plausible root cause hypotheses, ordered by rank ascending (rank 1 first)"
    )
    reasoning_summary: str = Field(
        description="1-2 sentence summary of the clinical reasoning process"
    )


# ─── Agent 3 — Red Flag Detector output ──────────────────────────────────────

class RedFlag(BaseModel):
    flag: str = Field(
        description="Name of the red flag or warning sign being evaluated"
    )
    present: bool = Field(
        description="True if this red flag is present based on the clinical data"
    )
    severity: str | None = Field(
        None,
        description=(
            "Severity if present=True: 'critical' | 'high' | 'medium' | 'low'. "
            "Null if present=False."
        )
    )
    recommended_action: str | None = Field(
        None,
        description=(
            "Specific action to take if present=True "
            "(e.g. 'Order TSH immediately', 'Refer to cardiologist'). "
            "Null if present=False."
        )
    )


class RedFlagReport(BaseModel):
    flags: list[RedFlag] = Field(
        description="All red flags evaluated — include both present and absent flags"
    )
    any_critical: bool = Field(
        description="True if any flag has severity='critical'"
    )
    summary: str = Field(
        description="1-2 sentence summary for the doctor about the most important findings"
    )

