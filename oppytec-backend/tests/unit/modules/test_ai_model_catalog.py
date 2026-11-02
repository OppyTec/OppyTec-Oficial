"""
oppytec-backend/tests/unit/modules/test_ai_model_catalog.py
Pruebas unitarias y de integración exhaustivas para el Catálogo y CRUD de Modelos LLM y Motores JEV:
1. Esquemas Pydantic V2: ConfigDict(extra='forbid'), regex en slug, tipos estrictos Decimal (cero float).
2. Dominio DDD Puro e Invariantes: default único por tier, protección de default, contingencia fallback.
3. Servicio de Aplicación AiModelCatalogService: CRUD, hot-reload con ModelConfigRegistry, regla de telemetría.
4. Endpoints REST RFC 7807 y Guardias RBAC de 3 niveles:
   - GET /api/v1/platform-admin/ai-models
   - GET /api/v1/platform-admin/ai-models/{model_slug}
   - POST /api/v1/platform-admin/ai-models
   - PUT /api/v1/platform-admin/ai-models/{model_slug}
   - DELETE /api/v1/platform-admin/ai-models/{model_slug}
"""
from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError

from src.core.exceptions import DomainValidationError, OppyTecError, ResourceNotFoundError
from src.core.security import create_access_token
from src.modules.oppy_ai.application.ai_model_catalog_service import AiModelCatalogService
from src.modules.oppy_ai.application.metered_ai_service import ModelConfigRegistry
from src.modules.oppy_ai.domain.ai_model_catalog import (
    AiEngineTier,
    AiModelConfigEntity,
    AiModelTariffSpec,
    validate_default_model_protection,
    validate_fallback_invariants,
)
from src.modules.oppy_ai.infrastructure.models import AiModelConfig
from src.modules.oppy_ai.presentation.router import (
    _ai_model_catalog_service,
    _model_registry,
)
from src.modules.oppy_ai.presentation.schemas import (
    AiModelConfigCreateRequest,
    AiModelConfigListResponse,
    AiModelConfigResponse,
    AiModelConfigUpdateRequest,
    AiModelDeleteResponse,
)

pytestmark = pytest.mark.unit


def _make_admin_headers(
    permissions: list[str],
    *,
    user_id: int = 1,
    is_global_staff: bool = True,
    hierarchy_rank: int = 10,
) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado para el plano de Platform Admin."""
    token = create_access_token(
        user_id=user_id,
        is_global_staff=is_global_staff,
        hierarchy_rank=hierarchy_rank,
        role_grants=permissions,
    )
    return {"Authorization": f"Bearer {token}"}


def _make_tenant_headers(
    permissions: list[str],
    *,
    user_id: int = 2,
) -> dict[str, str]:
    """Genera cabeceras con JWT de un usuario de Tenant."""
    token = create_access_token(
        user_id=user_id,
        tenant_id="22222222-2222-2222-2222-222222222222",
        holding_id="11111111-1111-1111-1111-111111111111",
        tenant_schema="tenant_demo",
        is_global_staff=False,
        role_grants=permissions,
    )
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. PRUEBAS DE ESQUEMAS PYDANTIC V2 Y ZERO-FLOAT
# ============================================================================


def test_schema_create_request_extra_forbid() -> None:
    """Verifica que campos no declarados disparen ValidationError por extra='forbid'."""
    with pytest.raises(ValidationError) as exc_info:
        AiModelConfigCreateRequest(
            model_slug="test-model",
            display_name="Test Model",
            provider="TestProvider",
            extra_field="unauthorized",  # Extra no permitido
        )
    assert "extra_forbidden" in str(exc_info.value)


def test_schema_create_request_zero_float_enforcement() -> None:
    """Verifica el rechazo estricto de tipos float en tarifas y scores."""
    # Rechazo en input_cost_per_1m_usd si es float
    with pytest.raises(ValidationError) as exc_info:
        AiModelConfigCreateRequest(
            model_slug="test-model",
            display_name="Test Model",
            provider="Google",
            input_cost_per_1m_usd=0.075,  # float prohibido
        )
    assert "Float type is strictly forbidden" in str(exc_info.value)

    # Rechazo en min_confidence_score si es float
    with pytest.raises(ValidationError) as exc_info:
        AiModelConfigCreateRequest(
            model_slug="test-model",
            display_name="Test Model",
            provider="Google",
            min_confidence_score=0.85,  # float prohibido
        )
    assert "Float type is strictly forbidden" in str(exc_info.value)


def test_schema_create_request_slug_regex_validation() -> None:
    """Verifica que model_slug cumpla el patrón ^[a-z0-9]+(?:[._-][a-z0-9]+)*$."""
    # Inválido: mayúsculas, espacios, símbolos raros
    invalid_slugs = ["Model_Slug", "model slug", "-invalid-start", "invalid-end-", "bad!char"]
    for slug in invalid_slugs:
        with pytest.raises(ValidationError):
            AiModelConfigCreateRequest(
                model_slug=slug,
                display_name="Display Name",
                provider="Provider",
            )

    # Válido: minúsculas, puntos, guiones, números
    valid = AiModelConfigCreateRequest(
        model_slug="gemini-3.8-flash.preview",
        display_name="Gemini Preview",
        provider="Google",
    )
    assert valid.model_slug == "gemini-3.8-flash.preview"


def test_schema_update_request_zero_float_enforcement() -> None:
    """Verifica que el schema de actualización también prohíba float y extra fields."""
    with pytest.raises(ValidationError):
        AiModelConfigUpdateRequest(output_cost_per_1m_usd=15.5)  # float prohibido

    with pytest.raises(ValidationError):
        AiModelConfigUpdateRequest(unknown_attr="foo")  # extra forbidden

    valid_update = AiModelConfigUpdateRequest(
        output_cost_per_1m_usd=Decimal("15.500000"),
        latency_p95_ms=900,
    )
    assert valid_update.output_cost_per_1m_usd == Decimal("15.500000")


def test_schema_list_and_response_serialization() -> None:
    """Verifica serialización de AiModelConfigResponse y AiModelConfigListResponse."""
    resp = AiModelConfigResponse(
        id=1,
        model_slug="gemini-3.8-flash",
        display_name="Gemini 3.8 Flash",
        provider="Google DeepMind",
        engine_tier="SYSTEM_2_LLM",
        input_cost_per_1m_usd=Decimal("0.075000"),
        cached_cost_per_1m_usd=Decimal("0.018750"),
        output_cost_per_1m_usd=Decimal("0.300000"),
        embedding_cost_per_1m_usd=Decimal("0.000000"),
        latency_p95_ms=750,
        min_confidence_score=None,
        max_context_tokens=1000000,
        is_enabled=True,
        is_default=True,
        is_fallback=False,
        description="Fast LLM",
        is_deleted=False,
    )
    list_resp = AiModelConfigListResponse(items=[resp], total=1)
    assert list_resp.total == 1
    assert list_resp.items[0].model_slug == "gemini-3.8-flash"


# ============================================================================
# 2. PRUEBAS DE DOMINIO E INVARIANTES DDD
# ============================================================================


def test_domain_tariff_spec_invariants() -> None:
    """Verifica invariantes del Value Object AiModelTariffSpec."""
    # Rechazo de float
    with pytest.raises(DomainValidationError):
        AiModelTariffSpec(input_cost_per_1m_usd=0.15)  # type: ignore

    # Rechazo de negativos
    with pytest.raises(DomainValidationError):
        AiModelTariffSpec(output_cost_per_1m_usd=Decimal("-0.01"))

    # Válido
    spec = AiModelTariffSpec(
        input_cost_per_1m_usd=Decimal("0.150000"),
        cached_cost_per_1m_usd=Decimal("0.037500"),
        output_cost_per_1m_usd=Decimal("0.600000"),
        embedding_cost_per_1m_usd=Decimal("0.000000"),
    )
    assert spec.input_cost_per_1m_usd == Decimal("0.150000")


def test_domain_entity_invariants() -> None:
    """Verifica reglas e invariantes en AiModelConfigEntity."""
    tariffs = AiModelTariffSpec()
    # Min confidence score fuera de rango
    with pytest.raises(DomainValidationError):
        AiModelConfigEntity(
            model_slug="jev-classifier",
            display_name="Jev",
            provider="JEV",
            engine_tier=AiEngineTier.SYSTEM_1_JEV,
            tariffs=tariffs,
            min_confidence_score=Decimal("1.5000"),  # > 1.0000
        )

    # Slug con mayúsculas se normaliza automáticamente
    entity = AiModelConfigEntity(
        model_slug="JEV-Classifier",
        display_name="Jev",
        provider="JEV",
        engine_tier=AiEngineTier.SYSTEM_1_JEV,
        tariffs=tariffs,
        min_confidence_score=Decimal("0.8500"),
    )
    assert entity.model_slug == "jev-classifier"


def test_domain_default_protection_and_fallback_invariants() -> None:
    """Verifica validadores de protección de modelo default y contingencia."""
    tariffs = AiModelTariffSpec()
    default_model = AiModelConfigEntity(
        model_slug="gemini-main",
        display_name="Gemini Main",
        provider="Google",
        engine_tier=AiEngineTier.SYSTEM_2_LLM,
        tariffs=tariffs,
        is_default=True,
    )

    # Invariante 2: Prohibido desactivar modelo default
    with pytest.raises(OppyTecError) as exc_info:
        validate_default_model_protection(default_model, new_is_enabled=False)
    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "CANNOT_DISABLE_DEFAULT_MODEL"

    # Invariante 3: Fallback deshabilitado rechazado
    with pytest.raises(DomainValidationError):
        validate_fallback_invariants(
            model_slug="backup-llm",
            tier=AiEngineTier.SYSTEM_2_LLM,
            is_default=False,
            is_fallback=True,
            is_enabled=False,  # Fallback debe estar activo
            existing_tier_models_count=2,
        )

    # Invariante 3: Fallback idéntico a default cuando hay más de un modelo
    with pytest.raises(OppyTecError) as exc_info:
        validate_fallback_invariants(
            model_slug="gemini-main",
            tier=AiEngineTier.SYSTEM_2_LLM,
            is_default=True,
            is_fallback=True,
            is_enabled=True,
            existing_tier_models_count=2,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "INVALID_FALLBACK_MODEL"


# ============================================================================
# 3. PRUEBAS DEL SERVICIO DE APLICACIÓN AiModelCatalogService
# ============================================================================


def test_service_list_and_get() -> None:
    """Verifica listados filtrados y búsqueda por slug."""
    registry = ModelConfigRegistry()
    service = AiModelCatalogService(model_registry=registry)

    # Listado completo
    all_models = service.list_models()
    assert len(all_models) >= 4

    # Filtrar por tier
    jev_models = service.list_models(tier="SYSTEM_1_JEV")
    assert all(m.engine_tier == "SYSTEM_1_JEV" for m in jev_models)
    assert len(jev_models) >= 1

    # Get por slug exitoso
    m = service.get_model_by_slug("gemini-3.8-flash")
    assert m.display_name == "Gemini 3.8 Flash"

    # Get inexistente -> 404
    with pytest.raises(ResourceNotFoundError):
        service.get_model_by_slug("non-existent-slug")


def test_service_create_and_hot_reload() -> None:
    """Verifica creación de modelo y sincronización inmediata con ModelConfigRegistry."""
    registry = ModelConfigRegistry()
    service = AiModelCatalogService(model_registry=registry)

    new_model_data = {
        "model_slug": "mistral-large-3",
        "display_name": "Mistral Large 3",
        "provider": "Mistral AI",
        "engine_tier": "SYSTEM_2_LLM",
        "input_cost_per_1m_usd": Decimal("2.000000"),
        "cached_cost_per_1m_usd": Decimal("0.500000"),
        "output_cost_per_1m_usd": Decimal("6.000000"),
        "embedding_cost_per_1m_usd": Decimal("0.000000"),
        "latency_p95_ms": 1100,
        "is_enabled": True,
        "is_default": False,
        "is_fallback": False,
    }
    created = service.create_model(new_model_data)
    assert created.model_slug == "mistral-large-3"

    # Verificar sincronización en caliente con el registro
    tariff = registry.get_tariff("mistral-large-3")
    assert tariff.input_cost_per_1m_usd == Decimal("2.000000")
    assert tariff.output_cost_per_1m_usd == Decimal("6.000000")


def test_service_atomic_default_switch() -> None:
    """Verifica que designar un nuevo modelo como default desmarque atómicamente al anterior."""
    registry = ModelConfigRegistry()
    service = AiModelCatalogService(model_registry=registry)

    # gemini-3.8-flash es el default actual de SYSTEM_2_LLM
    gemini = service.get_model_by_slug("gemini-3.8-flash")
    assert gemini.is_default is True

    # Crear nuevo modelo designado como is_default = True
    new_default = service.create_model({
        "model_slug": "gpt-5-omni",
        "display_name": "GPT-5 Omni",
        "provider": "OpenAI",
        "engine_tier": "SYSTEM_2_LLM",
        "input_cost_per_1m_usd": Decimal("2.500000"),
        "cached_cost_per_1m_usd": Decimal("0.500000"),
        "output_cost_per_1m_usd": Decimal("10.000000"),
        "is_default": True,
    })
    assert new_default.is_default is True

    # El anterior default ahora es False
    gemini_updated = service.get_model_by_slug("gemini-3.8-flash")
    assert gemini_updated.is_default is False


def test_service_delete_with_and_without_telemetry() -> None:
    """Verifica Soft Delete si existen llamadas históricas y Hard Delete si count == 0."""
    registry = ModelConfigRegistry()
    service = AiModelCatalogService(model_registry=registry)

    # 1. Intentar borrar modelo default -> 409
    with pytest.raises(OppyTecError) as exc_info:
        service.delete_model("gemini-3.8-flash")
    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "CANNOT_DELETE_DEFAULT_MODEL"

    # 2. claude-3-7-sonnet con 45 llamadas de telemetría simuladas
    service.set_telemetry_count("claude-3-7-sonnet", 45)

    # Intentar hard_delete=True con referencias -> 409
    with pytest.raises(OppyTecError) as exc_info:
        service.delete_model("claude-3-7-sonnet", hard_delete=True)
    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "CANNOT_HARD_DELETE_REFERENCED_MODEL"

    # Soft delete exitoso
    res = service.delete_model("claude-3-7-sonnet", hard_delete=False)
    assert res is True
    claude = service._models["claude-3-7-sonnet"]
    assert claude.is_deleted is True
    assert claude.is_enabled is False

    # 3. Modelo sin telemetría física (telemetry_refs == 0)
    service.create_model({
        "model_slug": "temp-scratch-model",
        "display_name": "Temp",
        "provider": "Temp",
        "engine_tier": "SYSTEM_2_LLM",
        "input_cost_per_1m_usd": Decimal("0.000000"),
        "output_cost_per_1m_usd": Decimal("0.000000"),
        "is_default": False,
    })
    service.set_telemetry_count("temp-scratch-model", 0)
    res_hard = service.delete_model("temp-scratch-model", hard_delete=True)
    assert res_hard is True
    assert "temp-scratch-model" not in service._models


# ============================================================================
# 4. PRUEBAS DE ENDPOINTS REST RFC 7807 Y GUARDIAS RBAC
# ============================================================================


@pytest.mark.asyncio
async def test_api_list_ai_models_authorized_read(async_client: httpx.AsyncClient) -> None:
    """Verifica GET /api/v1/platform-admin/ai-models para staff con permiso read."""
    headers = _make_admin_headers(["platform_admin.ai_models.read"])
    resp = await async_client.get("/api/v1/platform-admin/ai-models", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Validar campos de respuesta
    first = data[0]
    assert "model_slug" in first
    assert "input_cost_per_1m_usd" in first
    assert "latency_p95_ms" in first


@pytest.mark.asyncio
async def test_api_get_ai_model_by_slug(async_client: httpx.AsyncClient) -> None:
    """Verifica GET /api/v1/platform-admin/ai-models/{model_slug}."""
    headers = _make_admin_headers(["platform_admin.ai_models.read"])
    resp = await async_client.get("/api/v1/platform-admin/ai-models/gemini-3.8-flash", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["model_slug"] == "gemini-3.8-flash"
    assert data["is_default"] is True

    # 404 para modelo desconocido
    resp_404 = await async_client.get("/api/v1/platform-admin/ai-models/unknown-model", headers=headers)
    assert resp_404.status_code == 404
    err = resp_404.json()
    assert err["error_code"] == "MODEL_NOT_FOUND"


@pytest.mark.asyncio
async def test_api_create_ai_model_and_hot_reload(async_client: httpx.AsyncClient) -> None:
    """Verifica POST /api/v1/platform-admin/ai-models con hot-reload en tarifas."""
    headers = _make_admin_headers(["platform_admin.ai_models.create"])
    payload = {
        "model_slug": "deepseek-r1-fast",
        "display_name": "DeepSeek R1 Fast",
        "provider": "DeepSeek",
        "engine_tier": "SYSTEM_2_LLM",
        "input_cost_per_1m_usd": "0.550000",
        "cached_cost_per_1m_usd": "0.140000",
        "output_cost_per_1m_usd": "2.190000",
        "embedding_cost_per_1m_usd": "0.000000",
        "latency_p95_ms": 1500,
        "min_confidence_score": None,
        "max_context_tokens": 64000,
        "is_enabled": True,
        "is_default": False,
        "is_fallback": False,
        "description": "Modelo de razonamiento DeepSeek R1.",
    }
    resp = await async_client.post("/api/v1/platform-admin/ai-models", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["model_slug"] == "deepseek-r1-fast"
    assert data["output_cost_per_1m_usd"] == "2.190000"

    # Verificar hot-reload en _model_registry
    tariff = _model_registry.get_tariff("deepseek-r1-fast")
    assert tariff.output_cost_per_1m_usd == Decimal("2.190000")

    # Conflicto 409 si se intenta registrar de nuevo el mismo slug
    resp_dup = await async_client.post("/api/v1/platform-admin/ai-models", json=payload, headers=headers)
    assert resp_dup.status_code == 409
    assert resp_dup.json()["error_code"] == "MODEL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_api_update_ai_model_and_protect_default(async_client: httpx.AsyncClient) -> None:
    """Verifica PUT /api/v1/platform-admin/ai-models/{model_slug} e impedimento de desactivar default."""
    headers = _make_admin_headers(["platform_admin.ai_models.update"])

    # Intentar desactivar gemini-3.8-flash (que es default) -> 409 Conflict
    resp_err = await async_client.put(
        "/api/v1/platform-admin/ai-models/gemini-3.8-flash",
        json={"is_enabled": False},
        headers=headers,
    )
    assert resp_err.status_code == 409
    assert resp_err.json()["error_code"] == "CANNOT_DISABLE_DEFAULT_MODEL"

    # Actualización válida de tarifas y latencia
    resp_ok = await async_client.put(
        "/api/v1/platform-admin/ai-models/gemini-3.8-flash",
        json={"latency_p95_ms": 650, "output_cost_per_1m_usd": "0.350000"},
        headers=headers,
    )
    assert resp_ok.status_code == 200, resp_ok.text
    data = resp_ok.json()
    assert data["latency_p95_ms"] == 650
    assert data["output_cost_per_1m_usd"] == "0.350000"


@pytest.mark.asyncio
async def test_api_delete_ai_model_soft_vs_hard(async_client: httpx.AsyncClient) -> None:
    """Verifica DELETE /api/v1/platform-admin/ai-models/{model_slug} con resolución determinista."""
    admin_headers = _make_admin_headers([
        "platform_admin.ai_models.create",
        "platform_admin.ai_models.delete",
    ])

    # 1. Intentar borrar default -> 409
    resp_def = await async_client.delete(
        "/api/v1/platform-admin/ai-models/gemini-3.8-flash",
        headers=admin_headers,
    )
    assert resp_def.status_code == 409
    assert resp_def.json()["error_code"] == "CANNOT_DELETE_DEFAULT_MODEL"

    # 2. Crear modelo sin llamadas para hard delete
    await async_client.post(
        "/api/v1/platform-admin/ai-models",
        json={
            "model_slug": "ephemeral-test-model",
            "display_name": "Ephemeral",
            "provider": "Test",
            "engine_tier": "SYSTEM_2_LLM",
            "input_cost_per_1m_usd": "0.000000",
            "output_cost_per_1m_usd": "0.000000",
            "is_default": False,
        },
        headers=admin_headers,
    )
    _ai_model_catalog_service.set_telemetry_count("ephemeral-test-model", 0)

    # 0 llamadas -> 204 No Content
    resp_hard = await async_client.delete(
        "/api/v1/platform-admin/ai-models/ephemeral-test-model",
        headers=admin_headers,
    )
    assert resp_hard.status_code == 204

    # 3. Crear modelo con llamadas de telemetría para Soft Delete
    await async_client.post(
        "/api/v1/platform-admin/ai-models",
        json={
            "model_slug": "telemetry-protected-model",
            "display_name": "Telemetry Protected",
            "provider": "Test",
            "engine_tier": "SYSTEM_2_LLM",
            "input_cost_per_1m_usd": "1.000000",
            "output_cost_per_1m_usd": "2.000000",
            "is_default": False,
        },
        headers=admin_headers,
    )
    _ai_model_catalog_service.set_telemetry_count("telemetry-protected-model", 1250)

    # Borrado con telemetría -> 200 OK y Soft Delete payload
    resp_soft = await async_client.delete(
        "/api/v1/platform-admin/ai-models/telemetry-protected-model",
        headers=admin_headers,
    )
    assert resp_soft.status_code == 200, resp_soft.text
    soft_data = resp_soft.json()
    assert soft_data["action"] == "SOFT_DELETED_ARCHIVED"
    assert soft_data["model_slug"] == "telemetry-protected-model"
    assert soft_data["is_enabled"] is False
    assert soft_data["historical_telemetry_logs_preserved"] == 1250


@pytest.mark.asyncio
async def test_api_rbac_forbidden_for_insufficient_permissions(async_client: httpx.AsyncClient) -> None:
    """Verifica que un usuario con solo permiso de lectura sea rechazado (403) ante mutaciones."""
    read_only_headers = _make_admin_headers(["platform_admin.ai_models.read"])

    # Intento de POST con sólo permiso de lectura -> 403 Forbidden
    resp_post = await async_client.post(
        "/api/v1/platform-admin/ai-models",
        json={
            "model_slug": "unauthorized-model",
            "display_name": "Unauthorized",
            "provider": "None",
            "engine_tier": "SYSTEM_2_LLM",
            "input_cost_per_1m_usd": "0.000000",
            "output_cost_per_1m_usd": "0.000000",
        },
        headers=read_only_headers,
    )
    assert resp_post.status_code == 403

    # Intento de PUT con sólo permiso de lectura -> 403 Forbidden
    resp_put = await async_client.put(
        "/api/v1/platform-admin/ai-models/gemini-3.8-flash",
        json={"latency_p95_ms": 1000},
        headers=read_only_headers,
    )
    assert resp_put.status_code == 403

    # Intento de DELETE con sólo permiso de lectura -> 403 Forbidden
    resp_del = await async_client.delete(
        "/api/v1/platform-admin/ai-models/claude-3-7-sonnet",
        headers=read_only_headers,
    )
    assert resp_del.status_code == 403


@pytest.mark.asyncio
async def test_api_rbac_forbidden_for_tenant_scoped_token(async_client: httpx.AsyncClient) -> None:
    """Verifica que un token de plano Tenant no pueda acceder a endpoints globales de Platform Admin."""
    tenant_headers = _make_tenant_headers(["platform_admin.ai_models.read"])
    resp = await async_client.get("/api/v1/platform-admin/ai-models", headers=tenant_headers)
    assert resp.status_code == 403
