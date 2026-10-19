"""
oppytec-backend/src/adapters/email/__init__.py
Adaptadores de correo electrónico transaccional (`ResendSmtpEmailAdapter`) y Sinkhole seguro (`SinkholeMailpitEmailAdapter`).
"""
from __future__ import annotations

from src.adapters.email.protocol import EmailDeliveryReceipt, EmailMessage, EmailPort
from src.adapters.email.resend_smtp_adapter import ResendSmtpEmailAdapter
from src.adapters.email.sinkhole_mailpit_adapter import SinkholeMailpitEmailAdapter

__all__ = [
    "EmailDeliveryReceipt",
    "EmailMessage",
    "EmailPort",
    "ResendSmtpEmailAdapter",
    "SinkholeMailpitEmailAdapter",
]
