"""Pipeline process_file / process_folder / CLI — LLM and Sheets mocked."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from extract.intake import IntakeDocument
from extract.process import main, process_file, process_folder
from extract.schemas import (
    DocumentType,
    ExtractionResult,
    IntakeForm,
    LLMExtractionPayload,
)


def _clean_payload() -> LLMExtractionPayload:
    return LLMExtractionPayload(
        document_type=DocumentType.INTAKE_FORM,
        data={
            "patient_name": "Maria Elena Vargas",
            "dob": "1988-03-14",
            "phone": "(951) 555-0198",
            "email": "maria@example.com",
            "insurance_provider": "Delta",
            "policy_number": "DD-1",
            "reason_for_visit": "Cleaning",
            "medical_flags": [],
        },
        field_confidence={"patient_name": 0.95, "dob": 0.9, "reason_for_visit": 0.9},
        inferred_fields=[],
        overall_confidence=0.92,
    )


@patch("extract.process.write_result", side_effect=lambda r: r)
@patch("extract.process.extract_structured")
@patch("extract.process.load_document")
def test_process_file_happy_path(mock_load, mock_extract, mock_write):
    mock_load.return_value = IntakeDocument(
        path=Path("01_intake_clean.pdf"),
        filename="01_intake_clean.pdf",
        document_type=DocumentType.INTAKE_FORM,
        text="Patient Name: Maria Elena Vargas\nDOB: 1988-03-14",
    )
    mock_extract.return_value = _clean_payload()

    result = process_file("01_intake_clean.pdf", write_sheets=True)
    assert result.needs_review is False
    assert result.data.patient_name == "Maria Elena Vargas"
    mock_write.assert_called_once()


@patch("extract.process.write_result")
@patch("extract.process.extract_structured")
@patch("extract.process.load_document")
def test_process_file_skips_sheets_when_disabled(mock_load, mock_extract, mock_write):
    mock_load.return_value = IntakeDocument(
        path=Path("a.pdf"),
        filename="a.pdf",
        document_type=DocumentType.INTAKE_FORM,
        text="enough text here for extraction",
    )
    mock_extract.return_value = _clean_payload()

    process_file("a.pdf", write_sheets=False)
    mock_write.assert_not_called()


@patch("extract.process.write_result", side_effect=lambda r: r)
@patch("extract.process.extract_structured")
@patch("extract.process.load_document")
def test_process_file_empty_text_forces_review(mock_load, mock_extract, mock_write):
    mock_load.return_value = IntakeDocument(
        path=Path("blank.pdf"),
        filename="blank.pdf",
        document_type=DocumentType.INTAKE_FORM,
        text="   ",
    )
    result = process_file("blank.pdf", write_sheets=False)
    assert result.needs_review is True
    assert "empty_document_text" in result.review_reasons
    mock_extract.assert_not_called()
    mock_write.assert_not_called()


@patch("extract.process.write_result", side_effect=lambda r: r)
@patch("extract.process.extract_structured")
@patch("extract.process.load_document")
def test_process_file_source_filename_override(mock_load, mock_extract, mock_write):
    mock_load.return_value = IntakeDocument(
        path=Path("/tmp/xyz.pdf"),
        filename="xyz.pdf",
        document_type=DocumentType.INTAKE_FORM,
        text="Patient Name: Ada",
    )
    mock_extract.return_value = _clean_payload()

    result = process_file("/tmp/xyz.pdf", write_sheets=False, source_filename="upload_intake.pdf")
    assert result.source_filename == "upload_intake.pdf"


@patch("extract.process.process_file")
def test_process_folder_filters_supported(mock_process, tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF")
    (tmp_path / "b.txt").write_text("referral")
    (tmp_path / "ignore.bin").write_bytes(b"x")
    (tmp_path / ".hidden.pdf").write_bytes(b"%PDF")
    mock_process.return_value = ExtractionResult(
        source_filename="a.pdf",
        document_type=DocumentType.INTAKE_FORM,
        data=IntakeForm(),
        needs_review=True,
    )

    results = process_folder(tmp_path, write_sheets=False)
    assert len(results) == 2
    called_names = sorted(Path(c.args[0]).name for c in mock_process.call_args_list)
    assert called_names == ["a.pdf", "b.txt"]


def test_process_folder_missing_raises(tmp_path):
    with pytest.raises(NotADirectoryError):
        process_folder(tmp_path / "nope")


@patch("extract.process.process_file")
def test_main_single_file(mock_process, tmp_path, capsys):
    f = tmp_path / "one.pdf"
    f.write_bytes(b"%PDF")
    mock_process.return_value = ExtractionResult(
        source_filename="one.pdf",
        document_type=DocumentType.INTAKE_FORM,
        data=IntakeForm(patient_name="A", dob="2000-01-01", reason_for_visit="x"),
        overall_confidence=0.9,
        needs_review=False,
    )
    code = main([str(f)])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["processed"] == 1
    assert out["needs_review"] == 0


@patch("extract.process.process_folder")
def test_main_folder(mock_folder, tmp_path, capsys):
    mock_folder.return_value = [
        ExtractionResult(
            source_filename="a.pdf",
            document_type=DocumentType.INTAKE_FORM,
            data=IntakeForm(),
            needs_review=True,
            review_reasons=["missing_required:dob"],
        )
    ]
    code = main([str(tmp_path)])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["processed"] == 1
    assert out["needs_review"] == 1
