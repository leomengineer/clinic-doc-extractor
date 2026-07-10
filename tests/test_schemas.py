"""Schema and validation unit tests — no LLM or Sheets required."""

from extract.schemas import (
    DocumentType,
    IntakeForm,
    LLMExtractionPayload,
    ReferralEmail,
)
from extract.validate import validate_extraction


def test_intake_form_allows_nulls():
    form = IntakeForm(patient_name="Ada Lovelace", dob=None, medical_flags=["asthma"])
    assert form.patient_name == "Ada Lovelace"
    assert form.dob is None
    assert form.medical_flags == ["asthma"]


def test_referral_email_defaults():
    ref = ReferralEmail()
    assert ref.patient_name is None
    assert ref.notes is None


def test_clean_intake_passes():
    payload = LLMExtractionPayload(
        document_type=DocumentType.INTAKE_FORM,
        data={
            "patient_name": "Maria Elena Vargas",
            "dob": "1988-03-14",
            "phone": "(951) 555-0198",
            "email": "maria@example.com",
            "insurance_provider": "Delta Dental",
            "policy_number": "DD-44829103",
            "reason_for_visit": "Cleaning and sensitivity",
            "medical_flags": ["Penicillin allergy"],
        },
        field_confidence={
            "patient_name": 0.95,
            "dob": 0.9,
            "policy_number": 0.92,
            "reason_for_visit": 0.88,
        },
        inferred_fields=[],
        overall_confidence=0.93,
    )
    result = validate_extraction(payload, "01_intake_clean.pdf")
    assert result.needs_review is False
    assert result.review_reasons == []
    assert isinstance(result.data, IntakeForm)
    assert result.data.patient_name == "Maria Elena Vargas"


def test_messy_intake_flags_review():
    payload = LLMExtractionPayload(
        document_type=DocumentType.INTAKE_FORM,
        data={
            "patient_name": "J. Smith",
            "dob": None,
            "phone": "555-01",
            "email": None,
            "insurance_provider": "maybe MetLife",
            "policy_number": None,
            "reason_for_visit": "pain",
            "medical_flags": [],
        },
        field_confidence={
            "patient_name": 0.55,
            "reason_for_visit": 0.8,
            "insurance_provider": 0.4,
        },
        inferred_fields=["patient_name"],
        overall_confidence=0.45,
    )
    result = validate_extraction(payload, "02_intake_messy_partial.pdf")
    assert result.needs_review is True
    assert any(r.startswith("missing_required:dob") for r in result.review_reasons)
    assert any("low_confidence:patient_name" in r for r in result.review_reasons)
    assert any("inferred_critical:patient_name" in r for r in result.review_reasons)
    assert any("low_overall_confidence" in r for r in result.review_reasons)


def test_referral_missing_required():
    payload = LLMExtractionPayload(
        document_type=DocumentType.REFERRAL_EMAIL,
        data={
            "referring_dentist": None,
            "patient_name": "Sarah Nguyen",
            "reason": None,
            "urgency": "soon",
            "contact_info": "(951) 555-0177",
            "notes": None,
        },
        field_confidence={"patient_name": 0.9},
        inferred_fields=[],
        overall_confidence=0.8,
    )
    result = validate_extraction(payload, "03_referral.txt")
    assert result.needs_review is True
    assert any("missing_required:reason" in r for r in result.review_reasons)
    assert any("missing_required:referring_dentist" in r for r in result.review_reasons)
