# render/render.py
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import io

WIDTH, HEIGHT = 1080, 1920
BG = "#0E1117"
TEXT = "#E6EDF3"
BLUE = "#58A6FF"
GREEN = "#2ECC71"
RED = "#E74C3C"
AMBER = "#F1C40F"


def metric_color(value, good=True):
    if value is None:
        return TEXT
    if good:
        return GREEN if value > 0 else RED
    return RED if value > 0 else GREEN


def plot_weight(df):
    fig, ax = plt.subplots(figsize=(6, 3))
    recent = df.tail(14)
    ax.plot(recent["date"], recent["weight"], marker="o")
    ax.set_title("Weight Trend (14 days)")
    ax.grid(alpha=0.3)
    plt.xticks(rotation=45)

    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, dpi=160)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf)


def render_summary(df, metrics):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(img)

    try:
        f_big = ImageFont.truetype("DejaVuSans-Bold.ttf", 64)
        f_mid = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
        f_sm  = ImageFont.truetype("DejaVuSans.ttf", 32)
    except:
        f_big = f_mid = f_sm = ImageFont.load_default()

    # Header
    d.text((60, 40), "FITNESS EVOLUTION", fill=TEXT, font=f_big)
    d.text((60, 120), "Daily Performance Snapshot", fill=BLUE, font=f_sm)

    y = 200
    gap = 60

    d.text((60, y), f"Weight: {metrics['weight']} kg", fill=TEXT, font=f_mid); y += gap
    d.text((60, y), f"Maintenance: {metrics['maintenance']} kcal", fill=TEXT, font=f_mid); y += gap

    d.text(
        (60, y),
        f"Net Calories: {metrics['net']}",
        fill=metric_color(-metrics["net"]),
        font=f_mid
    )
    y += gap

    d.text(
        (60, y),
        f"Deficit %: {metrics['deficit']}%",
        fill=metric_color(metrics["deficit"]),
        font=f_mid
    )
    y += gap

    d.text(
        (60, y),
        f"Keto: {'YES' if metrics['keto'] else 'NO'}",
        fill=GREEN if metrics["keto"] else RED,
        font=f_mid
    )

    # Charts
    CHART_Y = 700
    img.paste(plot_weight(df), (60, CHART_Y))

    return img