import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO
from openpyxl.styles import Font, Alignment, PatternFill
from datetime import datetime
import plotly.express as px

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="PF AI Command Center", layout="wide")

# ---------------- ULTRA STYLISH UI THEME ----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    .stApp { background: radial-gradient(circle at top, #0f172a, #020617); color: #f8fafc; }

    /* Glassmorphism Header */
    .header-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.8));
        padding: 40px; border-radius: 28px; border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(12px); text-align: center; margin-bottom: 40px;
        box-shadow: 0 25px 50px rgba(0, 0, 0, 0.4);
    }
    .main-title {
        background: linear-gradient(90deg, #38bdf8, #818cf8, #34d399);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 3.8rem; line-height: 1.1;
    }
    .branding { color: #94a3b8; font-size: 1.2rem; letter-spacing: 2px; margin-top: 15px; font-weight: 600; }
    .blessing { color: #facc15; font-style: italic; margin-top: 20px; font-size: 1.1rem; }

    /* Command Center Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #2563eb, #0ea5e9);
        color: white !important; border: none; border-radius: 14px;
        font-weight: 800; height: 60px; width: 100%; transition: 0.4s;
        box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3); font-size: 1.1rem;
    }
    .stButton>button:hover { transform: translateY(-3px); box-shadow: 0 20px 40px rgba(37, 99, 235, 0.5); }

    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 25px; border-radius: 24px; backdrop-filter: blur(15px);
    }
    
    [data-testid="stFileUploader"] {
        background: rgba(30, 41, 59, 0.3) !important; border-radius: 20px !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- BRANDED HEADER ----------------
st.markdown("""
<div class="header-card">
    <div class="main-title">PF CHALLAN AI AUDITOR</div>
    <div class="branding">COMPLIANCE AUTOMATION BY <b>ABHISHEK JAKKULA</b></div>
    <div class="blessing">🌸 Lord Krishna Blessings: कर्मण्येवाधिकारस्ते मा फलेषु कदाचन 🌸</div>
</div>
""", unsafe_allow_html=True)

# ---------------- CORE HELPERS ----------------

def safe_extract(pattern, text):
    m = re.search(pattern, text, re.I | re.S)
    return m.group(1).strip() if m else "0"

def calculate_due_date(wage_month_str):
    try:
        # Expected: "Month Year" e.g., "January 2024"
        parts = wage_month_str.split()
        month_dt = datetime.strptime(parts[0], "%B")
        year = int(parts[1])
        # Due date is 15th of the NEXT month
        next_m = month_dt.month % 12 + 1
        next_y = year + (1 if month_dt.month == 12 else 0)
        return datetime(next_y, next_m, 15)
    except: return None

# ---------------- COMMAND CENTER ----------------
col_file, col_btn = st.columns([2, 1])
with col_file:
    files = st.file_uploader("📂 DROP PF CHALLAN PDFs HERE", type="pdf", accept_multiple_files=True)
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    run_audit = st.button("🚀 INITIATE PF AUDIT")

# ---------------- EXTRACTION ENGINE ----------------
if files and run_audit:
    all_rows = []
    with st.spinner("Decoding PF Challan structures..."):
        for f in files:
            with pdfplumber.open(f) as pdf:
                text = ""
                for p in pdf.pages:
                    if p.extract_text(): text += p.extract_text() + "\n"
                
                # Split text into individual challan blocks based on wage month marker
                blocks = re.split(r"(Dues for the wage month of\s*[A-Za-z]+\s*[0-9]{4})", text, flags=re.I)
                
                for i in range(1, len(blocks), 2):
                    content = blocks[i] + blocks[i+1]
                    
                    # Extract Month & Year
                    m_match = re.search(r"wage month of\s*([A-Za-z]+)\s*([0-9]{4})", content, re.I)
                    wage_month = f"{m_match.group(1).title()} {m_match.group(2)}" if m_match else "Unknown"
                    
                    # System Gen Date
                    sys_date_str = safe_extract(r"system generated challan on\s*.*?(\d{2}-[A-Z]{3}-\d{4})", content).upper()
                    
                    # Due Date & Status Logic
                    due_dt = calculate_due_date(wage_month)
                    status = "On Time ✅"
                    if due_dt and sys_date_str != "0":
                        try:
                            gen_dt = datetime.strptime(sys_date_str, "%d-%b-%Y")
                            if gen_dt > due_dt: status = "Late Payment ⚠️"
                        except: pass

                    all_rows.append({
                        "Wage Month": wage_month,
                        "Due Date": due_dt.strftime("%d-%b-%Y") if due_dt else "Unknown",
                        "Generated Date": sys_date_str,
                        "Payment Status": status,
                        "Admin Charges (₹)": float(safe_extract(r"Administration Charges.*?([0-9,]{2,})", content).replace(",", "")),
                        "Employer Share (₹)": float(safe_extract(r"Employer'?s Share Of.*?([0-9,]{2,})", content).replace(",", "")),
                        "Employee Share (₹)": float(safe_extract(r"Employee'?s Share Of.*?([0-9,]{2,})", content).replace(",", "")),
                        "Grand Total (₹)": float(safe_extract(r"Grand Total.*?([0-9,]{2,})", content).replace(",", "")),
                        "Source File": f.name
                    })

    if all_rows:
        df = pd.DataFrame(all_rows)
        
        # Dashboard Metrics
        st.markdown("### 📊 AUDIT COMMAND DASHBOARD")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Challans", len(df))
        m2.metric("Total PF Value", f"₹{df['Grand Total (₹)'].sum():,.2f}")
        late_count = len(df[df['Payment Status'] == "Late Payment ⚠️"])
        m3.metric("Late Filings", late_count, delta=late_count, delta_color="inverse")

        # Visual Analytics
        st.markdown("---")
        c_chart, c_dl = st.columns([1.5, 1])
        with c_chart:
            fig = px.bar(df, x='Wage Month', y=['Employer Share (₹)', 'Employee Share (₹)'], 
                         title="Month-wise Contribution Breakdown", barmode='group')
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig, use_container_width=True)
        
        with c_dl:
            st.markdown("#### 📥 SECURE REPORT EXPORT")
            st.info("Report is processed with auto-widening and bold headers.")
            
            # Professional Excel Logic (Fixing Gaps)
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="PF_Audit")
                ws = writer.sheets["PF_Audit"]
                
                # Styling
                header_fill = PatternFill(start_color="1e293b", end_color="1e293b", fill_type="solid")
                header_font = Font(bold=True, color="FFFFFF")
                for cell in ws[1]:
                    cell.font, cell.fill, cell.alignment = header_font, header_fill, Alignment(horizontal="center")
                
                # Auto-width columns
                for col in ws.columns:
                    max_len = max([len(str(cell.value)) for cell in col])
                    ws.column_dimensions[col[0].column_letter].width = max_len + 4

            st.download_button("🚀 DOWNLOAD PROFESSIONAL EXCEL AUDIT", data=output.getvalue(), file_name=f"PF_Audit_Report_{datetime.now().year}.xlsx")

        st.dataframe(df, use_container_width=True)
    else:
        st.error("❌ NO PF DATA DETECTED: Ensure the PDFs are original TRACES/EPFO digital challans.")

# ---------------- FOOTER ----------------
st.markdown("<br><hr>", unsafe_allow_html=True)
st.caption(f"© {datetime.now().year} | PRO AUDITOR SUITE | Developed by Abhishek Jakkula | jakkulaabhishek5@gmail.com")
