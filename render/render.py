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
    # Main card body
    draw.rectangle([x, y, x+w, y+h], fill=CARD_BG, outline="#1E3D52", width=2)
    # Neon top border accent
    draw.line([x, y, x+w, y], fill="#3E7DA3", width=3)
    try:
        f_small = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    except:
        f_small = ImageFont.load_default()
    draw.text((x+15, y-30), title.upper(), fill=CYAN, font=f_small)

def render_summary(df, metrics, workouts_today):
    # Expanded canvas height to prevent vertical crowding
    width, height = 1080, 1500 
    img = Image.new("RGB", (width, height), BG_DARK)
    draw = ImageDraw.Draw(img)
    
    try:
        f_huge = ImageFont.truetype("DejaVuSans-Bold.ttf", 110)
        f_mid = ImageFont.truetype("DejaVuSans-Bold.ttf", 45)
        f_reg = ImageFont.truetype("DejaVuSans.ttf", 28)
        f_day = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
    except:
        f_huge = f_mid = f_reg = f_day = ImageFont.load_default()

    # --- HEADER ---
    draw.rectangle([0, 0, width, 120], fill="#001F33")
    draw.text((40, 35), "FITNESS EVOLUTION MACHINE", fill=CYAN, font=f_mid)
    draw.text((width-240, 42), f"DAY {metrics['day_count']} OF 60", fill=CYAN, font=f_day) 
    draw.line([0, 120, width, 120], fill=CYAN, width=4)

    # --- PRIMARY BIO-METRICS ---
    draw.text((40, 150), "CURRENT MASS INDEX", fill=TEXT_GREY, font=f_reg)
    draw.text((40, 190), f"{metrics['weight']}", fill="#FFFFFF", font=f_huge)
    draw.text((440, 255), "KG", fill=CYAN, font=f_mid)
    draw.text((40, 310), f"PREDICTED TREND: {metrics.get('weekly_loss', 0)} KG / WEEK", fill=NEON_GREEN, font=f_reg)

    # RECALIBRATED CARD DIMENSIONS (W:310, H:460)
    col_w, start_y, card_h = 310, 420, 460 
    
    # ---------------------------------------------------------
    # 1. THERMODYNAMICS (MACRO DONUT + ALIGNED FOOTER)
    # ---------------------------------------------------------
    draw_glass_card(draw, 30, start_y, col_w, card_h, "Thermodynamics")
    
    latest = df.iloc[-1]
    p, c, f = latest.get('protein', 0), latest.get('carbs', 0), latest.get('fats', 0)
    total_in = int(latest.get('calories', 0))

    if total_in > 0:
        plt.style.use('dark_background')
        # Smaller figsize to reduce internal padding
        fig, ax = plt.subplots(figsize=(2.5, 2.5), facecolor=CARD_BG)
        macro_cals = [p*4, c*4, f*9]
        colors = [CYAN, GOLD, NEON_RED]
        
        ax.pie(macro_cals, colors=colors, startangle=90, wedgeprops=dict(width=0.45, edgecolor=CARD_BG))
        ax.set_facecolor(CARD_BG)
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=True, dpi=120)
        plt.close(fig)
        buf.seek(0)
        
        # Shifted UP (start_y + 30) to make room for legend
        donut_img = Image.open(buf).resize((220, 220))
        img.paste(donut_img, (75, start_y + 35), donut_img)
        
        # Legend: Placed clearly below donut, above footer
        draw.text((65, start_y + 265), f"P:{int(p)}g", fill=CYAN, font=f_day)
        draw.text((145, start_y + 265), f"C:{int(c)}g", fill=GOLD, font=f_day)
        draw.text((225, start_y + 265), f"F:{int(f)}g", fill=NEON_RED, font=f_day)

    # Grey Footer: Total Calories Consumed
    draw.rectangle([30, start_y + card_h - 60, 30 + col_w, start_y + card_h], fill=FOOTER_GREY)
    draw.text((50, start_y + card_h - 45), f"TOTAL INTAKE: {total_in} KCAL", fill=CYAN, font=f_day)

    # ---------------------------------------------------------
    # 2. BIO-CHEMICAL STACK (STAYING AS IS)
    # ---------------------------------------------------------
    draw_glass_card(draw, 385, start_y, col_w, card_h, "Bio-Chemical Stack")
    keto_col = NEON_GREEN if metrics['keto'] else NEON_RED
    draw.text((400, start_y+30), f"KETOSIS: {'ACTIVE' if metrics['keto'] else 'OFF'}", fill=keto_col, font=f_reg)
    supps = ["ECA Stack", "Berberine", "MCT Oil", "Chromium", "Gymnema", "R-ALA", "Mg Glycinate"]
    for i, s in enumerate(supps):
        draw.text((400, start_y+90+(i*42)), f"• {s}", fill=CYAN, font=f_reg)

    # ---------------------------------------------------------
    # 3. PHYSICAL OUTPUT (FIXED ALIGNMENT + FOOTER)
    # ---------------------------------------------------------
    draw_glass_card(draw, 740, start_y, col_w, card_h, "Physical Output")
    total_burned = 0
    if not workouts_today.empty:
        total_burned = int(workouts_today['burned'].sum())
        exercise_data = workouts_today.groupby('exercise')['burned'].sum().sort_values()
        
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(3, 3), facecolor=CARD_BG)
        bars = ax.barh(exercise_data.index, exercise_data.values, color=CYAN, height=0.6)
        
        ax.set_facecolor(CARD_BG)
        ax.axis('off') # Clean look
        
        for bar in bars:
            ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2, f'{int(bar.get_width())}', 
                    va='center', ha='left', color=NEON_GREEN, fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=True, dpi=120)
        plt.close(fig)
        buf.seek(0)
        chart_img = Image.open(buf).resize((270, 240))
        # Pasted higher to prevent footer overlap
        img.paste(chart_img, (760, start_y + 40), chart_img)

    # Grey Footer: Total Calories Burned
    draw.rectangle([740, start_y + card_h - 60, 740 + col_w, start_y + card_h], fill=FOOTER_GREY)
    draw.text((755, start_y + card_h - 45), f"TOTAL BURNED: {total_burned} KCAL", fill=NEON_GREEN, font=f_day)

    # ---------------------------------------------------------
    # FOOTER: WEIGHT TREND (PUSHED DOWN)
    # ---------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 3.5), facecolor=BG_DARK)
    recent = df.sort_values('date').tail(14)
    weights = pd.to_numeric(recent["weight"], errors='coerce').ffill().fillna(metrics['weight'])
    
    ax.plot(recent["date"], weights, color=CYAN, linewidth=4, marker='o', mfc=BG_DARK, markersize=10)
    ax.fill_between(recent["date"], weights, weights.min()-0.5, color=CYAN, alpha=0.1)
    
    # Annotation for the latest entry
    ax.annotate(f"{weights.iloc[-1]} KG", (recent["date"].iloc[-1], weights.iloc[-1]), 
                color="#FFFFFF", weight='bold', fontsize=16, xytext=(0, 15), 
                textcoords='offset points', ha='center')
    
    ax.set_title("MASS PROGRESSION (14-DAY WINDOW)", color=CYAN, fontweight='bold', fontsize=16, pad=25)
    ax.grid(color='#1E3D52', linestyle='--', alpha=0.3)
    plt.xticks(rotation=25, color=TEXT_GREY)
    plt.yticks(color=TEXT_GREY)
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=BG_DARK)
    plt.close(fig)
    buf.seek(0)
    # Pasted lower to clear the cards
    img.paste(Image.open(buf).resize((1020, 380)), (30, start_y + card_h + 50))

    # Motivation Signature
    sig_text = "PHYSIQUE: ASCENDING | FAT CELLS: TERMINATED"
    draw.text((width//2 - 350, height - 60), sig_text, fill=CYAN, font=f_reg)
    
    return img
