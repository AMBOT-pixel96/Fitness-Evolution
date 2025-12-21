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

# ================== UI HEADER ==================
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

# ================== ON-APP DASHBOARD (RESTORED) ==================
st.subheader("📊 Trends")

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

df["Maintenance"] = maintenance
st.plotly_chart(
    px.line(df, x="date", y=["Maintenance","Net"],
            title="Maintenance vs Net Calories"),
    use_container_width=True
)

st.plotly_chart(
    px.pie(
        values=[latest["protein_cals"], latest["carb_cals"], latest["fat_cals"]],
        names=["Protein","Carbs","Fats"],
        hole=0.55,
        title="Macro Split"
    ),
    use_container_width=True
)

burn_split = workouts_raw.groupby("workout_type", as_index=False)["calories"].sum()
st.plotly_chart(
    px.pie(burn_split, values="calories", names="workout_type",
           hole=0.5, title="Burn Split"),
    use_container_width=True
)

# ================== IMAGE HELPERS ==================
def plot_weight_img(df):
    fig, ax = plt.subplots(figsize=(6,3))
    recent = df.tail(21)
    ax.plot(recent["date"], recent["weight"], marker="o", linewidth=2)
    ax.set_title("Weight Trend (21 Days)")
    ax.grid(alpha=0.3)
    ax.tick_params(axis="x", rotation=45)
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="PNG", dpi=160)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf)

# ================== EXPORT SUMMARY ==================
st.subheader("📸 Export Summary")

if st.button("Export Summary"):
    img = Image.new("RGB", (1400,900), "#0E1117")
    d = ImageDraw.Draw(img)

    try:
        f_big = ImageFont.truetype("DejaVuSans-Bold.ttf", 52)
        f_med = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
    except:
        f_big = f_med = ImageFont.load_default()

    # Header
    d.text((40,30), "FITNESS EVOLUTION — DAILY SUMMARY", fill="#E6EDF3", font=f_big)

    # Metrics column
    metrics = [
        f"Weight: {W} kg",
        f"Maintenance: {maintenance} kcal",
        f"Net Calories: {int(latest['Net'])}",
        f"Deficit: {deficit_pct}%",
        f"Keto: {'YES' if latest['Keto'] else 'NO'}",
        f"Weekly Projection: {weekly_loss} kg"
    ]

    y = 130
    for m in metrics:
        d.text((40,y), m, fill="#58A6FF", font=f_med)
        y += 46

    # HERO chart
    img.paste(plot_weight_img(df), (520, 150))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    st.download_button(
        "⬇️ Download Image",
        buf,
        "fitness_summary.png",
        mime="image/png"
    )