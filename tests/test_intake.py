"""Intake: type detection and text loading from sample fixtures."""

from pathlib import Path

import pytest

from extract.intake import detect_type, load_document
from extract.schemas import DocumentType

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def test_detect_type_from_intake_filename():
    assert detect_type("01_intake_clean.pdf", "") == DocumentType.INTAKE_FORM
    assert detect_type("new_patient_form.pdf", "") == DocumentType.INTAKE_FORM
    assert detect_type("new-patient.pdf", "") == DocumentType.INTAKE_FORM


def test_detect_type_from_referral_filename():
    assert detect_type("03_referral_root_canal.txt", "") == DocumentType.REFERRAL_EMAIL
    assert detect_type("note.eml", "hello") == DocumentType.REFERRAL_EMAIL


def test_detect_type_from_text_heuristics():
    intake_text = "Insurance provider: Delta. Policy number: 123. Date of birth / DOB."
    referral_text = "I am referring this patient to a specialist for consult."
    assert detect_type("scan.pdf", intake_text) == DocumentType.INTAKE_FORM
    assert detect_type("scan.pdf", referral_text) == DocumentType.REFERRAL_EMAIL


def test_detect_type_defaults_to_intake_when_ambiguous():
    assert detect_type("mystery.pdf", "hello world") == DocumentType.INTAKE_FORM


def test_load_clean_intake_pdf():
    doc = load_document(SAMPLES / "01_intake_clean.pdf")
    assert doc.document_type == DocumentType.INTAKE_FORM
    assert "Maria Elena Vargas" in doc.text
    assert "Delta Dental" in doc.text
    assert doc.used_ocr is False
    assert doc.filename == "01_intake_clean.pdf"


def test_load_messy_intake_pdf():
    doc = load_document(SAMPLES / "02_intake_messy_partial.pdf")
    assert doc.document_type == DocumentType.INTAKE_FORM
    assert "J. Smith" in doc.text or "Smith" in doc.text


def test_load_referral_txt():
    doc = load_document(SAMPLES / "03_referral_root_canal.txt")
    assert doc.document_type == DocumentType.REFERRAL_EMAIL
    assert "Sarah Nguyen" in doc.text
    assert "Alan Cho" in doc.text


def test_load_referral_eml():
    doc = load_document(SAMPLES / "04_referral_urgent.eml")
    assert doc.document_type == DocumentType.REFERRAL_EMAIL
    assert "James Ortiz" in doc.text
    assert "From:" in doc.text or "Priya" in doc.text


def test_load_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_document(SAMPLES / "does_not_exist.pdf")
