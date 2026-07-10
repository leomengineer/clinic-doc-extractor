"""Sheets soft-fail, config detection, and row shaping."""

from unittest.mock import MagicMock, patch

from extract.schemas import DocumentType, ExtractionResult, IntakeForm, ReferralEmail
from extract.sheets import (
    PROCESSED_TAB,
    REVIEW_TAB,
    _row_for,
    sheets_configured,
    write_result,
)


def test_sheets_configured_false_when_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    monkeypatch.setenv("GOOGLE_SHEET_ID", "")
    assert sheets_configured() is False

    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", str(tmp_path / "missing.json"))
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet123")
    assert sheets_configured() is False


def test_sheets_configured_true_when_file_exists(monkeypatch, tmp_path):
    creds = tmp_path / "service_account.json"
    creds.write_text("{}")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", str(creds))
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet123")
    assert sheets_configured() is True


def test_write_result_soft_fails_when_unconfigured(monkeypatch):
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    monkeypatch.setenv("GOOGLE_SHEET_ID", "")
    result = ExtractionResult(
        source_filename="a.pdf",
        document_type=DocumentType.INTAKE_FORM,
        data=IntakeForm(patient_name="A", dob="2000-01-01", reason_for_visit="x"),
        overall_confidence=0.9,
        needs_review=False,
    )
    out = write_result(result)
    assert out.sheets_written is False
    assert out.sheets_tab is None


def test_row_for_intake_without_reasons():
    result = ExtractionResult(
        source_filename="01_intake_clean.pdf",
        document_type=DocumentType.INTAKE_FORM,
        data=IntakeForm(
            patient_name="Maria Elena Vargas",
            dob="1988-03-14",
            phone="(951) 555-0198",
            email="maria@example.com",
            insurance_provider="Delta",
            policy_number="DD-1",
            reason_for_visit="Cleaning",
            medical_flags=["Penicillin allergy", "hypertension"],
        ),
        overall_confidence=0.9333,
        needs_review=False,
    )
    row = _row_for(result, include_reasons=False)
    assert row[1] == "01_intake_clean.pdf"
    assert row[2] == "intake_form"
    assert row[3] == "Maria Elena Vargas"
    assert row[4] == "1988-03-14"
    assert row[10] == "Penicillin allergy; hypertension"
    assert row[16] == 0.933
    assert len(row) == 17


def test_row_for_referral_with_reasons():
    result = ExtractionResult(
        source_filename="03_referral.txt",
        document_type=DocumentType.REFERRAL_EMAIL,
        data=ReferralEmail(
            referring_dentist="Dr. Alan Cho",
            patient_name="Sarah Nguyen",
            reason="root canal eval",
            urgency="soon",
            contact_info="(951) 555-0177",
            notes="No allergies",
        ),
        overall_confidence=0.5,
        needs_review=True,
        review_reasons=["low_overall_confidence=0.50", "missing_required:x"],
    )
    row = _row_for(result, include_reasons=True)
    assert row[2] == "referral_email"
    assert row[3] == "Sarah Nguyen"
    assert row[11] == "Dr. Alan Cho"
    assert row[12] == "root canal eval"
    assert row[13] == "soon"
    assert "low_overall_confidence" in row[17]
    assert len(row) == 18


@patch("extract.sheets.sheets_configured", return_value=True)
def test_write_result_routes_to_processed_tab(mock_configured, monkeypatch, tmp_path):
    creds = tmp_path / "creds.json"
    creds.write_text("{}")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", str(creds))
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet123")

    mock_ws = MagicMock()
    mock_ws.row_values.return_value = ["timestamp"]
    mock_ss = MagicMock()
    mock_ss.worksheet.return_value = mock_ws
    mock_gc = MagicMock()
    mock_gc.open_by_key.return_value = mock_ss

    with (
        patch("gspread.authorize", return_value=mock_gc),
        patch("google.oauth2.service_account.Credentials.from_service_account_file"),
    ):
        result = ExtractionResult(
            source_filename="clean.pdf",
            document_type=DocumentType.INTAKE_FORM,
            data=IntakeForm(patient_name="A", dob="2000-01-01", reason_for_visit="x"),
            overall_confidence=0.95,
            needs_review=False,
        )
        out = write_result(result)

    assert out.sheets_written is True
    assert out.sheets_tab == PROCESSED_TAB
    mock_ss.worksheet.assert_called_with(PROCESSED_TAB)
    mock_ws.append_row.assert_called_once()


@patch("extract.sheets.sheets_configured", return_value=True)
def test_write_result_routes_to_needs_review_tab(mock_configured, monkeypatch, tmp_path):
    creds = tmp_path / "creds.json"
    creds.write_text("{}")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", str(creds))
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet123")

    mock_ws = MagicMock()
    mock_ws.row_values.return_value = ["timestamp"]
    mock_ss = MagicMock()
    mock_ss.worksheet.return_value = mock_ws
    mock_gc = MagicMock()
    mock_gc.open_by_key.return_value = mock_ss

    with (
        patch("gspread.authorize", return_value=mock_gc),
        patch("google.oauth2.service_account.Credentials.from_service_account_file"),
    ):
        result = ExtractionResult(
            source_filename="messy.pdf",
            document_type=DocumentType.INTAKE_FORM,
            data=IntakeForm(patient_name="B"),
            overall_confidence=0.3,
            needs_review=True,
            review_reasons=["missing_required:dob"],
        )
        out = write_result(result)

    assert out.sheets_written is True
    assert out.sheets_tab == REVIEW_TAB
    mock_ss.worksheet.assert_called_with(REVIEW_TAB)
