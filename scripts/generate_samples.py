"""Generate BrightSmile Dental sample intake PDFs and referral emails."""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


def _draw_intake(path: Path, fields: dict[str, str], title: str = "New Patient Intake Form") -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    y = height - 72

    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, y, "BrightSmile Dental Clinic")
    y -= 24
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, y, title)
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(72, y, "(951) 555-0142  ·  Riverside, CA")
    y -= 36

    labels = [
        ("Patient Name", "patient_name"),
        ("Date of Birth (DOB)", "dob"),
        ("Phone", "phone"),
        ("Email", "email"),
        ("Insurance Provider", "insurance_provider"),
        ("Policy Number", "policy_number"),
        ("Reason for Visit", "reason_for_visit"),
        ("Medical History / Flags", "medical_flags"),
    ]
    c.setFont("Helvetica", 11)
    for label, key in labels:
        value = fields.get(key, "")
        c.drawString(72, y, f"{label}: {value}")
        y -= 22

    c.showPage()
    c.save()


def main() -> None:
    SAMPLES.mkdir(parents=True, exist_ok=True)

    _draw_intake(
        SAMPLES / "01_intake_clean.pdf",
        {
            "patient_name": "Maria Elena Vargas",
            "dob": "1988-03-14",
            "phone": "(951) 555-0198",
            "email": "maria.vargas@email.example",
            "insurance_provider": "Delta Dental PPO",
            "policy_number": "DD-44829103",
            "reason_for_visit": "Tooth sensitivity on upper left; wants cleaning",
            "medical_flags": "Penicillin allergy; hypertension",
        },
    )

    # Deliberately incomplete / messy — missing policy # and DOB unclear
    _draw_intake(
        SAMPLES / "02_intake_messy_partial.pdf",
        {
            "patient_name": "J. Smith (?)",
            "dob": "",  # missing
            "phone": "555-01",  # truncated
            "email": "",
            "insurance_provider": "maybe MetLife??",
            "policy_number": "",  # missing — critical
            "reason_for_visit": "pain",
            "medical_flags": "[checkbox unclear]",
        },
        title="New Patient Intake Form (scanned copy — partial)",
    )

    (SAMPLES / "03_referral_root_canal.txt").write_text(
        """From: Dr. Alan Cho <acho@riversidefamilydental.example>
To: referrals@brightsmile.example
Subject: Referral — Sarah Nguyen for endodontic eval

Hi BrightSmile team,

I'm referring my patient Sarah Nguyen (DOB 1995-07-22) for evaluation of
possible root canal therapy on tooth #14. She has lingering sensitivity to
cold for 3 weeks after a deep filling.

Urgency: soon (ideally within 2 weeks)
Contact: patient cell (951) 555-0177; my office (951) 555-0100

Notes: No known drug allergies. Recent PA attached in chart (not included here).

Thanks,
Alan Cho, DDS
Riverside Family Dental
""",
        encoding="utf-8",
    )

    (SAMPLES / "04_referral_urgent.eml").write_text(
        """From: Dr. Priya Nair <pnair@valleyoralsurgery.example>
To: referrals@brightsmile.example
Subject: URGENT referral — swelling / possible abscess

Please see James Ortiz ASAP for facial swelling adjacent to #19.
Referring dentist: Dr. Priya Nair, Valley Oral Surgery.
Patient: James Ortiz
Reason: suspected abscess, difficulty chewing
Urgency: urgent — same day if possible
Contact: (951) 555-0166

Started amoxicillin yesterday per our office. Thanks.
""",
        encoding="utf-8",
    )

    print(f"Wrote samples to {SAMPLES}")


if __name__ == "__main__":
    main()
