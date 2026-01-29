import streamlit as st
import pdfplumber
import re
import pandas as pd
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import Font
import tempfile, os

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="PF Challan Automation Tool", layout="centered")

# ---------------- UI THEME ----------------
st.markdown("""
<style>
.stApp {background: radial-gradient(circle at top, #020617, #000000); color:white;}
.block-container {max-width:950px;padding:2.5rem;}
.header {
background:linear-gradient(135deg,#020617,#0f172a);
padding:28px;border-radius:20px;
box-shadow:0 0 40px rgba(56,189,248,0.25);
margin-bottom:28px;border:1px solid rgba(148,163,184,0.15);
}
.title{font-size:38px;font-weight:900;}
.sub{color:#cbd5e1;}
.krishna{color:#38bdf8;font-weight:600;margin-top:8px;}
.quote{color:#facc15;font-size:18px;font-style:italic;}
.brand{color:#38bdf8;margin-top:8px;}
.stButton>button{
background:linear-gradient(135deg,#2563eb,#0ea5e9);
border:none;border-radius:12px;font-weight:800;height:48px;
box-shadow:0 0 25px rgba(14,165,233,.7);}
.stButton>button:hover{transform:scale(1.03);}
label,p{color:white!important;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header">
<div class="title">📊 PF Challan Automation Tool</div>
<div class="sub">Fast • Accurate • Audit-Ready PF Challan Processing</div>
<div class="krishna">🌸 Lord Krishna Blessings</div>
<div class="quote">कर्मण्येवाधिकारस्ते मा फलेषु कदाचन</div>
<div class="brand">Tool developed by – Abhishek Jakkula</div>
</div>
""", unsafe_allow_html=True)

# ---------------- CORE HELPERS ----------------

def safe(pattern, text):
    m = re.search(pattern, text, re.I | re.S)
    return m.group(1).strip() if m else ""

def amount(x):
    try: return float(x.replace(",",""))
    except: return ""

def normalize_month(block):
    m = re.search(r"Dues for the wage month of\s*([A-Za-z]+)\s*([0-9]{4})", block, re.I)
    if m: return f"{m.group(1).title()} {m.group(2)}"
    return ""

def system_date(block):
    return safe(r"system generated challan on\s*.*?(\d{2}-[A-Z]{3}-\d{4})", block).upper()

def due_date(month):
    try:
        b=datetime.strptime(month,"%B %Y")
        y=b.year+(1 if b.month==12 else 0)
        m=1 if b.month==12 else b.month+1
        return datetime(y,m,15).strftime("%d-%b-%Y").upper()
    except: return ""

def split_challans(text):
    text=re.sub(r"\s+"," ",text)
    parts=re.split(r"(Dues for the wage month of\s*[A-Za-z]+\s*[0-9]{4})",text,flags=re.I)
    blocks=[]
    for i in range(1,len(parts),2):
        blocks.append(parts[i]+parts[i+1])
    return blocks

# ---------------- PF PARSER ----------------

def parse_pf(block):

    wage = normalize_month(block)

    return {
        "Wage Month": wage,
        "Due Date": due_date(wage),
        "System Generated Date": system_date(block),
        "Administration Charges": safe(r"Administration Charges.*?([0-9,]{2,})", block),
        "Employer's Share": safe(r"Employer'?s Share Of.*?([0-9,]{2,})", block),
        "Employee's Share": safe(r"Employee'?s Share Of.*?([0-9,]{2,})", block),
        "Employee Share Disallowance": "0",
        "Grand Total": safe(r"Grand Total.*?([0-9,]{2,})", block)
    }

# ---------------- EXCEL HEADER ----------------

def add_title(file):
    wb=load_workbook(file)
    ws=wb.active
    ws.insert_rows(1,2)
    ws["A1"]="Tool developed by - Abhishek Jakkula"
    ws["A1"].font=Font(bold=True)
    wb.save(file)

# ---------------- APP ----------------

st.markdown("### 📂 Upload PF Challan PDFs")
files = st.file_uploader("", type="pdf", accept_multiple_files=True)

if files and st.button("🚀 Process Challans"):

    data=[]

    with st.spinner("Reading PF challans..."):

        for f in files:
            with tempfile.NamedTemporaryFile(delete=False,suffix=".pdf") as tmp:
                tmp.write(f.read())
                path=tmp.name

            text=""
            with pdfplumber.open(path) as pdf:
                for p in pdf.pages:
                    t=p.extract_text()
                    if t: text+=t+"\n"

            for block in split_challans(text):
                row=parse_pf(block)
                row["Source File"]=f.name
                if row["Wage Month"]:
                    data.append(row)

            os.remove(path)

    if data:

        df=pd.DataFrame(data)

        cols=["Wage Month","Due Date","System Generated Date",
              "Administration Charges","Employer's Share","Employee's Share",
              "Employee Share Disallowance","Grand Total","Source File"]

        df=df[cols].reset_index(drop=True)

        out=f"PF_Monthwise_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(out,index=False)
        add_title(out)

        st.success("✅ PF challan report generated successfully")
        st.dataframe(df,use_container_width=True)

        with open(out,"rb") as f:
            st.download_button("📥 Download Excel",f,file_name=out)

    else:
        st.error("❌ No PF challan data detected.")
