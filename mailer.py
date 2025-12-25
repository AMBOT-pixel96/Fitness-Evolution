import io
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
from app import df, metrics, workouts_today, render_summary, st

def send_daily_email():
    img = render_summary(df, metrics, workouts_today)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    msg = MIMEMultipart("related")
    msg["From"] = st.secrets["email"]["sender_email"]
    msg["To"] = st.secrets["email"]["recipient_email"]
    msg["Subject"] = f"A.R.V.I.S. | DAILY REPORT | {datetime.now().strftime('%d %b')}"

    app_url = "https://fitness-evolution.streamlit.app" 

    body = f"""
    <body style="background-color: #050A0E; color: #00F2FF; font-family: monospace; padding: 20px;">
        <h2 style="border-bottom: 2px solid #00F2FF;">SYSTEM STATUS: NOMINAL</h2>
        <img src="cid:hud" style="width:100%; max-width:800px; border: 1px solid #1E3D52;">
        <div style="margin-top: 30px; text-align: center;">
            <a href="{app_url}" style="background-color: #00F2FF; color: #050A0E; padding: 18px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
               OPEN INPUT TERMINAL
            </a>
        </div>
    </body>
    """
    msg.attach(MIMEText(body, "html"))

    img_part = MIMEImage(img_bytes)
    img_part.add_header("Content-ID", "<hud>")
    msg.attach(img_part)

    with smtplib.SMTP(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"]) as server:
        server.starttls()
        server.login(st.secrets["email"]["sender_email"], st.secrets["email"]["app_password"])
        server.send_message(msg)
    print("✅ System: Daily Dispatch Successful.")

if __name__ == "__main__":
    send_daily_email()
