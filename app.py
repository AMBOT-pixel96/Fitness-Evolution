import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import os

from render.render import render_summary

# ================== PAGE CONFIG ==================
st.set_page_config(page_title="Evolution Machine", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: radial-gradient(circle, #001A2E 0%, #050A0E 100%); }
    .stMetric { border: 1px solid #1E3D52; background: #0A1926; padding: 20px; border-radius: 5px; }
    h1 { color: #00F2FF !important; font-family: 'Courier New', monospace; letter-spacing: 2px; }
    [data-testid="stSidebar"] { background-color: #050A0E; border-right: 1px solid #1E3D52; }
</style>
""", unsafe_allow_html=True)

# ================== THE SANITIZER ENGINE ==================
@st.cache_data(ttl=30)
def load_sheet(tab):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Fitness_Evolution_Master").worksheet(tab)
    
    raw_data = sheet.get_all_values()
    if not raw_data or len(raw_data) < 2:
        return pd.DataFrame()
        
    df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
    
    if "date" in df.columns:
        # FORCE everything to datetime. Format='mixed' is key for your two formats.
        df["date"] = pd.to_datetime(df["date"], format='mixed', dayfirst=True, errors='coerce')
        df = df.dropna(subset=['date'])
        
        # ELIMINATE GHOST DATES: Only keep data from the last 60 days to today
        # This prevents the "conking off" caused by 1970 or 2028 dates
        now = pd.Timestamp.now().normalize()
        df = df[(df["date"] > now - pd.Timedelta(days=90)) & (df["date"] <= now + pd.Timedelta(days=1))]
        df = df.sort_values("date")
    return df

# Initial Sync
weights_df   = load_sheet("weights")
macros_raw   = load_sheet("macros")
workouts_raw = load_sheet("workouts")
profile_df   = load_sheet("profile")

# --- PROCESS MACROS ---
for col in ["protein", "carbs", "fats"]:
    macros_raw[col] = pd.to_numeric(macros_raw[col], errors="coerce").fillna(0)
macros_df = macros_raw.groupby("date", as_index=False).agg({"protein":"sum","carbs":"sum","fats":"sum"})
macros_df["calories"] = (macros_df["protein"]*4 + macros_df["carbs"]*4 + macros_df["fats"]*9)

# --- PROCESS WORKOUTS ---
workouts_raw["calories"] = pd.to_numeric(workouts_raw["calories"], errors="coerce").fillna(0)
today_date = pd.Timestamp.now().normalize()
workouts_today = workouts_raw[workouts_raw['date'] == today_date].rename(columns={"calories": "burned"})

# Fallback to last known workout if today is empty
if (workouts_today.empty or workouts_today['burned'].sum() == 0) and not workouts_raw.empty:
    last_date = workouts_raw['date'].max()
    workouts_today = workouts_raw[workouts_raw['date'] == last_date].rename(columns={"calories": "burned"})

workouts_agg = workouts_raw.groupby("date", as_index=False).agg({"calories": "sum"}).rename(columns={"calories": "burned"})

# --- THE UNIFIED FUSION ---
# We merge on date, which is now a clean datetime object across all DFs
df = pd.merge(macros_df, workouts_agg, on="date", how="outer")
df = pd.merge(df, weights_df, on="date", how="outer").fillna(0)
df = df.sort_values("date").drop_duplicates('date')

# Force Numeric for Math
for c in ["calories", "burned", "weight", "protein", "carbs", "fats"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

df["Net"] = df["calories"] - df["burned"]

# ================== PHYSIOLOGY LOGIC ==================
W, maintenance, deficit_pct, weekly_loss = 0.0, 0, 0.0, 0.0
latest_net, latest_keto = 0, False
# Day count based on unique calendar days in the unified timeline
total_days = len(df['date'].unique()) if not df.empty else 1

if not weights_df.empty:
    w_series = pd.to_numeric(weights_df["weight"], errors='coerce').replace(0, np.nan).ffill()
    if not w_series.dropna().empty:
        W = float(w_series.dropna().iloc[-1])

if not profile_df.empty and W > 0:
    prof = profile_df.iloc[0]
    h, a = float(prof["height_cm"]), int(prof["age"])
    s = 5 if prof["gender"] == "Male" else -161
    maintenance = int((10*W + 6.25*h - 5*a + s) * 1.35)

if not df.empty:
    latest_row = df.iloc[-1]
    latest_net = int(latest_row.get("Net", 0))
    latest_keto = bool(latest_row.get("carbs", 100) <= 25 and latest_row.get("protein", 0) > 0)
    if maintenance > 0:
        deficit_pct = round((maintenance - latest_net) / maintenance * 100, 1)
    # Projection
    weekly_loss = round((abs(df.tail(7)["Net"].mean()) * 7) / 7700, 2) if len(df) >= 1 else 0

# ================== RENDER HUD ==================
st.title("⚡ FITNESS EVOLUTION MACHINE")

metrics_render = {
    "weight": W, "maintenance": maintenance, "net": latest_net,
    "deficit": deficit_pct, "keto": latest_keto, "weekly_loss": weekly_loss,
    "day_count": total_days
}

img_bytes = None
if not df.empty:
    try:
        # One last check to ensure types are clean for the renderer
        df["weight"] = df["weight"].replace(0, np.nan).ffill().fillna(W)
        img = render_summary(df, metrics_render, workouts_today)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        st.image(img, use_container_width=True)
    except Exception as e:
        st.error(f"Render Engine Error: {e}")
else:
    st.info("⚡ Awaiting initial Biometric Sync via Input Terminal.")

# ================== INPUT TERMINAL (SIDEBAR) ==================
with st.sidebar:
    st.title("📟 INPUT TERMINAL")
    
    # Standard helper for appending rows
    def sync_to_sheet(sheet_name, row):
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], 
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        client = gspread.authorize(creds)
        client.open("Fitness_Evolution_Master").worksheet(sheet_name).append_row(row)
        st.cache_data.clear()
        st.rerun()

    with st.expander("⚖️ WEIGHT", expanded=False):
        with st.form("w_form"):
            d = st.date_input("Date")
            val = st.number_input("Weight", step=0.1)
            if st.form_submit_button("SYNC"):
                sync_to_sheet("weights", [d.strftime('%d-%b-%y'), val])

    with st.expander("🥗 MEAL", expanded=False):
        with st.form("m_form"):
            d = st.date_input("Date")
            n = st.text_input("Meal Name", "Fuel")
            p, c, f = st.number_input("P"), st.number_input("C"), st.number_input("F")
            if st.form_submit_button("SYNC"):
                sync_to_sheet("macros", [d.strftime('%d-%b-%y'), n, p, c, f])

    with st.expander("🏋️ WORKOUT", expanded=True):
        with st.form("wo_form"):
            d = st.date_input("Date")
            t = st.selectbox("Type", ["Strength", "Cardio", "Static Cycle"])
            ex = st.text_input("Exercise")
            sets = st.number_input("Sets", step=1) if t == "Strength" else 0
            dur = st.number_input("Duration", step=1) if t != "Strength" else 0
            cal = st.number_input("Calories", step=1)
            if st.form_submit_button("SYNC"):
                sync_to_sheet("workouts", [d.strftime('%d-%b-%y'), t, ex, dur, sets, cal])

# ================== EMAIL DISPATCH ==================
if st.sidebar.button("📧 DISPATCH DAILY REPORT"):
    def send_email(image_data):
        msg = MIMEMultipart("related")
        msg["From"] = st.secrets["email"]["sender_email"]
        msg["To"] = st.secrets["email"]["recipient_email"]
        msg["Subject"] = f"A.R.V.I.S. | REPORT | {datetime.now().strftime('%d %b')}"
        body = f"""<body style="background-color: #050A0E; color: #00F2FF; font-family: monospace; padding: 20px;">
            <h2>SYSTEM STATUS: NOMINAL</h2>
            <img src="cid:hud" style="width:100%; max-width:800px; border: 1px solid #1E3D52;">
            <div style="margin-top: 20px;"><a href="https://fitness-evolution.streamlit.app" style="color:#00F2FF;">OPEN TERMINAL</a></div>
            </body>"""
        msg.attach(MIMEText(body, "html"))
        img_part = MIMEImage(image_data)
        img_part.add_header("Content-ID", "<hud>")
        msg.attach(img_part)
        with smtplib.SMTP(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"]) as s:
            s.starttls()
            s.login(st.secrets["email"]["sender_email"], st.secrets["email"]["app_password"])
            s.send_message(msg)
        st.success("Dispatched.")

    send_email(img_bytes)

if os.getenv("AUTO_EMAIL") == "1" and img_bytes:
    # Use the same function logic here
    pass 
