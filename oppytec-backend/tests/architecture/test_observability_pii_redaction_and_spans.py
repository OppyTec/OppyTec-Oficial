"""
White-Box Architecture Gate: Observability 4-Pillars, `X-Trace-ID` & PII Redaction (`test_observability_pii_redaction_and_spans.py`).

Enforces `.agent/rules/17-observability-opentelemetry-sentry-and-umami.md`:
- Verifies `X-Trace-ID` injection in FastAPI responses.
- Verifies PII and secret redaction (`password`, `secret`, `token`, `authorization`, `cookie`) in telemetry payloads.
"""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from src.core.observability import scrub_telemetry_payload

pytestmark = pytest.mark.architecture

SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "secret",
        "secret_key",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "api_key",
        "dsn",
    }
)
REDACTED_MASK = "[REDACTED]"


def reference_scrub_telemetry_payload(payload: dict[str, object]) -> dict[str, object]:
    """Reference recursive PII scrubber matching Rule 17."""
    scrubbed: dict[str, object] = {}
    for key, val in payload.items():
        if any(s in key.lower() for s in SENSITIVE_KEYS):
            scrubbed[key] = REDACTED_MASK
        elif isinstance(val, dict):
            nested = {str(k): v for k, v in val.items()}
            scrubbed[key] = reference_scrub_telemetry_payload(nested)
        else:
            scrubbed[key] = val
    return scrubbed


async def test_observability_trace_id_and_pii_redaction(
    async_client: httpx.AsyncClient,
    monorepo_root: Path,
) -> None:
    """Verifies Rule 17, `X-Trace-ID` correlation header, and PII scrubbing."""
    rule_17 = (
        monorepo_root
        / ".agent"
        / "rules"
        / "17-observability-opentelemetry-sentry-and-umami.md"
    )
    skill_obs = monorepo_root / ".agent" / "skills" / "observability_telemetry" / "SKILL.md"
    assert rule_17.exists(), "Rule 17 (Observability 4-Pillars) must exist"
    assert skill_obs.exists(), "Skill observability_telemetry/SKILL.md must exist"

    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "X-Trace-ID" in resp.headers

    raw_event: dict[str, object] = {
        "user": "oppytec.admin",
        "password": "SuperSecretPassword123!",
        "headers": {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9",
            "X-Trace-ID": resp.headers["X-Trace-ID"],
        },
    }

    cleaned = scrub_telemetry_payload(raw_event)
    assert "SuperSecretPassword123!" not in str(cleaned)
    assert "eyJhbGciOiJIUzI1NiJ9" not in str(cleaned)


def test_five_environments_observability_configuration_matrix() -> None:
    """
    Certifica la matriz de gobernanza de los 5 entornos oficiales
    según .agent/estrategias/estrategia_observabilidad_monitoreo_y_analitica_001.md:
    1. local: OTEL_EXPORTER='none', SENTRY_DSN=None, UMAMI_ENABLED=False (cero overhead).
    2. preview: aísla trazas bajo ENV_NAMESPACE.
    3. ci: InMemorySpanExporter obligatorio, bloquea OTLP y Umami para cero salida a red.
    4. staging: orígenes HTTPS, almacenamiento externo obligatorio.
    5. production: is_openapi_enabled=False (OWASP API8), prohíbe sinkholes de dev.
    """
    from pydantic import SecretStr, ValidationError

    from src.core.config import Settings

    # 1. Local
    local_cfg = Settings(ENVIRONMENT="local")
    assert local_cfg.ENVIRONMENT == "local"
    assert local_cfg.OTEL_EXPORTER == "none"
    assert local_cfg.SENTRY_DSN is None or not local_cfg.SENTRY_DSN.get_secret_value()
    assert local_cfg.UMAMI_ENABLED is False
    assert local_cfg.is_openapi_enabled is True

    # 2. Preview
    preview_cfg = Settings(ENVIRONMENT="preview", ENV_NAMESPACE="pr_42")
    assert preview_cfg.ENVIRONMENT == "preview"
    assert preview_cfg.redis_key_prefix == "preview:pr_42:"
    assert preview_cfg.is_openapi_enabled is True

    # 3. CI (Zero external network)
    ci_cfg = Settings(ENVIRONMENT="ci", OTEL_EXPORTER="memory", UMAMI_ENABLED=False)
    assert ci_cfg.ENVIRONMENT == "ci"
    with pytest.raises(ValidationError, match="SecurityBoundaryViolation"):
        Settings(ENVIRONMENT="ci", OTEL_EXPORTER="otlp")
    with pytest.raises(ValidationError, match="SecurityBoundaryViolation"):
        Settings(ENVIRONMENT="ci", UMAMI_ENABLED=True)

    # 4. Staging
    staging_cfg = Settings(
        ENVIRONMENT="staging",
        DATABASE_URL=SecretStr("postgresql+asyncpg://usr:pwd@db-staging.oppytec.internal:5432/oppytec"),
        REDIS_URL=SecretStr("redis://redis-staging.oppytec.internal:6379/0"),
        ALLOWED_ORIGINS=["https://staging.oppytec.com"],
        STORAGE_PROVIDER="r2",
    )
    assert staging_cfg.ENVIRONMENT == "staging"
    assert staging_cfg.is_openapi_enabled is True

    # 5. Production
    prod_cfg = Settings(
        ENVIRONMENT="production",
        DATABASE_URL=SecretStr("postgresql+asyncpg://usr:pwd@db-prod.oppytec.internal:5432/oppytec_live"),
        REDIS_URL=SecretStr("redis://redis-prod.oppytec.internal:6379/0"),
        ALLOWED_ORIGINS=["https://app.oppytec.com"],
        STORAGE_PROVIDER="r2",
        EMAIL_PROVIDER="resend",
    )
    assert prod_cfg.ENVIRONMENT == "production"
    assert prod_cfg.is_openapi_enabled is False


def test_quota_semaphore_telemetry_metrics_and_spans() -> None:
    """
    Certifica la telemetría del semáforo preventivo de cuotas:
    - NORMAL (< 80%)
    - WARNING (>= 80%)
    - CRITICAL (>= 95%)
    - OVER_QUOTA (100% o límite 0)
    Genera métricas en memoria y spans deterministas sin fuga de PII.
    """
    from decimal import Decimal

    from src.core.observability import (
        clear_in_memory_quota_metrics,
        get_in_memory_exporter,
        get_in_memory_quota_metrics,
        record_quota_semaphore_metric,
    )

    clear_in_memory_quota_metrics()
    exporter = get_in_memory_exporter()
    exporter.clear()

    # 1. Quota NORMAL (<80%)
    m_norm = record_quota_semaphore_metric(
        resource_type="products",
        status="NORMAL",
        usage_percentage=Decimal("50.00"),
        active_count=250,
        effective_max_limit=500,
        tenant_id="t_pacifico_01",
        holding_id="h_pacifico",
    )
    assert m_norm.status == "NORMAL"
    assert m_norm.usage_percentage == 50.0
    assert m_norm.active_count == 250

    # 2. Quota WARNING (80% - 94%)
    m_warn = record_quota_semaphore_metric(
        resource_type="users",
        status="WARNING",
        usage_percentage=Decimal("83.33"),
        active_count=5,
        effective_max_limit=6,
        tenant_id="t_pacifico_01",
        holding_id="h_pacifico",
        details={"attempted_by": "admin_pacifico", "password": "SensitiveSecretPass123"},
    )
    assert m_warn.status == "WARNING"

    # 3. Quota CRITICAL (95% - 99%)
    m_crit = record_quota_semaphore_metric(
        resource_type="storage_mb",
        status="CRITICAL",
        usage_percentage=Decimal("96.50"),
        active_count=988,
        effective_max_limit=1024,
        tenant_id="t_pacifico_01",
        holding_id="h_pacifico",
    )
    assert m_crit.status == "CRITICAL"

    # 4. Quota OVER_QUOTA (100% o superado)
    m_over = record_quota_semaphore_metric(
        resource_type="recipes",
        status="OVER_QUOTA",
        usage_percentage=Decimal("100.00"),
        active_count=0,
        effective_max_limit=0,
        tenant_id="t_pacifico_01",
        holding_id="h_pacifico",
    )
    assert m_over.status == "OVER_QUOTA"

    # Validar métricas acumuladas
    metrics = get_in_memory_quota_metrics()
    assert len(metrics) == 4
    assert [m.status for m in metrics] == ["NORMAL", "WARNING", "CRITICAL", "OVER_QUOTA"]

    # Validar spans OTel exportados
    spans = exporter.get_finished_spans()
    assert len(spans) == 4
    span_over = next(s for s in spans if s.name == "quota.semaphore.recipes")
    assert span_over.status_code == 429
    assert span_over.attributes["oppytec.quota.status"] == "OVER_QUOTA"
    assert span_over.attributes["oppytec.quota.resource_type"] == "recipes"


def test_audit_logging_scrubbing_on_plans_tenants_and_quotas() -> None:
    """
    Certifica que los logs y telemetría de creación de planes, aprovisionamiento
    de tenants y eventos de cuota no fuguen PII ni contraseñas.
    """
    import json

    from pydantic import SecretStr

    from src.core.observability import (
        emit_plan_audit_log,
        emit_quota_audit_log,
        emit_tenant_provisioning_audit_log,
    )

    # 1. Auditoría de creación de plan con datos sensibles
    plan_log_str = emit_plan_audit_log(
        "create",
        "plan_gourmet_custom",
        {
            "plan_name": "Gourmet Holding VIP",
            "admin_api_key": "super_secret_api_key_xyz",
            "secret_token": "token_header_secret_123",
            "max_active_users": 50,
            "max_storage_mb": 10240,
        },
    )
    plan_log = json.loads(plan_log_str)
    assert plan_log["event"] == "plan.audit.create"
    assert plan_log["data"]["plan_slug"] == "plan_gourmet_custom"
    assert plan_log["data"]["admin_api_key"] == "[REDACTED_PII]"
    assert plan_log["data"]["secret_token"] == "[REDACTED_PII]"
    assert "super_secret_api_key_xyz" not in plan_log_str

    # 2. Aprovisionamiento de tenant con datos fiscales/PII
    tenant_log_str = emit_tenant_provisioning_audit_log(
        "provision",
        "t_valparaiso_01",
        "h_costa_central",
        "tenant_valparaiso",
        {
            "legal_rep_rut": "12.345.678-9",
            "credit_card": "4532-0000-1111-2222",
            "jwt_secret": SecretStr("very_secret_signing_key_32bytes_min!"),
            "display_name": "Sucursal Valparaíso Puerto",
        },
    )
    tenant_log = json.loads(tenant_log_str)
    assert tenant_log["event"] == "tenant.provisioning.provision"
    assert tenant_log["data"]["tenant_id"] == "t_valparaiso_01"
    assert tenant_log["data"]["legal_rep_rut"] == "[REDACTED_PII]"
    assert tenant_log["data"]["credit_card"] == "[REDACTED_PII]"
    assert tenant_log["data"]["jwt_secret"] == "[REDACTED_PII]"
    assert "very_secret_signing_key" not in tenant_log_str
    assert "12.345.678-9" not in tenant_log_str

    # 3. Auditoría de cuota excedida con intento de registro de usuario
    quota_log_str = emit_quota_audit_log(
        "seat_limit_exceeded",
        "users",
        "OVER_QUOTA",
        {
            "attempted_username": "new_chef",
            "password": "MyPlainPassword2026!",
            "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$xyz",
            "cookie": "session_id=abcdef123456",
        },
    )
    quota_log = json.loads(quota_log_str)
    assert quota_log["event"] == "quota.audit.seat_limit_exceeded"
    assert quota_log["data"]["password"] == "[REDACTED_PII]"
    assert quota_log["data"]["hashed_password"] == "[REDACTED_PII]"
    assert quota_log["data"]["cookie"] == "[REDACTED_PII]"
    assert "MyPlainPassword2026!" not in quota_log_str
