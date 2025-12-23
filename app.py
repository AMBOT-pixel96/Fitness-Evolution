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

st.markdown("""
<style>
body { background-color: #0E1117; }
.block-container { padding-top: 1rem; }
h1,h2,h3,h4 { color: #E6EDF3; }
</style>
""", unsafe_allow_html=True)

# ================== GOOGLE SHEETS ==================
@st.cache_data(ttl=300)
def load_sheet(tab):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(creds)
    sheet = client.open("Fitness_Evolution_Master").worksheet(tab)
    df = pd.DataFrame(sheet.get_all_records())

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], dayfirst=True)

    return df

# ================== LOAD DATA ==================
weights_df   = load_sheet("weights")
macros_raw   = load_sheet("macros")
workouts_raw = load_sheet("workouts")
profile_df   = load_sheet("profile")

# ================== PREP MACROS ==================
for col in ["protein", "carbs", "fats"]:
    macros_raw[col] = pd.to_numeric(macros_raw[col], errors="coerce").fillna(0)

macros_raw["calories"] = (
    macros_raw["protein"] * 4 +
    macros_raw["carbs"] * 4 +
    macros_raw["fats"] * 9
)

macros_df = (
    macros_raw
    .groupby("date", as_index=False)
    .agg({
        "protein": "sum",
        "carbs": "sum",
        "fats": "sum",
        "calories": "sum"
    })
)

# ================== PREP WORKOUTS ==================
workouts_raw["calories"] = pd.to_numeric(workouts_raw["calories"], errors="coerce").fillna(0)

workouts_df = (
    workouts_raw
    .groupby("date", as_index=False)
    .agg({"calories": "sum"})
    .rename(columns={"calories": "burned"})
)

# ================== MERGE ==================
df = (
    macros_df
    .merge(workouts_df, on="date", how="outer")
    .merge(weights_df, on="date", how="left")
    .fillna(0)
)

if df.empty:
    st.warning("No data yet.")
    st.stop()

df = df.sort_values("date")
df["Net"] = df["calories"] - df["burned"]

# ================== PROFILE ==================
prof   = profile_df.iloc[0]
W      = float(df["weight"].iloc[-1])
H      = float(prof["height_cm"])
A      = int(prof["age"])
gender = prof["gender"]

# ================== ACTIVITY ==================
avg_burn = df.tail(7)["burned"].mean()
activity = (
    1.2 if avg_burn < 200 else
    1.35 if avg_burn < 400 else
    1.5 if avg_burn < 600 else
    1.65
)

# ================== MAINTENANCE ==================
s = 5 if gender == "Male" else -161
maintenance = int((10*W + 6.25*H - 5*A + s) * activity)

# ================== FIXED KETO LOGIC ==================
df["protein_cals"] = df["protein"] * 4
df["carb_cals"]    = df["carbs"] * 4
df["fat_cals"]     = df["fats"] * 9

df["Keto"] = (
    (df["carbs"] <= 25) &
    (df["fat_cals"] > df["protein_cals"]) &
    (df["fat_cals"] > df["carb_cals"])
)

# ================== METRICS ==================
latest = df.iloc[-1]

deficit_pct = round((maintenance - latest["Net"]) / maintenance * 100, 1)
weekly_loss = round((abs(df.tail(7)["Net"].mean()) * 7) / 7700, 2)

# ================== UI ==================
st.title("🔥 Fitness Evolution — Command Center")
st.caption("Sheets → Intelligence → Action")

c1, c2, c3, c4 = st.columns(4)
c1.metric("⚖️ Weight", f"{W} kg")
c2.metric("🔥 Maintenance", f"{maintenance} kcal")
c3.metric("📉 Deficit %", f"{deficit_pct}%")
c4.metric("🔮 Weekly Projection", f"{weekly_loss} kg")

st.caption(
    f"Keto Today: {'🟢 YES' if latest['Keto'] else '🔴 NO'} | "
    f"Activity Multiplier: {activity}"
)

# ================== DASHBOARD CHARTS ==================
st.plotly_chart(
    px.line(df, x="date", y="weight", title="Weight Trend", markers=True),
    use_container_width=True
)

st.plotly_chart(
    px.bar(df, x="date", y=["calories","burned"], barmode="group",
           title="Calories In vs Out"),
    use_container_width=True
)

st.plotly_chart(
    px.line(df, x="date", y="Net", title="Net Calories", markers=True),
    use_container_width=True
)

# ================== IMAGE RENDER (EXTERNAL ENGINE) ==================
metrics = {
    "weight": W,
    "maintenance": maintenance,
    "net": int(latest["Net"]),
    "deficit": deficit_pct,
    "keto": bool(latest["Keto"])
}

img = render_summary(df, metrics)

buf = io.BytesIO()
img.save(buf, format="PNG")
buf.seek(0)

# ================== EMAIL ENGINE ==================
def build_email_body():
    keto = "YES 🟢" if latest["Keto"] else "NO 🔴"
    return f"""
    <html>
    <body style="background:#0E1117;color:#E6EDF3;font-family:Arial;">
        <h2>🔥 Fitness Evolution — Daily Report</h2>
        <ul>
            <li>Weight: {W} kg</li>
            <li>Maintenance: {maintenance} kcal</li>
            <li>Net Calories: {int(latest['Net'])}</li>
            <li>Deficit %: {deficit_pct}</li>
            <li>Keto: {keto}</li>
            <li>Weekly Projection: {weekly_loss} kg</li>
        </ul>
        <img src="cid:scorecard" style="width:100%;max-width:800px;border-radius:14px;">
    </body>
    </html>
    """

def send_email(image_bytes):
    msg = MIMEMultipart("related")
    msg["From"] = st.secrets["email"]["sender_email"]
    msg["To"] = st.secrets["email"]["recipient_email"]
    msg["Subject"] = "🔥 Fitness Evolution — Daily Summary"

    alt = MIMEMultipart("alternative")
    msg.attach(alt)
    alt.attach(MIMEText(build_email_body(), "html"))

    img_part = MIMEImage(image_bytes)
    img_part.add_header("Content-ID", "<scorecard>")
    msg.attach(img_part)

    with smtplib.SMTP(
        st.secrets["email"]["smtp_server"],
        st.secrets["email"]["smtp_port"]
    ) as server:
        server.starttls()
        server.login(
            st.secrets["email"]["sender_email"],
            st.secrets["email"]["app_password"]
        )
        server.send_message(msg)

# ================== EXPORT SUMMARY ==================
st.markdown("### 📸 Export Summary")

st.image(img, use_column_width=True)

st.download_button(
    "⬇️ Download Image",
    buf,
    "fitness_summary.png",
    "image/png"
)

if st.button("📧 Send Test Email"):
    send_email(buf.getvalue())
    st.success("Email sent 📬 Check inbox")

# ================== AUTO EMAIL (GITHUB ACTIONS) ==================
if os.getenv("AUTO_EMAIL") == "1":
    send_email(buf.getvalue())