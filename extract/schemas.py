"""Pydantic schemas for clinic document extraction."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    INTAKE_FORM = "intake_form"
    REFERRAL_EMAIL = "referral_email"


class IntakeForm(BaseModel):
    """New-patient intake form fields."""

    patient_name: str | None = None
    dob: str | None = None  # YYYY-MM-DD when possible
    phone: str | None = None
    email: str | None = None
    insurance_provider: str | None = None
    policy_number: str | None = None
    reason_for_visit: str | None = None
    medical_flags: list[str] = Field(default_factory=list)


class ReferralEmail(BaseModel):
    """Referral email from another dentist / provider."""

    referring_dentist: str | None = None
    patient_name: str | None = None
    reason: str | None = None
    urgency: str | None = None  # e.g. routine, soon, urgent
    contact_info: str | None = None
    notes: str | None = None


class LLMExtractionPayload(BaseModel):
    """Shape the LLM is asked to return (before review routing)."""

    document_type: DocumentType
    data: dict[str, Any]
    field_confidence: dict[str, float] = Field(default_factory=dict)
    inferred_fields: list[str] = Field(default_factory=list)
    overall_confidence: float = 0.0


class ExtractionResult(BaseModel):
    """Validated extraction with human-in-the-loop routing."""

    source_filename: str
    document_type: DocumentType
    data: IntakeForm | ReferralEmail
    field_confidence: dict[str, float] = Field(default_factory=dict)
    inferred_fields: list[str] = Field(default_factory=list)
    overall_confidence: float = 0.0
    needs_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    sheets_written: bool = False
    sheets_tab: str | None = None


# Fields that must be present for a clean (non-review) intake row
INTAKE_REQUIRED = ("patient_name", "dob", "reason_for_visit")
# Critical fields: inferred values always force review
INTAKE_CRITICAL = ("policy_number", "dob", "patient_name")

REFERRAL_REQUIRED = ("patient_name", "reason", "referring_dentist")
REFERRAL_CRITICAL = ("patient_name", "reason")
