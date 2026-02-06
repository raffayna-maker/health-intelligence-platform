"""Email service for sending appointment reminders via Gmail SMTP."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import get_settings

settings = get_settings()


class EmailService:
    """Service for sending emails via Gmail SMTP."""

    def __init__(self):
        self.gmail_address = settings.gmail_address
        self.gmail_password = settings.gmail_app_password
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def send_appointment_reminder(
        self,
        to_email: str,
        patient_name: str,
        days_since_last_appointment: int,
    ) -> dict:
        """Send an appointment follow-up reminder email."""
        try:
            # Create message
            message = MIMEMultipart()
            message["From"] = self.gmail_address
            message["To"] = to_email
            message["Subject"] = "Time for Your Follow-up Appointment"

            # Email body
            body = f"""
Hello {patient_name},

We hope this message finds you well. Our records show it has been {days_since_last_appointment} days since your last appointment with us.

Your health is important to us, and we'd like to schedule a follow-up appointment to ensure you're receiving the best care possible.

Please call our office at your earliest convenience to schedule your next appointment, or reply to this email and we'll be happy to assist you.

Best regards,
Healthcare Intelligence Platform
            """.strip()

            message.attach(MIMEText(body, "plain"))

            # Connect to Gmail SMTP server and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.gmail_address, self.gmail_password)
                server.send_message(message)

            return {
                "success": True,
                "message": f"Email sent to {to_email}",
                "to": to_email,
                "patient": patient_name,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "to": to_email,
                "patient": patient_name,
            }


email_service = EmailService()
