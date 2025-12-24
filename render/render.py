# render/render.py
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import numpy as np
import matplotlib.pyplot as plt

# --- STARK HUD THEME ---
CYAN = "#00F2FF"
DEEP_BLUE = "#001A2E"
BG_DARK = "#050A0E"
GLOW_CYAN = "#00E5FF"
NEON_GREEN = "#39FF14"
NEON_RED = "#FF3131"
TEXT_GREY = "#A0B0B9"

def draw_glass_card(draw, x, y, w, h, title=""):
    """Draws a futuristic semi-transparent glass container"""
    # Card Body
    draw.rectangle([x, y, x+w, y+h], fill="#0A1926", outline="#1E3D52", width=2)
    # Glossy Top Edge
    draw.line([x, y, x+w, y], fill="#3E7DA3", width=3)
    # Title
    try:
        f_small = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
    except:
        f_small = ImageFont.load_default()
    draw.text((x+15, y-35), title.upper(), fill=CYAN, font=f_small)

def render_summary(df, metrics):
    width, height = 1080, 1080  # Square HUD for maximum impact
    img = Image.new("RGB", (width, height), BG_DARK)
    draw = ImageDraw.Draw(img)
    
    try:
        f_huge = ImageFont.truetype("DejaVuSans-Bold.ttf", 100)
        f_mid = ImageFont.truetype("DejaVuSans-Bold.ttf", 45)
        f_reg = ImageFont.truetype("DejaVuSans.ttf", 30)
    except:
        f_huge = f_mid = f_reg = ImageFont.load_default()

    # --- TOP BAR: ASCENSION PROTOCOL ---
    draw.rectangle([0, 0, width, 120], fill="#001F33")
    draw.text((40, 35), "ASCENSION PROTOCOL", fill=CYAN, font=f_mid)
    draw.text((width-380, 35), f"DAY {len(df)} OF 90", fill=CYAN, font=f_mid)
    draw.line([0, 120, width, 120], fill=CYAN, width=4)

    # --- MAIN BIOMETRIC (CENTER TOP) ---
    draw.text((40, 160), f"{metrics['weight']}", fill="#FFFFFF", font=f_huge)
    draw.text((360, 210), "KG", fill=CYAN, font=f_mid)
    draw.text((40, 270), f"PROJECTION: {metrics.get('weekly_loss', 0)} KG/WEEK", fill=NEON_GREEN, font=f_reg)

    # --- THREE COLUMN HUD ---
    col_w = 310
    start_y = 380
    card_h = 350
    
    # 1. THERMODYNAMICS (Calories)
    draw_glass_card(draw, 30, start_y, col_w, card_h, "Thermodynamics")
    draw.text((50, start_y+30), f"MAINTENANCE: {metrics['maintenance']}", fill=TEXT_GREY, font=f_reg)
    # Deficit Bar
    bar_h = 200
    draw.rectangle([60, start_y+80, 90, start_y+80+bar_h], fill="#1E3D52")
    fill_h = int(bar_h * (metrics['deficit']/100))
    draw.rectangle([60, start_y+80+(bar_h-fill_h), 90, start_y+80+bar_h], fill=NEON_RED)
    draw.text((110, start_y+150), f"NET: {metrics['net']}", fill="#FFFFFF", font=f_mid)

    # 2. BIO-CHEMICAL STACK (Keto/Status)
    draw_glass_card(draw, 385, start_y, col_w, card_h, "Bio-Chemical Stack")
    keto_col = NEON_GREEN if metrics['keto'] else NEON_RED
    draw.text((405, start_y+50), "KETOSIS:", fill=TEXT_GREY, font=f_reg)
    draw.text((405, start_y+90), "CONFIRMED" if metrics['keto'] else "OFFLINE", fill=keto_col, font=f_mid)
    draw.text((405, start_y+180), "• MCT OIL: ACTIVE", fill=CYAN, font=f_reg)
    draw.text((405, start_y+230), "• BERBERINE: ON", fill=CYAN, font=f_reg)

    # 3. PHYSICAL OUTPUT
    draw_glass_card(draw, 740, start_y, col_w, card_h, "Physical Output")
    draw.text((760, start_y+50), "WORKOUT: STABLE", fill=NEON_GREEN, font=f_reg)
    draw.ellipse([840, start_y+150, 940, start_y+250], outline=CYAN, width=5) # Mini Gauge
    draw.text((865, start_y+185), "100%", fill="#FFFFFF", font=f_reg)

    # --- BOTTOM CHART: THE BILLIONAIRE GOAL ---
    # We use Matplotlib to generate the line but style it to match the HUD
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 3), facecolor=BG_DARK)
    recent = df.tail(14)
    ax.plot(recent["date"], recent["weight"], color=CYAN, linewidth=4)
    ax.fill_between(recent["date"], recent["weight"], min(recent['weight'])-1, color=CYAN, alpha=0.2)
    ax.set_title("ACTUAL WEIGHT (14D) - BILLIONAIRE GOAL", color=CYAN, fontweight='bold')
    ax.axis('off')
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=BG_DARK)
    plt.close(fig)
    buf.seek(0)
    chart_img = Image.open(buf).resize((1000, 250))
    img.paste(chart_img, (40, 750))

    # --- FOOTER MOTIVATION ---
    footer_text = "PHYSIQUE: ASCENDING. FAT CELLS: SCREAMING."
    draw.text((width//2 - 350, height-60), footer_text, fill=CYAN, font=f_reg)

    return img
