"""Detect document type and extract raw text (OCR when needed)."""

from __future__ import annotations

import email
import re
from dataclasses import dataclass
from email import policy
from pathlib import Path

from pypdf import PdfReader

from extract.schemas import DocumentType

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}
EMAIL_EXTS = {".txt", ".eml"}
PDF_EXTS = {".pdf"}

# Heuristic keywords for type detection
_INTAKE_HINTS = re.compile(
    r"intake|new\s*patient|medical\s*history|insurance\s*provider|policy\s*number|date\s*of\s*birth|\bdob\b",
    re.I,
)
_REFERRAL_HINTS = re.compile(
    r"referr|referring|colleague|please\s+see|specialist|consult",
    re.I,
)


@dataclass
class IntakeDocument:
    path: Path
    filename: str
    document_type: DocumentType
    text: str
    used_ocr: bool = False


def load_document(path: str | Path) -> IntakeDocument:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    used_ocr = False

    if suffix in EMAIL_EXTS:
        text = _load_email(path)
    elif suffix in PDF_EXTS:
        text, used_ocr = _load_pdf(path)
    elif suffix in IMAGE_EXTS:
        text = _ocr_image(path)
        used_ocr = True
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")

    doc_type = detect_type(path.name, text)
    return IntakeDocument(
        path=path,
        filename=path.name,
        document_type=doc_type,
        text=text.strip(),
        used_ocr=used_ocr,
    )


def detect_type(filename: str, text: str) -> DocumentType:
    name = filename.lower()
    if "referral" in name or name.endswith(".eml"):
        return DocumentType.REFERRAL_EMAIL
    if "intake" in name or "new_patient" in name or "new-patient" in name:
        return DocumentType.INTAKE_FORM

    intake_score = len(_INTAKE_HINTS.findall(text))
    referral_score = len(_REFERRAL_HINTS.findall(text))
    if referral_score > intake_score:
        return DocumentType.REFERRAL_EMAIL
    return DocumentType.INTAKE_FORM


def _load_email(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".eml":
        msg = email.message_from_string(raw, policy=policy.default)
        parts = []
        if msg["from"]:
            parts.append(f"From: {msg['from']}")
        if msg["subject"]:
            parts.append(f"Subject: {msg['subject']}")
        body = msg.get_body(preferencelist=("plain", "html"))
        if body is not None:
            parts.append(body.get_content())
        else:
            parts.append(raw)
        return "\n".join(parts)
    return raw


def _load_pdf(path: Path) -> tuple[str, bool]:
    reader = PdfReader(str(path))
    parts = [(page.extract_text() or "") for page in reader.pages]
    text = "\n".join(parts).strip()
    # Scanned / image-only PDFs often yield almost no text
    if len(text) < 40:
        ocr_text = _ocr_pdf(path)
        if ocr_text.strip():
            return ocr_text, True
    return text, False


def _ocr_pdf(path: Path) -> str:
    try:
        from pdf2image import convert_from_path
    except ImportError:
        return ""

    try:
        images = convert_from_path(str(path), dpi=200)
    except Exception:
        return ""

    chunks = []
    for img in images:
        chunks.append(_ocr_pil(img))
    return "\n".join(chunks)


def _ocr_image(path: Path) -> str:
    from PIL import Image

    return _ocr_pil(Image.open(path))


def _ocr_pil(image) -> str:
    try:
        import pytesseract
    except ImportError:
        return ""
    try:
        return pytesseract.image_to_string(image) or ""
    except Exception:
        return ""
