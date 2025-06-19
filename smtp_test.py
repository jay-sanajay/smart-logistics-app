import os
from dotenv import load_dotenv
from email.message import EmailMessage
import aiosmtplib
import asyncio

load_dotenv()

async def test_smtp():
    message = EmailMessage()
    message["From"] = os.getenv("SMTP_USERNAME")
    message["To"] = os.getenv("SMTP_USERNAME")
    message["Subject"] = "SMTP Test"
    message.set_content("If you got this, SMTP is working!")

    try:
        await aiosmtplib.send(
            message,
            hostname=os.getenv("SMTP_HOST"),
            port=int(os.getenv("SMTP_PORT")),
            start_tls=True,
            username=os.getenv("SMTP_USERNAME"),
            password=os.getenv("SMTP_PASSWORD"),
        )
        print("✅ SMTP test successful")
    except Exception as e:
        print("❌ SMTP test failed:", e)

asyncio.run(test_smtp())
