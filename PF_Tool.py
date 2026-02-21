import streamlit as st
import pdfplumber
import re
import pandas as pd
from datetime import datetime
from openpyxl.styles import Font, Alignment, PatternFill
from io import BytesIO
import plotly.express as px

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Abhishek Jakkula | Professional Suite", layout="wide")

# ---------------- ULTRA STYLISH UI THEME ----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    
    /* Main Background */
    .stApp { background: radial-gradient(circle at top, #0f172a, #020617); color: #f8fafc; }

    /* Header Styling */
    .header-container {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.8));
        padding: 30px; border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(12px); text-align: center; margin-bottom: 30px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
    }
    .main-title {
        background: linear-gradient(90deg, #38bdf8, #818cf8, #34d399);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 3.5rem; line-height: 1.2;
    }
    .branding-sub { color: #94a3b8; font-size: 1.1rem; letter-spacing: 1px; margin-top: 10px; }
    .krishna-blessing { color: #facc15; font-style: italic; margin-top: 15px; font-size: 1rem; }

    /* Component Styling */
    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 20px; backdrop-filter: blur(10px);
    }
    [data-testid="stFileUploader"] {
        background: rgba(30, 41, 59, 0.3) !important; border-radius: 20px !important;
        border: 2px dashed rgba(56, 189, 248, 0.3) !important;
    }
    .stButton>button {
        background: linear-gradient(90deg, #2563eb, #0ea5e9);
        color: white !important; border: none; border-radius: 12px;
        font-weight: 800; height: 55px; width: 100%; transition: 0.4s;
        box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2);
    }
    .stButton>button:hover { transform: translateY(-3px); box-shadow: 0 15px 30px rgba(37, 99, 235, 0.4); }
    
    /* Table Styling */
    [data-testid="stDataFrame"] { border-radius: 20px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ---------------- BRANDED HEADER ----------------
st.markdown("""
<div class="header-container">
    <div class="main-title">AUTOMATION COMMAND CENTER</div>
    <div class="branding-sub">PREMIUM COMPLIANCE TOOLS BY <b>ABHISHEK JAKKULA</b></div>
    <div class="krishna-blessing">🌸 Lord Krishna Blessings: कर्मण्येवाधिकारस्ते मा फलेषु कदाचन 🌸</div>
    <div style="color: #38bdf8; font-size: 0.9rem; margin-top: 5px;">jakkulaabhishek5@gmail.com</div>
</div>
""", unsafe_allow_html=True)

# ---------------- APP SELECTOR ----------------
tool_choice = st.radio("Select Tool to Launch:", ["PF AI Auditor", "TDS Challan AI Auditor"], horizontal=True)

if tool_choice == "PF AI Auditor":
    st.markdown("### 📊 PF Challan Processing")
    # ... [Insert the Improved PF Code Logic here] ...
    st.info("Upload PF Challan PDFs to begin the automated audit.")

elif tool_choice == "TDS Challan AI Auditor":
    st.markdown("### 🕉️ Statutory TDS Audit")
    # ... [Insert the Improved TDS Code Logic here] ...
    st.info("Upload TDS Challan PDFs for IT Act 2026 Statutory Check.")

# ---------------- FOOTER ----------------
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align: center; color: #64748b; font-size: 0.85rem; padding-bottom: 20px;">
    © {datetime.now().year} | Designed & Developed by Abhishek Jakkula | All Rights Reserved.
</div>
""", unsafe_allow_html=True)
