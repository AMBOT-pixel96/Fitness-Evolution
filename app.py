import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import plotly.express as px
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ------------------ PAGE CONFIG ------------------
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
h1, h2, h3, h4, h5, h6 { color: #E6EDF3; }
</style>
""", unsafe_allow_html=True)

# ------------------ DB SETUP ------------------
conn = sqlite3.connect("fitness.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    workout_type TEXT,
    exercise TEXT,
    duration INTEGER,
    sets INTEGER,
    calories INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS macros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    meal INTEGER,
    protein INTEGER,
    carbs INTEGER,
    fats INTEGER,
    calories INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS supplements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    supplement TEXT,
    dosage REAL,
    unit TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS weights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE,
    weight REAL
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS user_profile (
    username TEXT PRIMARY KEY,
    gender TEXT,
    height_cm REAL,
    age INTEGER
)
""")

conn.commit()

# ------------------ HELPERS ------------------
def excel_template(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer

def normalize_dates(df):
    df["date"] = pd.to_datetime(df["date"], dayfirst=True).dt.strftime("%Y-%m-%d")
    return df

# ------------------ HEADER ------------------
st.title("🔥 Fitness Evolution — Keto 60 Tracker")
st.caption("Built on discipline, data & zero excuses 😌")

# ------------------ NAV ------------------
card = st.radio(
    "Select Module",
    ["🏋️ Workout", "🥩 Macros", "💊 Supplements", "📊 Logs"],
    horizontal=True
)

# ================== WORKOUT ==================
if card == "🏋️ Workout":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🏋️ Workout Log")

    with st.form("workout_form"):
        w_date = st.date_input("Date", value=date.today())
        w_type = st.selectbox("Workout Type", ["Cardio", "Strength", "Mobility"])
        exercise = st.text_input("Exercise")
        calories = st.number_input("Calories Burnt", 0, 2000)

        if st.form_submit_button("🔥 Log Workout"):
            c.execute(
                "INSERT INTO workouts VALUES (NULL,?,?,?,?,?,?)",
                (str(w_date), w_type, exercise, 0, 0, calories)
            )
            conn.commit()
            st.success("Workout logged 🫡")

    df = pd.read_sql("SELECT * FROM workouts ORDER BY date DESC", conn)
    st.dataframe(df, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ================== MACROS ==================
elif card == "🥩 Macros":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🥩 Macro Log")

    with st.form("macro_form"):
        m_date = st.date_input("Date", value=date.today())
        meal = st.number_input("Meal #", 1, 6)
        p = st.number_input("Protein (g)", 0)
        cbs = st.number_input("Carbs (g)", 0)
        f = st.number_input("Fats (g)", 0)
        calories = p*4 + cbs*4 + f*9

        if st.form_submit_button("🔥 Log Meal"):
            c.execute(
                "INSERT INTO macros VALUES (NULL,?,?,?,?,?,?)",
                (str(m_date), meal, p, cbs, f, calories)
            )
            conn.commit()
            st.success("Meal logged 😌")

    df = pd.read_sql("SELECT * FROM macros ORDER BY date DESC", conn)
    st.dataframe(df, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ================== SUPPLEMENTS ==================
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
            st.success("Supplement logged 💊")

    df = pd.read_sql("SELECT * FROM supplements ORDER BY date DESC", conn)
    st.dataframe(df, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ================== LOGS (FIXED) ==================
elif card == "📊 Logs":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📊 Logs & Intelligence")

    # ---- MANUAL WEIGHT ENTRY ----
    st.markdown("### ⚖️ Log Weight")

    with st.form("weight_form"):
        w_date = st.date_input("Date", value=date.today(), key="w_date")
        weight = st.number_input("Weight (kg)", 0.0, 300.0, step=0.1, key="w_val")

        if st.form_submit_button("🔥 Save Weight"):
            c.execute("""
                INSERT INTO weights (date, weight)
                VALUES (?, ?)
                ON CONFLICT(date) DO UPDATE SET weight=excluded.weight
            """, (str(w_date), weight))
            conn.commit()
            st.success("Weight saved 📉")

    # ---- WEIGHT EXCEL UPLOAD (UPSERT SAFE) ----
    st.markdown("### 📥 Upload Historical Weights")

    template = pd.DataFrame(columns=["date","weight"])
    st.download_button(
        "⬇️ Download Weight Template",
        excel_template(template),
        "weight_template.xlsx"
    )

    file = st.file_uploader("Upload Weight Excel", type=["xlsx"], key="weight_upload")

    if file and st.button("🔥 Import Weights"):
        df_up = normalize_dates(pd.read_excel(file))
        for _, r in df_up.iterrows():
            c.execute("""
                INSERT INTO weights (date, weight)
                VALUES (?, ?)
                ON CONFLICT(date) DO UPDATE SET weight=excluded.weight
            """, (r["date"], r["weight"]))
        conn.commit()
        st.success("Weight history imported ⚖️")

    # ---- DATA + CHARTS ----
    weights = pd.read_sql("SELECT date, weight FROM weights ORDER BY date", conn)
    macros = pd.read_sql("SELECT date, SUM(calories) calories FROM macros GROUP BY date", conn)
    workouts = pd.read_sql("SELECT date, SUM(calories) burned FROM workouts GROUP BY date", conn)

    logs = macros.merge(workouts, on="date", how="outer").merge(weights, on="date", how="left").fillna(0)
    logs["date"] = pd.to_datetime(logs["date"])
    logs["Net"] = logs["calories"] - logs["burned"]

    st.plotly_chart(px.line(weights, x="date", y="weight", title="Weight Trend"), use_container_width=True)
    st.plotly_chart(px.bar(logs, x="date", y=["calories","burned"], barmode="group", title="Calories In vs Out"), use_container_width=True)
    st.plotly_chart(px.line(logs, x="date", y="Net", title="Net Calories"), use_container_width=True)

    st.dataframe(logs, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)