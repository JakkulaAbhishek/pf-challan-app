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
st.set_page_config(page_title="AJ PF Challan Tool", layout="centered")

# ---------------- THEME & STYLING ----------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
}
.block-container {
    background: rgba(0,0,0,0.75);
    padding: 2rem;
    border-radius: 18px;
}
h1,h2,h3,h4,p,label { color: white !important; }
.header-box {
    text-align:center;
    padding:25px;
    border-radius:20px;
    border:2px solid #ff2d2d;
    box-shadow:0px 0px 25px #ff2d2d;
    margin-bottom:20px;
}
.shloka {
    color:#ffd700;
    font-style:italic;
}
</style>
""", unsafe_allow_html=True)

# ---------------- LOGO ----------------
if os.path.exists("aj_logo.png"):
    with open("aj_logo.png", "rb") as img:
        encoded = base64.b64encode(img.read()).decode()
    st.markdown(f"""
    <div style="text-align:center;">
        <img src="data:image/png;base64,{encoded}" width="200">
    </div>
    """, unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("""
<div class="header-box">
<h1>📊 PF Challan Automation Tool</h1>
<h3>🦚 Lord Krishna Blessings</h3>
<p class="shloka">कर्मण्येवाधिकारस्ते मा फलेषु कदाचन</p>
<p style="color:#cccccc;">Tool developed by - Abhishek Jakkula</p>
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

    admin = to_amount(pick(block, r"Administration Charges\s+[0-9]+\s+([0-9,]+)"))
    employer = to_amount(pick(block, r"Employer's Share Of\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+([0-9,]+)"))
    employee = to_amount(employee_share_str)
    grand_total = admin + employer + employee

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
    ws = wb.active
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

        # ✅ ADD SERIAL NUMBER
        df.insert(0, "S.No", range(1, len(df) + 1))

        output_file = f"PF_Monthwise_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(output_file, index=False)
        add_title_to_excel(output_file)

        st.success("✅ Professional PF report generated successfully")
        st.dataframe(df, use_container_width=True)

        with open(output_file, "rb") as f:
            st.download_button("📥 Download Excel", f, file_name=output_file)

    else:
        st.error("No PF challan data found.")
