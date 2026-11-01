"""
oppytec-backend/tests/unit/modules/test_admin_jev_consumption_api.py
Suite de pruebas unitarias y de integración REST para la Consola FinOps de Decisiones JEV:
- `JevConsumptionService`: agregaciones, jerarquía Holding -> Tenant -> Logs,
  evaluaciones calibradas (AUTO_ACCEPTED, FLAGGED_WARNING, FALLBACK_LLM),
  cálculo de micro-costos, latencia promedio y ahorro estimado frente a Gemini Pro ($0.0025 USD).
- `GET /api/v1/platform-admin/jev-consumption`:
  - Respuesta HTTP 200 con serialización estricta Pydantic v2.
  - Filtros server-side: search, caller_feature, decision_primitive, calibrated_action, holding_id, tenant_id, page, page_size.
  - Validación de RBAC con HTTP 403 Forbidden para tokens no autorizados o sin permiso `platform_admin.tokens.read`.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from src.core.security import create_access_token
from src.modules.tenancy.application.jev_consumption_service import (
    DEFAULT_THEORETICAL_GEMINI_PRO_COST_USD,
    JevConsumptionService,
)
from src.modules.tenancy.domain.saas_policy_math import DEFAULT_USD_TO_CLP_RATE
from src.modules.tenancy.presentation.platform_admin_router import (
    _jev_consumption_service,
)
from src.modules.tenancy.presentation.schemas_platform_admin import (
    JevConsumptionSummaryResponse,
)

pytestmark = pytest.mark.unit


def _make_admin_headers(
    permissions: list[str],
    user_id: int = 1,
    is_global_staff: bool = True,
    is_superuser_god: bool = False,
    hierarchy_rank: int = 10,
) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado para el plano global / platform-admin."""
    token = create_access_token(
        user_id=user_id,
        is_global_staff=is_global_staff,
        is_superuser_god=is_superuser_god,
        hierarchy_rank=hierarchy_rank,
        role_grants=permissions,
    )
    return {
        "Authorization": f"Bearer {token}",
    }


@pytest.fixture(autouse=True)
def _reset_jev_service_state() -> None:
    """Aísla el estado en memoria antes de cada prueba."""
    _jev_consumption_service.reset()


# ============================================================================
# 1. PRUEBAS UNITARIAS DE SERVICIO: JevConsumptionService
# ============================================================================


def test_jev_service_default_aggregations_and_metrics() -> None:
    """Verifica agregaciones, conteos calibrados y cálculo FinOps de ahorro en la muestra por defecto."""
    service = JevConsumptionService()
    summary = service.get_jev_consumption_summary()

    # 5 decisiones por defecto
    assert summary.total_decisions_all == 5
    assert summary.total_logs_count == 5
    assert isinstance(summary.total_cost_usd_all, Decimal)
    assert isinstance(summary.total_cost_clp_all, Decimal)
    assert isinstance(summary.total_credits_deducted_all, Decimal)
    assert isinstance(summary.avg_latency_ms_all, Decimal)

    # Conteos de acciones calibradas
    assert summary.total_auto_accepted_all == 2
    assert summary.total_flagged_warning_all == 1
    assert summary.total_fallback_llm_all == 2
    assert (
        summary.total_auto_accepted_all
        + summary.total_flagged_warning_all
        + summary.total_fallback_llm_all
        == summary.total_decisions_all
    )

    # Verificación del cálculo de micro-costos (4 + 6 + 8 + 5 + 2 = 25 micro-USD = 0.000025)
    assert summary.total_cost_usd_all == Decimal("0.000025")

    # Verificación de ahorro FinOps estimado:
    # 5 * $0.002500 = $0.012500 USD costo teórico Gemini Pro
    # Ahorro USD = $0.012500 - $0.000025 = $0.012475 USD
    expected_savings_usd = (
        Decimal("5") * DEFAULT_THEORETICAL_GEMINI_PRO_COST_USD
    ) - Decimal("0.000025")
    assert summary.estimated_savings_usd_all == expected_savings_usd
    assert summary.estimated_savings_usd_all == Decimal("0.012475")

    # Ahorro CLP = 0.012475 * 950 = 11.85125 -> 11.85 CLP
    expected_savings_clp = (expected_savings_usd * DEFAULT_USD_TO_CLP_RATE).quantize(
        Decimal("0.01")
    )
    assert summary.estimated_savings_clp_all == expected_savings_clp
    assert summary.estimated_savings_clp_all == Decimal("11.85")

    # Latencia promedio: (12 + 18 + 15 + 22 + 9) / 5 = 76 / 5 = 15.20 ms
    assert summary.avg_latency_ms_all == Decimal("15.20")


def test_jev_service_hierarchical_grouping() -> None:
    """Verifica la agrupación jerárquica Holding -> Tenant -> Logs."""
    service = JevConsumptionService()
    summary = service.get_jev_consumption_summary()

    # 2 Holdings
    assert len(summary.holdings) == 2
    holding_ids = {h.holding_id for h in summary.holdings}
    assert holding_ids == {"holding_genesis", "holding_pacifico"}

    # Holding Génesis
    h_genesis = next(h for h in summary.holdings if h.holding_id == "holding_genesis")
    assert h_genesis.holding_name == "Holding Principal Génesis"
    assert h_genesis.total_decisions == 3
    assert len(h_genesis.tenants) == 1
    t_genesis = h_genesis.tenants[0]
    assert t_genesis.tenant_id == "tenant_genesis"
    assert t_genesis.tenant_name == "Local Central Génesis"
    assert t_genesis.total_decisions == 3
    assert len(t_genesis.logs) == 3
    assert t_genesis.auto_accepted_count == 1
    assert t_genesis.flagged_warning_count == 1
    assert t_genesis.fallback_llm_count == 1

    # Holding Pacífico
    h_pacifico = next(h for h in summary.holdings if h.holding_id == "holding_pacifico")
    assert h_pacifico.holding_name == "Grupo Gastronómico Pacífico SpA"
    assert h_pacifico.total_decisions == 2
    assert len(h_pacifico.tenants) == 1
    t_pacifico = h_pacifico.tenants[0]
    assert t_pacifico.tenant_id == "tenant_pacifico_centro"
    assert t_pacifico.total_decisions == 2
    assert len(t_pacifico.logs) == 2
    assert t_pacifico.auto_accepted_count == 1
    assert t_pacifico.fallback_llm_count == 1

    # Lista plana de tenants en el resumen
    assert len(summary.tenants) == 2
    tenant_ids = {t.tenant_id for t in summary.tenants}
    assert tenant_ids == {"tenant_genesis", "tenant_pacifico_centro"}


def test_jev_service_filters() -> None:
    """Verifica todos los filtros soportados por el servicio."""
    service = JevConsumptionService()

    # 1. Filtro search
    res_search = service.get_jev_consumption_summary(search="harina")
    assert res_search.total_decisions_all == 1
    assert res_search.all_logs[0].decision_id == "dec_recipe_mapping_001"

    # 2. Filtro caller_feature
    res_feature = service.get_jev_consumption_summary(caller_feature="invoice_parser")
    assert res_feature.total_decisions_all == 1
    assert res_feature.all_logs[0].caller_feature == "invoice_parser"
    assert res_feature.all_logs[0].holding_id == "holding_pacifico"

    # 3. Filtro decision_primitive
    res_prim = service.get_jev_consumption_summary(decision_primitive="ROUTE")
    assert res_prim.total_decisions_all == 2
    assert all(l.decision_primitive == "ROUTE" for l in res_prim.all_logs)

    # 4. Filtro calibrated_action
    res_action = service.get_jev_consumption_summary(calibrated_action="AUTO_ACCEPTED")
    assert res_action.total_decisions_all == 2
    assert all(l.calibrated_action == "AUTO_ACCEPTED" for l in res_action.all_logs)

    # 5. Filtro holding_id
    res_holding = service.get_jev_consumption_summary(holding_id="holding_pacifico")
    assert res_holding.total_decisions_all == 2
    assert len(res_holding.holdings) == 1
    assert res_holding.holdings[0].holding_id == "holding_pacifico"

    # 6. Filtro tenant_id
    res_tenant = service.get_jev_consumption_summary(tenant_id="tenant_genesis")
    assert res_tenant.total_decisions_all == 3
    assert len(res_tenant.tenants) == 1
    assert res_tenant.tenants[0].tenant_id == "tenant_genesis"


def test_jev_service_pagination() -> None:
    """Verifica la paginación de registros en all_logs."""
    service = JevConsumptionService()

    # Página 1 de tamaño 2
    p1 = service.get_jev_consumption_summary(page=1, page_size=2)
    assert p1.total_logs_count == 5
    assert len(p1.all_logs) == 2
    assert p1.page == 1
    assert p1.page_size == 2

    # Página 2 de tamaño 2
    p2 = service.get_jev_consumption_summary(page=2, page_size=2)
    assert len(p2.all_logs) == 2
    assert p2.page == 2

    # Página 3 de tamaño 2 (último elemento)
    p3 = service.get_jev_consumption_summary(page=3, page_size=2)
    assert len(p3.all_logs) == 1
    assert p3.page == 3

    # IDs de todas las páginas deben ser disjuntos
    ids_p1 = {l.id for l in p1.all_logs}
    ids_p2 = {l.id for l in p2.all_logs}
    ids_p3 = {l.id for l in p3.all_logs}
    assert ids_p1.isdisjoint(ids_p2)
    assert ids_p2.isdisjoint(ids_p3)
    assert len(ids_p1 | ids_p2 | ids_p3) == 5


def test_jev_service_record_log_and_reset() -> None:
    """Verifica que se puedan registrar nuevas decisiones dinámicamente y reiniciar el estado."""
    service = JevConsumptionService()

    new_log = service.record_log(
        holding_id="holding_genesis",
        holding_name="Holding Principal Génesis",
        tenant_id="tenant_genesis",
        tenant_name="Local Central Génesis",
        tenant_schema="tenant_genesis",
        caller_feature="ocr_receipt",
        decision_id="dec_ocr_999",
        decision_primitive="EXTRACT",
        input_summary="Extracción total boleta",
        result_value="TOTAL_25990",
        confidence_score=Decimal("0.9995"),
        calibrated_action="AUTO_ACCEPTED",
        provider_cost_usd=Decimal("0.000010"),
        latency_ms=25,
    )

    assert new_log.id is not None
    assert new_log.caller_feature == "ocr_receipt"

    summary_after = service.get_jev_consumption_summary()
    assert summary_after.total_decisions_all == 6
    assert summary_after.all_logs[0].decision_id == "dec_ocr_999"

    # Reset
    service.reset()
    summary_reset = service.get_jev_consumption_summary()
    assert summary_reset.total_decisions_all == 5


def test_jev_service_empty_results_safe_math() -> None:
    """Verifica que un resultado sin coincidencias no lance ZeroDivisionError y retorne ceros Decimales."""
    service = JevConsumptionService()
    summary = service.get_jev_consumption_summary(search="palabra_totalmente_inexistente_99999")

    assert summary.total_decisions_all == 0
    assert summary.total_cost_usd_all == Decimal("0.000000")
    assert summary.total_cost_clp_all == Decimal("0.00")
    assert summary.total_credits_deducted_all == Decimal("0.00")
    assert summary.avg_latency_ms_all == Decimal("0.00")
    assert summary.total_auto_accepted_all == 0
    assert summary.total_flagged_warning_all == 0
    assert summary.total_fallback_llm_all == 0
    assert summary.estimated_savings_usd_all == Decimal("0.000000")
    assert summary.estimated_savings_clp_all == Decimal("0.00")
    assert summary.holdings == []
    assert summary.tenants == []
    assert summary.all_logs == []


# ============================================================================
# 2. PRUEBAS DE ENDPOINT REST: GET /api/v1/platform-admin/jev-consumption
# ============================================================================


@pytest.mark.asyncio
async def test_get_jev_consumption_endpoint_success_200(async_client: httpx.AsyncClient) -> None:
    """Verifica que el endpoint REST retorne 200 OK con esquema completo y métricas serializadas."""
    headers = _make_admin_headers(["platform_admin.tokens.read"])

    resp = await async_client.get("/api/v1/platform-admin/jev-consumption", headers=headers)
    assert resp.status_code == 200, resp.text

    data = resp.json()

    # Validar campos de nivel superior
    assert data["total_decisions_all"] == 5
    assert Decimal(data["total_cost_usd_all"]) == Decimal("0.000025")
    assert Decimal(data["estimated_savings_usd_all"]) == Decimal("0.012475")
    assert Decimal(data["estimated_savings_clp_all"]) == Decimal("11.85")
    assert Decimal(data["avg_latency_ms_all"]) == Decimal("15.20")
    assert data["total_auto_accepted_all"] == 2
    assert data["total_flagged_warning_all"] == 1
    assert data["total_fallback_llm_all"] == 2

    # Validar jerarquía Holdings
    assert len(data["holdings"]) == 2
    holding_map = {h["holding_id"]: h for h in data["holdings"]}
    assert "holding_genesis" in holding_map
    assert "holding_pacifico" in holding_map
    assert holding_map["holding_genesis"]["total_decisions"] == 3
    assert len(holding_map["holding_genesis"]["tenants"]) == 1

    # Validar lista plana de Tenants
    assert len(data["tenants"]) == 2
    tenant_map = {t["tenant_id"]: t for t in data["tenants"]}
    assert "tenant_genesis" in tenant_map
    assert "tenant_pacifico_centro" in tenant_map

    # Validar all_logs
    assert len(data["all_logs"]) == 5
    first_log = data["all_logs"][0]
    assert "id" in first_log
    assert "decision_id" in first_log
    assert "caller_feature" in first_log
    assert "confidence_score" in first_log
    assert "provider_cost_usd" in first_log
    assert "latency_ms" in first_log

    # Validar conformidad con el esquema Pydantic
    parsed = JevConsumptionSummaryResponse.model_validate(data)
    assert parsed.total_decisions_all == 5


@pytest.mark.asyncio
async def test_get_jev_consumption_endpoint_filters(async_client: httpx.AsyncClient) -> None:
    """Verifica filtros por query params en el endpoint REST."""
    headers = _make_admin_headers(["platform_admin.tokens.read"])

    # 1. Filtro por caller_feature
    r1 = await async_client.get(
        "/api/v1/platform-admin/jev-consumption?caller_feature=invoice_parser",
        headers=headers,
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["total_decisions_all"] == 1
    assert d1["all_logs"][0]["caller_feature"] == "invoice_parser"

    # 2. Filtro por calibrated_action
    r2 = await async_client.get(
        "/api/v1/platform-admin/jev-consumption?calibrated_action=AUTO_ACCEPTED",
        headers=headers,
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["total_decisions_all"] == 2
    assert all(l["calibrated_action"] == "AUTO_ACCEPTED" for l in d2["all_logs"])

    # 3. Filtro por decision_primitive
    r3 = await async_client.get(
        "/api/v1/platform-admin/jev-consumption?decision_primitive=SCORE",
        headers=headers,
    )
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["total_decisions_all"] == 1
    assert d3["all_logs"][0]["decision_primitive"] == "SCORE"

    # 4. Filtro por holding_id
    r4 = await async_client.get(
        "/api/v1/platform-admin/jev-consumption?holding_id=holding_pacifico",
        headers=headers,
    )
    assert r4.status_code == 200
    d4 = r4.json()
    assert d4["total_decisions_all"] == 2
    assert len(d4["holdings"]) == 1
    assert d4["holdings"][0]["holding_id"] == "holding_pacifico"

    # 5. Filtro por tenant_id
    r5 = await async_client.get(
        "/api/v1/platform-admin/jev-consumption?tenant_id=tenant_genesis",
        headers=headers,
    )
    assert r5.status_code == 200
    d5 = r5.json()
    assert d5["total_decisions_all"] == 3
    assert len(d5["tenants"]) == 1
    assert d5["tenants"][0]["tenant_id"] == "tenant_genesis"

    # 6. Paginación
    r6 = await async_client.get(
        "/api/v1/platform-admin/jev-consumption?page=1&page_size=3",
        headers=headers,
    )
    assert r6.status_code == 200
    d6 = r6.json()
    assert d6["total_logs_count"] == 5
    assert len(d6["all_logs"]) == 3
    assert d6["page"] == 1
    assert d6["page_size"] == 3


@pytest.mark.asyncio
async def test_get_jev_consumption_endpoint_rbac_denial_403(async_client: httpx.AsyncClient) -> None:
    """Verifica que usuarios sin permiso 'platform_admin.tokens.read' reciban HTTP 403 Forbidden."""
    # 1. Usuario con permisos de tenant pero sin permiso global
    tenant_token = create_access_token(
        user_id=101,
        holding_id="holding_genesis",
        tenant_id="tenant_genesis",
        is_global_staff=False,
        is_superuser_god=False,
        role_grants=["inventory.stock.read", "recipes.manage"],
    )
    unauthorized_headers = {"Authorization": f"Bearer {tenant_token}"}

    r1 = await async_client.get(
        "/api/v1/platform-admin/jev-consumption",
        headers=unauthorized_headers,
    )
    assert r1.status_code == 403

    # 2. Usuario con permiso de platform_admin.plans pero no de tokens
    plans_only_token = create_access_token(
        user_id=202,
        is_global_staff=True,
        is_superuser_god=False,
        role_grants=["platform_admin.plans.read"],
    )
    plans_headers = {"Authorization": f"Bearer {plans_only_token}"}

    r2 = await async_client.get(
        "/api/v1/platform-admin/jev-consumption",
        headers=plans_headers,
    )
    assert r2.status_code == 403
