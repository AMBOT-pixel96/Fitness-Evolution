import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
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
st.set_page_config(
    page_title="Fitness Evolution",
    page_icon="🔥",
    layout="wide"
)

# Custom CSS for that High-Tech feel
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0E1117; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    .stMetric { background-color: #161B22; border-radius: 10px; padding: 15px; border: 1px solid #30363D; }
    h1, h2, h3 { color: #58A6FF !important; font-family: 'Courier New', monospace; }
</style>
""", unsafe_allow_html=True)

# ================== GOOGLE SHEETS ==================
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

# ================== DATA PROCESSING ==================
weights_df   = load_sheet("weights")
macros_raw   = load_sheet("macros")
workouts_raw = load_sheet("workouts")
profile_df   = load_sheet("profile")

for col in ["protein", "carbs", "fats"]:
    macros_raw[col] = pd.to_numeric(macros_raw[col], errors="coerce").fillna(0)

macros_raw["calories"] = (macros_raw["protein"] * 4 + macros_raw["carbs"] * 4 + macros_raw["fats"] * 9)
macros_df = macros_raw.groupby("date", as_index=False).agg({"protein": "sum", "carbs": "sum", "fats": "sum", "calories": "sum"})

workouts_raw["calories"] = pd.to_numeric(workouts_raw["calories"], errors="coerce").fillna(0)
workouts_df = workouts_raw.groupby("date", as_index=False).agg({"calories": "sum"}).rename(columns={"calories": "burned"})

df = macros_df.merge(workouts_df, on="date", how="outer").merge(weights_df, on="date", how="left").fillna(0)
df = df.sort_values("date")
df["Net"] = df["calories"] - df["burned"]

# ================== PHYSIOLOGY LOGIC ==================
prof = profile_df.iloc[0]
W = float(df["weight"].replace(0, np.nan).ffill().iloc[-1])
H, A, gender = float(prof["height_cm"]), int(prof["age"]), prof["gender"]

avg_burn = df.tail(7)["burned"].mean()
activity = 1.2 if avg_burn < 200 else 1.35 if avg_burn < 400 else 1.5 if avg_burn < 600 else 1.65
s = 5 if gender == "Male" else -161
maintenance = int((10*W + 6.25*H - 5*A + s) * activity)

# Keto Logic
df["Keto"] = (df["carbs"] <= 25) & ((df["fats"]*9) > (df["protein"]*4))

# Metrics calculation
latest = df.iloc[-1]
deficit_pct = round((maintenance - latest["Net"]) / maintenance * 100, 1)
weekly_loss = round((abs(df.tail(7)["Net"].mean()) * 7) / 7700, 2)

# ================== UI COMMAND CENTER ==================
st.title("⚡ COMMAND CENTER: EVOLUTION")

c1, c2, c3, c4 = st.columns(4)
c1.metric("⚖️ BODY MASS", f"{W} kg")
c2.metric("🔥 MAINT. CAP", f"{maintenance} kcal")
c3.metric("📉 DEFICIT", f"{deficit_pct}%")
c4.metric("🔮 WEEKLY PROJ", f"{weekly_loss} kg")

st.plotly_chart(px.line(df, x="date", y="weight", title="BIOMETRIC TRACKING: WEIGHT", markers=True).update_layout(template="plotly_dark"), use_container_width=True)

# ================== IMAGE ENGINE ==================
render_metrics = {
    "weight": W,
    "maintenance": maintenance,
    "net": int(latest["Net"]),
    "deficit": deficit_pct,
    "keto": bool(latest["Keto"])
}

img = render_summary(df, render_metrics)
buf = io.BytesIO()
img.save(buf, format="PNG")
img_bytes = buf.getvalue()

# ================== EMAIL SYSTEM ==================
def build_email_body():
    keto_label = "STABLE 🟢" if latest["Keto"] else "DISRUPTED 🔴"
    return f"""
    <html>
    <body style="background:#0E1117; color:#E6EDF3; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding:20px;">
        <h2 style="color:#58A6FF;">🔥 DAILY SYSTEM REPORT: FITNESS EVOLUTION</h2>
        <div style="border-left: 4px solid #58A6FF; padding-left: 15px; margin-bottom: 20px;">
            <p><b>Current Mass:</b> {W} kg</p>
            <p><b>Energy Deficit:</b> {deficit_pct}%</p>
            <p><b>Keto Status:</b> {keto_label}</p>
        </div>
        <img src="cid:scorecard" style="width:100%; max-width:600px; border-radius:15px; border: 1px solid #30363D;">
        <p style="color:#8B949E; font-size:12px; margin-top:20px;">Sent via Evolution Automated Intelligence</p>
    </body>
    </html>
    """

def send_email(image_data):
    msg = MIMEMultipart("related")
    msg["From"] = st.secrets["email"]["sender_email"]
    msg["To"] = st.secrets["email"]["recipient_email"]
    msg["Subject"] = f"🔥 Evolution Report: {datetime.now().strftime('%d %b')}"

    alt = MIMEMultipart("alternative")
    msg.attach(alt)
    alt.attach(MIMEText(build_email_body(), "html"))

    img_part = MIMEImage(image_data)
    img_part.add_header("Content-ID", "<scorecard>")
    msg.attach(img_part)

    with smtplib.SMTP(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"]) as server:
        server.starttls()
        server.login(st.secrets["email"]["sender_email"], st.secrets["email"]["app_password"])
        server.send_message(msg)

# ================== EXPORT & TRIGGER ==================
st.image(img, caption="Preview: High-Tech Daily Scorecard", use_container_width=True)

if st.button("📧 DISPATCH TEST REPORT"):
    send_email(img_bytes)
    st.success("Report Dispatched to Inbox.")

if os.getenv("AUTO_EMAIL") == "1":
    send_email(img_bytes)
