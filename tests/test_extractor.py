"""Extractor helpers and mocked structured LLM calls."""

from pathlib import Path
from unittest.mock import patch

from extract.extractor import _json_schema_for, _normalize_confidence, extract_structured
from extract.intake import IntakeDocument
from extract.schemas import DocumentType, LLMExtractionPayload


def test_json_schema_intake_has_required_fields():
    schema = _json_schema_for(DocumentType.INTAKE_FORM)
    assert schema["type"] == "object"
    assert "patient_name" in schema["properties"]["data"]["properties"]
    assert "medical_flags" in schema["properties"]["data"]["properties"]
    assert schema["properties"]["field_confidence"]["type"] == "array"


def test_json_schema_referral_has_required_fields():
    schema = _json_schema_for(DocumentType.REFERRAL_EMAIL)
    props = schema["properties"]["data"]["properties"]
    assert "referring_dentist" in props
    assert "urgency" in props
    assert "patient_name" in props


def test_normalize_confidence_from_array():
    raw = {
        "field_confidence": [
            {"field": "patient_name", "confidence": 0.9},
            {"field": "dob", "confidence": 0.8},
            {"bad": True},
        ]
    }
    out = _normalize_confidence(raw)
    assert out["field_confidence"] == {"patient_name": 0.9, "dob": 0.8}


def test_normalize_confidence_keeps_dict():
    raw = {"field_confidence": {"patient_name": 1.0}}
    assert _normalize_confidence(raw)["field_confidence"] == {"patient_name": 1.0}


def test_normalize_confidence_invalid_becomes_empty():
    raw = {"field_confidence": "nope"}
    assert _normalize_confidence(raw)["field_confidence"] == {}


@patch("extract.extractor.call_llm_structured")
def test_extract_structured_forces_document_type(mock_llm):
    mock_llm.return_value = {
        "document_type": "referral_email",  # wrong on purpose
        "data": {
            "patient_name": "Maria Elena Vargas",
            "dob": "1988-03-14",
            "phone": None,
            "email": None,
            "insurance_provider": "Delta",
            "policy_number": "DD-1",
            "reason_for_visit": "Cleaning",
            "medical_flags": [],
        },
        "field_confidence": [
            {"field": "patient_name", "confidence": 0.95},
        ],
        "inferred_fields": [],
        "overall_confidence": 0.9,
    }
    doc = IntakeDocument(
        path=Path("01_intake_clean.pdf"),
        filename="01_intake_clean.pdf",
        document_type=DocumentType.INTAKE_FORM,
        text="Patient Name: Maria Elena Vargas",
    )
    payload = extract_structured(doc)
    assert isinstance(payload, LLMExtractionPayload)
    assert payload.document_type == DocumentType.INTAKE_FORM
    assert payload.data["patient_name"] == "Maria Elena Vargas"
    assert payload.field_confidence["patient_name"] == 0.95
    mock_llm.assert_called_once()
