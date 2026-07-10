"""LLM structured extraction against Pydantic-backed JSON schemas."""

from __future__ import annotations

from typing import Any

from extract.intake import IntakeDocument
from extract.llm import call_llm_structured
from extract.schemas import DocumentType, LLMExtractionPayload

SYSTEM = """You extract structured data from dental clinic documents for BrightSmile Dental Clinic.

Rules:
- Return only values you can read in the document text.
- Use null for any field you cannot find. Never invent names, dates, policy numbers, or phone numbers.
- medical_flags should list checked conditions / allergies mentioned (empty list if none).
- field_confidence: per-field score from 0.0 to 1.0 (1.0 = clearly printed/written, lower if unclear or partial).
- inferred_fields: list field names you guessed or normalized heavily (e.g. expanded an abbreviation). Prefer leaving a field null over inferring.
- overall_confidence: your confidence in the whole extraction (0.0–1.0).
- document_type must match the document you were given.
"""


def _json_schema_for(doc_type: DocumentType) -> dict[str, Any]:
    if doc_type == DocumentType.INTAKE_FORM:
        data_props = {
            "patient_name": {"type": ["string", "null"]},
            "dob": {"type": ["string", "null"]},
            "phone": {"type": ["string", "null"]},
            "email": {"type": ["string", "null"]},
            "insurance_provider": {"type": ["string", "null"]},
            "policy_number": {"type": ["string", "null"]},
            "reason_for_visit": {"type": ["string", "null"]},
            "medical_flags": {
                "type": "array",
                "items": {"type": "string"},
            },
        }
        data_required = list(data_props.keys())
    else:
        data_props = {
            "referring_dentist": {"type": ["string", "null"]},
            "patient_name": {"type": ["string", "null"]},
            "reason": {"type": ["string", "null"]},
            "urgency": {"type": ["string", "null"]},
            "contact_info": {"type": ["string", "null"]},
            "notes": {"type": ["string", "null"]},
        }
        data_required = list(data_props.keys())

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "document_type": {
                "type": "string",
                "enum": [doc_type.value],
            },
            "data": {
                "type": "object",
                "additionalProperties": False,
                "properties": data_props,
                "required": data_required,
            },
            "field_confidence": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "field": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["field", "confidence"],
                },
            },
            "inferred_fields": {
                "type": "array",
                "items": {"type": "string"},
            },
            "overall_confidence": {"type": "number"},
        },
        "required": [
            "document_type",
            "data",
            "field_confidence",
            "inferred_fields",
            "overall_confidence",
        ],
    }


def _normalize_confidence(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert field_confidence array (OpenAI-strict friendly) to a dict."""
    fc = raw.get("field_confidence", {})
    if isinstance(fc, list):
        raw["field_confidence"] = {
            item["field"]: float(item["confidence"])
            for item in fc
            if isinstance(item, dict) and "field" in item and "confidence" in item
        }
    elif not isinstance(fc, dict):
        raw["field_confidence"] = {}
    return raw


def extract_structured(doc: IntakeDocument) -> LLMExtractionPayload:
    schema = _json_schema_for(doc.document_type)
    user = (
        f"Document type hint: {doc.document_type.value}\n"
        f"Filename: {doc.filename}\n"
        f"OCR used: {doc.used_ocr}\n\n"
        f"--- DOCUMENT TEXT ---\n{doc.text}\n--- END ---"
    )
    raw = call_llm_structured(SYSTEM, user, schema)
    # Force the detected type if the model drifts
    raw["document_type"] = doc.document_type.value
    raw = _normalize_confidence(raw)
    return LLMExtractionPayload.model_validate(raw)
