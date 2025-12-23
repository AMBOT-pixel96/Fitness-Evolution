import io
import streamlit as st
from app import (
    df,
    latest,
    W,
    maintenance,
    deficit_pct,
    weekly_loss,
    render_summary,
    build_email_body,
    send_email
)

def main():
    metrics = {
        "weight": W,
        "maintenance": maintenance,
        "net": int(latest["Net"]),
        "deficit": deficit_pct,
        "keto": bool(latest["Keto"])
    }

    img = render_summary(df, metrics)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    send_email(buf.getvalue())
    print("✅ Daily email sent")

if __name__ == "__main__":
    main()