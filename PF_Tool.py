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

st.set_page_config(
    page_title="PF Challan Automation Tool",
    page_icon="📊",
    layout="centered"
)

# ---------------- DARK PREMIUM UI ----------------

st.markdown("""
<style>

.stApp {
    background: radial-gradient(circle at top, #111827, #020617);
    font-family: "Segoe UI", sans-serif;
    color: white;
}

.block-container {
    background: #020617;
    padding: 2.8rem;
    border-radius: 18px;
    box-shadow: 0px 20px 40px rgba(0,0,0,0.7);
}

.header-card {
    background: linear-gradient(135deg, #020617, #0f172a, #020617);
    padding: 32px;
    border-radius: 20px;
    margin-bottom: 28px;
    box-shadow: inset 0px 0px 40px rgba(56,189,248,0.15);
}

.header-title {
    color: white;
    font-size: 42px;
    font-weight: 900;
}

.header-sub {
    color: #e5e7eb;
    font-size: 18px;
    margin-top: 6px;
}

.header-krishna {
    color: #38bdf8;
    font-size: 17px;
    margin-top: 8px;
    font-weight: 600;
}

.header-quote {
    color: #facc15;
    font-style: italic;
    margin-top: 4px;
    font-size: 15px;
}

.header-brand {
    color: #38bdf8;
    font-size: 15px;
    margin-top: 10px;
    font-weight: 600;
}

.section-card {
    background: #020617;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #1e293b;
    margin-bottom: 15px;
    color: white;
}

label, p, h1, h2, h3, h4 {
    color: white !important;
}

.stButton>button {
    background: linear-gradient(135deg, #2563eb, #0ea5e9);
    color: white;
    border-radius: 10px;
    height: 46px;
    font-weight: 700;
    border: none;
    box-shadow: 0px 0px 18px rgba(56,189,248,0.6);
}

.stButton>button:hover {
    background: linear-gradient(135deg, #1d4ed8, #0284c7);
    box-shadow: 0px 0px 25px rgba(56,189,248,0.9);
}

[data-testid="stFileUploader"] {
    background: #020617;
    border-radius: 12px;
    border: 1px solid #1e293b;
    padding: 12px;
}

</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------

st.markdown("""
<div class="header-card">
    <div class="header-title">📊 PF Challan Automation Tool</div>
    <div class="header-sub">Fast • Accurate • Audit-Ready PF Challan Processing</div>
    <div class="header-krishna">🌸 Lord Krishna Blessings</div>
    <div class="header-quote">कर्मण्येवाधिकारस्ते मा फलेषु कदाचन</div>
    <div class="header-brand">Tool developed by – Abhishek Jakkula</div>
</div>
""", unsafe_allow_html=True)

# ---------------- HELPERS ----------------

def pick(text, pattern):
    m = re.search(pattern, text, re.I)
    return m.group(1).strip() if m else ""

def clean_system_date(text):
    m = re.search(r"(\\d{2}-[A-Z]{3}-\\d{4})", text, re.I)
    return m.group(1).upper() if m else ""

def calculate_due_date(wage_month):
    try:
        base = datetime.strptime(wage_month, "%B %Y")
        year = base.year + (1 if base.month == 12 else 0)
        month = 1 if base.month == 12 else base.month + 1
        return datetime(year, month, 15)
    except:
        return None

def to_date(date_str):
    try:
        return datetime.strptime(date_str, "%d-%b-%Y")
    except:
        return None

def to_amount(val):
    try:
        return float(val.replace(",", ""))
    except:
        return 0.0

def split_challans(full_text):
    full_text = re.sub(r"\\s+", " ", full_text)
    parts = re.split(r"(Dues for the wage month of\\s+[A-Za-z]+\\s+\\d{4})", full_text, flags=re.I)
    challans = []
    for i in range(1, len(parts), 2):
        challans.append(parts[i] + " " + parts[i+1])
    return challans

# ---------------- PARSER ----------------

def parse_pf_challan(block):

    wage_month = pick(block, r"Dues for the wage month of\\s*([A-Za-z]+\\s+\\d{4})")
    system_raw = pick(block, r"system generated challan on\\s*([0-9A-Za-z\\-: ]+)")
    system_date_str = clean_system_date(system_raw)
    system_date = to_date(system_date_str)
    due_date = calculate_due_date(wage_month)

    admin = to_amount(pick(block, r"Administration Charges\\s+[0-9]+\\s+([0-9,]+)"))
    employer = to_amount(pick(block, r"Employer's Share Of\\s+[0-9,]+\\s+[0-9,]+\\s+[0-9,]+\\s+[0-9,]+\\s+[0-9,]+\\s+([0-9,]+)"))
    employee = to_amount(pick(block, r"Employee's Share Of\\s+[0-9,]+\\s+[0-9,]+\\s+[0-9,]+\\s+[0-9,]+\\s+[0-9,]+\\s+([0-9,]+)"))

    grand_total = admin + employer + employee

    disallowance = 0
    if system_date and due_date and system_date > due_date:
        disallowance = employee

    return {
        "Wage Month": wage_month,
        "Due Date": due_date.strftime("%d-%b-%Y").upper() if due_date else "",
        "System Generated Date": system_date_str,
        "Administration Charges": admin,
        "Employer's Share": employer,
        "Employee's Share": employee,
        "Employee Share Disallowance": disallowance,
        "Grand Total (Verified)": grand_total
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

st.markdown('<div class="section-card">📂 Upload PF Challan PDFs</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Upload one or multiple PF challan PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files and st.button("🚀 Process Challans"):

    all_records = []

    with st.spinner("Processing PF Challans..."):
        for uploaded_file in uploaded_files:

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                file_path = tmp.name

            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += "\\n" + t

            challan_blocks = split_challans(text)

            for block in challan_blocks:
                data = parse_pf_challan(block)
                data["Source File"] = uploaded_file.name
                all_records.append(data)

            os.remove(file_path)

    if all_records:

        df = pd.DataFrame(all_records)
        df.insert(0, "S.No", range(1, len(df) + 1))

        output_file = f"PF_Challans_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="PF Challans Summary", index=False)

        add_title_to_excel(output_file)

        st.success("✅ PF Challans Summary generated successfully")
        st.dataframe(df, use_container_width=True)

        with open(output_file, "rb") as f:
            st.download_button("📥 Download Excel Report", f, file_name=output_file)

    else:
        st.error("❌ No usable PF challan data found.")
