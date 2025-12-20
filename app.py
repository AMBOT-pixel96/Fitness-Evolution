import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import plotly.express as px

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

conn.commit()

# ------------------ HEADER ------------------
st.title("🔥 Fitness Evolution — Keto 60 Tracker")
st.caption("Built on pain, discipline & bad decisions avoided 😌")

# ------------------ CARD SELECTOR ------------------
card = st.radio(
    "Select Module",
    ["🏋️ Workout", "🥩 Macros", "💊 Supplements", "📊 Logs"],
    horizontal=True
)

# ------------------ WORKOUT CARD ------------------
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

        submitted = st.form_submit_button("🔥 Log Workout")

        if submitted:
            c.execute(
                "INSERT INTO workouts (date, workout_type, exercise, duration, sets, calories) VALUES (?,?,?,?,?,?)",
                (str(w_date), w_type, exercise, duration, sets, calories)
            )
            conn.commit()
            st.success("Workout logged. Beast mode respected 🫡")

    df = pd.read_sql("SELECT * FROM workouts ORDER BY date DESC", conn)
    st.dataframe(df, use_container_width=True)
    st.download_button("⬇️ Export CSV", df.to_csv(index=False), "workouts.csv")
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ MACROS CARD ------------------
elif card == "🥩 Macros":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🥩 Macro Log")

    with st.form("macro_form"):
        col1, col2 = st.columns(2)
        m_date = col1.date_input("Date", value=date.today())
        meal = col2.number_input("Meal #", 1, 6)

        p = st.number_input("Protein (g)", 0)
        cbs = st.number_input("Carbs (g)", 0)
        f = st.number_input("Fats (g)", 0)

        calories = p*4 + cbs*4 + f*9
        st.metric("Calories", calories)

        submitted = st.form_submit_button("🔥 Log Meal")

        if submitted:
            c.execute(
                "INSERT INTO macros (date, meal, protein, carbs, fats, calories) VALUES (?,?,?,?,?,?)",
                (str(m_date), meal, p, cbs, f, calories)
            )
            conn.commit()
            st.success("Meal logged. Ketosis nods approvingly 😌")

    df = pd.read_sql("SELECT * FROM macros ORDER BY date DESC", conn)
    st.dataframe(df, use_container_width=True)
    st.download_button("⬇️ Export CSV", df.to_csv(index=False), "macros.csv")
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ SUPPLEMENTS CARD ------------------
elif card == "💊 Supplements":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("💊 Supplement Log")

    with st.form("supp_form"):
        s_date = st.date_input("Date", value=date.today())
        supp = st.text_input("Supplement")
        dose = st.number_input("Dosage", 0.0)
        unit = st.selectbox("Unit", ["mg", "mcg", "g", "ml"])

        submitted = st.form_submit_button("🔥 Log Supplement")

        if submitted:
            existing = c.execute(
                "SELECT id, dosage FROM supplements WHERE date=? AND supplement=? AND unit=?",
                (str(s_date), supp, unit)
            ).fetchone()

            if existing:
                new_dose = existing[1] + dose
                c.execute("UPDATE supplements SET dosage=? WHERE id=?", (new_dose, existing[0]))
            else:
                c.execute(
                    "INSERT INTO supplements (date, supplement, dosage, unit) VALUES (?,?,?,?)",
                    (str(s_date), supp, dose, unit)
                )
            conn.commit()
            st.success("Supp logged. Liver says thanks (probably) 🤣")

    df = pd.read_sql("SELECT * FROM supplements ORDER BY date DESC", conn)
    st.dataframe(df, use_container_width=True)
    st.download_button("⬇️ Export CSV", df.to_csv(index=False), "supplements.csv")
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ LOGS DASHBOARD ------------------
else:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📊 Day-wise Logs")

    macros = pd.read_sql("""
        SELECT date,
               SUM(protein) protein,
               SUM(carbs) carbs,
               SUM(fats) fats,
               SUM(calories) calories
        FROM macros
        GROUP BY date
    """, conn)

    workouts = pd.read_sql("""
        SELECT date, SUM(calories) burned
        FROM workouts
        GROUP BY date
    """, conn)

    logs = pd.merge(macros, workouts, on="date", how="left").fillna(0)
    logs["Net"] = logs["calories"] - logs["burned"]

    st.dataframe(logs, use_container_width=True)

    if not logs.empty:
        fig = px.line(logs, x="date", y="Net", title="Net Calories Trend")
        st.plotly_chart(fig, use_container_width=True)

    st.download_button("⬇️ Export Daily Logs", logs.to_csv(index=False), "daily_logs.csv")
    st.markdown("</div>", unsafe_allow_html=True)
