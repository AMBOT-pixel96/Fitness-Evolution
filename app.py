import streamlit as st
import engine
import reports
from datetime import datetime, timedelta
import pandas as pd
from render.render import render_summary

# ================== PAGE CONFIG ==================
st.set_page_config(page_title="Evolution Machine", page_icon="⚡", layout="wide")

# Custom CSS for the Stark-Industries Vibe
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: radial-gradient(circle, #001A2E 0%, #050A0E 100%); }
    h1 { color: #00F2FF !important; font-family: 'Courier New', monospace; letter-spacing: 2px; }
    .stButton>button { 
        background-color: #00F2FF; 
        color: #050A0E; 
        font-weight: bold; 
        border-radius: 5px; 
        width: 100%;
        border: none;
        padding: 0.5rem;
    }
    .stButton>button:hover {
        background-color: #FFFFFF;
        color: #050A0E;
    }
</style>
""", unsafe_allow_html=True)

# ================== DATA FETCHING ==================
@st.cache_data(ttl=60)
def get_cached_data():
    # Pulls from engine.py which handles the heavy lifting
    return engine.fetch_and_process(st.secrets["gcp_service_account"])

try:
    df, metrics, workouts_today = get_cached_data()
except Exception as e:
    st.error(f"Intelligence Sync Failed: {e}")
    st.stop()

# ================== RENDER HUD ==================
st.title("⚡ FITNESS EVOLUTION MACHINE")

if not df.empty:
    try:
        # Standardize weight for the graph renderer
        df["weight"] = pd.to_numeric(df["weight"], errors='coerce').ffill().fillna(metrics['weight'])
        img = render_summary(df, metrics, workouts_today)
        st.image(img, width='stretch')
    except Exception as e:
        st.error(f"HUD Rendering Offline: {e}")
else:
    st.info("⚡ System Online: Awaiting Biometric Uplink from Cloud Terminal.")

# ================== DOSSIER GENERATION CENTER ==================
st.divider()
st.subheader("📑 BIOMETRIC DOSSIER GENERATOR")
st.caption("Generate high-fidelity PDF reports for nutritional audit and physiological tracking.")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Executive Summary (Daily)")
    report_date = st.date_input("Target Date", datetime.now())
    if st.button("PREPARE DAILY PDF"):
        with st.spinner("Compiling Dossier..."):
            pdf_bytes = reports.generate_pdf_report(df, metrics, report_date, report_date)
            st.success("✅ Daily Dossier Compiled.")
            st.download_button(
                label="📥 DOWNLOAD DAILY REPORT",
                data=pdf_bytes,
                file_name=f"Daily_Dossier_{report_date.strftime('%d_%b_%y')}.pdf",
                mime="application/pdf"
            )

with col2:
    st.markdown("### Tactical Audit (Range)")
    # Default to last 7 days
    d_range = st.date_input("Select Analysis Range", [datetime.now() - timedelta(days=7), datetime.now()])
    
    if st.button("PREPARE RANGE PDF"):
        if len(d_range) == 2:
            with st.spinner("Analyzing Trends..."):
                pdf_bytes = reports.generate_pdf_report(df, metrics, d_range[0], d_range[1])
                st.success("✅ Tactical Audit Compiled.")
                st.download_button(
                    label="📥 DOWNLOAD RANGE REPORT",
                    data=pdf_bytes,
                    file_name=f"Tactical_Audit_{d_range[0].strftime('%d%b')}_to_{d_range[1].strftime('%d%b')}.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("Please select both a Start and End date for the range.")

# ================== SYSTEM FOOTER ==================
st.sidebar.markdown("### SYSTEM: NOMINAL")
st.sidebar.caption(f"Last Sync: {datetime.now().strftime('%H:%M:%S')}")
st.sidebar.divider()
st.sidebar.info("""
**A.R.V.I.S. Protocol**
- Data source: Google Cloud
- Engine: V3.4 'Dossier'
- Status: Physique Ascending
""")

if st.sidebar.button("Force Clear Cache"):
    st.cache_data.clear()
    st.rerun()
