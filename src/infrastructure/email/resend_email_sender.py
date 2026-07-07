from __future__ import annotations

import resend

from src.domain.ports.email_sender import EmailSender
from src.infrastructure.config import settings


class ResendEmailSender(EmailSender):
    def __init__(self) -> None:
        resend.api_key = settings.resend_api_key

    def send_password_reset(self, to_email: str, reset_token: str) -> None:
        resend.Emails.send({
            "from": settings.resend_from,
            "to": [to_email],
            "subject": "Recuperar contraseña — Job Match",
            "text": (
                f"Usá este token para restablecer tu contraseña:\n\n"
                f"{reset_token}\n\n"
                f"Expira en {settings.reset_token_ttl_minutes} minutos.\n\n"
                f"Si no solicitaste este cambio, ignorá este mensaje."
            ),
        })
