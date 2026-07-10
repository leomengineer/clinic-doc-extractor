"""API tests — mock pipeline so no LLM or Sheets required."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from extract.api import app
from extract.schemas import DocumentType, ExtractionResult, IntakeForm

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@patch("extract.api.process_file")
def test_extract_upload(mock_process):
    mock_process.return_value = ExtractionResult(
        source_filename="01_intake_clean.pdf",
        document_type=DocumentType.INTAKE_FORM,
        data=IntakeForm(
            patient_name="Maria Elena Vargas",
            dob="1988-03-14",
            reason_for_visit="Cleaning",
            medical_flags=["Penicillin allergy"],
        ),
        field_confidence={"patient_name": 0.95},
        inferred_fields=[],
        overall_confidence=0.93,
        needs_review=False,
        review_reasons=[],
        sheets_written=False,
        sheets_tab=None,
    )

    resp = client.post(
        "/extract",
        files={"file": ("01_intake_clean.pdf", b"%PDF-fake", "application/pdf")},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["needs_review"] is False
    assert data["data"]["patient_name"] == "Maria Elena Vargas"
    mock_process.assert_called_once()
    kwargs = mock_process.call_args
    assert kwargs.kwargs.get("source_filename") == "01_intake_clean.pdf" or (
        len(kwargs.args) >= 1
    )


@patch("extract.api.process_file")
def test_extract_needs_review(mock_process):
    mock_process.return_value = ExtractionResult(
        source_filename="02_intake_messy_partial.pdf",
        document_type=DocumentType.INTAKE_FORM,
        data=IntakeForm(patient_name="J. Smith", reason_for_visit="pain"),
        field_confidence={"patient_name": 0.5},
        inferred_fields=["patient_name"],
        overall_confidence=0.4,
        needs_review=True,
        review_reasons=["missing_required:dob", "low_confidence:patient_name=0.50"],
        sheets_written=False,
    )

    resp = client.post(
        "/extract",
        files={"file": ("02_intake_messy_partial.pdf", b"partial", "application/pdf")},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["needs_review"] is True
    assert len(data["review_reasons"]) >= 1


@patch("extract.api.process_folder")
def test_process_default_folder(mock_folder):
    mock_folder.return_value = []

    resp = client.post("/process", json={})

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "processed": 0, "needs_review": 0, "results": []}
    mock_folder.assert_called_once_with("./inbox")


@patch("extract.api.process_folder")
def test_process_custom_folder(mock_folder):
    mock_folder.return_value = [
        ExtractionResult(
            source_filename="a.pdf",
            document_type=DocumentType.INTAKE_FORM,
            data=IntakeForm(patient_name="A", dob="2000-01-01", reason_for_visit="x"),
            overall_confidence=0.9,
            needs_review=False,
        ),
        ExtractionResult(
            source_filename="b.pdf",
            document_type=DocumentType.INTAKE_FORM,
            data=IntakeForm(patient_name="B"),
            overall_confidence=0.3,
            needs_review=True,
            review_reasons=["missing_required:dob"],
        ),
    ]

    resp = client.post("/process", json={"folder": "./samples"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["processed"] == 2
    assert body["needs_review"] == 1
    mock_folder.assert_called_once_with("./samples")


def test_extract_missing_file():
    resp = client.post("/extract")
    assert resp.status_code == 422
