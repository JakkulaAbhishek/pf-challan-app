import streamlit as st
import pdfplumber
import re
import pandas as pd
from datetime import datetime
from openpyxl.styles import Font, Alignment, PatternFill
from io import BytesIO
import math

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="PF Challan AI Auditor", layout="wide")

# ---------------- UI THEME (Consistent with CA Tools) ----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    .stApp { background: #0f172a; color: #f8fafc; }
    
    .header-title {
        background: linear-gradient(90deg, #38bdf8, #818cf8);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.8rem; text-align: center; margin-bottom: 0px;
    }
    .quote {
        background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 25px;
        color: #facc15; font-style: italic;
    }
    .stButton>button {
        background: linear-gradient(90deg, #2563eb, #0ea5e9);
        color: white !important; border: none; border-radius: 12px;
        font-weight: 800; height: 48px; width: 100%; transition: 0.3s;
    }
    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown('<div class="header-title">📊 PF CHALLAN AI AUDITOR</div>', unsafe_allow_html=True)
st.markdown("""
<div class="quote">
    "उद्धरेदात्मनाऽत्मानं नात्मानमवसादयेत्। आत्मैव ह्यात्मनो बन्धुरात्मैव रिपुरात्मनः॥" <br>
    <span style="font-size: 0.9rem; color: #94a3b8;">Elevate yourself by your own mind. Developed by Abhishek Jakkula</span>
</div>
""", unsafe_allow_html=True)

# ---------------- CORE HELPERS ----------------

def safe(pattern, text):
    m = re.search(pattern, text, re.I | re.S)
    return m.group(1).strip() if m else "0"

def normalize_month(block):
    m = re.search(r"Dues for the wage month of\s*([A-Za-z]+)\s*([0-9]{4})", block, re.I)
    return f"{m.group(1).title()} {m.group(2)}" if m else ""

def system_date(block):
    res = safe(r"system generated challan on\s*.*?(\d{2}-[A-Z]{3}-\d{4})", block)
    return res.upper()

def calculate_due_date(wage_month_str):
    try:
        b = datetime.strptime(wage_month_str, "%B %Y")
        # Due date is 15th of the next month
        next_month = b.month % 12 + 1
        year = b.year + (1 if b.month == 12 else 0)
        return datetime(year, next_month, 15)
    except: return None

# ---------------- EXCEL EXPORTER ----------------
def to_excel_formatted(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='PF_Audit_Report')
        workbook = writer.book
        worksheet = writer.sheets['PF_Audit_Report']
        
        # Header Styling
        header_fill = PatternFill(start_color="1e293b", end_color="1e293b", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        for cell in worksheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            
        # Auto-Width Logic
        for col in worksheet.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try: max_length = max(max_length, len(str(cell.value)))
                except: pass
            worksheet.column_dimensions[column].width = max_length + 3
    return output.getvalue()

# ---------------- MAIN APP ----------------
files = st.file_uploader("📂 Upload PF Challan PDFs", type="pdf", accept_multiple_files=True)

if files:
    if st.button("🚀 PROCESS & AUDIT CHALLANS"):
        all_data = []
        for f in files:
            with pdfplumber.open(f) as pdf:
                text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                
            # Split blocks
            blocks = re.split(r"(Dues for the wage month of\s*[A-Za-z]+\s*[0-9]{4})", text, flags=re.I)
            for i in range(1, len(blocks), 2):
                content = blocks[i] + blocks[i+1]
                wage_month = normalize_month(content)
                gen_date_str = system_date(content)
                
                # Payment Status Logic
                due_dt = calculate_due_date(wage_month)
                status = "On Time ✅"
                if due_dt and gen_date_str != "0":
                    try:
                        gen_dt = datetime.strptime(gen_date_str, "%d-%B-%Y")
                        if gen_dt > due_dt:
                            status = "Late Payment ⚠️"
                    except: pass

                all_data.append({
                    "Wage Month": wage_month,
                    "Due Date": due_dt.strftime("%d-%b-%Y") if due_dt else "Unknown",
                    "Generated Date": gen_date_str,
                    "Payment Status": status,
                    "Admin Charges": float(safe(r"Administration Charges.*?([0-9,]{2,})", content).replace(",","")),
                    "Employer Share": float(safe(r"Employer'?s Share Of.*?([0-9,]{2,})", content).replace(",","")),
                    "Employee Share": float(safe(r"Employee'?s Share Of.*?([0-9,]{2,})", content).replace(",","")),
                    "Grand Total": float(safe(r"Grand Total.*?([0-9,]{2,})", content).replace(",","")),
                    "Source": f.name
                })

        if all_data:
            df = pd.DataFrame(all_data)
            
            # Insights
            st.markdown("### 📊 Auditor Insights")
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Challans", len(df))
            m2.metric("Total PF Value", f"₹{df['Grand Total'].sum():,.2f}")
            late_count = len(df[df['Payment Status'] == "Late Payment ⚠️"])
            m3.metric("Late Filings", late_count, delta=late_count, delta_color="inverse")

            st.dataframe(df, use_container_width=True)
            
            st.download_button(
                "📥 Download Professional Excel Audit",
                data=to_excel_formatted(df),
                file_name=f"PF_Audit_{datetime.now().strftime('%Y%m%d')}.xlsx"
            )
        else:
            st.error("❌ No PF data detected. Please check your PDF format.")

st.caption("⚙️ Auditor Tool developed by Abhishek Jakkula")
