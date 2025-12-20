import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import plotly.express as px
from io import BytesIO
import numpy as np
from PIL import Image, ImageDraw, ImageFont
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
.card {
    background-color: #161B22;
    padding: 1.2rem;
    border-radius: 14px;
    margin-bottom: 1rem;
}
h1,h2,h3,h4,h5,h6 { color: #E6EDF3; }
</style>
""", unsafe_allow_html=True)

# ================== DB ==================
conn = sqlite3.connect("fitness.db", check_same_thread=False)
c = conn.cursor()

# ================== TABLES ==================
c.executescript("""
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    workout_type TEXT,
    exercise TEXT,
    duration INTEGER,
    sets INTEGER,
    calories INTEGER
);

CREATE TABLE IF NOT EXISTS macros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    meal INTEGER,
    protein INTEGER,
    carbs INTEGER,
    fats INTEGER,
    calories INTEGER
);

CREATE TABLE IF NOT EXISTS supplements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    supplement TEXT,
    dosage REAL,
    unit TEXT
);

CREATE TABLE IF NOT EXISTS weights (
    date TEXT PRIMARY KEY,
    weight REAL
);

CREATE TABLE IF NOT EXISTS user_profile (
    username TEXT PRIMARY KEY,
    gender TEXT,
    height_cm REAL,
    age INTEGER
);
""")
conn.commit()

# ================== HELPERS ==================
def excel_template(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    buf.seek(0)
    return buf

def normalize_dates(df):
    df["date"] = pd.to_datetime(df["date"], dayfirst=True).dt.strftime("%Y-%m-%d")
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
# ================== WORKOUT ===========================
# ======================================================
if card == "🏋️ Workout":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🏋️ Workout Log")

    with st.form("workout_form"):
        col1, col2, col3 = st.columns(3)
        w_date = col1.date_input("Date", value=date.today())
        w_type = col2.selectbox("Workout Type", ["Cardio", "Strength", "Mobility"])
        exercise = col3.text_input("Exercise")

        mode = st.radio("Log Type", ["Duration (mins)", "Sets"], horizontal=True)
        duration = st.number_input("Duration (mins)", 0, 300) if mode == "Duration (mins)" else 0
        sets = st.number_input("Sets", 0, 50) if mode == "Sets" else 0
        calories = st.number_input("Calories Burnt", 0, 3000)

        if st.form_submit_button("🔥 Log Workout"):
            c.execute(
                "INSERT INTO workouts VALUES (NULL,?,?,?,?,?,?)",
                (str(w_date), w_type, exercise, duration, sets, calories)
            )
            conn.commit()
            st.success("Workout logged.")

    df = pd.read_sql("SELECT * FROM workouts ORDER BY date DESC", conn)
    st.dataframe(df, use_container_width=True)

    st.markdown("### 📥 Upload Historical Workouts")
    st.download_button("⬇️ Template", excel_template(
        pd.DataFrame(columns=["date","workout_type","exercise","duration","sets","calories"])
    ), "workout_template.xlsx")

    file = st.file_uploader("Upload Workout Excel", type="xlsx")
    if file and st.button("🔥 Import Workouts"):
        df_up = normalize_dates(pd.read_excel(file))
        df_up.to_sql("workouts", conn, if_exists="append", index=False)
        st.success("Workout history imported.")

    st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# ================== MACROS ============================
# ======================================================
elif card == "🥩 Macros":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🥩 Macro Log")

    with st.form("macro_form"):
        m_date = st.date_input("Date", value=date.today())
        meal = st.number_input("Meal #", 1, 10)
        p = st.number_input("Protein (g)", 0)
        cbs = st.number_input("Carbs (g)", 0)
        f = st.number_input("Fats (g)", 0)
        calories = p*4 + cbs*4 + f*9
        st.metric("Calories", calories)

        if st.form_submit_button("🔥 Log Meal"):
            c.execute(
                "INSERT INTO macros VALUES (NULL,?,?,?,?,?,?)",
                (str(m_date), meal, p, cbs, f, calories)
            )
            conn.commit()
            st.success("Meal logged.")

    df = pd.read_sql("SELECT * FROM macros ORDER BY date DESC", conn)
    st.dataframe(df, use_container_width=True)

    st.markdown("### 📥 Upload Historical Macros")
    st.download_button("⬇️ Template", excel_template(
        pd.DataFrame(columns=["date","meal","protein","carbs","fats"])
    ), "macros_template.xlsx")

    file = st.file_uploader("Upload Macros Excel", type="xlsx")
    if file and st.button("🔥 Import Macros"):
        df_up = normalize_dates(pd.read_excel(file))
        df_up["calories"] = df_up["protein"]*4 + df_up["carbs"]*4 + df_up["fats"]*9
        df_up.to_sql("macros", conn, if_exists="append", index=False)
        st.success("Macro history imported.")

    st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# ================== SUPPLEMENTS =======================
# ======================================================
elif card == "💊 Supplements":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("💊 Supplement Log")

    with st.form("supp_form"):
        s_date = st.date_input("Date", value=date.today())
        supp = st.text_input("Supplement")
        dose = st.number_input("Dosage", 0.0)
        unit = st.selectbox("Unit", ["mg","mcg","g","ml"])

        if st.form_submit_button("🔥 Log Supplement"):
            c.execute(
                "INSERT INTO supplements VALUES (NULL,?,?,?,?)",
                (str(s_date), supp, dose, unit)
            )
            conn.commit()
            st.success("Supplement logged.")

    df = pd.read_sql("SELECT * FROM supplements ORDER BY date DESC", conn)
    st.dataframe(df, use_container_width=True)

    st.markdown("### 📥 Upload Historical Supplements")
    st.download_button("⬇️ Template", excel_template(
        pd.DataFrame(columns=["date","supplement","dosage","unit"])
    ), "supplements_template.xlsx")

    file = st.file_uploader("Upload Supplements Excel", type="xlsx")
    if file and st.button("🔥 Import Supplements"):
        df_up = normalize_dates(pd.read_excel(file))
        df_up.to_sql("supplements", conn, if_exists="append", index=False)
        st.success("Supplement history imported.")

    st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# ================== LOGS + V2 =========================
# ======================================================
elif card == "📊 Logs":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📊 Logs & Intelligence")

    # ---------- WEIGHT ----------
    with st.form("weight_form"):
        w_date = st.date_input("Date", value=date.today())
        weight = st.number_input("Weight (kg)", 0.0, 300.0, step=0.1)
        if st.form_submit_button("🔥 Save Weight"):
            c.execute("""
                INSERT INTO weights (date, weight)
                VALUES (?,?)
                ON CONFLICT(date) DO UPDATE SET weight=excluded.weight
            """, (str(w_date), weight))
            conn.commit()
            st.success("Weight saved.")

    st.markdown("### 📥 Upload Historical Weights")
    st.download_button("⬇️ Template", excel_template(
        pd.DataFrame(columns=["date","weight"])
    ), "weight_template.xlsx")

    file = st.file_uploader("Upload Weight Excel", type="xlsx")
    if file and st.button("🔥 Import Weights"):
        df_up = normalize_dates(pd.read_excel(file))
        for _, r in df_up.iterrows():
            c.execute("""
                INSERT INTO weights (date, weight)
                VALUES (?,?)
                ON CONFLICT(date) DO UPDATE SET weight=excluded.weight
            """, (r["date"], r["weight"]))
        conn.commit()
        st.success("Weight history imported.")

    # ---------- PROFILE ----------
    with st.expander("⚙️ User Profile"):
        username = st.text_input("Username", value="default_user")
        gender = st.radio("Gender", ["Male","Female"], horizontal=True)
        height = st.number_input("Height (cm)", 100.0, 250.0)
        age = st.number_input("Age", 10, 100)

        if st.button("💾 Save Profile"):
            c.execute("""
                INSERT INTO user_profile VALUES (?,?,?,?)
                ON CONFLICT(username)
                DO UPDATE SET gender=excluded.gender,
                              height_cm=excluded.height_cm,
                              age=excluded.age
            """, (username, gender, height, age))
            conn.commit()
            st.success("Profile saved.")

    # ---------- DATA ----------
    weights = pd.read_sql("SELECT * FROM weights ORDER BY date", conn)
    macros = pd.read_sql("""
        SELECT date, SUM(calories) calories, SUM(carbs) carbs, SUM(fats) fats
        FROM macros GROUP BY date
    """, conn)
    workouts = pd.read_sql("""
        SELECT date, SUM(calories) burned
        FROM workouts GROUP BY date
    """, conn)

    df = macros.merge(workouts, on="date", how="outer").merge(weights, on="date", how="left").fillna(0)
    df["date"] = pd.to_datetime(df["date"])
    df["Net"] = df["calories"] - df["burned"]

    # ---------- ACTIVITY ----------
    avg_burn = df.tail(7)["burned"].mean()
    activity = 1.2 if avg_burn < 200 else 1.35 if avg_burn < 400 else 1.5 if avg_burn < 600 else 1.65

    profile = pd.read_sql("SELECT * FROM user_profile WHERE username=?", conn, params=[username])
    maintenance = None
    if not profile.empty and not weights.empty:
        W = weights["weight"].iloc[-1]
        H = profile["height_cm"].iloc[0]
        A = profile["age"].iloc[0]
        s = 5 if profile["gender"].iloc[0] == "Male" else -161
        maintenance = int((10*W + 6.25*H - 5*A + s) * activity)

    # ---------- METRICS ----------
    sel = df.iloc[-1]
    deficit_pct = round((maintenance - sel["Net"]) / maintenance * 100,1) if maintenance else None
    keto = sel["carbs"] < 25 and sel["fats"]*9/sel["calories"] >= 0.6 if sel["calories"]>0 else False
    proj = round(W - (abs(df.tail(7)["Net"].mean())*7/7700),2) if not weights.empty else None

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("⚖️ Weight", f"{W} kg")
    c2.metric("🔥 Maintenance", f"{maintenance} kcal" if maintenance else "-")
    c3.metric("📉 Deficit %", f"{deficit_pct}%" if deficit_pct else "-")
    c4.metric("🔮 7-Day Projection", f"{proj} kg" if proj else "-")

    st.caption(f"Keto: {'🟢 YES' if keto else '🔴 NO'} | Activity Multiplier: {activity}")

    # ---------- CHARTS ----------
    st.plotly_chart(px.line(df, x="date", y="weight", title="Weight Trend", markers=True), use_container_width=True)
    st.plotly_chart(px.bar(df, x="date", y=["calories","burned"], barmode="group", title="Calories In vs Out"), use_container_width=True)
    st.plotly_chart(px.line(df, x="date", y="Net", title="Net Calories", markers=True), use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)