# render/render.py
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np
import matplotlib.pyplot as plt

# --- TONY STARK HUD THEME ---
CYAN = "#00F2FF"
DEEP_BLUE = "#001A2E"
BG_DARK = "#050A0E"
NEON_GREEN = "#39FF14"
NEON_RED = "#FF3131"
TEXT_GREY = "#A0B0B9"

def draw_glass_card(draw, x, y, w, h, title=""):
    draw.rectangle([x, y, x+w, y+h], fill="#0A1926", outline="#1E3D52", width=2)
    draw.line([x, y, x+w, y], fill="#3E7DA3", width=3)
    try:
        f_small = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    except:
        f_small = ImageFont.load_default()
    draw.text((x+15, y-30), title.upper(), fill=CYAN, font=f_small)

def render_summary(df, metrics, workouts_today):
    width, height = 1080, 1350 
    img = Image.new("RGB", (width, height), BG_DARK)
    draw = ImageDraw.Draw(img)
    
    try:
        f_huge = ImageFont.truetype("DejaVuSans-Bold.ttf", 110)
        f_mid = ImageFont.truetype("DejaVuSans-Bold.ttf", 45)
        f_reg = ImageFont.truetype("DejaVuSans.ttf", 28)
        f_stats = ImageFont.truetype("DejaVuSans-Bold.ttf", 35)
    except:
        f_huge = f_mid = f_reg = f_stats = ImageFont.load_default()

    # --- HEADER: FITNESS EVOLUTION MACHINE ---
    draw.rectangle([0, 0, width, 120], fill="#001F33")
    draw.text((40, 35), "FITNESS EVOLUTION MACHINE", fill=CYAN, font=f_mid)
    draw.text((width-350, 40), f"DAY {len(df)} OF 60", fill=CYAN, font=f_reg)
    draw.line([0, 120, width, 120], fill=CYAN, width=4)

    # --- PRIMARY BIO-METRICS ---
    draw.text((40, 150), "DAILY REPORT", fill=TEXT_GREY, font=f_reg)
    draw.text((40, 190), f"{metrics['weight']}", fill="#FFFFFF", font=f_huge)
    draw.text((440, 255), "KG", fill=CYAN, font=f_mid)
    draw.text((40, 310), f"PROJECTION: {metrics.get('weekly_loss', 0)} KG/WEEK", fill=NEON_GREEN, font=f_reg)

    # --- THREE COLUMN HUD ---
    col_w, start_y, card_h = 310, 400, 420
    
    # 1. THERMODYNAMICS
    draw_glass_card(draw, 30, start_y, col_w, card_h, "Thermodynamics")
    draw.text((50, start_y+30), f"MAINT: {metrics['maintenance']}", fill=TEXT_GREY, font=f_reg)
    bar_h = 220
    draw.rectangle([60, start_y+80, 90, start_y+80+bar_h], fill="#1E3D52")
    fill_h = int(bar_h * (min(metrics['deficit'], 100)/100))
    draw.rectangle([60, start_y+80+(bar_h-fill_h), 90, start_y+80+bar_h], fill=NEON_RED)
    draw.text((110, start_y+160), f"NET: {metrics['net']}", fill="#FFFFFF", font=f_stats)

    # 2. BIO-CHEMICAL STACK (Complete Supp List)
    draw_glass_card(draw, 385, start_y, col_w, card_h, "Bio-Chemical Stack")
    keto_col = NEON_GREEN if metrics['keto'] else NEON_RED
    draw.text((400, start_y+30), f"KETOSIS: {'ACTIVE' if metrics['keto'] else 'OFF'}", fill=keto_col, font=f_reg)
    supps = ["ECA Stack", "Berberine", "MCT Oil", "Chromium", "Gymnema", "R-ALA", "Mg Glycinate"]
    for i, s in enumerate(supps):
        draw.text((400, start_y+80+(i*40)), f"• {s}", fill=CYAN, font=f_reg)

    # 3. PHYSICAL OUTPUT (Workout Pie)
    draw_glass_card(draw, 740, start_y, col_w, card_h, "Physical Output")
    plt.style.use('dark_background')
    if not workouts_today.empty and workouts_today['burned'].sum() > 0:
        fig, ax = plt.subplots(figsize=(3, 3), facecolor='#0A1926')
        ax.pie(workouts_today['burned'], colors=[CYAN, "#79C0FF", "#3E7DA3"], startangle=140)
        centre_circle = plt.Circle((0,0), 0.70, fc='#0A1926')
        ax.add_artist(centre_circle)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=True)
        plt.close(fig)
        buf.seek(0)
        workout_pie = Image.open(buf).resize((240, 240))
        img.paste(workout_pie, (775, start_y+100), workout_pie)
        draw.text((760, start_y+30), f"BURN: {int(workouts_today['burned'].sum())}", fill=NEON_GREEN, font=f_reg)
    else:
        draw.text((760, start_y+150), "NO DATA", fill=TEXT_GREY, font=f_reg)

    # --- BOTTOM CHART: WEIGHT TREND WITH AXIS ---
    fig, ax = plt.subplots(figsize=(10, 3.5), facecolor=BG_DARK)
    recent = df.tail(14)
    ax.plot(recent["date"], recent["weight"], color=CYAN, linewidth=3, marker='o', markersize=6, mfc=BG_DARK, mew=2)
    ax.fill_between(recent["date"], recent["weight"], recent["weight"].min()-1, color=CYAN, alpha=0.1)
    
    # Label only the latest point
    latest_date = recent["date"].iloc[-1]
    latest_val = recent["weight"].iloc[-1]
    ax.annotate(f"{latest_val}", (latest_date, latest_val), textcoords="offset points", xytext=(0,10), ha='center', color="#FFFFFF", weight='bold')
    
    ax.set_title("ACTUAL WEIGHT (14D) - BILLIONAIRE GOAL", color=CYAN, pad=10)
    ax.set_ylabel("KG", color=TEXT_GREY)
    ax.grid(color='#1E3D52', linestyle='--', alpha=0.5)
    ax.tick_params(axis='x', rotation=30, colors=TEXT_GREY)
    ax.tick_params(axis='y', colors=TEXT_GREY)
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=BG_DARK)
    plt.close(fig)
    buf.seek(0)
    img.paste(Image.open(buf).resize((1000, 350)), (40, 880))

    # --- FOOTER ---
    draw.text((width//2 - 380, height-60), "PHYSIQUE: ASCENDING. FAT CELLS: SCREAMING.", fill=CYAN, font=f_reg)

    return img
