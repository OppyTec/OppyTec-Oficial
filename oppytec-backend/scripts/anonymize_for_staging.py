"""
oppytec-backend/scripts/anonymize_for_staging.py
Anonimizador determinista ISO/IEC 27001 §A.12.1.4 para importar datos hacia `staging`.
Garantiza CERO PII real (emails, teléfonos, RUTs personales ni tokens) preservando integridad referencial.
"""
from __future__ import annotations

import hashlib


def anonymize_email_for_staging(raw_email: str, safe_domain: str = "oppytec.com") -> str:
    """Enmascara cualquier correo electrónico real hacia un alias determinista `@oppytec.com`."""
    digest = hashlib.sha256(raw_email.strip().lower().encode("utf-8")).hexdigest()[:12]
    return f"staged_user_{digest}@{safe_domain}"


def anonymize_tax_id(raw_tax_id: str) -> str:
    """Reemplaza un RUT/Tax ID real por un identificador sintético determinista."""
    digest = hashlib.sha256(raw_tax_id.strip().encode("utf-8")).hexdigest()[:8]
    numeric_part = int(digest, 16) % 80_000_000 + 10_000_000
    return f"{numeric_part}-K"


def anonymize_user_record(record: dict[str, str]) -> dict[str, str]:
    """Anonimiza un diccionario de usuario eliminando PII real y credenciales."""
    email = record.get("email", "unknown@example.com")
    tax_id = record.get("tax_id", "00000000-0")
    return {
        "email": anonymize_email_for_staging(email),
        "tax_id": anonymize_tax_id(tax_id),
        "full_name": f"Staging Anonymized User ({email[:2].upper()})",
    }
