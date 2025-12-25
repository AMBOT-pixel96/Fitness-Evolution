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
    .stForm { background-color: rgba(0, 242, 255, 0.05); border: 1px solid #1E3D52; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ================== DATA ENGINE (TEMPORAL RECONCILIATION) ==================
@st.cache_data(ttl=60)
def load_sheet(tab):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Fitness_Evolution_Master").worksheet(tab)
    
    raw_data = sheet.get_all_values()
    if not raw_data or len(raw_data) < 2:
        return pd.DataFrame()
        
    df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
    df = df.replace(r'^\s*$', np.nan, regex=True)
    
    if "date" in df.columns:
        # THE FIX: Mixed format parsing + cleaning ghost dates
        df["date"] = pd.to_datetime(df["date"], format='mixed', dayfirst=True, errors='coerce')
        df = df.dropna(subset=['date'])
        # Filter out extreme outlier dates that break Matplotlib scaling
        now = pd.Timestamp.now()
        df = df[(df["date"] > now - pd.Timedelta(days=365)) & (df["date"] < now + pd.Timedelta(days=30))]
        df = df.sort_values("date")
    return df

# Initial Sync
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

# Fallback for Workouts Display
if (workouts_today.empty or workouts_today['burned'].sum() == 0) and not workouts_raw.empty:
    last_date = workouts_raw['date'].max()
    workouts_today = workouts_raw[workouts_raw['date'] == last_date].rename(columns={"calories": "burned"})

workouts_agg = workouts_raw.groupby("date", as_index=False).agg({"calories": "sum"}).rename(columns={"calories": "burned"})

# --- MASTER FUSION (Historical Baseline) ---
df = macros_df.merge(workouts_agg, on="date", how="outer").merge(weights_df, on="date", how="left").fillna(0)
df = df.sort_values("date").drop_duplicates('date')
df["Net"] = pd.to_numeric(df["calories"]) - pd.to_numeric(df["burned"])

# ================== PHYSIOLOGY LOGIC (ROBUST FALLBACK) ==================
W, maintenance, deficit_pct, weekly_loss = 0.0, 0, 0.0, 0.0
latest_net, latest_keto = 0, False
total_days = len(df['date'].unique()) if not df.empty else 1

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
    try:
        latest_row = df.iloc[-1]
        latest_net = int(latest_row.get("Net", 0))
        # Keto check: Carbs <= 25 and we actually have data for that day
        latest_keto = bool(latest_row.get("carbs", 100) <= 25 and latest_row.get("protein", 0) > 0)
        
        if maintenance > 0:
            deficit_pct = round((maintenance - latest_net) / maintenance * 100, 1)
        
        recent_net = df.tail(7)["Net"]
        if not recent_net.empty:
            weekly_loss = round((abs(recent_net.mean()) * 7) / 7700, 2)
    except: pass

# ================== RENDER HUD ==================
st.title("⚡ FITNESS EVOLUTION MACHINE")

metrics_render = {
    "weight": W, "maintenance": maintenance, "net": latest_net,
    "deficit": deficit_pct, "keto": latest_keto, "weekly_loss": weekly_loss,
    "day_count": total_days
}

img_bytes = None
# Render if at least weight data or merged data exists
if not weights_df.empty or not df.empty:
    try:
        # Use a dummy row if fusion failed but historical weight exists
        render_df = df if not df.empty else pd.DataFrame([{"date": pd.Timestamp.now(), "weight": W}])
        render_df["weight"] = pd.to_numeric(render_df["weight"], errors='coerce').ffill()
        
        img = render_summary(render_df, metrics_render, workouts_today)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        st.image(img, use_container_width=True)
    except Exception as e:
        st.error(f"Render Engine Offline: {e}")
else:
    st.info("⚡ System Online: Awaiting initial Biometric Sync via Input Terminal.")

# ================== INPUT TERMINAL (SIDEBAR) ==================
with st.sidebar:
    st.title("📟 INPUT TERMINAL")
    
    with st.expander("⚖️ WEIGHT UPLINK", expanded=False):
        with st.form("weight_form", clear_on_submit=True):
            w_date = st.date_input("Date", datetime.now(), key="w_d")
            w_val = st.number_input("Weight (kg)", step=0.1, format="%.1f")
            if st.form_submit_button("SYNC WEIGHT"):
                creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                client = gspread.authorize(creds)
                client.open("Fitness_Evolution_Master").worksheet("weights").append_row([w_date.strftime('%d-%b-%y'), w_val])
                st.success("Weight Logged")
                st.cache_data.clear()
                st.rerun()

    with st.expander("🥗 FUEL INTAKE", expanded=False):
        with st.form("macro_form", clear_on_submit=True):
            m_date = st.date_input("Date", datetime.now(), key="m_d")
            m_name = st.text_input("Meal Name", "Macro Session")
            mp, mc, mf = st.number_input("P", step=1), st.number_input("C", step=1), st.number_input("F", step=1)
            if st.form_submit_button("SYNC FUEL"):
                creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                client = gspread.authorize(creds)
                client.open("Fitness_Evolution_Master").worksheet("macros").append_row([m_date.strftime('%d-%b-%y'), m_name, mp, mc, mf])
                st.success("Fuel Logged")
                st.cache_data.clear()
                st.rerun()

    with st.expander("🏋️ PHYSICAL OUTPUT", expanded=True):
        with st.form("workout_form", clear_on_submit=True):
            wo_date = st.date_input("Date", datetime.now(), key="wo_d")
            wo_type = st.selectbox("Type", ["Strength", "Cardio", "Static Cycle"])
            ex_name = st.text_input("Exercise Name")
            
            if wo_type == "Strength":
                sets, duration = st.number_input("Sets", step=1, value=0), 0
            else:
                duration, sets = st.number_input("Duration (mins)", step=1, value=0), 0
                
            cals = st.number_input("Calories Burned", step=1)
            if st.form_submit_button("SYNC OUTPUT"):
                creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                client = gspread.authorize(creds)
                client.open("Fitness_Evolution_Master").worksheet("workouts").append_row([
                    wo_date.strftime('%d-%b-%y'), wo_type, ex_name, duration, sets, cals
                ])
                st.success("Output Logged")
                st.cache_data.clear()
                st.rerun()

# ================== EMAIL DISPATCH ==================
def send_email(image_data):
    if image_data is None:
        st.warning("No visual data for dispatch.")
        return
        
    msg = MIMEMultipart("related")
    msg["From"] = st.secrets["email"]["sender_email"]
    msg["To"] = st.secrets["email"]["recipient_email"]
    msg["Subject"] = f"A.R.V.I.S. | DAILY REPORT | {datetime.now().strftime('%d %b')}"

    app_url = "https://fitness-evolution.streamlit.app" 
    body = f"""
    <body style="background-color: #050A0E; color: #00F2FF; font-family: monospace; padding: 20px;">
        <h2 style="border-bottom: 2px solid #00F2FF;">SYSTEM STATUS: NOMINAL</h2>
        <img src="cid:hud" style="width:100%; max-width:800px; border: 1px solid #1E3D52;">
        <div style="margin-top: 30px; text-align: center;">
            <a href="{app_url}" style="background-color: #00F2FF; color: #050A0E; padding: 18px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
               OPEN INPUT TERMINAL
            </a>
        </div>
    </body>
    """
    msg.attach(MIMEText(body, "html"))
    img_part = MIMEImage(image_data)
    img_part.add_header("Content-ID", "<hud>")
    msg.attach(img_part)

    with smtplib.SMTP(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"]) as server:
        server.starttls()
        server.login(st.secrets["email"]["sender_email"], st.secrets["email"]["app_password"])
        server.send_message(msg)
    st.success("System: Report Dispatched.")

with st.sidebar:
    st.divider()
    if st.button("📧 DISPATCH DAILY REPORT"):
        send_email(img_bytes)

if os.getenv("AUTO_EMAIL") == "1" and img_bytes:
    send_email(img_bytes)
