"""Streamlit upload UI — drop a doc, see Processed vs Needs Review sheet status."""

import os

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Clinic Intake Extractor", page_icon="🦷", layout="centered")
st.title("Clinic Intake Extractor")
st.caption(
    "Drop an intake form or referral email. Clean rows go to the Processed sheet; "
    "uncertain ones go to Needs Review."
)

uploaded = st.file_uploader(
    "Drop a PDF, image, or referral email",
    type=["pdf", "png", "jpg", "jpeg", "txt", "eml"],
    help="New-patient intake PDFs and referral .txt / .eml files work best.",
)

extract = st.button(
    "Extract & write to Sheet",
    type="primary",
    disabled=uploaded is None,
    use_container_width=True,
)

if extract and uploaded is not None:
    with st.spinner(f"Extracting {uploaded.name}…"):
        files = {
            "file": (
                uploaded.name,
                uploaded.getvalue(),
                uploaded.type or "application/octet-stream",
            )
        }
        try:
            r = httpx.post(f"{API_URL}/extract", files=files, timeout=180.0)
            r.raise_for_status()
            st.session_state["last_result"] = r.json()
            st.session_state["last_filename"] = uploaded.name
        except httpx.ConnectError:
            st.error(
                f"Cannot reach the API at `{API_URL}`. "
                "Start it in another terminal with `make api`."
            )
            st.stop()
        except httpx.HTTPError as exc:
            st.error(f"API error: {exc}")
            st.stop()

result = st.session_state.get("last_result")
if not result:
    st.info("Upload a document, then click **Extract & write to Sheet**.")
    st.stop()

filename = st.session_state.get("last_filename", result.get("source_filename", "document"))
needs = bool(result.get("needs_review"))
written = bool(result.get("sheets_written"))
tab = result.get("sheets_tab")
confidence = float(result.get("overall_confidence") or 0)
data = result.get("data") or {}
patient = data.get("patient_name") or "(no name extracted)"

st.divider()

# Primary status — the thing you care about for the demo
if needs:
    st.error(f"**Needs review** — `{filename}`")
    if written and tab:
        st.markdown(f"Row written to the **{tab}** tab in Google Sheets.")
    elif not written:
        st.markdown(
            "Extraction flagged for review, but **Sheets was not written** "
            "(check `GOOGLE_SERVICE_ACCOUNT_JSON` / `GOOGLE_SHEET_ID` in `.env`)."
        )
else:
    st.success(f"**Successful** — `{filename}`")
    if written and tab:
        st.markdown(f"Row written to the **{tab}** tab in Google Sheets.")
    elif not written:
        st.markdown(
            "Clean extraction, but **Sheets was not written** "
            "(check credentials in `.env`)."
        )

c1, c2, c3 = st.columns(3)
c1.metric("Patient", patient)
c2.metric("Confidence", f"{confidence:.0%}")
c3.metric("Sheet tab", tab if written else "not written")

if result.get("review_reasons"):
    st.subheader("Why it needs review")
    for reason in result["review_reasons"]:
        st.markdown(f"- `{reason}`")

st.subheader("Extracted fields")
st.json(data)

with st.expander("Full API response"):
    st.json(result)
