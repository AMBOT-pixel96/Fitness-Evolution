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

# ================== DATA ENGINE ==================
@st.cache_data(ttl=300)
def load_sheet(tab):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Fitness_Evolution_Master").worksheet(tab)
    df = pd.DataFrame(sheet.get_all_records())
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], dayfirst=True)
    return df

# Fetch Data
weights_df = load_sheet("weights")
macros_raw = load_sheet("macros")
workouts_raw = load_sheet("workouts")
profile_df = load_sheet("profile")

# Process Macros
for col in ["protein", "carbs", "fats"]:
    macros_raw[col] = pd.to_numeric(macros_raw[col], errors="coerce").fillna(0)
macros_df = macros_raw.groupby("date", as_index=False).agg({"protein": "sum", "carbs": "sum", "fats": "sum"})
macros_df["calories"] = (macros_df["protein"] * 4 + macros_df["carbs"] * 4 + macros_df["fats"] * 9)

# Process Workouts (FIXED: Today or Last Entry Fallback)
workouts_raw["calories"] = pd.to_numeric(workouts_raw["calories"], errors="coerce").fillna(0)
today_date = pd.Timestamp.now().normalize()
workouts_today = workouts_raw[workouts_raw['date'] == today_date].rename(columns={"calories": "burned"})

if workouts_today.empty:
    last_date = workouts_raw['date'].max()
    workouts_today = workouts_raw[workouts_raw['date'] == last_date].rename(columns={"calories": "burned"})

workouts_agg = workouts_raw.groupby("date", as_index=False).agg({"calories": "sum"}).rename(columns={"calories": "burned"})

# Master DF
df = macros_df.merge(workouts_agg, on="date", how="outer").merge(weights_df, on="date", how="left").fillna(0)
df = df.sort_values("date")
df["Net"] = df["calories"] - df["burned"]

# ================== PHYSIOLOGY ==================
prof = profile_df.iloc[0]
W = float(df["weight"].replace(0, np.nan).ffill().iloc[-1])
maintenance = int((10*W + 6.25*float(prof["height_cm"]) - 5*int(prof["age"]) + 5) * 1.35)
latest = df.iloc[-1]
deficit_pct = round((maintenance - latest["Net"]) / maintenance * 100, 1)
weekly_loss = round((abs(df.tail(7)["Net"].mean()) * 7) / 7700, 2)

# ================== RENDER HUD ==================
st.title("⚡ FITNESS EVOLUTION MACHINE")

metrics = {
    "weight": W, "maintenance": maintenance, "net": int(latest["Net"]),
    "deficit": deficit_pct, "keto": (latest["carbs"] <= 25), "weekly_loss": weekly_loss
}

img = render_summary(df, metrics, workouts_today)
buf = io.BytesIO()
img.save(buf, format="PNG")
img_bytes = buf.getvalue()

st.image(img, use_container_width=True)

# ================== EMAIL SYSTEM ==================
def send_email(image_data):
    msg = MIMEMultipart("related")
    msg["From"] = st.secrets["email"]["sender_email"]
    msg["To"] = st.secrets["email"]["recipient_email"]
    msg["Subject"] = f"A.R.V.I.S. | DAILY REPORT | {datetime.now().strftime('%d %b')}"

    body = f"""
    <body style="background-color: #050A0E; color: #00F2FF; font-family: monospace; padding: 20px;">
        <h2 style="border-bottom: 2px solid #00F2FF;">SYSTEM STATUS: NOMINAL</h2>
        <img src="cid:hud" style="width:100%; max-width:800px; border: 1px solid #1E3D52;">
        <p style="color: #A0B0B9; margin-top: 20px;">Stay eccentric. Stay genius. Protocol continues.</p>
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

if st.button("🚀 SYNC TO MOBILE"):
    send_email(img_bytes)
    st.success("Report Synced.")

if os.getenv("AUTO_EMAIL") == "1":
    send_email(img_bytes)
