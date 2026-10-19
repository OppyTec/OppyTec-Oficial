"""
Vector Red Team 11 (`tests/security_redteam/test_11_environment_boundary_and_failfast.py`):
- Guardia de contaminación Cross-Environment: bloquea que `local`, `preview` o `ci` apunten a bases de datos
  o Redis de `staging` o `production`.
- Fail-Fast en el milisegundo 0 ante claves secretas débiles (`< 32 chars`, baja entropía Shannon `< 3.0` o substrings prohibidos).
- Desactivación estricta de OpenAPI (`/docs`, `/redoc`, `/openapi.json` -> HTTP 404) cuando `ENVIRONMENT == "production"`.
- Obligatoriedad del Sinkhole Mailpit en entornos no productivos (bloqueo HTTP 403 ante dominios externos fuera de `SAFE_OUTBOUND_EMAIL_DOMAINS`).
"""
from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from src.adapters.email.protocol import EmailMessage
from src.adapters.email.sinkhole_mailpit_adapter import SinkholeMailpitEmailAdapter
from src.core.config import Settings, get_settings
from src.core.exceptions import OppyTecError
from src.main import create_app

pytestmark = pytest.mark.security_redteam


def test_cross_environment_contamination_blocked_for_local_preview_and_ci() -> None:
    """Verifica que `local`, `preview` y `ci` fallen en el milisegundo 0 si apuntan a hosts de `staging` o `production`."""
    for non_prod_env in ("local", "preview", "ci"):
        with pytest.raises(ValidationError, match="CrossEnvironmentViolation"):
            Settings(
                ENVIRONMENT=non_prod_env,
                DATABASE_URL=SecretStr(
                    "postgresql+asyncpg://user:pass@oppytec-prod-db.internal:5432/oppytec"
                ),
            )
        with pytest.raises(ValidationError, match="CrossEnvironmentViolation"):
            Settings(
                ENVIRONMENT=non_prod_env,
                REDIS_URL=SecretStr("redis://redis-staging.oppytec.internal:6379/0"),
            )


def test_failfast_on_weak_secret_length_or_low_shannon_entropy() -> None:
    """Verifica que `Settings` rechace claves `< 32` caracteres, repetitivas o con substrings débiles."""
    # Clave demasiado corta (< 32 chars)
    with pytest.raises(ValidationError, match="Fail-Fast Security Error"):
        Settings(SECRET_KEY=SecretStr("short_key_123!"))

    # Clave de 40 caracteres pero baja entropía Shannon ("aaaaaaaaaa...")
    with pytest.raises(ValidationError, match="Fail-Fast Security Error"):
        Settings(JWT_ACCESS_SECRET_KEY=SecretStr("a" * 40))

    # Clave con substring débil conocido ("changeme")
    with pytest.raises(ValidationError, match="Fail-Fast Security Error"):
        Settings(
            JWT_REFRESH_SECRET_KEY=SecretStr("changeme_9x8B7v6N5m4L3k2J1h0G!@#_extra_long")
        )


async def test_openapi_endpoints_return_404_in_production_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que en `ENVIRONMENT='production'` las rutas `/docs`, `/redoc` y `/openapi.json` respondan HTTP 404."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", '["https://app.oppytec.com"]')
    monkeypatch.setenv("STORAGE_PROVIDER", "r2")
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    get_settings.cache_clear()

    try:
        prod_app = create_app()
        transport = httpx.ASGITransport(app=prod_app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            for doc_route in ("/docs", "/redoc", "/openapi.json"):
                resp = await client.get(doc_route)
                assert resp.status_code == 404, (
                    f"Expected 404 for {doc_route} in production, got {resp.status_code}"
                )
    finally:
        get_settings.cache_clear()


async def test_sinkhole_mailpit_blocks_external_domains_in_non_production() -> None:
    """
    Verifica que `SinkholeMailpitEmailAdapter` permita dominios en `SAFE_OUTBOUND_EMAIL_DOMAINS`
    y lance `OppyTecError` (HTTP 403 `UNSAFE_OUTBOUND_EMAIL_DOMAIN`) ante dominios de clientes externos.
    """
    settings = Settings(
        ENVIRONMENT="local",
        EMAIL_PROVIDER="mailpit",
        SAFE_OUTBOUND_EMAIL_DOMAINS=["oppytec.com"],
    )
    sinkhole = SinkholeMailpitEmailAdapter(settings=settings)

    safe_receipt = await sinkhole.send_email(
        EmailMessage(
            recipient_email="qa.auditor@oppytec.com",
            subject="Alerta QA",
            body_text="Prueba controlada",
            body_html="<p>Prueba controlada</p>",
        )
    )
    assert safe_receipt.sinkhole_intercepted is True
    assert safe_receipt.delivered is True

    with pytest.raises(OppyTecError) as exc_info:
        await sinkhole.send_email(
            EmailMessage(
                recipient_email="cliente.real@gmail.com",
                subject="Fuga de correo",
                body_text="No debe salir jamás",
                body_html="<p>No debe salir jamás</p>",
            )
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "UNSAFE_OUTBOUND_EMAIL_DOMAIN"
