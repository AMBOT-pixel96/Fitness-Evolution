import streamlit as st
import engine
from datetime import datetime

# UI Config - Focused & Clean
st.set_page_config(page_title="Evolution Machine", page_icon="⚡", layout="wide")

# Fetch via Engine
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

# Sidebar is now empty/hidden by default in Streamlit or used for simple info
st.sidebar.markdown("### SYSTEM: ONLINE")
st.sidebar.caption(f"Last Sync: {datetime.now().strftime('%H:%M:%S')}")
