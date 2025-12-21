import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import date
from PIL import Image, ImageDraw, ImageFont
import io
import gspread
from google.oauth2.service_account import Credentials
# from email.message import EmailMessage   # Step 3 enable
# import smtplib                            # Step 3 enable

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
h1,h2,h3,h4,h5,h6 { color: #E6EDF3; }
</style>
""", unsafe_allow_html=True)

# ================== HELPERS ==================
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


def generate_scorecard_v3(df, latest, maintenance, deficit_pct, weekly_loss):
    img = Image.new("RGB", (1400, 1600), "#0E1117")
    d = ImageDraw.Draw(img)

    try:
        f_big = ImageFont.truetype("DejaVuSans-Bold.ttf", 64)
        f_mid = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
        f_sm = ImageFont.truetype("DejaVuSans.ttf", 34)
    except:
        f_big = f_mid = f_sm = ImageFont.load_default()

    y = 60
    d.text((60, y), "FITNESS EVOLUTION — DAILY INTEL", fill="#E6EDF3", font=f_big)
    y += 90

    metrics = [
        ("Weight", f"{latest['weight']} kg"),
        ("Maintenance", f"{maintenance} kcal"),
        ("Net Calories", int(latest["Net"])),
        ("Deficit %", f"{deficit_pct}%"),
        ("Weekly Projection", f"{weekly_loss} kg"),
        ("Keto Status", "YES 🟢" if latest["Keto"] else "NO 🔴")
    ]

    for label, value in metrics:
        d.text((60, y), f"{label} :", fill="#8B949E", font=f_sm)
        d.text((400, y), f"{value}", fill="#58A6FF", font=f_mid)
        y += 65

    y += 30
    verdict = (
        "🔥 On Track. Maintain discipline."
        if latest["Keto"] and latest["Net"] < maintenance
        else "⚠️ Course correction advised."
    )

    d.rectangle([50, y, 1350, y+120], outline="#30363D", width=3)
    d.text((80, y+35), verdict, fill="#E6EDF3", font=f_mid)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ================== LOAD DATA ==================
weights_df = load_sheet("weights")
macros_raw = load_sheet("macros")
workouts_raw = load_sheet("workouts")
profile_df = load_sheet("profile")

# ================== TRANSFORMS ==================
macros_raw["calories"] = (
    macros_raw["protein"]*4 +
    macros_raw["carbs"]*4 +
    macros_raw["fats"]*9
)

macros_df = macros_raw.groupby("date", as_index=False).agg({
    "protein": "sum",
    "carbs": "sum",
    "fats": "sum",
    "calories": "sum"
})

workouts_df = workouts_raw.groupby("date", as_index=False).agg(
    {"calories": "sum"}
).rename(columns={"calories": "burned"})

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
prof = profile_df.iloc[0]
W = df["weight"].iloc[-1]
H = prof["height_cm"]
A = prof["age"]
gender = prof["gender"]

avg_burn = df.tail(7)["burned"].mean()
activity = 1.2 if avg_burn < 200 else 1.35 if avg_burn < 400 else 1.5 if avg_burn < 600 else 1.65
s = 5 if gender == "Male" else -161
maintenance = int((10*W + 6.25*H - 5*A + s) * activity)

# ================== KETO LOGIC (FINAL) ==================
df["protein_cals"] = df["protein"]*4
df["carb_cals"] = df["carbs"]*4
df["fat_cals"] = df["fats"]*9

df["Keto"] = (
    (df["carbs"] <= 25) &
    (df["fat_cals"] > df["protein_cals"]) &
    (df["fat_cals"] > df["carb_cals"])
)

latest = df.iloc[-1]
deficit_pct = round((maintenance - latest["Net"]) / maintenance * 100, 1)
weekly_loss = round((abs(df.tail(7)["Net"].mean())*7)/7700, 2)

# ================== UI ==================
st.title("🔥 Fitness Evolution — Command Center")
st.caption("Sheets → Intelligence → Action")

c1,c2,c3,c4 = st.columns(4)
c1.metric("⚖️ Weight", f"{W} kg")
c2.metric("🔥 Maintenance", f"{maintenance} kcal")
c3.metric("📉 Deficit %", f"{deficit_pct}%")
c4.metric("🔮 Weekly Projection", f"{weekly_loss} kg")

st.caption(
    f"Keto Today: {'🟢 YES' if latest['Keto'] else '🔴 NO'} | "
    f"Activity Multiplier: {activity}"
)

# ================== CHARTS ==================
st.plotly_chart(px.line(df, x="date", y="weight", title="Weight Trend", markers=True), True)
st.plotly_chart(px.bar(df, x="date", y=["calories","burned"],
                       barmode="group", title="Calories In vs Out"), True)
st.plotly_chart(px.line(df, x="date", y="Net", title="Net Calories", markers=True), True)

df["Maintenance"] = maintenance
st.plotly_chart(px.line(df, x="date", y=["Maintenance","Net"],
                        title="Maintenance vs Net"), True)

# ================== IMAGE V3 EXPORT ==================
st.markdown("### 📸 Export Intelligence Scorecard")

if st.button("Generate Image"):
    img_buf = generate_scorecard_v3(
        df=df,
        latest=latest,
        maintenance=maintenance,
        deficit_pct=deficit_pct,
        weekly_loss=weekly_loss
    )

    st.download_button(
        "⬇️ Download Image",
        img_buf,
        "fitness_scorecard_v3.png",
        "image/png"
    )

# ================== EMAIL ENGINE (DISABLED – STEP 3) ==================
# def send_email(image_buffer):
#     ...