import io
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# 👇 import only what we need from app
from app import (
    generate_summary_image,
    build_email_body
)

import streamlit as st  # needed for secrets

def send_email():
    img = generate_summary_image()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    msg = MIMEMultipart("related")
    msg["From"] = st.secrets["email"]["sender_email"]
    msg["To"] = st.secrets["email"]["recipient_email"]
    msg["Subject"] = "🔥 Fitness Evolution — Daily Summary"

    alt = MIMEMultipart("alternative")
    msg.attach(alt)
    alt.attach(MIMEText(build_email_body(), "html"))

    image = MIMEImage(buf.read())
    image.add_header("Content-ID", "<scorecard>")
    msg.attach(image)

    with smtplib.SMTP(
        st.secrets["email"]["smtp_server"],
        st.secrets["email"]["smtp_port"]
    ) as server:
        server.starttls()
        server.login(
            st.secrets["email"]["sender_email"],
            st.secrets["email"]["app_password"]
        )
        server.send_message(msg)

    print("✅ Email sent successfully")

if __name__ == "__main__":
    send_email()