"""
oppytec-backend/src/adapters/email/resend_smtp_adapter.py
Adaptador de correo electrónico transaccional para `production` (Resend / SMTP),
con delegación automática al `SinkholeMailpitEmailAdapter` si se invoca fuera de `production`.
"""
from __future__ import annotations

import uuid

from src.adapters.email.protocol import EmailDeliveryReceipt, EmailMessage
from src.adapters.email.sinkhole_mailpit_adapter import SinkholeMailpitEmailAdapter
from src.core.config import Settings, get_settings


class ResendSmtpEmailAdapter:
    """
    Adaptador de despacho de correo vía Resend / SMTP para `production`.
    En `local`, `preview`, `ci` y `staging` enruta obligatoriamente por `SinkholeMailpitEmailAdapter`.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings: Settings = settings or get_settings()
        self._sinkhole = SinkholeMailpitEmailAdapter(settings=self._settings)
        self.sent_production_messages: list[EmailMessage] = []

    async def send_email(self, message: EmailMessage) -> EmailDeliveryReceipt:
        """Envía el mensaje en producción o lo filtra por el Sinkhole en entornos inferiores."""
        if self._settings.ENVIRONMENT != "production":
            return await self._sinkhole.send_email(message)

        self.sent_production_messages.append(message)
        return EmailDeliveryReceipt(
            message_id=f"resend-{uuid.uuid4()}",
            provider=self._settings.EMAIL_PROVIDER,
            recipient_email=message.recipient_email,
            sinkhole_intercepted=False,
            delivered=True,
        )
