import streamlit as st
import engine
from datetime import datetime

# UI Config
st.set_page_config(page_title="Evolution Machine", page_icon="⚡", layout="wide")

# Fetch via Engine (Uses Streamlit's cache wrapper)
@st.cache_data(ttl=60)
def get_cached_data():
    return engine.fetch_and_process(st.secrets["gcp_service_account"])

df, metrics, workouts_today = get_cached_data()

# --- RENDER HUD ---
st.title("⚡ FITNESS EVOLUTION MACHINE")
if not df.empty:
    from render.render import render_summary
    img = render_summary(df, metrics, workouts_today)
    st.image(img, width='stretch')
else:
    st.info("Awaiting Biometric Uplink...")

# --- INPUT TERMINAL ---
with st.sidebar:
    st.title("📟 INPUT TERMINAL")
    # (Keep your existing st.form logic here for appending rows)
    # Just call st.cache_data.clear() and st.rerun() after sync.
