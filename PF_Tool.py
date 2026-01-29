import streamlit as st
import pdfplumber
import re
import pandas as pd
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import Font
import tempfile
import os
import base64

# ---------------- PAGE CONFIG ----------------

st.set_page_config(page_title="PF Challan Automation Tool", layout="centered")

# ---------------- PREMIUM UI THEME ----------------

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #cbe9ff, #e8f6ff, #b3e5ff);
    font-family: 'Segoe UI', sans-serif;
}

.block-container {
    background: rgba(255,255,255,0.80);
    padding: 2.5rem;
    border-radius: 22px;
    box-shadow: 0px 10px 30px rgba(0,0,0,0.15);
}

.main-card {
    background: linear-gradient(135deg, #0f172a, #020617);
    padding: 28px;
    border-radius: 22px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 25px;
}

.title-text {
    color: #ffffff;
    font-size: 42px;
    font-weight: 800;
}

.subtext {
    color: #9fd3ff;
    font-size: 18px;
}

.shloka {
    color: #ffd700;
    font-style: italic;
    font-size: 16px;
}

.brand {
    color: #c7e7ff;
    font-size: 14px;
}

.logo-box img {
    border-radius: 50%;
    border: 4px solid #38bdf8;
    width: 110px;
    height: 110px;
    object-fit: cover;
    box-shadow: 0px 0px 25px rgba(56,189,248,0.8);
}

</style>
""", unsafe_allow_html=True)

# ---------------- LOGO + HEADER ----------------

logo_html = ""
if os.path.exists("aj_logo.png"):
    with open("aj_logo.png", "rb") as img:
        encoded = base64.b64encode(img.read()).decode()
    logo_html = f"""
    <div class="logo-box">
        <img src="data:image/png;base64,{encoded}">
    </div>
    """

st.markdown(f"""
<div class="main-card">
    <div>
        <div class="title-text">📊 PF Challan Automation Tool</div>
        <div class="subtext">🌸 Lord Krishna Blessings</div>
        <div class="shloka">कर्मण्येवाधिकारस्ते मा फलेषु कदाचन</div>
        <div class="brand">Tool developed by – Abhishek Jakkula</div>
    </div>
    {logo_html}
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
        "Grand Total (Rechecked)": grand_total
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
        df.insert(0, "S.No", range(1, len(df) + 1))

        output_file = f"PF_Monthwise_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="PF Challans Summary", index=False)

        add_title_to_excel(output_file)

        st.success("✅ PF Challans Summary generated successfully")
        st.dataframe(df)

        with open(output_file, "rb") as f:
            st.download_button("📥 Download Excel Report", f, file_name=output_file)

    else:
        st.error("❌ No PF challan data found.")
