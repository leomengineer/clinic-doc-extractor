"""Validate LLM output and route uncertain extractions for human review."""

from __future__ import annotations

import os

from pydantic import ValidationError

from extract.schemas import (
    INTAKE_CRITICAL,
    INTAKE_REQUIRED,
    REFERRAL_CRITICAL,
    REFERRAL_REQUIRED,
    DocumentType,
    ExtractionResult,
    IntakeForm,
    LLMExtractionPayload,
    ReferralEmail,
)


def _confidence_floor() -> float:
    return float(os.environ.get("CONFIDENCE_FLOOR", "0.7"))


def validate_extraction(
    payload: LLMExtractionPayload,
    source_filename: str,
) -> ExtractionResult:
    reasons: list[str] = []
    floor = _confidence_floor()

    try:
        if payload.document_type == DocumentType.INTAKE_FORM:
            data = IntakeForm.model_validate(payload.data)
            required = INTAKE_REQUIRED
            critical = INTAKE_CRITICAL
        else:
            data = ReferralEmail.model_validate(payload.data)
            required = REFERRAL_REQUIRED
            critical = REFERRAL_CRITICAL
    except ValidationError as exc:
        # Fall back to empty typed model so callers still get a result
        if payload.document_type == DocumentType.INTAKE_FORM:
            data = IntakeForm()
        else:
            data = ReferralEmail()
        reasons.append(f"schema_validation_failed: {exc.error_count()} error(s)")

    for field in required:
        value = getattr(data, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            reasons.append(f"missing_required:{field}")

    for field, score in payload.field_confidence.items():
        if score < floor:
            reasons.append(f"low_confidence:{field}={score:.2f}")

    for field in payload.inferred_fields:
        if field in critical:
            reasons.append(f"inferred_critical:{field}")

    if payload.overall_confidence < floor:
        reasons.append(f"low_overall_confidence={payload.overall_confidence:.2f}")

    # Dedupe while preserving order
    seen: set[str] = set()
    unique_reasons = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            unique_reasons.append(r)

    return ExtractionResult(
        source_filename=source_filename,
        document_type=payload.document_type,
        data=data,
        field_confidence=payload.field_confidence,
        inferred_fields=payload.inferred_fields,
        overall_confidence=payload.overall_confidence,
        needs_review=bool(unique_reasons),
        review_reasons=unique_reasons,
    )
