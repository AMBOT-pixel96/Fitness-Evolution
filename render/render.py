# render/render.py
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# --- THEME CONSTANTS ---
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
        f_small = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
    except: f_small = ImageFont.load_default()
    draw.text((x+20, y-35), title.upper(), fill=CYAN, font=f_small)

def render_summary(df, metrics, workouts_today):
    # SHRUNK total height to a "Safe Zone" of 2800px to avoid server-side cropping
    width, height = 1080, 2800 
    img = Image.new("RGB", (width, height), BG_DARK)
    draw = ImageDraw.Draw(img)
    
    try:
        f_huge = ImageFont.truetype("DejaVuSans-Bold.ttf", 100)
        f_mid = ImageFont.truetype("DejaVuSans-Bold.ttf", 50)
        f_reg = ImageFont.truetype("DejaVuSans.ttf", 30)
        f_day = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
    except: f_huge = f_mid = f_reg = f_day = ImageFont.load_default()

    # --- 1. COMPACT HEADER ---
    draw.rectangle([0, 0, width, 160], fill="#001F33") 
    draw.text((40, 30), "FITNESS EVOLUTION MACHINE", fill=CYAN, font=f_mid)
    draw.text((40, 95), f"DAY {metrics['day_count']} OF 60", fill=CYAN, font=f_day) 
    draw.line([0, 160, width, 160], fill=CYAN, width=5)

    # --- 2. PRIMARY MASS INDEX ---
    draw.text((60, 200), "CURRENT MASS INDEX", fill=TEXT_GREY, font=f_reg)
    draw.text((60, 240), f"{metrics['weight']}", fill="#FFFFFF", font=f_huge)
    draw.text((450, 290), "KG", fill=CYAN, font=f_mid)
    draw.text((60, 360), f"PREDICTED TREND: {metrics.get('weekly_loss', 0)} KG / WEEK", fill=NEON_GREEN, font=f_reg)

    # Vertical Layout: Tightened spacing
    current_y = 500
    card_x, card_w, card_h, spacing = 60, 960, 440, 100

    # --- 3. THERMODYNAMICS ---
    draw_glass_card(draw, card_x, current_y, card_w, card_h, "Thermodynamics")
    latest = df.iloc[-1]
    p, c, f = latest.get('protein', 0), latest.get('carbs', 0), latest.get('fats', 0)
    total_in = int(latest.get('calories', 0))
    if total_in > 0:
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(3.5, 3.5), facecolor=CARD_BG)
        ax.pie([p*4, c*4, f*9], colors=[CYAN, GOLD, NEON_RED], startangle=90, wedgeprops=dict(width=0.4, edgecolor=CARD_BG))
        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=True, dpi=100)
        plt.close(fig)
        img.paste(Image.open(buf).resize((280, 280)), (100, current_y + 40), Image.open(buf).resize((280, 280)))
        draw.text((480, current_y + 80), f"PROTEIN: {int(p)}g", fill=CYAN, font=f_day)
        draw.text((480, current_y + 140), f"CARBS:   {int(c)}g", fill=GOLD, font=f_day)
        draw.text((480, current_y + 200), f"FATS:    {int(f)}g", fill=NEON_RED, font=f_day)
    draw.rectangle([card_x, current_y + card_h - 60, card_x + card_w, current_y + card_h], fill=FOOTER_GREY)
    draw.text((card_x + 30, current_y + card_h - 48), f"TOTAL INTAKE: {total_in} KCAL", fill=CYAN, font=f_day)

    current_y += card_h + spacing

    # --- 4. BIO-CHEMICAL STACK ---
    draw_glass_card(draw, card_x, current_y, card_w, card_h, "Bio-Chemical Stack")
    draw.text((card_x + 40, current_y + 30), f"KETOSIS: {'ACTIVE' if metrics['keto'] else 'OFF'}", fill=(NEON_GREEN if metrics['keto'] else NEON_RED), font=f_day)
    supps = ["ECA Stack", "Berberine", "MCT Oil", "Chromium", "Gymnema", "R-ALA", "Mg Glycinate"]
    for i, s in enumerate(supps):
        row, col = i % 2, i // 2
        draw.text((card_x + 40 + (row * 400), current_y + 90 + (col * 55)), f"• {s}", fill=CYAN, font=f_reg)

    current_y += card_h + spacing

    # --- 5. PHYSICAL OUTPUT ---
    draw_glass_card(draw, card_x, current_y, card_w, card_h, "Physical Output")
    total_burned = int(workouts_today['burned'].sum()) if not workouts_today.empty else 0
    if not workouts_today.empty:
        ex_data = workouts_today.groupby('exercise')['burned'].sum().sort_values()
        fig, ax = plt.subplots(figsize=(8, 3.2), facecolor=CARD_BG)
        bars = ax.barh(ex_data.index, ex_data.values, color=CYAN, height=0.6)
        ax.tick_params(axis='y', colors=TEXT_GREY, labelsize=12)
        ax.set_frame_on(False)
        ax.get_xaxis().set_visible(False)
        for bar in bars:
            ax.text(bar.get_width() + 10, bar.get_y() + bar.get_height()/2, f'{int(bar.get_width())} KCAL', va='center', ha='left', color=NEON_GREEN, fontsize=10, fontweight='bold')
        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=True, dpi=120)
        plt.close(fig)
        img.paste(Image.open(buf).resize((880, 280)), (card_x + 20, current_y + 40), Image.open(buf).resize((880, 280)))
    draw.rectangle([card_x, current_y + card_h - 60, card_x + card_w, current_y + card_h], fill=FOOTER_GREY)
    draw.text((card_x + 30, current_y + card_h - 48), f"TOTAL BURNED: {total_burned} KCAL", fill=NEON_GREEN, font=f_day)

    current_y += card_h + spacing

    # --- 6. WEIGHT TREND (14D) ---
    fig, ax = plt.subplots(figsize=(10, 4), facecolor=BG_DARK)
    recent = df.sort_values('date').tail(14)
    weights = pd.to_numeric(recent["weight"], errors='coerce').ffill().fillna(metrics['weight'])
    ax.plot(recent["date"], weights, color=CYAN, linewidth=4, marker='o', mfc=BG_DARK, markersize=10)
    ax.fill_between(recent["date"], weights, weights.min()-0.5, color=CYAN, alpha=0.1)
    
    # Latest Point Label
    last_idx = len(weights) - 1
    ax.annotate(f"{weights.iloc[last_idx]} KG", 
                (recent["date"].iloc[last_idx], weights.iloc[last_idx]), 
                textcoords="offset points", xytext=(0,20), ha='center', 
                color='#FFFFFF', weight='bold', fontsize=10,
                bbox=dict(boxstyle='round,pad=0.2', fc=BG_DARK, ec=CYAN, lw=1))

    ax.set_title("WEIGHT TREND (14D)", color=CYAN, fontweight='bold', fontsize=16, pad=25)
    plt.xticks(rotation=25, color=TEXT_GREY, fontsize=10)
    plt.yticks(color=TEXT_GREY, fontsize=10)
    ax.grid(color='#1E3D52', linestyle='--', alpha=0.3)
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=BG_DARK)
    plt.close(fig)
    img.paste(Image.open(buf).resize((940, 480)), (70, current_y + 20))

    # --- 7. FINAL DYNAMIC FOOTER ---
    maint = metrics.get('maintenance', 3000)
    net_cals = total_in - total_burned
    deficit_perc = int((1 - (net_cals / maint)) * 100)
    
    # Explicitly placed within the 2800px limit
    footer_text = f"THERMODYNAMIC STATUS: {deficit_perc}% DEFICIT"
    draw.text((width//2 - 350, height - 120), footer_text, fill=NEON_GREEN, font=f_mid)
    
    return img
