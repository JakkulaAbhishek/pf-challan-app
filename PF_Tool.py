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

# ---------------- PREMIUM UI ----------------
st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at top, #0b1220, #020617);
    color: white;
    font-family: "Segoe UI", sans-serif;
}
.block-container {
    background: #020617;
    padding: 2.5rem;
    border-radius: 18px;
}
.header-box {
    background: linear-gradient(135deg, #020617, #0f172a, #020617);
    padding: 30px;
    border-radius: 20px;
    box-shadow: 0px 0px 40px rgba(56,189,248,0.35);
    margin-bottom: 30px;
}
.title {
    font-size: 42px;
    font-weight: 900;
    color: white;
}
.sub {
    color: #cbd5e1;
    font-size: 17px;
}
.krishna {
    color: #38bdf8;
    font-size: 18px;
    margin-top: 10px;
    font-weight: 600;
}
.quote {
    color: #facc15;
    font-size: 18px;
    font-style: italic;
}
.brand {
    color: #38bdf8;
    font-weight: 600;
}
.stButton>button {
    background: linear-gradient(135deg, #2563eb, #0ea5e9);
    color: white;
    border-radius: 10px;
    height: 48px;
    font-weight: 800;
    border: none;
    box-shadow: 0px 0px 20px rgba(37,99,235,0.5);
}
label, p, h1, h2, h3 {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <div class="title">📊 PF Challan Automation Tool</div>
    <p class="sub">Fast • Accurate • Audit-Ready PF Challan Processing</p>
    <p class="krishna">🌸 Lord Krishna Blessings</p>
    <p class="quote">कर्मण्येवाधिकारस्ते मा फलेषु कदाचन</p>
    <p class="brand">Tool developed by - Abhishek Jakkula</p>
</div>
""", unsafe_allow_html=True)

# ---------------- HELPERS ----------------
def pick(text, pattern):
    m = re.search(pattern, text, re.I | re.S)
    return m.group(1).strip() if m else ""

def to_amount(val):
    try:
        return float(val.replace(",", "").strip())
    except:
        return 0.0

def calculate_due_date(wage_month):
    try:
        base = datetime.strptime(wage_month, "%B %Y")
        year = base.year + (1 if base.month == 12 else 0)
        month = 1 if base.month == 12 else base.month + 1
        return datetime(year, month, 15).strftime("%d-%b-%Y").upper()
    except:
        return ""

# ---------------- 🔥 MONTH-SAFE SPLITTER ----------------
def split_challans(text):

    text = re.sub(r"\s+", " ", text)

    months = r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}"
    matches = [(m.start(), m.group()) for m in re.finditer(months, text, re.I)]

    blocks = []
    for i in range(len(matches)):
        start = matches[i][0]
        end = matches[i+1][0] if i+1 < len(matches) else len(text)
        blocks.append(text[start:end])

    return blocks

# ---------------- CHALLAN PARSER ----------------
def parse_pf_challan(block):

    wage_month = pick(block, r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}")

    system_date = pick(block, r"(\d{2}-[A-Z]{3}-\d{4})")
    due_date = calculate_due_date(wage_month)

    admin = to_amount(pick(block, r"Administration Charges.*?([0-9,]{3,})"))
    employer = to_amount(pick(block, r"Employer'?s Share Of.*?([0-9,]{3,})"))
    employee = to_amount(pick(block, r"Employee'?s Share Of.*?([0-9,]{3,})"))

    challan_total = to_amount(pick(block, r"Grand Total.*?([0-9,]{3,})"))
    computed_total = admin + employer + employee

    return {
        "Wage Month": wage_month,
        "Due Date": due_date,
        "System Generated Date": system_date,
        "Administration Charges": admin,
        "Employer's Share": employer,
        "Employee's Share": employee,
        "Computed Total": computed_total,
        "Challan Total": challan_total,
        "Match Status": "MATCH ✅" if abs(computed_total - challan_total) < 1 else "MISMATCH ❌"
    }

# ---------------- EXCEL TITLE ----------------
def add_title_to_excel(file_path):
    wb = load_workbook(file_path)
    ws = wb["PF Challans Summary"]
    ws.insert_rows(1, amount=2)
    ws["A1"] = "Tool developed by - Abhishek Jakkula"
    ws["A1"].font = Font(bold=True)
    wb.save(file_path)

# ---------------- UI ----------------
uploaded_files = st.file_uploader("📂 Upload PF Challan PDFs", type=["pdf"], accept_multiple_files=True)

if uploaded_files and st.button("🚀 Process Challans"):

    all_records = []
    sl = 1

    with st.spinner("Scanning all months..."):

        for uploaded_file in uploaded_files:

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                path = tmp.name

            text = ""
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += "\n" + t

            blocks = split_challans(text)
            st.info(f"📄 Months detected in file: {len(blocks)}")

            for block in blocks:
                data = parse_pf_challan(block)
                data["Sl No"] = sl
                data["Source File"] = uploaded_file.name
                all_records.append(data)
                sl += 1

            os.remove(path)

    if all_records:

        df = pd.DataFrame(all_records)
        df = df[[
            "Sl No","Wage Month","Due Date","System Generated Date",
            "Administration Charges","Employer's Share","Employee's Share",
            "Computed Total","Challan Total","Match Status","Source File"
        ]]

        output = f"PF_Challans_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="PF Challans Summary")

        add_title_to_excel(output)

        st.success("✅ All months detected & September issue fixed successfully")
        st.dataframe(df, use_container_width=True)

        with open(output, "rb") as f:
            st.download_button("📥 Download Excel Report", f, file_name=output)

    else:
        st.error("❌ No PF challan data found.")
