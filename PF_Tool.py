import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO
from openpyxl.styles import Font, Alignment, PatternFill
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

# ---------------- UI CONFIG ----------------
st.set_page_config(page_title="TDS Challan AI Auditor", layout="wide")

# ----------- ULTRA STYLISH CSS -----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    .stApp { background: radial-gradient(circle at top, #0f172a, #020617); color: #f8fafc; }
    .header-title {
        background: linear-gradient(90deg, #38bdf8, #22c55e);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 3rem; text-align: center; margin-bottom: 10px;
    }
    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 16px; backdrop-filter: blur(10px);
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-title">🕉️ TDS CHALLAN AI AUDITOR</div>', unsafe_allow_html=True)

# ----------- IT ACT STATUTORY DATA -----------
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

files = st.file_uploader("📄 Upload TDS Challan PDFs", type="pdf", accept_multiple_files=True)

def to_excel_final(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="TDS_Audit")
        ws = writer.sheets["TDS_Audit"]
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1e293b", end_color="1e293b", fill_type="solid")
        for cell in ws[1]:
            cell.font, cell.fill, cell.alignment = header_font, header_fill, Alignment(horizontal="center")
        for col in ws.columns:
            max_len = max([len(str(cell.value)) for cell in col])
            ws.column_dimensions[col[0].column_letter].width = max_len + 3
    return buf.getvalue()

def extract_tds_data(text):
    challans = re.split(r"Challan Receipt|Taxpayer Counterfoil", text, flags=re.IGNORECASE)
    rows = []
    for ch in challans:
        ch = re.sub(r'[^\x00-\x7F]+', ' ', ch)
        if not re.search(r"Challan No|CIN|BSR", ch, re.IGNORECASE): continue
        def get_v(p):
            m = re.search(p, ch, re.IGNORECASE)
            return m.group(1).replace(",", "").strip() if m else "0"
        
        dep_date_str = get_v(r"Date of Deposit\s*[:\-]?\s*(\d{2}-[A-Za-z]{3}-\d{4})")
        if dep_date_str == "0": continue
        dep_date = datetime.strptime(dep_date_str, "%d-%b-%Y")
        
        nature_code = get_v(r"Section\s*[:\-]?\s*(\w+)")
        nature_desc = SECTION_DATA.get(nature_code.upper(), nature_code)
        
        rows.append({
            "Financial Year": get_v(r"Financial Year\s*[:\-]?\s*([\d\-]+)"),
            "Section": nature_desc,
            "Deposit Date": dep_date.strftime("%d-%b-%Y"),
            "Status": "On Time ✅" if (dep_date - (dep_date - relativedelta(months=1)).replace(day=15)).days <= 0 else "Late ⚠️",
            "Tax (₹)": float(get_v(r"A\s*Tax\s*₹?\s*([\d,.]+)")),
            "Interest (₹)": float(get_v(r"D\s*Interest\s*₹?\s*([\d,.]+)")),
            "Total Paid (₹)": float(get_v(r"Total\s*.*?₹?\s*([\d,.]+)")),
            "Challan No": get_v(r"Challan No\s*[:\-]?\s*(\d+)")
        })
    return rows

if files:
    all_data = []
    for f in files:
        with pdfplumber.open(f) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            all_data += extract_tds_data(text)
    if all_data:
        df = pd.DataFrame(all_data)
        st.metric("Total Tax Collected", f"₹{df['Tax (₹)'].sum():,.2f}")
        st.plotly_chart(px.pie(df, names='Section', values='Tax (₹)', hole=0.4), use_container_width=True)
        st.download_button("📥 Download Excel Report", to_excel_final(df), "TDS_Statutory_Audit.xlsx")
        st.dataframe(df, use_container_width=True)
