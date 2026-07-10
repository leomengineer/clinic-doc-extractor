"""Single-file and batch extraction pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from extract.extractor import extract_structured
from extract.intake import IMAGE_EXTS, EMAIL_EXTS, PDF_EXTS, load_document
from extract.schemas import ExtractionResult
from extract.sheets import write_result
from extract.validate import validate_extraction

load_dotenv()

SUPPORTED = PDF_EXTS | IMAGE_EXTS | EMAIL_EXTS | {".md"}


def process_file(
    path: str | Path,
    write_sheets: bool = True,
    source_filename: str | None = None,
) -> ExtractionResult:
    doc = load_document(path)
    filename = source_filename or doc.filename
    if source_filename:
        doc.filename = source_filename

    if not doc.text.strip():
        # Empty OCR / empty file — force review with empty payload shape
        from extract.schemas import DocumentType, IntakeForm, LLMExtractionPayload, ReferralEmail

        empty_data = (
            IntakeForm().model_dump()
            if doc.document_type == DocumentType.INTAKE_FORM
            else ReferralEmail().model_dump()
        )
        payload = LLMExtractionPayload(
            document_type=doc.document_type,
            data=empty_data,
            field_confidence={},
            inferred_fields=[],
            overall_confidence=0.0,
        )
        result = validate_extraction(payload, filename)
        if "empty_document_text" not in result.review_reasons:
            result.review_reasons = ["empty_document_text", *result.review_reasons]
            result.needs_review = True
    else:
        payload = extract_structured(doc)
        result = validate_extraction(payload, filename)

    if write_sheets:
        result = write_result(result)
    return result


def process_folder(folder: str | Path, write_sheets: bool = True) -> list[ExtractionResult]:
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(folder)

    files = sorted(
        p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED and not p.name.startswith(".")
    )
    return [process_file(p, write_sheets=write_sheets) for p in files]


def _result_to_dict(result: ExtractionResult) -> dict:
    return result.model_dump(mode="json")


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    target = argv[0] if argv else "./inbox"
    path = Path(target)

    if path.is_file():
        results = [process_file(path)]
    else:
        results = process_folder(path)

    summary = {
        "ok": True,
        "processed": len(results),
        "needs_review": sum(1 for r in results if r.needs_review),
        "results": [_result_to_dict(r) for r in results],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
