import streamlit as st
import pdfplumber
import re
import pandas as pd
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import Font
import tempfile
import os

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="PF Challan Automation Tool", layout="centered")

# ---------------- CUSTOM CSS ----------------
st.markdown("""
<style>
body {
    background-color: #050b18;
    color: white;
}
.main {
    background-color: #050b18;
}
.block-container {
    padding-top: 2rem;
}
.header-box {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    padding: 30px;
    border-radius: 18px;
    box-shadow: 0px 0px 25px rgba(0,140,255,0.3);
}
.big-title {
    font-size: 38px;
    font-weight: 800;
    color: white;
}
.sub {
    color: #dcdcdc;
    font-size: 16px;
}
.brand {
    color: #4cc9f0;
    font-weight: 600;
}
.quote {
    color: #ffd166;
    font-size: 18px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("""
<div class="header-box">
    <div class="big-title">📊 PF Challan Automation Tool</div>
    <p class="sub">Fast • Accurate • Audit-Ready PF Challan Processing</p>
    <p>🌸 <b>Lord Krishna Blessings</b></p>
    <p class="quote">कर्मण्येवाधिकारस्ते मा फलेषु कदाचन</p>
    <p class="brand">Tool developed by – Abhishek Jakkula</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ---------------- HELPERS ----------------
def pick(text, pattern):
    m = re.search(pattern, text, re.I)
    return m.group(1).strip() if m else ""

def to_amount(val):
    try:
        return float(val.replace(",", "").strip())
    except:
        return 0.0

def split_challans(text):
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(Dues for the wage month of\s+[A-Za-z]+\s*\d{4})", text, flags=re.I)
    blocks = []
    for i in range(1, len(parts), 2):
        blocks.append(parts[i] + " " + parts[i+1])
    return blocks

# ---------------- PARSER ----------------
def parse_pf_challan(block):

    wage_month = pick(block, r"Dues for the wage month of\s*([A-Za-z]+\s*\d{4})")

    admin = to_amount(pick(block, r"Administration Charges.*?TOTAL\s+([0-9,]+)"))
    employer = to_amount(pick(block, r"Employer's Share Of.*?TOTAL\s+([0-9,]+)"))
    employee = to_amount(pick(block, r"Employee's Share Of.*?TOTAL\s+([0-9,]+)"))
    challan_total = to_amount(pick(block, r"Grand Total.*?([0-9,]{2,})"))

    computed_total = admin + employer + employee
    status = "MATCH ✅" if abs(computed_total - challan_total) < 1 else "MISMATCH ❌"

    return {
        "Wage Month": wage_month,
        "Administration Charges": admin,
        "Employer Share": employer,
        "Employee Share": employee,
        "Computed Grand Total": computed_total,
        "Challan Grand Total": challan_total,
        "Status": status
    }

# ---------------- EXCEL TITLE ----------------
def format_excel(file):
    wb = load_workbook(file)
    ws = wb["PF Challans Summary"]
    ws.insert_rows(1)
    ws["A1"] = "Tool developed by - Abhishek Jakkula"
    ws["A1"].font = Font(bold=True)
    wb.save(file)

# ---------------- UI ----------------
st.subheader("📂 Upload PF Challan PDFs")

uploaded_files = st.file_uploader(
    "Upload one or multiple PF challan PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files and st.button("🚀 Process Challans"):

    all_records = []
    sl = 1

    with st.spinner("Reading and validating challans..."):

        for file in uploaded_files:

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file.read())
                path = tmp.name

            text = ""
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += "\n" + t

            blocks = split_challans(text)

            for block in blocks:
                row = parse_pf_challan(block)
                row["Sl No"] = sl
                row["Source File"] = file.name
                all_records.append(row)
                sl += 1

            os.remove(path)

    if all_records:

        df = pd.DataFrame(all_records)
        df = df[[
            "Sl No", "Wage Month", "Administration Charges",
            "Employer Share", "Employee Share",
            "Computed Grand Total", "Challan Grand Total",
            "Status", "Source File"
        ]]

        output = f"PF_Challans_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="PF Challans Summary")

        format_excel(output)

        st.success("✅ PF challans processed & validated successfully")
        st.dataframe(df)

        with open(output, "rb") as f:
            st.download_button("📥 Download Excel Report", f, file_name=output)

    else:
        st.error("❌ No usable PF challan data found.")
