"""Streamlit upload UI — calls the /extract API and shows JSON + confidence."""

import os

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Clinic Intake Extractor", page_icon="🦷")
st.title("Clinic Intake Extractor")
st.caption(
    "Turns messy intake forms and referral emails into validated structured data. "
    "Uncertain fields are flagged for human review."
)

uploaded = st.file_uploader(
    "Drop a PDF, image, or referral email (.txt / .eml)",
    type=["pdf", "png", "jpg", "jpeg", "txt", "eml"],
)

if uploaded is not None:
    if st.button("Extract", type="primary"):
        with st.spinner("Extracting…"):
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream")}
            try:
                r = httpx.post(f"{API_URL}/extract", files=files, timeout=180.0)
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPError as exc:
                st.error(f"API error: {exc}")
                st.stop()

        needs = data.get("needs_review", False)
        if needs:
            st.warning("Needs review — uncertain or incomplete fields flagged.")
        else:
            st.success("Clean extraction — ready for the Processed sheet.")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Overall confidence", f"{data.get('overall_confidence', 0):.2f}")
        with col2:
            tab = data.get("sheets_tab") or "not written"
            st.metric("Sheets tab", tab if data.get("sheets_written") else "skipped (no credentials)")

        if data.get("review_reasons"):
            st.subheader("Review reasons")
            for reason in data["review_reasons"]:
                st.write(f"- `{reason}`")

        if data.get("field_confidence"):
            st.subheader("Per-field confidence")
            st.json(data["field_confidence"])

        st.subheader("Extracted data")
        st.json(data.get("data", {}))

        with st.expander("Full response"):
            st.json(data)
