# clinic-doc-extractor

Turns messy intake forms and referral emails into validated, structured data — automatically flagging anything it's unsure about for human review.

Front desk spends ~3 minutes per intake form retyping into the system. This does it in seconds with a confidence score, and routes uncertain fields to a **Needs Review** sheet instead of guessing.

Sequel to [docs-rag-chatbot](../docs-rag-chatbot): that project answered patient questions from clinic docs; this one processes the paperwork BrightSmile Dental receives.

## Architecture

```
PDF / image / email
   → intake (detect type + extract text; OCR if scanned)
   → LLM structured extract (schema-forced JSON)
   → Pydantic validate + confidence gate
   → clean → Google Sheet "Processed"
   → uncertain → Google Sheet "Needs Review" + reason
   → return JSON (API / Streamlit)
```

No vector DB. The hard parts are reliable structured output, validation, and honest uncertainty — not retrieval.

At scale, OCR cost can be tiered (Docling for complex layouts → lighter OCR for simple pages → cloud OCR only when needed). This demo uses one path: **pypdf** for digital PDFs, **Tesseract** via pytesseract when text is missing.

## Quick start

```bash
# 1. deps + env
uv sync
cp .env.example .env
# put OPENAI_API_KEY=... (or ANTHROPIC_API_KEY=... and LLM_PROVIDER=anthropic)
# optional: GOOGLE_SERVICE_ACCOUNT_JSON + GOOGLE_SHEET_ID for Sheets delivery

# 2. sample fixtures
make samples

# 3. run API + UI
make api          # terminal 1 — http://localhost:8000
make ui           # terminal 2 — Streamlit upload UI
```

OCR demos (scanned PDFs / images) need Tesseract installed locally: `brew install tesseract` (and Poppler for PDF→image: `brew install poppler`).

Batch mode (unattended folder → Sheet):

```bash
cp samples/* inbox/
make process
```

## API

- `POST /extract` multipart `file` → extraction JSON (validated + review flags)
- `POST /process` `{"folder": "./inbox"}` → batch summary + results
- `GET /health`

## Config (`.env`)

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | `openai` or `anthropic` |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | API keys |
| `CONFIDENCE_FLOOR` | Per-field / overall floor below which docs go to Needs Review (default `0.7`) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Path to throwaway service-account JSON (never commit) |
| `GOOGLE_SHEET_ID` | Dedicated demo spreadsheet ID |
| `API_URL` | Where Streamlit sends extract requests |

Sheets is optional: without credentials the API/UI still return JSON.

## Features

1. Upload `samples/01_intake_clean.pdf` → high-confidence JSON + row on **Processed** (when Sheets configured).
2. Upload `samples/02_intake_messy_partial.pdf` → extracts what it can, sets `needs_review`, lists reasons, routes to **Needs Review**.
3. Drop files in `inbox/`, run `make process` → batch write without opening the UI.
4. Swap `LLM_PROVIDER=anthropic` — same structured-output path, provider-agnostic.

## Stack

Python · FastAPI · Pydantic · OpenAI/Anthropic (structured output) · pypdf · pytesseract · gspread · Streamlit · [uv](https://github.com/astral-sh/uv)

## Scope (intentionally skipped)

Custom model training, every document type, a fancy review dashboard (the Needs Review Sheet tab is the review UI), queueing/async workers. Production-shaped demo, not production-complete.
