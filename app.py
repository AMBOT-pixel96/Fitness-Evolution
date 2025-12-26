import streamlit as st
import engine
import reports
from datetime import datetime, timedelta
import pandas as pd

# ================== PAGE CONFIG ==================
st.set_page_config(page_title="Evolution Machine", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: radial-gradient(circle, #001A2E 0%, #050A0E 100%); }
    h1 { color: #00F2FF !important; font-family: 'Courier New', monospace; letter-spacing: 2px; }
    .stButton>button { background-color: #00F2FF; color: #050A0E; font-weight: bold; border-radius: 5px; width: 100%; }
</style>
""", unsafe_allow_html=True)

# Fetch Data
@st.cache_data(ttl=60)
def get_cached_data():
    return engine.fetch_and_process(st.secrets["gcp_service_account"])

df, metrics, workouts_today = get_cached_data()

# ================== RENDER HUD ==================
st.title("⚡ FITNESS EVOLUTION MACHINE")

if not df.empty:
    from render.render import render_summary
    img = render_summary(df, metrics, workouts_today)
    st.image(img, width='stretch')
else:
    st.info("Awaiting Biometric Uplink...")

# ================== DOSSIER GENERATION CENTER ==================
st.divider()
st.subheader("📑 BIOMETRIC DOSSIER GENERATOR")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Executive Summary (Daily)")
    report_date = st.date_input("Target Date", datetime.now())
    if st.button("PREPARE DAILY PDF"):
        pdf_bytes = reports.generate_pdf_report(df, metrics, report_date, report_date)
        st.download_button(
            label="📥 DOWNLOAD DAILY DOSSIER",
            data=pdf_bytes,
            file_name=f"Daily_Dossier_{report_date}.pdf",
            mime="application/pdf"
        )

with col2:
    st.markdown("### Tactical Audit (Range)")
    d_range = st.date_input("Select Range", [datetime.now() - timedelta(days=7), datetime.now()])
    if st.button("PREPARE RANGE PDF") and len(d_range) == 2:
        pdf_bytes = reports.generate_pdf_report(df, metrics, d_range[0], d_range[1])
        st.download_button(
            label="📥 DOWNLOAD RANGE DOSSIER",
            data=pdf_bytes,
            file_name=f"Tactical_Audit_{d_range[0]}_to_{d_range[1]}.pdf",
            mime="application/pdf"
        )

# Sidebar System Info
st.sidebar.markdown("### SYSTEM: ONLINE")
st.sidebar.caption(f"Last Intelligence Sync: {datetime.now().strftime('%H:%M:%S')}")
st.sidebar.divider()
st.sidebar.info("PDF Reports utilize Industry-Standard Biometric Analytics.")
