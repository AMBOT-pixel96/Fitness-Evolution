import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

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
W      = df["weight"].iloc[-1]
H      = prof["height_cm"]
A      = prof["age"]
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
st.plotly_chart(px.line(df, x="date", y="weight", title="Weight Trend", markers=True), True)
st.plotly_chart(px.bar(df, x="date", y=["calories","burned"], barmode="group",
                       title="Calories In vs Out"), True)
st.plotly_chart(px.line(df, x="date", y="Net", title="Net Calories", markers=True), True)

# ================== IMAGE HELPERS ==================
def plot_weight_img(df):
    fig, ax = plt.subplots(figsize=(4,2))
    recent = df.tail(14)
    ax.plot(recent["date"], recent["weight"], marker="o")
    ax.set_title("Weight (14d)")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(alpha=0.3)
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="PNG", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf)

def plot_macro_donut_img(row):
    fig, ax = plt.subplots(figsize=(3,3))
    ax.pie(
        [row["protein_cals"], row["carb_cals"], row["fat_cals"]],
        labels=["Protein","Carbs","Fats"],
        autopct="%1.0f%%",
        startangle=90
    )
    ax.set_title("Macros")
    buf = io.BytesIO()
    fig.savefig(buf, format="PNG", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf)

def generate_summary_image():
    img = Image.new("RGB", (1400,1000), "#0E1117")
    d = ImageDraw.Draw(img)

    try:
        f_big = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
        f_med = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
    except:
        f_big = f_med = ImageFont.load_default()

    d.text((40,30), "FITNESS EVOLUTION — DAILY SUMMARY", fill="#E6EDF3", font=f_big)

    metrics = [
        f"Weight: {W} kg",
        f"Maintenance: {maintenance} kcal",
        f"Net Calories: {int(latest['Net'])}",
        f"Deficit %: {deficit_pct}",
        f"Keto: {'YES' if latest['Keto'] else 'NO'}",
        f"Weekly Projection: {weekly_loss} kg"
    ]

    y = 120
for m in metrics:
    d.text((40, y), m, fill="#58A6FF", font=f_med)
    y += 42

# ⬇️ MUST start at SAME indentation as 'y = 120'
CHART_Y = 420

img.paste(plot_weight_img(df), (40, CHART_Y))
img.paste(plot_macro_donut_img(latest), (520, CHART_Y))

return img

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
        <img src="cid:scorecard" style="width:100%;max-width:800px;border-radius:12px;">
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

    img = MIMEImage(image_bytes)
    img.add_header("Content-ID", "<scorecard>")
    msg.attach(img)

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

img = generate_summary_image()
buf = io.BytesIO()
img.save(buf, format="PNG")
buf.seek(0)

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