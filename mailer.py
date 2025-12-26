import engine
import toml
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
import io

def send_eod_report():
    # 1. Load Secrets Manually (No Streamlit)
    secrets = toml.load(".streamlit/secrets.toml")
    
    # 2. Get Data & Render via Engine
    df, metrics, workouts_today = engine.fetch_and_process(secrets["gcp_service_account"])
    from render.render import render_summary
    img = render_summary(df, metrics, workouts_today)
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    # 3. SMTP Logic
    msg = MIMEMultipart("related")
    msg["From"] = secrets["email"]["sender_email"]
    msg["To"] = secrets["email"]["recipient_email"]
    msg["Subject"] = f"A.R.V.I.S. | EOD REPORT | {datetime.now().strftime('%d %b')}"

    body = f"""<body style="background-color: #050A0E; color: #00F2FF; font-family: monospace; padding: 20px;">
        <h2>SYSTEM STATUS: NOMINAL</h2>
        <img src="cid:hud" style="width:100%; max-width:800px; border: 1px solid #1E3D52;">
        </body>"""
    msg.attach(MIMEText(body, "html"))
    img_part = MIMEImage(img_bytes)
    img_part.add_header("Content-ID", "<hud>")
    msg.attach(img_part)

    with smtplib.SMTP(secrets["email"]["smtp_server"], secrets["email"]["smtp_port"]) as s:
        s.starttls()
        s.login(secrets["email"]["sender_email"], secrets["email"]["app_password"])
        s.send_message(msg)
    print("🚀 A.R.V.I.S. dispatched the report successfully.")

if __name__ == "__main__":
    send_eod_report()
