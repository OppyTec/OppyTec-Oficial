"""
oppytec-backend/src/adapters/email/sinkhole_mailpit_adapter.py
Interceptor obligatorio en entornos `local`, `preview`, `ci` y `staging` que bloquea cualquier envío
a dominios externos fuera de `SAFE_OUTBOUND_EMAIL_DOMAINS` (prevención de fuga de correos a clientes reales).
"""
from __future__ import annotations

import uuid

from src.adapters.email.protocol import EmailDeliveryReceipt, EmailMessage
from src.core.config import Settings, get_settings
from src.core.exceptions import OppyTecError


def extract_email_domain(email_address: str) -> str:
    """Extrae el dominio en minúsculas de una dirección de correo electrónico."""
    cleaned = email_address.strip().lower()
    if "@" not in cleaned:
        raise ValueError(f"Invalid email address '{email_address}'.")
    return cleaned.rsplit("@", 1)[1]


class SinkholeMailpitEmailAdapter:
    """
    Adaptador Sinkhole (Mailpit / memoria) obligatorio para entornos no productivos.
    Rechaza cualquier destinatario cuyo dominio no pertenezca a `SAFE_OUTBOUND_EMAIL_DOMAINS`.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings: Settings = settings or get_settings()
        self.captured_messages: list[EmailMessage] = []

    def is_recipient_domain_allowed(self, recipient_email: str) -> bool:
        """Verifica que el dominio del destinatario esté permitido en `SAFE_OUTBOUND_EMAIL_DOMAINS`."""
        domain = extract_email_domain(recipient_email)
        allowed_domains = {
            d.strip().lower().lstrip("@")
            for d in self._settings.SAFE_OUTBOUND_EMAIL_DOMAINS
            if d.strip()
        }
        return domain in allowed_domains

    async def send_email(self, message: EmailMessage) -> EmailDeliveryReceipt:
        """
        Intercepta el correo en el Sinkhole si el dominio está en `SAFE_OUTBOUND_EMAIL_DOMAINS`,
        o lanza `OppyTecError` (HTTP 403) si intenta salir hacia un dominio externo no autorizado.
        """
        if not self.is_recipient_domain_allowed(message.recipient_email):
            domain = extract_email_domain(message.recipient_email)
            raise OppyTecError(
                f"SinkholeEmailBlocked: Outbound email to external domain '{domain}' is forbidden "
                f"in environment '{self._settings.ENVIRONMENT}'.",
                i18n_key="common:errors.unsafe_outbound_email_domain",
                status_code=403,
                error_code="UNSAFE_OUTBOUND_EMAIL_DOMAIN",
                context={"domain": domain, "environment": self._settings.ENVIRONMENT},
            )
        self.captured_messages.append(message)
        return EmailDeliveryReceipt(
            message_id=f"mailpit-{uuid.uuid4()}",
            provider="mailpit_sinkhole",
            recipient_email=message.recipient_email,
            sinkhole_intercepted=True,
            delivered=True,
        )
