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
st.set_page_config(page_title="Evolution HUD", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: radial-gradient(circle, #001A2E 0%, #050A0E 100%); }
    .stMetric { border: 1px solid #1E3D52; background: #0A1926; padding: 20px; border-radius: 5px; }
    h1 { color: #00F2FF !important; font-family: 'Courier New', monospace; letter-spacing: 2px; }
</style>
""", unsafe_allow_html=True)

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

# Load and Prep
weights_df = load_sheet("weights")
macros_raw = load_sheet("macros")
workouts_raw = load_sheet("workouts")
profile_df = load_sheet("profile")

for col in ["protein", "carbs", "fats"]:
    macros_raw[col] = pd.to_numeric(macros_raw[col], errors="coerce").fillna(0)
macros_df = macros_raw.groupby("date", as_index=False).agg({"protein": "sum", "carbs": "sum", "fats": "sum"})
macros_df["calories"] = (macros_df["protein"] * 4 + macros_df["carbs"] * 4 + macros_df["fats"] * 9)

workouts_df = workouts_raw.groupby("date", as_index=False).agg({"calories": "sum"}).rename(columns={"calories": "burned"})

df = macros_df.merge(workouts_df, on="date", how="outer").merge(weights_df, on="date", how="left").fillna(0)
df = df.sort_values("date")
df["Net"] = df["calories"] - df["burned"]

# ================== LOGIC ==================
prof = profile_df.iloc[0]
W = float(df["weight"].replace(0, np.nan).ffill().iloc[-1])
maintenance = int((10*W + 6.25*float(prof["height_cm"]) - 5*int(prof["age"]) + 5) * 1.35) # Hardcoded activity for demo
latest = df.iloc[-1]
deficit_pct = round((maintenance - latest["Net"]) / maintenance * 100, 1)
weekly_loss = round((abs(df.tail(7)["Net"].mean()) * 7) / 7700, 2)

# ================== RENDER HUD ==================
st.title("⚡ SYSTEM: ASCENSION PROTOCOL")

render_metrics = {
    "weight": W,
    "maintenance": maintenance,
    "net": int(latest["Net"]),
    "deficit": deficit_pct,
    "keto": (latest["carbs"] <= 25),
    "weekly_loss": weekly_loss
}

# The HUD Image
img = render_summary(df, render_metrics)
buf = io.BytesIO()
img.save(buf, format="PNG")
img_bytes = buf.getvalue()

st.image(img, use_container_width=True)

# ================== EMAIL SYSTEM ==================
def send_email(image_data):
    msg = MIMEMultipart("related")
    msg["From"] = st.secrets["email"]["sender_email"]
    msg["To"] = st.secrets["email"]["recipient_email"]
    msg["Subject"] = f"A.R.V.I.S. | Daily Bio-Metric Report | {datetime.now().strftime('%d %b')}"

    body = f"""
    <html>
    <body style="background-color: #050A0E; color: #00F2FF; font-family: monospace;">
        <h2>PROTOCOL STATUS: ONLINE</h2>
        <img src="cid:hud" style="width:100%; max-width:800px; border: 2px solid #00F2FF;">
        <p style="color: #A0B0B9;">Target: Eccentric Billionaire Genius. Don't stop.</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(body, "html"))
    img_part = MIMEImage(image_data)
    img_part.add_header("Content-ID", "<hud>")
    msg.attach(img_part)

    with smtplib.SMTP(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"]) as server:
        server.starttls()
        server.login(st.secrets["email"]["sender_email"], st.secrets["email"]["app_password"])
        server.send_message(msg)

if st.button("🚀 INITIATE DISPATCH"):
    send_email(img_bytes)
    st.success("Report Synchronized to Inbox.")

if os.getenv("AUTO_EMAIL") == "1":
    send_email(img_bytes)
