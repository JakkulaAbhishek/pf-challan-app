import streamlit as st
import pdfplumber
import pytesseract
import re
import pandas as pd
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import Font
import tempfile
import os

# ---------------- CONFIG ----------------

st.set_page_config(page_title="PF Challan Tool", layout="centered")

# ---------------- UI THEME ----------------

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
    background: linear-gradient(135deg, #0f172a, #020617);
    padding: 30px;
    border-radius: 20px;
    box-shadow: 0px 0px 25px rgba(0,140,255,0.25);
    margin-bottom: 30px;
}
.title {
    font-size: 40px;
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
    height: 46px;
    font-weight: 700;
    border: none;
}
label, p, h1, h2, h3 {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------

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

# ---------------- CHALLAN PARSER ----------------

def parse_pf_challan(block):

    wage_month = pick(block, r"Dues for the wage month of\s*([A-Za-z]+\s+\d{4})")
    system_raw = pick(block, r"system generated challan on\s*([0-9A-Za-z\-: ]+)")
    system_date_str = clean_system_date(system_raw)
    system_date = to_date(system_date_str)
    due_date = calculate_due_date(wage_month)

    employee_share_str = pick(
        block, r"Employee's Share Of\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+([0-9,]+)"
    )

    employee_share = to_amount(employee_share_str)
    disallowance = 0

    if system_date and due_date and system_date > due_date:
        disallowance = employee_share

    return {
        "Wage Month": wage_month,
        "Due Date": due_date.strftime("%d-%b-%Y").upper() if due_date else "",
        "System Generated Date": system_date_str,
        "Administration Charges": pick(block, r"Administration Charges\s+[0-9]+\s+([0-9,]+)"),
        "Employer's Share": pick(block, r"Employer's Share Of\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+([0-9,]+)"),
        "Employee's Share": employee_share_str,
        "Employee Share Disallowance": f"{int(disallowance):,}" if disallowance else "0",
        "Grand Total": pick(block, r"Grand Total.*?([0-9,]{3,})")
    }

# ---------------- EXCEL TITLE ----------------

def add_title_to_excel(file_path):
    wb = load_workbook(file_path)
    ws = wb.active
    ws.insert_rows(1, amount=2)
    ws["A1"] = "Tool developed by - Abhishek Jakkula"
    ws["A1"].font = Font(bold=True)
    wb.save(file_path)

# ---------------- UI ----------------

uploaded_files = st.file_uploader(
    "📂 Upload PF Challan PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files and st.button("🚀 Process Challans"):

    all_records = []

    with st.spinner("Processing PDFs..."):

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

        final_columns = [
            "Wage Month",
            "Due Date",
            "System Generated Date",
            "Administration Charges",
            "Employer's Share",
            "Employee's Share",
            "Employee Share Disallowance",
            "Grand Total",
            "Source File"
        ]

        df = df[final_columns].dropna(how="all").reset_index(drop=True)

        output_file = f"PF_Monthwise_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(output_file, index=False)
        add_title_to_excel(output_file)

        st.success("✅ Excel generated successfully")
        st.dataframe(df, use_container_width=True)

        with open(output_file, "rb") as f:
            st.download_button("📥 Download Excel", f, file_name=output_file)

    else:
        st.error("No PF challan data found.")
