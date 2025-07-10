from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from typing import List
from config.settings import Settings
import logging

logger = logging.getLogger('uvicorn.error')

class EmailService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.SMTP_USER,
            MAIL_PASSWORD=settings.SMTP_PASSWORD,
            MAIL_FROM=settings.EMAILS_FROM_EMAIL,
            MAIL_PORT=settings.SMTP_PORT,
            MAIL_SERVER=settings.SMTP_HOST,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
            
        )
    async def send_account_setup_email(self, email_to: EmailStr, token: str):
        subject = "Set Up Your Account for mini-RAG"
        setup_link = f"{self.settings.FRONTEND_URL}/set-password?token={token}"
        body = f"""
        <p>Welcome to the IILA-RAG system!</p>
        <p>An account has been created for you. Please click the link below to set your password. This link is valid for 24 hours.</p>
        <p><a href="{setup_link}">{setup_link}</a></p>
        <p>If you did not request this, please ignore this email.</p>
        """
        message = MessageSchema(
            subject=subject,
            recipients=[email_to],
            body=body,
            subtype=MessageType.html
        )
        fm = FastMail(self.conf)
        try:
            await fm.send_message(message)
            logger.info(f"Account setup email sent to {email_to}")
        except Exception as e:
            logger.error(f"Failed to send account setup email to {email_to}: {e}")

    async def send_new_account_email(self, email_to: EmailStr, temporary_password: str):
        subject = "Your New Account for mini-RAG"
        body = f"""
        <p>Welcome to the mini-RAG system!</p>
        <p>An account has been created for you. Please log in using the following temporary password and change it immediately.</p>
        <p><b>Temporary Password:</b> {temporary_password}</p>
        """
        message = MessageSchema(
            subject=subject,
            recipients=[email_to],
            body=body,
            subtype=MessageType.html
        )
        fm = FastMail(self.conf)
        try:
            await fm.send_message(message)
            logger.info(f"New account email sent to {email_to}")
        except Exception as e:
            logger.error(f"Failed to send new account email to {email_to}: {e}")

    async def send_password_reset_email(self, email_to: EmailStr, token: str, frontend_url: str):
        subject = "Password Reset Request for mini-RAG"
        reset_link = f"{frontend_url}/reset-password?token={token}"
        body = f"""
        <p>You requested a password reset for your mini-RAG account.</p>
        <p>Please click the link below to set a new password. This link is valid for 15 minutes.</p>
        <p><a href="{reset_link}">{reset_link}</a></p>
        <p>If you did not request this, please ignore this email.</p>
        """
        message = MessageSchema(
            subject=subject,
            recipients=[email_to],
            body=body,
            subtype=MessageType.html
        )
        fm = FastMail(self.conf)
        try:
            await fm.send_message(message)
            logger.info(f"Password reset email sent to {email_to}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email_to}: {e}")