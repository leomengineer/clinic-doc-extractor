"""Validation routing edge cases."""

from extract.schemas import DocumentType, LLMExtractionPayload, ReferralEmail
from extract.validate import validate_extraction


def test_inferred_policy_number_forces_review(monkeypatch):
    monkeypatch.setenv("CONFIDENCE_FLOOR", "0.7")
    payload = LLMExtractionPayload(
        document_type=DocumentType.INTAKE_FORM,
        data={
            "patient_name": "Test Patient",
            "dob": "1990-01-01",
            "phone": None,
            "email": None,
            "insurance_provider": "Aetna",
            "policy_number": "AE-999",
            "reason_for_visit": "Checkup",
            "medical_flags": [],
        },
        field_confidence={
            "patient_name": 0.95,
            "dob": 0.95,
            "policy_number": 0.9,
            "reason_for_visit": 0.9,
        },
        inferred_fields=["policy_number"],
        overall_confidence=0.9,
    )
    result = validate_extraction(payload, "intake.pdf")
    assert result.needs_review is True
    assert "inferred_critical:policy_number" in result.review_reasons


def test_blank_string_counts_as_missing_required():
    payload = LLMExtractionPayload(
        document_type=DocumentType.INTAKE_FORM,
        data={
            "patient_name": "   ",
            "dob": "1990-01-01",
            "phone": None,
            "email": None,
            "insurance_provider": None,
            "policy_number": None,
            "reason_for_visit": "Cleaning",
            "medical_flags": [],
        },
        field_confidence={"dob": 0.9, "reason_for_visit": 0.9},
        inferred_fields=[],
        overall_confidence=0.9,
    )
    result = validate_extraction(payload, "blank_name.pdf")
    assert result.needs_review is True
    assert "missing_required:patient_name" in result.review_reasons


def test_confidence_floor_env_respected(monkeypatch):
    monkeypatch.setenv("CONFIDENCE_FLOOR", "0.95")
    payload = LLMExtractionPayload(
        document_type=DocumentType.INTAKE_FORM,
        data={
            "patient_name": "Ada",
            "dob": "1990-01-01",
            "phone": None,
            "email": None,
            "insurance_provider": None,
            "policy_number": None,
            "reason_for_visit": "Cleaning",
            "medical_flags": [],
        },
        field_confidence={"patient_name": 0.9, "dob": 0.9, "reason_for_visit": 0.9},
        inferred_fields=[],
        overall_confidence=0.9,
    )
    result = validate_extraction(payload, "intake.pdf")
    assert result.needs_review is True
    assert any("low_confidence:patient_name" in r for r in result.review_reasons)
    assert any("low_overall_confidence" in r for r in result.review_reasons)


def test_clean_referral_passes():
    payload = LLMExtractionPayload(
        document_type=DocumentType.REFERRAL_EMAIL,
        data={
            "referring_dentist": "Dr. Alan Cho",
            "patient_name": "Sarah Nguyen",
            "reason": "root canal eval",
            "urgency": "soon",
            "contact_info": "(951) 555-0177",
            "notes": "No allergies",
        },
        field_confidence={
            "referring_dentist": 0.95,
            "patient_name": 0.95,
            "reason": 0.9,
        },
        inferred_fields=[],
        overall_confidence=0.94,
    )
    result = validate_extraction(payload, "03_referral.txt")
    assert result.needs_review is False
    assert isinstance(result.data, ReferralEmail)
    assert result.data.patient_name == "Sarah Nguyen"


def test_invalid_data_shape_flags_schema_validation():
    payload = LLMExtractionPayload(
        document_type=DocumentType.INTAKE_FORM,
        data={"medical_flags": "not-a-list"},  # wrong type
        field_confidence={},
        inferred_fields=[],
        overall_confidence=0.9,
    )
    result = validate_extraction(payload, "bad.pdf")
    assert result.needs_review is True
    assert any(r.startswith("schema_validation_failed") for r in result.review_reasons)


def test_dedupes_review_reasons():
    payload = LLMExtractionPayload(
        document_type=DocumentType.INTAKE_FORM,
        data={
            "patient_name": None,
            "dob": None,
            "phone": None,
            "email": None,
            "insurance_provider": None,
            "policy_number": None,
            "reason_for_visit": None,
            "medical_flags": [],
        },
        field_confidence={},
        inferred_fields=[],
        overall_confidence=0.2,
    )
    result = validate_extraction(payload, "empty.pdf")
    assert len(result.review_reasons) == len(set(result.review_reasons))
