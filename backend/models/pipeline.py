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
