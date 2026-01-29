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

# ---------------- GOOGLE STYLE PREMIUM UI ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800;900&display=swap');

.stApp {
    background: radial-gradient(circle at top, #0b1220, #020617);
    color: white;
    font-family: 'Inter', sans-serif;
}

.block-container {
    padding: 2.5rem;
    max-width: 900px;
}

.header-box {
    background: linear-gradient(135deg, #020617, #0f172a, #020617);
    padding: 34px;
    border-radius: 22px;
    box-shadow: 0px 0px 50px rgba(56,189,248,0.45);
    margin-bottom: 30px;
    border: 1px solid rgba(148,163,184,0.15);
}

.title {
    font-size: 44px;
    font-weight: 900;
    color: white;
    letter-spacing: 0.5px;
}

.sub {
    color: #cbd5e1;
    font-size: 17px;
    margin-top: 8px;
}

.krishna {
    color: #38bdf8;
    font-size: 18px;
    margin-top: 14px;
    font-weight: 600;
}

.quote {
    color: #facc15;
    font-size: 19px;
    font-style: italic;
    margin-top: 2px;
}

.brand {
    color: #38bdf8;
    font-weight: 600;
    margin-top: 12px;
}

.upload-box {
    background: #020617;
    border-radius: 16px;
    padding: 24px;
    border: 1px solid rgba(148,163,184,0.15);
    box-shadow: inset 0 0 20px rgba(56,189,248,0.08);
}

.stButton>button {
    background: linear-gradient(135deg, #2563eb, #0ea5e9);
    color: white;
    border-radius: 12px;
    height: 48px;
    font-weight: 800;
    border: none;
    font-size: 16px;
    box-shadow: 0px 0px 25px rgba(37,99,235,0.6);
}

.stButton>button:hover {
    transform: scale(1.03);
    box-shadow: 0px 0px 40px rgba(14,165,233,0.9);
}

label, p, h1, h2, h3 {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <div class="title">📊 PF Challan Automation Tool</div>
    <div class="sub">Fast • Accurate • Audit-Ready PF Challan Processing</div>
    <div class="krishna">🌸 Lord Krishna Blessings</div>
    <div class="quote">कर्मण्येवाधिकारस्ते मा फलेषु कदाचन</div>
    <div class="brand">Tool developed by - Abhishek Jakkula</div>
</div>
""", unsafe_allow_html=True)

# ---------------- HELPERS ----------------

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

# ---------------- 🚨 BULLETPROOF MONTH ENGINE ----------------

MONTH_REGEX = r"(January|February|March|April|May|June|July|August|September|October|November|December)[\s\-]*([0-9]{4})"

def normalize_month(text):
    m = re.search(MONTH_REGEX, text, re.I)
    if m:
        return f"{m.group(1).title()} {m.group(2)}"
    return ""

def split_challans(text):

    text = re.sub(r"\s+", " ", text)

    matches = [(m.start(), normalize_month(m.group())) 
               for m in re.finditer(MONTH_REGEX, text, re.I)]

    blocks = []
    for i in range(len(matches)):
        start = matches[i][0]
        end = matches[i+1][0] if i+1 < len(matches) else len(text)
        blocks.append(text[start:end])

    return blocks

# ---------------- CHALLAN PARSER ----------------

def parse_pf_challan(block):

    wage_month = normalize_month(block)
    system_date = re.search(r"\d{2}-[A-Z]{3}-\d{4}", block)

    admin = to_amount(re.search(r"Administration Charges.*?([0-9,]{3,})", block, re.I | re.S).group(1)) if re.search(r"Administration Charges", block, re.I) else 0
    employer = to_amount(re.search(r"Employer'?s Share Of.*?([0-9,]{3,})", block, re.I | re.S).group(1)) if re.search(r"Employer", block, re.I) else 0
    employee = to_amount(re.search(r"Employee'?s Share Of.*?([0-9,]{3,})", block, re.I | re.S).group(1)) if re.search(r"Employee", block, re.I) else 0
    challan_total = to_amount(re.search(r"Grand Total.*?([0-9,]{3,})", block, re.I | re.S).group(1)) if re.search(r"Grand Total", block, re.I) else 0

    computed = admin + employer + employee

    return {
        "Wage Month": wage_month,
        "Due Date": calculate_due_date(wage_month),
        "System Generated Date": system_date.group() if system_date else "",
        "Administration Charges": admin,
        "Employer's Share": employer,
        "Employee's Share": employee,
        "Computed Total": computed,
        "Challan Total": challan_total,
        "Match Status": "MATCH ✅" if abs(computed - challan_total) < 1 else "MISMATCH ❌"
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

st.markdown("### 📂 Upload PF Challan PDFs")
uploaded_files = st.file_uploader("", type=["pdf"], accept_multiple_files=True)

if uploaded_files and st.button("🚀 Process Challans"):

    all_records = []
    sl = 1

    with st.spinner("Scanning all months including September2024 format..."):

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
            st.success(f"📄 Months detected: {len(blocks)}")

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

        st.success("✅ All months extracted successfully (September2024 fixed)")
        st.dataframe(df, use_container_width=True)

        with open(output, "rb") as f:
            st.download_button("📥 Download Excel Report", f, file_name=output)

    else:
        st.error("❌ No PF challan data found.")
