"""
oppytec-backend/src/adapters/email/protocol.py
Contrato (`EmailPort`) y DTOs inmutables (`EmailMessage`, `EmailDeliveryReceipt`) para envío de correos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class EmailMessage:
    """Mensaje de correo electrónico tipado con clave de plantilla `i18n`."""

    recipient_email: str
    subject: str
    body_text: str
    body_html: str | None = None
    locale: str = "es"
    template_key: str = "common:emails.notification"
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EmailDeliveryReceipt:
    """Comprobante inmutable de entrega o intercepción Sinkhole de correo."""

    message_id: str
    provider: str
    recipient_email: str
    sinkhole_intercepted: bool
    delivered: bool


@runtime_checkable
class EmailPort(Protocol):
    """Puerto asíncrono de despacho de correo electrónico."""

    async def send_email(self, message: EmailMessage) -> EmailDeliveryReceipt:
        """Envía o intercepta un `EmailMessage` devolviendo `EmailDeliveryReceipt`."""
        ...
