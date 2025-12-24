# render/render.py
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np

# --- THEME DESIGN ---
BG_COLOR = "#0E1117"     # Deep Space Dark
CARD_COLOR = "#161B22"   # Slate Card
TEXT_COLOR = "#E6EDF3"   # Off-White
ACCENT_BLUE = "#58A6FF"  # High-Tech Blue
ACCENT_GREEN = "#238636" # Success Green
ACCENT_RED = "#DA3633"   # Alert Red

def create_styled_charts(df, metrics):
    """Generates a composite of visualizations using Matplotlib"""
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(10, 10), facecolor=BG_COLOR)
    
    # 1. Weight Trend (Top)
    ax1 = plt.subplot2grid((2, 2), (0, 0), colspan=2)
    recent = df.tail(14)
    ax1.plot(recent["date"], recent["weight"], color=ACCENT_BLUE, marker='o', linewidth=3, markersize=8)
    ax1.fill_between(recent["date"], recent["weight"], min(recent["weight"])-0.5, color=ACCENT_BLUE, alpha=0.15)
    ax1.set_title("BIOMETRIC TREND: WEIGHT (14D)", fontsize=14, pad=15, color=ACCENT_BLUE, fontweight='bold')
    ax1.grid(color='#30363D', linestyle='--', alpha=0.3)
    for spine in ax1.spines.values(): spine.set_visible(False)

    # 2. Macro Distribution (Bottom Left)
    ax2 = plt.subplot2grid((2, 2), (1, 0))
    latest = df.iloc[-1]
    macro_vals = [latest['protein'], latest['carbs'], latest['fats']]
    macro_labels = ['PRO', 'CHO', 'FAT']
    colors = [ACCENT_BLUE, "#79C0FF", ACCENT_GREEN]
    
    wedges, texts, autotexts = ax2.pie(macro_vals, labels=macro_labels, autopct='%1.0f%%', 
                                      colors=colors, startangle=140, pctdistance=0.8)
    plt.setp(autotexts, size=10, weight="bold")
    # Draw donut hole
    centre_circle = plt.Circle((0,0), 0.70, fc=BG_COLOR)
    ax2.add_artist(centre_circle)
    ax2.set_title("FUEL COMPOSITION", fontsize=12, fontweight='bold')

    # 3. Energy Balance (Bottom Right)
    ax3 = plt.subplot2grid((2, 2), (1, 1))
    # Net vs Maintenance
    categories = ['Net', 'Maint']
    vals = [metrics['net'], metrics['maintenance']]
    bars = ax3.bar(categories, vals, color=[ACCENT_RED if metrics['net'] > 0 else ACCENT_GREEN, '#30363D'])
    ax3.set_title("ENERGY DIFFERENTIAL", fontsize=12, fontweight='bold')
    for spine in ax3.spines.values(): spine.set_visible(False)
    ax3.yaxis.set_visible(False)

    plt.tight_layout(pad=4.0)
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=BG_COLOR, dpi=120)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf)

def render_summary(df, metrics):
    """Main rendering engine for the Daily Scorecard"""
    width, height = 1080, 1920
    img = Image.new("RGB", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Font Handling (Fallback for different environments)
    try:
        f_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 70)
        f_val = ImageFont.truetype("DejaVuSans-Bold.ttf", 90)
        f_lab = ImageFont.truetype("DejaVuSans.ttf", 35)
    except:
        f_title = f_val = f_lab = ImageFont.load_default()

    # --- HEADER ---
    draw.text((60, 80), "SYSTEM: FITNESS EVOLUTION", fill=TEXT_COLOR, font=f_title)
    draw.line((60, 170, 1020, 170), fill=ACCENT_BLUE, width=4)

    # --- DATA GRID (The HUD) ---
    def draw_stat(x, y, label, value, color):
        draw.text((x, y), label, fill="#8B949E", font=f_lab)
        draw.text((x, y+55), str(value), fill=color, font=f_val)

    # Row 1
    draw_stat(60, 240, "CURRENT MASS", f"{metrics['weight']} KG", TEXT_COLOR)
    draw_stat(580, 240, "METABOLIC CAP", f"{metrics['maintenance']} KCAL", ACCENT_BLUE)
    
    # Row 2
    draw_stat(60, 460, "CALORIE DEFICIT", f"{metrics['deficit']}%", ACCENT_GREEN)
    keto_status = "STABLE" if metrics['keto'] else "OUT"
    keto_color = ACCENT_GREEN if metrics['keto'] else ACCENT_RED
    draw_stat(580, 460, "KETO PROTOCOL", keto_status, keto_color)

    # --- CHART INJECTION ---
    charts_img = create_styled_charts(df, metrics)
    # Resize slightly to fit the width well
    charts_img = charts_img.resize((960, 960))
    img.paste(charts_img, (60, 700))

    # --- FOOTER ---
    draw.rectangle([0, height-120, width, height], fill=ACCENT_BLUE)
    footer_text = "GENIUS PLAYBOY EDITION | PERFORMANCE LOG"
    draw.text((width//2 - 350, height-85), footer_text, fill=BG_COLOR, font=f_lab)

    return img
