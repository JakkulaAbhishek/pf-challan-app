import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO
from openpyxl.styles import Font, Alignment, PatternFill
from datetime import datetime
import plotly.express as px
from fpdf import FPDF

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="PF AI Auditor | Abhishek Jakkula", layout="wide", page_icon="📊")

# ---------------- ULTRA STYLISH UI ----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: radial-gradient(circle at 20% 20%, #0f172a 0%, #020617 100%); color: #f8fafc; }
    .header-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.8));
        padding: 40px; border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px); text-align: center; margin-bottom: 40px;
    }
    .main-title {
        background: linear-gradient(90deg, #38bdf8, #60a5fa, #34d399);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 3.2rem;
    }
    .stButton>button {
        background: linear-gradient(90deg, #2563eb, #0ea5e9);
        color: white !important; border: none; border-radius: 12px;
        font-weight: 700; height: 54px; width: 100%; transition: all 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- BRANDED HEADER ----------------
st.markdown("""
<div class="header-card">
    <div class="main-title">PF CHALLAN AI AUDITOR</div>
    <div style="color: #94a3b8; font-size: 1.1rem; letter-spacing: 2px; margin-top: 10px; font-weight: 600;">STATUTORY COMPLIANCE BY ABHISHEK JAKKULA</div>
    <div style="color: #facc15; font-style: italic; margin-top: 20px; font-size: 1rem;">🌸 Lord Krishna Blessings: कर्मण्येवाधिकारस्ते मा फलेषु कदाचन 🌸</div>
</div>
""", unsafe_allow_html=True)

# ---------------- HELPERS ----------------
def safe_extract(pattern, text):
    m = re.search(pattern, text, re.I | re.S)
    return m.group(1).strip() if m else "0"

def calculate_due_date(wage_month_str):
    try:
        parts = wage_month_str.split()
        month_dt = datetime.strptime(parts[0], "%B")
        year = int(parts[1])
        next_m = month_dt.month % 12 + 1
        next_y = year + (1 if month_dt.month == 12 else 0)
        return datetime(next_y, next_m, 15)
    except: return None

# ---------------- PDF GENERATOR (FIXED ENCODING) ----------------
def generate_pdf_summary(df, total_pf, disallowance, late_count):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "STATUTORY PF COMPLIANCE AUDIT", ln=True, align='C')
    pdf.ln(10)
    
    # Table Header
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    w = [30, 25, 25, 20, 35, 35, 35, 25, 35] 
    headers = ["Wage Month", "Due Date", "Paid Date", "Late", "Employer Rs", "Employee Rs", "Total Rs", "Status", "Disallowance"]
    for i in range(len(headers)):
        pdf.cell(w[i], 10, headers[i], 1, 0, 'C', True)
    pdf.ln()

    # Table Rows
    pdf.set_font("Arial", '', 8)
    pdf.set_text_color(0, 0, 0)
    for index, row in df.iterrows():
        pdf.cell(w[0], 8, str(row['Wage Month']), 1)
        pdf.cell(w[1], 8, str(row['Due Date']), 1, 0, 'C')
        pdf.cell(w[2], 8, str(row['Generated Date']), 1, 0, 'C')
        pdf.cell(w[3], 8, str(row['Late Days']), 1, 0, 'C')
        pdf.cell(w[4], 8, f"{row['Employer Share (INR)']:,.2f}", 1, 0, 'R')
        pdf.cell(w[5], 8, f"{row['Employee Share (INR)']:,.2f}", 1, 0, 'R')
        pdf.cell(w[6], 8, f"{row['Grand Total (INR)']:,.2f}", 1, 0, 'R')
        pdf.cell(w[7], 8, "Late" if row['Late Days'] > 0 else "On Time", 1, 0, 'C')
        pdf.cell(w[8], 8, f"{row['PF Disallowance (INR)']:,.2f}", 1, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# ---------------- MAIN APP ----------------
files = st.file_uploader("📂 DROP PF CHALLAN PDFs HERE", type="pdf", accept_multiple_files=True)
run_audit = st.button("🚀 INITIATE SYSTEM AUDIT")

if files and run_audit:
    all_rows = []
    for f in files:
        with pdfplumber.open(f) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            blocks = re.split(r"(Dues for the wage month of\s*[A-Za-z]+\s*[0-9]{4})", text, flags=re.I)
            for i in range(1, len(blocks), 2):
                content = blocks[i] + blocks[i+1]
                m_match = re.search(r"wage month of\s*([A-Za-z]+)\s*([0-9]{4})", content, re.I)
                wage_month = f"{m_match.group(1).title()} {m_match.group(2)}" if m_match else "Unknown"
                sys_date_str = safe_extract(r"system generated challan on\s*.*?(\d{2}-[A-Z]{3}-\d{4})", content).upper()
                due_dt = calculate_due_date(wage_month)
                emp_share = float(safe_extract(r"Employee'?s Share Of.*?([0-9,]{2,})", content).replace(",", ""))
                late_days = (datetime.strptime(sys_date_str, "%d-%b-%Y") - due_dt).days if due_dt and sys_date_str != "0" else 0
                
                all_rows.append({
                    "Wage Month": wage_month, "Due Date": due_dt.strftime("%d-%b-%Y") if due_dt else "N/A",
                    "Generated Date": sys_date_str, "Late Days": max(0, late_days),
                    "Employer Share (INR)": float(safe_extract(r"Employer'?s Share Of.*?([0-9,]{2,})", content).replace(",", "")),
                    "Employee Share (INR)": emp_share, "PF Disallowance (INR)": emp_share if late_days > 0 else 0.0,
                    "Grand Total (INR)": float(safe_extract(r"Grand Total.*?([0-9,]{2,})", content).replace(",", ""))
                })

    if all_rows:
        df = pd.DataFrame(all_rows)
        st.markdown("### 📊 STATUTORY DASHBOARD")
        d1, d2, d3 = st.columns(3)
        total_pf = df['Grand Total (INR)'].sum()
        total_dis = df['PF Disallowance (INR)'].sum()
        d1.metric("TOTAL PF AUDITED", f"INR {total_pf:,.2f}")
        d2.metric("TAX DISALLOWANCE", f"INR {total_dis:,.2f}", delta_color="inverse")
        d3.metric("LATE FILINGS", len(df[df['Late Days'] > 0]))

        st.markdown("---")
        pdf_data = generate_pdf_summary(df, total_pf, total_dis, len(df[df['Late Days'] > 0]))
        st.download_button("📜 DOWNLOAD PDF AUDIT TRAIL", pdf_data, "PF_Audit_Trail.pdf", "application/pdf")
        st.dataframe(df, use_container_width=True)

st.caption("© 2026 | Enterprise Auditor Pro | Developed by Abhishek Jakkula")
