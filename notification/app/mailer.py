import smtplib
from email.message import EmailMessage
import logging
from notification.app.config import settings

logger = logging.getLogger(__name__)

def send_onboarding_email(email: str, device_id: str, request_id: int, owner_address: str):
    msg = EmailMessage()
    msg['Subject'] = f"Action Required: Onboarding Request for Device {device_id}"
    msg['From'] = "system@s4t-trust-hpc.local"
    msg['To'] = email

    content = f"""
Hello,

An onboarding request has been submitted for device:
Device ID: {device_id}
Request ID: {request_id}
Owner Address: {owner_address}

Please review this request. You can approve or reject it using your owner wallet on the platform.

Best regards,
S4T Trust HPC System
"""
    msg.set_content(content)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.send_message(msg)
        logger.info(f"Notification email sent to {email} for request {request_id}")
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")
