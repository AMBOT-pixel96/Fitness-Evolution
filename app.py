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

# High-Tech Styling
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: radial-gradient(circle, #001A2E 0%, #050A0E 100%); }
    .stMetric { border: 1px solid #1E3D52; background: #0A1926; padding: 20px; border-radius: 5px; }
    h1 { color: #00F2FF !important; font-family: 'Courier New', monospace; letter-spacing: 2px; }
    [data-testid="stSidebar"] { background-color: #050A0E; border-right: 1px solid #1E3D52; }
</style>
""", unsafe_allow_html=True)

# ================== DATA ENGINE (TEMPORAL SANITIZER) ==================
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
        # THE FIX: Coerce everything into a unified datetime object, ignoring "ghost" years
        df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['date'])
        # Filter for sanity: Remove any dates more than 1 year in the future/past
        now = pd.Timestamp.now()
        df = df[(df["date"] > now - pd.Timedelta(days=365)) & (df["date"] < now + pd.Timedelta(days=365))]
        df = df.sort_values("date")
    return df

# Fetch Data
try:
    weights_df   = load_sheet("weights")
    macros_raw   = load_sheet("macros")
    workouts_raw = load_sheet("workouts")
    profile_df   = load_sheet("profile")
except Exception as e:
    st.error(f"Sync Interrupted: {e}")
    st.stop()

# --- MACRO PROCESSING ---
for col in ["protein", "carbs", "fats"]:
    macros_raw[col] = pd.to_numeric(macros_raw[col], errors="coerce").fillna(0)
macros_df = macros_raw.groupby("date", as_index=False).agg({"protein": "sum", "carbs": "sum", "fats": "sum"})
macros_df["calories"] = (macros_df["protein"] * 4 + macros_df["carbs"] * 4 + macros_df["fats"] * 9)

# --- WORKOUT PROCESSING ---
workouts_raw["calories"] = pd.to_numeric(workouts_raw["calories"], errors="coerce").fillna(0)
today_date = pd.Timestamp.now().normalize()
workouts_today = workouts_raw[workouts_raw['date'] == today_date].rename(columns={"calories": "burned"})

if (workouts_today.empty or workouts_today['burned'].sum() == 0) and not workouts_raw.empty:
    last_date = workouts_raw['date'].max()
    workouts_today = workouts_raw[workouts_raw['date'] == last_date].rename(columns={"calories": "burned"})

workouts_agg = workouts_raw.groupby("date", as_index=False).agg({"calories": "sum"}).rename(columns={"calories": "burned"})

# --- MASTER FUSION ---
df = macros_df.merge(workouts_agg, on="date", how="outer").merge(weights_df, on="date", how="left").fillna(0)
df = df.sort_values("date")
df["Net"] = pd.to_numeric(df["calories"]) - pd.to_numeric(df["burned"])

# ================== PHYSIOLOGY ENGINE ==================
W, maintenance, deficit_pct, weekly_loss = 125.0, 3000, 0.0, 0.0
latest_net, latest_keto = 0, False
total_days = len(df)

if not weights_df.empty:
    w_series = pd.to_numeric(weights_df["weight"], errors='coerce').ffill()
    if not w_series.dropna().empty:
        W = float(w_series.dropna().iloc[-1])

if not profile_df.empty and W > 0:
    prof = profile_df.iloc[0]
    h_cm, age_val = float(prof["height_cm"]), int(prof["age"])
    s = 5 if prof.get("gender") == "Male" else -161
    maintenance = int((10*W + 6.25*h_cm - 5*age_val + s) * 1.35)

if not df.empty:
    latest_row = df.iloc[-1]
    latest_net = int(latest_row.get("Net", 0))
    latest_keto = bool(latest_row.get("carbs", 100) <= 25 and latest_row.get("carbs", 0) > 0)
    if maintenance > 0:
        deficit_pct = round((maintenance - latest_net) / maintenance * 100, 1)
    recent_net = df.tail(7)["Net"]
    if not recent_net.empty:
        weekly_loss = round((abs(recent_net.mean()) * 7) / 7700, 2)

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
        # Ensure data types are strictly numeric for Matplotlib
        df["weight"] = pd.to_numeric(df["weight"], errors='coerce').ffill()
        img = render_summary(df, metrics_render, workouts_today)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        st.image(img, use_container_width=True)
    except Exception as e:
        st.error(f"Render Engine Offline: {e}")
else:
    st.info("⚡ Awaiting initial Biometric Sync via Input Terminal.")

# ================== INPUT TERMINAL (SIDEBAR) ==================
with st.sidebar:
    st.title("📟 INPUT TERMINAL")
    with st.form("weight_form", clear_on_submit=True):
        w_date = st.date_input("Date", datetime.now())
        w_val = st.number_input("Weight (kg)", step=0.1, format="%.1f")
        if st.form_submit_button("SYNC WEIGHT"):
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
            client = gspread.authorize(creds)
            client.open("Fitness_Evolution_Master").worksheet("weights").append_row([w_date.strftime('%d-%b-%y'), w_val])
            st.cache_data.clear()
            st.rerun()

    # (Repeat similar forms for Fuel and Workouts, ensuring .strftime('%d-%b-%y') for all)
