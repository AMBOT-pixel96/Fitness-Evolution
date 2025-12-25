import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app import st # To get your secrets

def send_reminder():
    msg = MIMEMultipart()
    msg["From"] = st.secrets["email"]["sender_email"]
    msg["To"] = st.secrets["email"]["recipient_email"]
    msg["Subject"] = "⚠️ ACTION REQUIRED: LOG DAILY METRICS"

    app_url = "https://fitness-evolution.streamlit.app" 
    
    body = f"""
    <body style="background-color: #050A0E; color: #00F2FF; font-family: monospace; padding: 40px; text-align: center;">
        <h1 style="border-bottom: 2px solid #00F2FF; padding-bottom: 10px;">EVOLUTION UPLINK</h1>
        <p style="font-size: 16px; color: #A0B0B9;">The machine requires data to calculate today's progress.</p>
        <div style="margin: 40px 0;">
            <a href="{app_url}" style="background-color: #00F2FF; color: #050A0E; padding: 20px 40px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 18px; border: 2px solid #00F2FF;">
               🚀 OPEN INPUT TERMINAL
            </a>
        </div>
        <p style="color: #FF3131; font-size: 12px;">Final report will be generated at 10:30 PM IST.</p>
    </body>
    """
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"]) as server:
        server.starttls()
        server.login(st.secrets["email"]["sender_email"], st.secrets["email"]["app_password"])
        server.send_message(msg)
    print("✅ Reminder Sent.")

if __name__ == "__main__":
    send_reminder()
