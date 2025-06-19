import smtplib
from email.mime.text import MIMEText

msg = MIMEText("✅ This is a test email from FastAPI Gmail SMTP setup.")
msg["Subject"] = "SMTP Test"
msg["From"] = "jaytakalgavankar@gmail.com"
msg["To"] = "yourfriend@example.com"  # Replace with your second email

try:
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login("jaytakalgavankar@gmail.com", "psgi kdqa qppj opeu")
        server.send_message(msg)
        print("✅ Email sent successfully!")
except Exception as e:
    print("❌ Error sending email:", e)
