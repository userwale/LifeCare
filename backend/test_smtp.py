"""
Standalone SMTP diagnostic script.
Run: python test_smtp.py
"""
import smtplib
import ssl
import sys
import io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import dotenv_values

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load .env
env = dotenv_values(".env")
HOST     = env.get("SMTP_HOST", "smtp.gmail.com")
PORT     = int(env.get("SMTP_PORT", "587"))
USERNAME = env.get("SMTP_USERNAME", "")
PASSWORD = env.get("SMTP_PASSWORD", "")
FROM     = env.get("SMTP_FROM_EMAIL", USERNAME)
TO       = env.get("ADMIN_EMAIL", USERNAME)

print("=" * 60)
print("SMTP DIAGNOSTIC")
print("=" * 60)
print(f"  Host:     {HOST}")
print(f"  Port:     {PORT}")
print(f"  Username: {USERNAME}")
print(f"  Password: {'*' * len(PASSWORD)} ({len(PASSWORD)} chars)")
print(f"  From:     {FROM}")
print(f"  To:       {TO}")
print()

if not USERNAME or not PASSWORD:
    print("[FAIL] SMTP_USERNAME or SMTP_PASSWORD is empty in .env!")
    exit(1)

# Build test message
msg = MIMEMultipart("alternative")
msg["Subject"] = "LifeCare - SMTP Test (code: 123456)"
msg["From"]    = f"LifeCare <{FROM}>"
msg["To"]      = TO
msg.attach(MIMEText("Your test OTP code is: 123456", "plain", "utf-8"))
msg.attach(MIMEText("<h1>Test OTP: 123456</h1><p>SMTP is working!</p>", "html", "utf-8"))

# Try multiple methods
methods = [
    ("SMTP_SSL (port 465)",        465, "ssl"),
    ("SMTP + STARTTLS (port 587)", 587, "starttls"),
]

for name, port_try, mode in methods:
    print(f"--- Trying: {name} ---")
    try:
        if mode == "ssl":
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(HOST, port_try, context=context, timeout=15)
        else:
            server = smtplib.SMTP(HOST, port_try, timeout=15)
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()

        print(f"  [OK] Connected to {HOST}:{port_try}")

        server.login(USERNAME, PASSWORD)
        print(f"  [OK] Login successful as {USERNAME}")

        server.send_message(msg)
        print(f"  [OK] Email sent to {TO}")

        server.quit()
        print(f"\n>>> SUCCESS with {name}! Check your inbox at {TO}")
        print(f"    Use SMTP_PORT={port_try} in your .env")
        exit(0)

    except smtplib.SMTPAuthenticationError as e:
        print(f"  [FAIL] Authentication FAILED: {e}")
        print(f"     Your App Password may be invalid or revoked.")
        print(f"     Generate a new one: https://myaccount.google.com/apppasswords")
    except smtplib.SMTPConnectError as e:
        print(f"  [FAIL] Connection FAILED: {e}")
    except TimeoutError:
        print(f"  [FAIL] Connection TIMED OUT on port {port_try}")
        print(f"     Your network/firewall may be blocking this port.")
    except OSError as e:
        print(f"  [FAIL] Network error: {e}")
    except Exception as e:
        print(f"  [FAIL] Error: {type(e).__name__}: {e}")
    print()

print("=" * 60)
print("[FAIL] ALL METHODS FAILED")
print("   Possible causes:")
print("   1. Gmail App Password is invalid -> regenerate at myaccount.google.com/apppasswords")
print("   2. Network/firewall blocks ports 465 and 587")
print("   3. Antivirus is intercepting SMTP connections")
print("=" * 60)
