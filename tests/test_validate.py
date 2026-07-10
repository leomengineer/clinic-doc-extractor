"""Validation routing edge cases."""

from extract.schemas import DocumentType, LLMExtractionPayload
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
