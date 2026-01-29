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

# ---------------- GOOGLE-STYLE UI ----------------

st.markdown("""
<style>

.stApp {
    background: linear-gradient(120deg, #e3f2fd, #f8fbff);
    font-family: "Segoe UI", sans-serif;
}

.block-container {
    background: white;
    padding: 2.5rem;
    border-radius: 18px;
    box-shadow: 0px 12px 30px rgba(0,0,0,0.08);
}

.header-card {
    background: linear-gradient(135deg, #0d47a1, #1976d2);
    padding: 28px;
    border-radius: 16px;
    margin-bottom: 25px;
}

.header-title {
    color: white;
    font-size: 40px;
    font-weight: 800;
}

.header-sub {
    color: #e3f2fd;
    font-size: 18px;
    margin-top: 6px;
}

.header-quote {
    color: #ffd54f;
    font-style: italic;
    margin-top: 4px;
}

.header-brand {
    color: #bbdefb;
    font-size: 14px;
    margin-top: 8px;
}

.section-card {
    background: #f5f9ff;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #e3f2fd;
    margin-bottom: 15px;
}

.stButton>button {
    background: linear-gradient(135deg, #1976d2, #0d47a1);
    color: white;
    border-radius: 10px;
    height: 45px;
    font-weight: bold;
    border: none;
}

.stButton>button:hover {
    background: linear-gradient(135deg, #0d47a1, #08306b);
}

</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------

st.markdown("""
<div class="header-card">
    <div class="header-title">📊 PF Challan Automation Tool</div>
    <div class="header-sub">Fast • Accurate • Audit-Ready PF Challan Processing</div>
    <div class="header-quote">🌸 कर्मण्येवाधिकारस्ते मा फलेषु कदाचन</div>
    <div class="header-brand">Tool developed by – Abhishek Jakkula</div>
</div>
""", unsafe_allow_html=True)

# ---------------- HELPERS ----------------

def pick(text, pattern):
    m = re.search(pattern, text, re.I)
    return m.group(1).strip() if m else ""

def clean_system_date(text):
    m = re.search(r"(\d{2}-[A-Z]{3}-\d{4})", text, re.I)
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
    full_text = re.sub(r"\s+", " ", full_text)
    parts = re.split(r"(Dues for the wage month of\s+[A-Za-z]+\s+\d{4})", full_text, flags=re.I)
    challans = []
    for i in range(1, len(parts), 2):
        challans.append(parts[i] + " " + parts[i+1])
    return challans

# ---------------- PARSER ----------------

def parse_pf_challan(block):

    wage_month = pick(block, r"Dues for the wage month of\s*([A-Za-z]+\s+\d{4})")
    system_raw = pick(block, r"system generated challan on\s*([0-9A-Za-z\-: ]+)")
    system_date_str = clean_system_date(system_raw)
    system_date = to_date(system_date_str)
    due_date = calculate_due_date(wage_month)

    admin = to_amount(pick(block, r"Administration Charges\s+[0-9]+\s+([0-9,]+)"))
    employer = to_amount(pick(block, r"Employer's Share Of\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+([0-9,]+)"))
    employee = to_amount(pick(block, r"Employee's Share Of\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+([0-9,]+)"))

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
                        text += "\n" + t

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
