import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO
from openpyxl.styles import Font, Alignment, PatternFill
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import plotly.express as px

# ---------------- UI CONFIG ----------------
st.set_page_config(page_title="Abhishek Jakkula | TDS AI Auditor", layout="wide")

# ----------- ULTRA STYLISH GLASS-MORPHISM CSS -----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    .stApp { background: radial-gradient(circle at top, #0f172a, #020617); color: #f8fafc; }

    .header-container {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.8));
        padding: 30px; border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(12px); text-align: center; margin-bottom: 30px;
    }
    .main-title {
        background: linear-gradient(90deg, #38bdf8, #34d399);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 3.5rem;
    }
    .branding-sub { color: #94a3b8; font-size: 1.1rem; letter-spacing: 1px; margin-top: 10px; }
    
    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 20px; backdrop-filter: blur(10px);
    }
    .stButton>button {
        background: linear-gradient(90deg, #10b981, #3b82f6);
        color: white !important; border: none; border-radius: 12px;
        font-weight: 800; height: 55px; width: 100%; transition: 0.4s;
        box-shadow: 0 10px 20px rgba(16, 185, 129, 0.2);
    }
    .stButton>button:hover { transform: translateY(-3px); box-shadow: 0 15px 30px rgba(16, 185, 129, 0.4); }
</style>
""", unsafe_allow_html=True)

# ---------------- BRANDED HEADER ----------------
st.markdown("""
<div class="header-container">
    <div class="main-title">🕉️ TDS CHALLAN AI AUDITOR</div>
    <div class="branding-sub">STATUTORY COMPLIANCE SUITE BY <b>ABHISHEK JAKKULA</b></div>
    <div style="color: #facc15; font-style: italic; margin-top: 15px;">🌸 Lord Krishna Blessings: कर्मण्येवाधिकारस्ते मा फलेषु कदाचन 🌸</div>
</div>
""", unsafe_allow_html=True)

# ----------- IT ACT STATUTORY RATES -----------
SECTION_DATA = {
    "94C": "194C - Contractor (1%/2%)",
    "94J": "194J - Professional (10%)",
    "194JB": "194JB - Prof. Special (2%)",
    "94I": "194I - Rent (10%)",
    "94H": "194H - Commission (5%)",
    "92B": "192 - Salary (As per Slab)",
    "94Q": "194Q - Goods Purchase (0.1%)",
    "94A": "194A - Interest (10%)"
}

# ----------- FILE UPLOAD & RUN BUTTON -----------
col_up, col_run = st.columns([2, 1])
with col_up:
    files = st.file_uploader("📂 Upload TDS Challan PDFs", type="pdf", accept_multiple_files=True)

# ----------- EXCEL EXPORTER ENGINE -----------
def to_excel_pro(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="TDS_Audit")
        ws = writer.sheets["TDS_Audit"]
        
        # Professional Header Styling
        header_fill = PatternFill(start_color="1e293b", end_color="1e293b", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for cell in ws[1]:
            cell.font, cell.fill, cell.alignment = header_font, header_fill, Alignment(horizontal="center")
        
        # Auto-Width and Numeric Formatting
        for col in ws.columns:
            max_len = 0
            column_letter = col[0].column_letter
            for cell in col:
                try: max_len = max(max_len, len(str(cell.value)))
                except: pass
                if isinstance(cell.value, (int, float)) and cell.row > 1:
                    cell.number_format = '#,##0.00'
            ws.column_dimensions[column_letter].width = max_len + 4
            
        ws.freeze_panes = "A2"
    return buf.getvalue()

# ----------- EXTRACTION ENGINE -----------
def extract_all(text):
    challans = re.split(r"Challan Receipt|Taxpayer Counterfoil|Income Tax", text, flags=re.IGNORECASE)
    rows = []

    for ch in challans:
        ch = re.sub(r'[^\x00-\x7F]+', ' ', ch) 
        if not re.search(r"Challan No|CIN|BSR|Amount", ch, re.IGNORECASE):
            continue

        def get_v(patterns):
            for p in patterns:
                m = re.search(p, ch, re.IGNORECASE)
                if m: return m.group(1).replace(",", "").strip()
            return "0"

        dep_date_str = get_v([r"Date of Deposit\s*[:\-]?\s*(\d{2}-[A-Za-z]{3}-\d{4})", r"Deposit Date\s*(\d{2}/\d{2}/\d{4})"])
        if dep_date_str == "0": continue
        
        try: dep_date = datetime.strptime(dep_date_str, "%d-%b-%Y")
        except:
            try: dep_date = datetime.strptime(dep_date_str, "%d/%m/%Y")
            except: continue

        nature_code = get_v([r"Nature of Payment\s*[:\-]?\s*(\w+)", r"Section\s*[:\-]?\s*(\w+)"]).upper()
        nature_desc = SECTION_DATA.get(nature_code, nature_code)

        tax = float(get_v([r"A\s*Tax\s*₹?\s*([\d,.]+)"]))
        interest = float(get_v([r"D\s*Interest\s*₹?\s*([\d,.]+)"]))
        total = float(get_v([r"Total\s*.*?₹?\s*([\d,.]+)"]))

        tds_month_date = dep_date - relativedelta(months=1)
        due_date = (tds_month_date + relativedelta(months=1)).replace(day=7)
        delay_days = max(0, (dep_date - due_date).days)

        rows.append({
            "Financial Year": get_v([r"Financial Year\s*[:\-]?\s*([\d\-]+)"]),
            "Statutory Section": nature_desc,
            "TDS Month": tds_month_date.strftime("%B"),
            "Deposit Date": dep_date.strftime("%d-%b-%Y"),
            "Status": "On Time ✅" if delay_days <= 0 else f"Late ({delay_days} days) ⚠️",
            "Tax (₹)": tax,
            "Interest (₹)": interest,
            "Total Paid (₹)": total,
            "Challan No": get_v([r"Challan No\s*[:\-]?\s*(\d+)"]),
            "BSR Code": get_v([r"BSR Code\s*[:\-]?\s*(\d+)"])
        })
    return rows

# ----------- MAIN EXECUTION -----------
with col_run:
    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("🚀 INITIATE AI AUDIT")

if files and run_btn:
    all_data = []
    for f in files:
        with pdfplumber.open(f) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            all_data += extract_all(text)

    if all_data:
        df = pd.DataFrame(all_data)
        
        st.markdown("### 📊 Auditor Command Dashboard")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Challans", len(df))
        m2.metric("Total Tax (₹)", f"{df['Tax (₹)'].sum():,.2f}")
        late_count = len(df[df['Status'].str.contains("Late")])
        m3.metric("Late Filings", late_count, delta=late_count, delta_color="inverse")

        st.markdown("---")
        c1, c2 = st.columns([1, 1])
        with c1:
            fig = px.pie(df, names='Statutory Section', values='Tax (₹)', 
                         title="Tax Allocation by Section", hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("#### 📥 Secure Report Export")
            st.info("The report is audit-ready with statutory rate labels and formatted values.")
            st.download_button("🚀 DOWNLOAD PROFESSIONAL EXCEL AUDIT", data=to_excel_pro(df), file_name=f"TDS_Audit_{datetime.now().strftime('%Y%m%d')}.xlsx")

        st.dataframe(df.style.format({"Tax (₹)": "{:,.2f}", "Total Paid (₹)": "{:,.2f}", "Interest (₹)": "{:,.2f}"}), use_container_width=True)
    else:
        st.error("❌ No valid patterns found. If this is a scanned PDF, please ensure you use an OCR-ready version.")

# ----------- FOOTER -----------
st.markdown("<br><hr>", unsafe_allow_html=True)
st.caption("⚙️ Statutory Auditor Pro | Developed by Abhishek Jakkula | jakkulaabhishek5@gmail.com")
