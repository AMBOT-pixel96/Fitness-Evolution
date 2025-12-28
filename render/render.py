# render/render.py
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# --- STARK LUXURY THEME ---
CYAN = "#00F2FF"
BG_DARK = "#050A0E"
NEON_GREEN = "#39FF14"
NEON_RED = "#FF3131"
TEXT_GREY = "#A0B0B9"
CARD_BG = "#0A1926"
FOOTER_GREY = "#1E2A35"
GOLD = "#FFD700"

def draw_glass_card(draw, x, y, w, h, title=""):
    draw.rectangle([x, y, x+w, y+h], fill=CARD_BG, outline="#1E3D52", width=2)
    draw.line([x, y, x+w, y], fill="#3E7DA3", width=3)
    try:
        f_small = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    except: f_small = ImageFont.load_default()
    draw.text((x+15, y-30), title.upper(), fill=CYAN, font=f_small)

def render_summary(df, metrics, workouts_today):
    # INCREASE HEIGHT to 1500 to prevent overlap
    width, height = 1080, 1500 
    img = Image.new("RGB", (width, height), BG_DARK)
    draw = ImageDraw.Draw(img)
    
    try:
        f_huge = ImageFont.truetype("DejaVuSans-Bold.ttf", 110)
        f_mid = ImageFont.truetype("DejaVuSans-Bold.ttf", 45)
        f_reg = ImageFont.truetype("DejaVuSans.ttf", 26) # Slightly smaller for safety
        f_day = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
    except: f_huge = f_mid = f_reg = f_day = ImageFont.load_default()

    # --- HEADER ---
    draw.rectangle([0, 0, width, 120], fill="#001F33")
    draw.text((40, 35), "FITNESS EVOLUTION MACHINE", fill=CYAN, font=f_mid)
    draw.text((width-240, 42), f"DAY {metrics['day_count']} OF 60", fill=CYAN, font=f_day) 

    # --- PRIMARY BIO-METRICS ---
    draw.text((40, 160), "CURRENT MASS INDEX", fill=TEXT_GREY, font=f_reg)
    draw.text((40, 200), f"{metrics['weight']}", fill="#FFFFFF", font=f_huge)
    draw.text((440, 265), "KG", fill=CYAN, font=f_mid)
    draw.text((40, 320), f"PREDICTED TREND: {metrics.get('weekly_loss', 0)} KG / WEEK", fill=NEON_GREEN, font=f_reg)

    # RECALIBRATED CARD COORDINATES
    col_w, start_y, card_h = 310, 420, 460 # Increased card height
    
    # ---------------------------------------------------------
    # 1. THERMODYNAMICS (FIXED SPACING)
    # ---------------------------------------------------------
    draw_glass_card(draw, 30, start_y, col_w, card_h, "Thermodynamics")
    latest = df.iloc[-1]
    p, c, f = latest.get('protein', 0), latest.get('carbs', 0), latest.get('fats', 0)
    total_in = int(latest.get('calories', 0))

    if total_in > 0:
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(3, 3), facecolor=CARD_BG)
        ax.pie([p*4, c*4, f*9], colors=[CYAN, GOLD, NEON_RED], startangle=90, wedgeprops=dict(width=0.45, edgecolor=CARD_BG))
        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=True, dpi=100)
        plt.close(fig)
        donut_img = Image.open(buf).resize((230, 230))
        img.paste(donut_img, (70, start_y + 40), donut_img) # Shifted up
        
        # Legend - Shifted down to avoid donut overlap
        draw.text((60, start_y + 300), f"P:{int(p)}g", fill=CYAN, font=f_day)
        draw.text((140, start_y + 300), f"C:{int(c)}g", fill=GOLD, font=f_day)
        draw.text((220, start_y + 300), f"F:{int(f)}g", fill=NEON_RED, font=f_day)

    # Footer
    draw.rectangle([30, start_y + card_h - 60, 30 + col_w, start_y + card_h], fill=FOOTER_GREY)
    draw.text((45, start_y + card_h - 45), f"TOTAL INTAKE: {total_in} KCAL", fill=CYAN, font=f_day)

    # ---------------------------------------------------------
    # 2. BIO-CHEMICAL STACK
    # ---------------------------------------------------------
    draw_glass_card(draw, 385, start_y, col_w, card_h, "Bio-Chemical Stack")
    keto_col = NEON_GREEN if metrics['keto'] else NEON_RED
    draw.text((400, start_y+30), f"KETOSIS: {'ACTIVE' if metrics['keto'] else 'OFF'}", fill=keto_col, font=f_reg)
    supps = ["ECA Stack", "Berberine", "MCT Oil", "Chromium", "Gymnema", "R-ALA", "Mg Glycinate"]
    for i, s in enumerate(supps):
        draw.text((400, start_y+90+(i*42)), f"• {s}", fill=CYAN, font=f_reg)

    # ---------------------------------------------------------
    # 3. PHYSICAL OUTPUT (FIXED FOOTER)
    # ---------------------------------------------------------
    draw_glass_card(draw, 740, start_y, col_w, card_h, "Physical Output")
    total_burned = 0
    if not workouts_today.empty:
        total_burned = int(workouts_today['burned'].sum())
        exercise_data = workouts_today.groupby('exercise')['burned'].sum().sort_values()
        fig, ax = plt.subplots(figsize=(3.5, 3.5), facecolor=CARD_BG)
        bars = ax.barh(exercise_data.index, exercise_data.values, color=CYAN, height=0.6)
        ax.axis('off') # Hide all axes for cleaner look
        for bar in bars:
            ax.text(bar.get_width(), bar.get_y() + bar.get_height()/2, f' {int(bar.get_width())}', 
                    va='center', ha='left', color=NEON_GREEN, fontsize=11, fontweight='bold')
        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=True, dpi=120)
        plt.close(fig)
        chart_img = Image.open(buf).resize((280, 250))
        img.paste(chart_img, (755, start_y+50), chart_img)

    # Footer
    draw.rectangle([740, start_y + card_h - 60, 740 + col_w, start_y + card_h], fill=FOOTER_GREY)
    draw.text((755, start_y + card_h - 45), f"TOTAL BURNED: {total_burned} KCAL", fill=NEON_GREEN, font=f_day)

    # ---------------------------------------------------------
    # TREND GRAPH (PUSHED DOWN)
    # ---------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 3.5), facecolor=BG_DARK)
    recent = df.sort_values('date').tail(14)
    weights = pd.to_numeric(recent["weight"], errors='coerce').ffill().fillna(metrics['weight'])
    ax.plot(recent["date"], weights, color=CYAN, linewidth=3, marker='o', mfc=BG_DARK, markersize=8)
    ax.fill_between(recent["date"], weights, weights.min()-0.5, color=CYAN, alpha=0.1)
    ax.set_title("MASS PROGRESSION (14-DAY WINDOW)", color=CYAN, fontweight='bold', fontsize=14, pad=20)
    ax.grid(color='#1E3D52', linestyle='--', alpha=0.3)
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=BG_DARK)
    plt.close(fig)
    img.paste(Image.open(buf).resize((1000, 360)), (40, start_y + card_h + 40))

    draw.text((width//2 - 350, height - 50), "PHYSIQUE: ASCENDING | FAT CELLS: TERMINATED", fill=CYAN, font=f_reg)
    return img
