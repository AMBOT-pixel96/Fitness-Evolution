import streamlit as st
import engine
import reports
from datetime import datetime, timedelta
import pandas as pd
from render.render import render_summary

st.set_page_config(page_title="Genius Protocol", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: radial-gradient(circle, #001A2E 0%, #050A0E 100%); }
    h1 { color: #FFFFFF !important; font-family: 'Helvetica', sans-serif; font-weight: 800; letter-spacing: -1px; }
    .stButton>button { 
        background-color: transparent; 
        color: #00F2FF; 
        border: 1px solid #00F2FF; 
        font-family: 'Courier New', monospace;
        letter-spacing: 2px;
    }
    .stButton>button:hover { background-color: #00F2FF; color: #050A0E; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def get_cached_data():
    return engine.fetch_and_process(st.secrets["gcp_service_account"])

df, metrics, workouts_today = get_cached_data()

st.title("THE GENIUS PROTOCOL")

if not df.empty:
    img = render_summary(df, metrics, workouts_today)
    st.image(img, width='stretch')

st.divider()
st.subheader("📑 GENERATE BIOMETRIC DOSSIER")

col1, col2 = st.columns(2)
with col1:
    r_date = st.date_input("Target Date", datetime.now())
    if st.button("GENERATE DAILY DOSSIER"):
        pdf_bytes = reports.generate_pdf_report(df, metrics, r_date, r_date)
        st.download_button(label="📥 DOWNLOAD PDF", data=pdf_bytes, file_name=f"Dossier_{r_date}.pdf", mime="application/pdf")

with col2:
    d_range = st.date_input("Select Analysis Range", [datetime.now() - timedelta(days=7), datetime.now()])
    if st.button("GENERATE TACTICAL AUDIT") and len(d_range) == 2:
        pdf_bytes = reports.generate_pdf_report(df, metrics, d_range[0], d_range[1])
        st.download_button(label="📥 DOWNLOAD PDF", data=pdf_bytes, file_name="Tactical_Audit.pdf", mime="application/pdf")

st.sidebar.markdown("### PROTOCOL: ACTIVE")
st.sidebar.caption(f"Last Intelligence Sync: {datetime.now().strftime('%H:%M:%S')}")
