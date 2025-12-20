import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import plotly.express as px
from io import BytesIO

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

conn.commit()

# ------------------ HELPERS ------------------
def excel_template(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer

# ------------------ HEADER ------------------
st.title("🔥 Fitness Evolution — Keto 60 Tracker")
st.caption("Built on discipline, data & zero excuses 😌")

# ------------------ CARD SELECTOR ------------------
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
        col1, col2, col3 = st.columns(3)
        w_date = col1.date_input("Date", value=date.today())
        w_type = col2.selectbox("Workout Type", ["Cardio", "Strength", "Mobility"])
        exercise = col3.text_input("Exercise")

        toggle = st.radio("Log Type", ["Duration (mins)", "Sets"], horizontal=True)
        duration, sets = 0, 0
        if toggle == "Duration (mins)":
            duration = st.number_input("Duration (mins)", 0, 300)
        else:
            sets = st.number_input("Sets", 0, 50)

        calories = st.number_input("Calories Burnt", 0, 2000)

        if st.form_submit_button("🔥 Log Workout"):
            c.execute(
                "INSERT INTO workouts VALUES (NULL,?,?,?,?,?,?)",
                (str(w_date), w_type, exercise, duration, sets, calories)
            )
            conn.commit()
            st.success("Workout logged 🫡")

    df = pd.read_sql("SELECT * FROM workouts ORDER BY date DESC", conn)
    st.dataframe(df, use_container_width=True)
    st.download_button("⬇️ Export CSV", df.to_csv(index=False), "workouts.csv")

    # ---- EXCEL UPLOAD ----
    st.markdown("### 📥 Upload Historical Workouts")
    template = pd.DataFrame(columns=["date","workout_type","exercise","duration","sets","calories"])
    st.download_button("⬇️ Download Template", excel_template(template), "workout_template.xlsx")
    file = st.file_uploader("Upload Excel", type=["xlsx"])
    if file and st.button("🔥 Import Workouts"):
        pd.read_excel(file).to_sql("workouts", conn, if_exists="append", index=False)
        st.success("Workout history imported 💥")

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
        st.metric("Calories", calories)

        if st.form_submit_button("🔥 Log Meal"):
            c.execute(
                "INSERT INTO macros VALUES (NULL,?,?,?,?,?,?)",
                (str(m_date), meal, p, cbs, f, calories)
            )
            conn.commit()
            st.success("Meal logged 😌")

    df = pd.read_sql("SELECT * FROM macros ORDER BY date DESC", conn)
    st.dataframe(df, use_container_width=True)
    st.download_button("⬇️ Export CSV", df.to_csv(index=False), "macros.csv")

    # ---- EXCEL UPLOAD ----
    st.markdown("### 📥 Upload Historical Macros")
    template = pd.DataFrame(columns=["date","meal","protein","carbs","fats"])
    st.download_button("⬇️ Download Template", excel_template(template), "macros_template.xlsx")
    file = st.file_uploader("Upload Excel", type=["xlsx"])
    if file and st.button("🔥 Import Macros"):
        df_up = pd.read_excel(file)
        df_up["calories"] = df_up["protein"]*4 + df_up["carbs"]*4 + df_up["fats"]*9
        df_up.to_sql("macros", conn, if_exists="append", index=False)
        st.success("Macro history imported 🔥")

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
            st.success("Supplement logged 🤣")

    df = pd.read_sql("SELECT * FROM supplements ORDER BY date DESC", conn)
    st.dataframe(df, use_container_width=True)
    st.download_button("⬇️ Export CSV", df.to_csv(index=False), "supplements.csv")

    # ---- EXCEL UPLOAD ----
    st.markdown("### 📥 Upload Historical Supplements")
    template = pd.DataFrame(columns=["date","supplement","dosage","unit"])
    st.download_button("⬇️ Download Template", excel_template(template), "supplements_template.xlsx")
    file = st.file_uploader("Upload Excel", type=["xlsx"])
    if file and st.button("🔥 Import Supplements"):
        pd.read_excel(file).to_sql("supplements", conn, if_exists="append", index=False)
        st.success("Supplement history imported 💊")

    st.markdown("</div>", unsafe_allow_html=True)

# ================== LOGS ==================
elif card == "📊 Logs":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📊 Day-wise Logs")

    # ---- WEIGHT ENTRY ----
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
            st.success("Weight saved 📉")

    # ---- EXCEL UPLOAD ----
    st.markdown("### 📥 Upload Historical Weights")
    template = pd.DataFrame(columns=["date","weight"])
    st.download_button("⬇️ Download Template", excel_template(template), "weight_template.xlsx")
    file = st.file_uploader("Upload Excel", type=["xlsx"])
    if file and st.button("🔥 Import Weights"):
        pd.read_excel(file).to_sql("weights", conn, if_exists="append", index=False)
        st.success("Weight history imported ⚖️")

    # ---- DATA + GRAPHS ----
    weights = pd.read_sql("SELECT * FROM weights ORDER BY date", conn)
    macros = pd.read_sql("SELECT date, SUM(calories) calories FROM macros GROUP BY date", conn)
    workouts = pd.read_sql("SELECT date, SUM(calories) burned FROM workouts GROUP BY date", conn)

    logs = pd.merge(macros, workouts, on="date", how="outer").fillna(0)
    logs = pd.merge(logs, weights, on="date", how="left")
    logs["Net Calories"] = logs["calories"] - logs["burned"]

    if not weights.empty:
        st.plotly_chart(px.line(weights, x="date", y="weight", markers=True, title="Weight Trend"), use_container_width=True)

    if not logs.empty:
        st.plotly_chart(px.bar(logs, x="date", y=["calories","burned"], barmode="group", title="Calories In vs Out"), use_container_width=True)
        st.plotly_chart(px.line(logs, x="date", y="Net Calories", markers=True, title="Net Calories"), use_container_width=True)

    st.dataframe(logs, use_container_width=True)
    st.download_button("⬇️ Export Daily Logs", logs.to_csv(index=False), "daily_logs.csv")
    st.markdown("</div>", unsafe_allow_html=True)