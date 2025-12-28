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
        f_small = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
    except: f_small = ImageFont.load_default()
    draw.text((x+20, y-35), title.upper(), fill=CYAN, font=f_small)

def render_summary(df, metrics, workouts_today):
    # VERTICAL STACK CANVAS: 1080w x 2800h for ultimate breathing room
    width, height = 1080, 2800 
    img = Image.new("RGB", (width, height), BG_DARK)
    draw = ImageDraw.Draw(img)
    
    try:
        f_huge = ImageFont.truetype("DejaVuSans-Bold.ttf", 120)
        f_mid = ImageFont.truetype("DejaVuSans-Bold.ttf", 55)
        f_reg = ImageFont.truetype("DejaVuSans.ttf", 32)
        f_day = ImageFont.truetype("DejaVuSans-Bold.ttf", 38)
    except: f_huge = f_mid = f_reg = f_day = ImageFont.load_default()

    # --- HEADER ---
    draw.rectangle([0, 0, width, 140], fill="#001F33")
    draw.text((40, 45), "FITNESS EVOLUTION MACHINE", fill=CYAN, font=f_mid)
    draw.text((width-320, 52), f"DAY {metrics['day_count']} OF 60", fill=CYAN, font=f_day) 
    draw.line([0, 140, width, 140], fill=CYAN, width=5)

    # --- PRIMARY BIO-METRICS ---
    draw.text((60, 180), "CURRENT MASS INDEX", fill=TEXT_GREY, font=f_reg)
    draw.text((60, 230), f"{metrics['weight']}", fill="#FFFFFF", font=f_huge)
    draw.text((480, 300), "KG", fill=CYAN, font=f_mid)
    draw.text((60, 380), f"PREDICTED TREND: {metrics.get('weekly_loss', 0)} KG / WEEK", fill=NEON_GREEN, font=f_reg)

    # VERTICAL LAYOUT CONFIG
    card_x, card_w = 60, 960
    card_h = 500
    spacing = 80
    current_y = 480

    # ---------------------------------------------------------
    # 1. THERMODYNAMICS (WIDE MACRO DONUT)
    # ---------------------------------------------------------
    draw_glass_card(draw, card_x, current_y, card_w, card_h, "Thermodynamics")
    
    latest = df.iloc[-1]
    p, c, f = latest.get('protein', 0), latest.get('carbs', 0), latest.get('fats', 0)
    total_in = int(latest.get('calories', 0))

    if total_in > 0:
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(4, 4), facecolor=CARD_BG)
        ax.pie([p*4, c*4, f*9], colors=[CYAN, GOLD, NEON_RED], startangle=90, wedgeprops=dict(width=0.45, edgecolor=CARD_BG))
        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=True, dpi=120)
        plt.close(fig)
        donut_img = Image.open(buf).resize((320, 320))
        img.paste(donut_img, (100, current_y + 60), donut_img)
        
        # Macro Detail Table inside the card
        draw.text((500, current_y + 100), f"PROTEIN: {int(p)}g", fill=CYAN, font=f_day)
        draw.text((500, current_y + 170), f"CARBS:   {int(c)}g", fill=GOLD, font=f_day)
        draw.text((500, current_y + 240), f"FATS:    {int(f)}g", fill=NEON_RED, font=f_day)

    # Standard Footer
    draw.rectangle([card_x, current_y + card_h - 70, card_x + card_w, current_y + card_h], fill=FOOTER_GREY)
    draw.text((card_x + 30, current_y + card_h - 55), f"TOTAL INTAKE: {total_in} KCAL", fill=CYAN, font=f_day)

    current_y += card_h + spacing

    # ---------------------------------------------------------
    # 2. BIO-CHEMICAL STACK (WIDE LIST)
    # ---------------------------------------------------------
    draw_glass_card(draw, card_x, current_y, card_w, card_h, "Bio-Chemical Stack")
    keto_col = NEON_GREEN if metrics['keto'] else NEON_RED
    draw.text((card_x + 40, current_y + 40), f"KETOSIS: {'ACTIVE' if metrics['keto'] else 'OFF'}", fill=keto_col, font=f_day)
    
    supps = ["ECA Stack", "Berberine", "MCT Oil", "Chromium", "Gymnema", "R-ALA", "Mg Glycinate"]
    for i, s in enumerate(supps):
        row, col = i % 2, i // 2
        draw.text((card_x + 40 + (row * 400), current_y + 110 + (col * 65)), f"• {s}", fill=CYAN, font=f_reg)

    current_y += card_h + spacing

    # ---------------------------------------------------------
    # 3. PHYSICAL OUTPUT (FIXED Y-LABELS)
    # ---------------------------------------------------------
    draw_glass_card(draw, card_x, current_y, card_w, card_h, "Physical Output")
    total_burned = 0
    if not workouts_today.empty:
        total_burned = int(workouts_today['burned'].sum())
        ex_data = workouts_today.groupby('exercise')['burned'].sum().sort_values()
        
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(8, 3.5), facecolor=CARD_BG)
        bars = ax.barh(ex_data.index, ex_data.values, color=CYAN, height=0.6)
        
        ax.set_facecolor(CARD_BG)
        # ENABLING Y-LABELS
        ax.tick_params(axis='y', colors=TEXT_GREY, labelsize=14)
        ax.tick_params(axis='x', colors='none')
        for spine in ['top', 'right', 'bottom', 'left']: ax.spines[spine].set_visible(False)
        
        for bar in bars:
            ax.text(bar.get_width() + 10, bar.get_y() + bar.get_height()/2, f'{int(bar.get_width())} KCAL', 
                    va='center', ha='left', color=NEON_GREEN, fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=True, dpi=130)
        plt.close(fig)
        chart_img = Image.open(buf).resize((900, 330))
        img.paste(chart_img, (card_x + 20, current_y + 50), chart_img)

    # Footer
    draw.rectangle([card_x, current_y + card_h - 70, card_x + card_w, current_y + card_h], fill=FOOTER_GREY)
    draw.text((card_x + 30, current_y + card_h - 55), f"TOTAL BURNED: {total_burned} KCAL", fill=NEON_GREEN, font=f_day)

    current_y += card_h + spacing

    # ---------------------------------------------------------
    # 4. TREND GRAPH (ULTRA-WIDE)
    # ---------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 4.5), facecolor=BG_DARK)
    recent = df.sort_values('date').tail(14)
    weights = pd.to_numeric(recent["weight"], errors='coerce').ffill().fillna(metrics['weight'])
    ax.plot(recent["date"], weights, color=CYAN, linewidth=5, marker='o', mfc=BG_DARK, markersize=12)
    ax.fill_between(recent["date"], weights, weights.min()-0.5, color=CYAN, alpha=0.1)
    ax.set_title("MASS PROGRESSION (14-DAY WINDOW)", color=CYAN, fontweight='bold', fontsize=18, pad=30)
    ax.grid(color='#1E3D52', linestyle='--', alpha=0.4)
    plt.xticks(rotation=25, color=TEXT_GREY, fontsize=12)
    plt.yticks(color=TEXT_GREY, fontsize=12)
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=BG_DARK)
    plt.close(fig)
    img.paste(Image.open(buf).resize((980, 500)), (50, current_y))

    # Motivation Signature
    sig_text = "PHYSIQUE: ASCENDING | FAT CELLS: TERMINATED"
    draw.text((width//2 - 400, height - 100), sig_text, fill=CYAN, font=f_mid)
    
    return img
