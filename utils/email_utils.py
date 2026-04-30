import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# [CONFGURATION REQUIRED]
# Replace these with your actual Gmail account and App Password
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = "vpipavanshi@gmail.com"  # The sender email
EMAIL_PASS = "bttl rhll jixx sbtr"    # Your Google App Password (not regular password)

async def send_reset_otp_email(recipient_email: str, otp: str):
    """
    Sends a 6-digit OTP to the recipient's email using SMTP.
    """
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = recipient_email
    msg['Subject'] = "Smart Garbage - Your Password Reset OTP"

    body = f"""
    Hello,

    You requested a password reset for your Smart Garbage account.
    Your 6-digit verification code is:

    {otp}

    This code will expire shortly. If you did not request this, please ignore this email.

    Regards,
    Smart Garbage Team
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Create SMTP session
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() # Secure the connection
        
        # Login
        server.login(EMAIL_USER, EMAIL_PASS)
        
        # Send Email
        text = msg.as_string()
        server.sendmail(EMAIL_USER, recipient_email, text)
        
        # Close connection
        server.quit()
        
        print(f"--- EMAIL SENT SUCCESSFULLY ---")
        print(f"Recipient: {recipient_email}")
        print(f"Code: {otp}")
        print(f"-------------------------------\n")
        return True
    except Exception as e:
        print(f"--- EMAIL SENDING FAILED ---")
        print(f"Error: {e}")
        print(f"---------------------------\n")
        return False
