import io
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime

# Import the core processing from app and the renderer
from app import df, metrics, workouts_today, render_summary, st

def send_daily_email():
    # 1. Generate the Image using the existing renderer
    img = render_summary(df, metrics, workouts_today)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    # 2. Build the Email Message
    msg = MIMEMultipart("related")
    msg["From"] = st.secrets["email"]["sender_email"]
    msg["To"] = st.secrets["email"]["recipient_email"]
    msg["Subject"] = f"A.R.V.I.S. | DAILY REPORT | {datetime.now().strftime('%d %b')}"

    # HTML Body
    body = f"""
    <body style="background-color: #050A0E; color: #00F2FF; font-family: monospace; padding: 20px;">
        <h2 style="border-bottom: 2px solid #00F2FF;">SYSTEM STATUS: NOMINAL</h2>
        <p style="color: #A0B0B9;">Target: Eccentric Billionaire Genius. Protocol is active.</p>
        <img src="cid:hud" style="width:100%; max-width:800px; border: 1px solid #1E3D52;">
    </body>
    """
    msg.attach(MIMEText(body, "html"))

    # Attach the Image HUD
    img_part = MIMEImage(img_bytes)
    img_part.add_header("Content-ID", "<hud>")
    msg.attach(img_part)

    # 3. Send via SMTP
    try:
        with smtplib.SMTP(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"]) as server:
            server.starttls()
            server.login(st.secrets["email"]["sender_email"], st.secrets["email"]["app_password"])
            server.send_message(msg)
        print("✅ Daily report dispatched successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

if __name__ == "__main__":
    send_daily_email()
