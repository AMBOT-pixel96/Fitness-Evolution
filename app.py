import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import io
import gspread
from google.oauth2.service_account import Credentials

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
.card {
    background-color: #161B22;
    padding: 1.2rem;
    border-radius: 14px;
    margin-bottom: 1rem;
}
h1,h2,h3,h4,h5,h6 { color: #E6EDF3; }
</style>
""", unsafe_allow_html=True)

# ================== GOOGLE SHEETS ==================
@st.cache_data(ttl=300)
def load_sheet(tab_name):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)
    sheet = client.open("Fitness_Evolution_Master").worksheet(tab_name)
    df = pd.DataFrame(sheet.get_all_records())

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], dayfirst=True)

    return df

# ================== HEADER ==================
st.title("🔥 Fitness Evolution — Keto 60 Tracker")
st.caption("Built on discipline, data & zero excuses 😌")

card = st.radio(
    "Select Module",
    ["🏋️ Workout", "🥩 Macros", "💊 Supplements", "📊 Logs"],
    horizontal=True
)

# ======================================================
# ================== PLACEHOLDER TABS ==================
# ======================================================
if card in ["🏋️ Workout", "🥩 Macros", "💊 Supplements"]:
    st.info("✋ Data entry disabled. Google Sheets is the source of truth now.")

# ======================================================
# ================== LOGS + V2 =========================
# ======================================================
elif card == "📊 Logs":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📊 Logs & Intelligence")

    # ---------- LOAD SHEETS ----------
    weights_df = load_sheet("weights")
    macros_raw = load_sheet("macros")
    workouts_raw = load_sheet("workouts")
    profile_df = load_sheet("profile")

    if weights_df.empty or macros_raw.empty:
        st.info("No data yet.")
        st.stop()

    # ---------- MACROS ----------
    macros_raw["calories"] = (
        macros_raw["protein"] * 4 +
        macros_raw["carbs"] * 4 +
        macros_raw["fats"] * 9
    )

    macros_df = (
        macros_raw
        .groupby("date", as_index=False)
        .agg({
            "calories": "sum",
            "protein": "sum",
            "carbs": "sum",
            "fats": "sum"
        })
    )

    # ---------- WORKOUT BURN ----------
    workouts_df = (
        workouts_raw
        .groupby("date", as_index=False)
        .agg({"calories": "sum"})
        .rename(columns={"calories": "burned"})
    )

    # ---------- MERGE ----------
    df = (
        macros_df
        .merge(workouts_df, on="date", how="left")
        .merge(weights_df, on="date", how="left")
        .fillna(0)
        .sort_values("date")
    )

    df["Net"] = df["calories"] - df["burned"]

    # ---------- ACTIVITY ----------
    avg_burn = df.tail(7)["burned"].mean()
    activity = (
        1.2 if avg_burn < 200 else
        1.35 if avg_burn < 400 else
        1.5 if avg_burn < 600 else
        1.65
    )

    # ---------- PROFILE ----------
    p = profile_df.iloc[0]
    W = weights_df["weight"].iloc[-1]
    H = p["height_cm"]
    A = p["age"]
    s = 5 if p["gender"] == "Male" else -161

    maintenance = int((10*W + 6.25*H - 5*A + s) * activity)

    sel = df.iloc[-1]
    deficit_pct = round((maintenance - sel["Net"]) / maintenance * 100, 1)

    keto = (
        sel["carbs"] < 25 and
        (sel["fats"]*9 / sel["calories"]) >= 0.6
    )

    proj = round(W - (abs(df.tail(7)["Net"].mean())*7/7700), 2)

    # ---------- METRICS ----------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⚖️ Weight", f"{W} kg")
    c2.metric("🔥 Maintenance", f"{maintenance} kcal")
    c3.metric("📉 Deficit %", f"{deficit_pct}%")
    c4.metric("🔮 7-Day Projection", f"{proj} kg")

    st.caption(f"Keto: {'🟢 YES' if keto else '🔴 NO'} | Activity Multiplier: {activity}")

    # ---------- CHARTS ----------
    st.plotly_chart(px.line(df, x="date", y="weight", title="Weight Trend", markers=True), True)
    st.plotly_chart(px.bar(df, x="date", y=["calories","burned"], barmode="group", title="Calories In vs Out"), True)
    st.plotly_chart(px.line(df, x="date", y="Net", title="Net Calories", markers=True), True)

    df["Maintenance"] = maintenance
    st.plotly_chart(
        px.line(df, x="date", y=["Maintenance","Net"], title="Maintenance vs Net Calories"),
        True
    )

    # ---------- DONUTS ----------
    last = df.iloc[-1]
    st.plotly_chart(px.pie(
        values=[last["protein"]*4, last["carbs"]*4, last["fats"]*9],
        names=["Protein","Carbs","Fats"],
        hole=0.55,
        title="Macro Split"
    ), True)

    wt = (
        workouts_raw
        .groupby("workout_type", as_index=False)
        .agg({"calories": "sum"})
    )

    if not wt.empty:
        st.plotly_chart(px.pie(
            wt,
            values="calories",
            names="workout_type",
            hole=0.5,
            title="Burn Split by Workout Type"
        ), True)

    # ---------- SCORECARD EXPORT ----------
    st.markdown("### 📸 Export Scorecard")

    if st.button("📸 Generate Image"):
        img = Image.new("RGB", (1080,1080), "#0E1117")
        d = ImageDraw.Draw(img)

        try:
            f = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
        except:
            f = ImageFont.load_default()

        y = 80
        d.text((60,y), "FITNESS EVOLUTION", fill="#E6EDF3", font=f); y+=80

        lines = [
            f"Date: {sel['date'].date()}",
            f"Weight: {W} kg",
            f"Net Calories: {int(sel['Net'])}",
            f"Maintenance: {maintenance}",
            f"Deficit %: {deficit_pct}",
            f"Keto: {'YES' if keto else 'NO'}"
        ]

        for l in lines:
            d.text((60,y), l, fill="#58A6FF", font=f); y+=60

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        st.download_button(
            "⬇️ Download Image",
            buf,
            "fitness_scorecard.png",
            "image/png"
        )

    st.markdown("</div>", unsafe_allow_html=True)