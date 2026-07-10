"""Google Sheets delivery — Processed vs Needs Review tabs."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

from extract.schemas import ExtractionResult, IntakeForm, ReferralEmail

load_dotenv()

PROCESSED_TAB = "Processed"
REVIEW_TAB = "Needs Review"

PROCESSED_HEADERS = [
    "timestamp",
    "source_filename",
    "document_type",
    "patient_name",
    "dob",
    "phone",
    "email",
    "insurance_provider",
    "policy_number",
    "reason_for_visit",
    "medical_flags",
    "referring_dentist",
    "referral_reason",
    "urgency",
    "contact_info",
    "notes",
    "overall_confidence",
]

REVIEW_HEADERS = PROCESSED_HEADERS + ["review_reasons"]


def sheets_configured() -> bool:
    path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    return bool(path and sheet_id and os.path.isfile(path))


def write_result(result: ExtractionResult) -> ExtractionResult:
    """Write a row to the appropriate tab. Soft-fails if Sheets is not configured."""
    if not sheets_configured():
        result.sheets_written = False
        result.sheets_tab = None
        return result

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        result.sheets_written = False
        return result

    creds_path = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(sheet_id)

    tab_name = REVIEW_TAB if result.needs_review else PROCESSED_TAB
    headers = REVIEW_HEADERS if result.needs_review else PROCESSED_HEADERS
    worksheet = _get_or_create_worksheet(spreadsheet, tab_name, headers)
    worksheet.append_row(_row_for(result, include_reasons=result.needs_review), value_input_option="USER_ENTERED")

    result.sheets_written = True
    result.sheets_tab = tab_name
    return result


def _get_or_create_worksheet(spreadsheet, title: str, headers: list[str]):
    try:
        ws = spreadsheet.worksheet(title)
    except Exception:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
        ws.append_row(headers)
        return ws

    existing = ws.row_values(1)
    if not existing:
        ws.append_row(headers)
    return ws


def _row_for(result: ExtractionResult, include_reasons: bool) -> list[Any]:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    data = result.data

    patient_name = getattr(data, "patient_name", None) or ""
    dob = ""
    phone = ""
    email = ""
    insurance = ""
    policy = ""
    reason_visit = ""
    medical = ""
    referring = ""
    referral_reason = ""
    urgency = ""
    contact = ""
    notes = ""

    if isinstance(data, IntakeForm):
        dob = data.dob or ""
        phone = data.phone or ""
        email = data.email or ""
        insurance = data.insurance_provider or ""
        policy = data.policy_number or ""
        reason_visit = data.reason_for_visit or ""
        medical = "; ".join(data.medical_flags)
    elif isinstance(data, ReferralEmail):
        referring = data.referring_dentist or ""
        referral_reason = data.reason or ""
        urgency = data.urgency or ""
        contact = data.contact_info or ""
        notes = data.notes or ""

    row = [
        ts,
        result.source_filename,
        result.document_type.value,
        patient_name,
        dob,
        phone,
        email,
        insurance,
        policy,
        reason_visit,
        medical,
        referring,
        referral_reason,
        urgency,
        contact,
        notes,
        round(result.overall_confidence, 3),
    ]
    if include_reasons:
        row.append("; ".join(result.review_reasons))
    return row
