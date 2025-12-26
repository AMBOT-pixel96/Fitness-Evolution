import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from render.render import render_summary
import io

def fetch_and_process(creds_info):
    # 1. AUTH & FETCH
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Fitness_Evolution_Master")

    def load_tab(name):
        data = sheet.worksheet(name).get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format='mixed', dayfirst=True, errors='coerce')
            df = df.dropna(subset=['date']).sort_values("date")
        return df

    weights_df = load_tab("weights")
    macros_raw = load_tab("macros")
    workouts_raw = load_tab("workouts")
    profile_df = load_tab("profile")

    # 2. PROCESSING
    for col in ["protein", "carbs", "fats"]:
        macros_raw[col] = pd.to_numeric(macros_raw[col], errors="coerce").fillna(0)
    macros_df = macros_raw.groupby("date", as_index=False).agg({"protein":"sum","carbs":"sum","fats":"sum"})
    macros_df["calories"] = (macros_df["protein"]*4 + macros_df["carbs"]*4 + macros_df["fats"]*9)

    workouts_raw["calories"] = pd.to_numeric(workouts_raw["calories"], errors="coerce").fillna(0)
    workouts_agg = workouts_raw.groupby("date", as_index=False).agg({"calories": "sum"}).rename(columns={"calories": "burned"})

    df = pd.merge(macros_df, workouts_agg, on="date", how="outer")
    df = pd.merge(df, weights_df, on="date", how="outer").fillna(0)
    df = df.sort_values("date").drop_duplicates('date')
    
    for c in ["calories", "burned", "weight", "protein", "carbs", "fats"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    df["Net"] = df["calories"] - df["burned"]

    # 3. PHYSIOLOGY
    W, maintenance = 0.0, 0
    if not weights_df.empty:
        W = float(pd.to_numeric(weights_df["weight"], errors='coerce').ffill().iloc[-1])
    
    if not profile_df.empty and W > 0:
        p = profile_df.iloc[0]
        h, a = float(p["height_cm"]), int(p["age"])
        s = 5 if p["gender"] == "Male" else -161
        maintenance = int((10*W + 6.25*h - 5*a + s) * 1.35)

    latest_row = df.iloc[-1] if not df.empty else {}
    metrics = {
        "weight": W, "maintenance": maintenance, 
        "net": int(latest_row.get("Net", 0)),
        "deficit": round((maintenance - int(latest_row.get("Net", 0))) / maintenance * 100, 1) if maintenance > 0 else 0,
        "keto": bool(latest_row.get("carbs", 100) <= 25 and latest_row.get("protein", 0) > 0),
        "weekly_loss": round((abs(df.tail(7)["Net"].mean()) * 7) / 7700, 2) if len(df) >= 1 else 0,
        "day_count": len(df['date'].unique()) if not df.empty else 1
    }

    # Workout Fallback for Render
    today_date = pd.Timestamp.now().normalize()
    workouts_today = workouts_raw[workouts_raw['date'] == today_date].rename(columns={"calories": "burned"})
    if workouts_today.empty and not workouts_raw.empty:
        workouts_today = workouts_raw[workouts_raw['date'] == workouts_raw['date'].max()].rename(columns={"calories": "burned"})

    return df, metrics, workouts_today
