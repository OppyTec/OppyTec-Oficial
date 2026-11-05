"""
oppytec-backend/tests/integration/test_holding_hub_api.py
Suite de pruebas de integración completas para Holding Hub Enterprise (Etapa 2):
1. `GET /api/v1/holding-hub/summary`: KPIs consolidados, balance de IA, seguridad y sucursales.
2. `GET /api/v1/holding-hub/tenants`: Tarjetas de sucursales con telemetría de IA y estado operativo.
3. `GET /api/v1/holding-hub/daily-credit-usage`: Serie temporal continua para Recharts (7, 14, 30 días, filtrable).
4. `PUT /api/v1/holding-hub/credit-distribution`: Modos shared vs allocated con validación de cupos.
5. `POST /api/v1/holding-hub/purchase-credits`: Recarga de bolsa IA en Decimal ($15 CLP, $0.015 USD).
6. `POST /api/v1/holding-hub/change-plan`: Upgrade/cambio de plan corporativo con validación 404 y anti-IDOR.
7. `GET /api/v1/holding-hub/benchmarking`: Ranking cross-tenant por ventas, rotación de stock y % de merma.
8. Validación RBAC de 3 niveles (`holding.hub.view`, `holding.plans.manage`, `holding.credits.distribute`)
   y aislamiento estricto multi-holding (anti-IDOR 403).
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

import httpx
import pytest
from sqlalchemy import select, text

from src.core.database import get_session_factory
from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.modules.tenancy.application.holding_hub_service import (
    HoldingHubService,
    parse_uuid_safely,
)
from src.modules.tenancy.domain.holding_hub import (
    CreditDistributionMode,
    calculate_holding_ai_usage_pct,
    compute_safety_cap_status,
    validate_credit_distribution_sum,
)
from src.modules.tenancy.infrastructure.models import (
    Holding,
    HoldingCreditDistribution,
    HoldingCreditPurchase,
    LegalEntity,
    SystemPlan,
    Tenant,
)

pytestmark = pytest.mark.integration


# =============================================================================
# FIXTURES DE BASE DE DATOS Y ENTORNO
# =============================================================================


@pytest.fixture(autouse=True)
async def clean_security_and_db_state() -> AsyncIterator[None]:
    """Limpia sesiones revocadas y recicla el pool del engine por cada loop de test."""
    import src.core.database as db_module
    clear_revoked_sessions()
    get_rate_limiter().reset()
    if db_module._engine is not None:
        await db_module._engine.dispose()
    db_module._engine = None
    db_module._session_factory = None
    yield
    if db_module._engine is not None:
        await db_module._engine.dispose()
    db_module._engine = None
    db_module._session_factory = None



@pytest.fixture
async def holding_seed_data() -> AsyncIterator[dict[str, Any]]:
    """Crea una jerarquía de Holding corporativo con 2 sucursales para pruebas de integración."""
    factory = get_session_factory()
    async with factory() as session:
        # 1. Asegurar planes comerciales en DB
        plan_basic = (await session.execute(select(SystemPlan).where(SystemPlan.slug == "basic"))).scalar_one_or_none()
        plan_enterprise = (await session.execute(select(SystemPlan).where(SystemPlan.slug == "enterprise"))).scalar_one_or_none()
        if not plan_basic:
            plan_basic = SystemPlan(
                slug="basic",
                name="Plan Básico",
                monthly_ai_credits=1000,
                price_clp=Decimal("34990.00"),
                price_usd=Decimal("39.00"),
            )
            session.add(plan_basic)
        if not plan_enterprise:
            plan_enterprise = SystemPlan(
                slug="enterprise",
                name="Plan Corporativo",
                monthly_ai_credits=10000,
                price_clp=Decimal("149990.00"),
                price_usd=Decimal("165.00"),
            )
            session.add(plan_enterprise)
        await session.commit()

        # 2. Crear Holding
        holding_id = uuid.uuid4()
        holding = Holding(
            id=holding_id,
            nombre="Grupo Gastronómico Bellavista SpA",
            plan_id=plan_enterprise.id,
            ai_credit_balance=Decimal("10000.00"),
            credit_distribution_mode="shared",
            is_active=True,
        )
        session.add(holding)

        # 3. Crear Entidades Legales y Sucursales
        le_1_id = uuid.uuid4()
        le_1 = LegalEntity(
            id=le_1_id,
            holding_id=holding_id,
            tax_id=f"76{uuid.uuid4().hex[:6]}-1",
            legal_name="Restaurante Bellavista Centro SpA",
        )
        t_1_id = uuid.uuid4()
        t_1 = Tenant(
            id=t_1_id,
            holding_id=holding_id,
            legal_entity_id=le_1_id,
            schema_name=f"tenant_bv_centro_{uuid.uuid4().hex[:4]}",
            slug=f"bv-centro-{uuid.uuid4().hex[:4]}",
            nombre_comercial="Bellavista Centro Bistró",
            is_active=True,
        )

        le_2_id = uuid.uuid4()
        le_2 = LegalEntity(
            id=le_2_id,
            holding_id=holding_id,
            tax_id=f"77{uuid.uuid4().hex[:6]}-2",
            legal_name="Restaurante Bellavista Costanera SpA",
        )
        t_2_id = uuid.uuid4()
        t_2 = Tenant(
            id=t_2_id,
            holding_id=holding_id,
            legal_entity_id=le_2_id,
            schema_name=f"tenant_bv_costanera_{uuid.uuid4().hex[:4]}",
            slug=f"bv-costanera-{uuid.uuid4().hex[:4]}",
            nombre_comercial="Bellavista Costanera Grill",
            is_active=True,
        )

        session.add_all([le_1, t_1, le_2, t_2])
        await session.commit()

    seed = {
        "holding_id": holding_id,
        "holding_name": "Grupo Gastronómico Bellavista SpA",
        "plan_basic_id": plan_basic.id,
        "plan_enterprise_id": plan_enterprise.id,
        "tenant_1_id": t_1_id,
        "tenant_1_name": "Bellavista Centro Bistró",
        "tenant_2_id": t_2_id,
        "tenant_2_name": "Bellavista Costanera Grill",
    }

    try:
        yield seed
    finally:
        async with factory() as session:
            await session.execute(text("DELETE FROM public.holding_credit_purchases WHERE holding_id = :hid;"), {"hid": holding_id})
            await session.execute(text("DELETE FROM public.holding_credit_distributions WHERE holding_id = :hid;"), {"hid": holding_id})
            await session.execute(text("DELETE FROM public.tenants WHERE holding_id = :hid;"), {"hid": holding_id})
            await session.execute(text("DELETE FROM public.legal_entities WHERE holding_id = :hid;"), {"hid": holding_id})
            await session.execute(text("DELETE FROM public.holdings WHERE id = :hid;"), {"hid": holding_id})
            await session.commit()


@pytest.fixture
def holding_owner_token(holding_seed_data: dict[str, Any]) -> str:
    """Token JWT de Propietario de Holding con permisos completos de Holding Hub."""
    h_id = str(holding_seed_data["holding_id"])
    return create_access_token(
        user_id=701,
        holding_id=h_id,
        tenant_id=str(holding_seed_data["tenant_1_id"]),
        hierarchy_rank=0,
        is_holding_owner=True,
        contracted_modules=["holding", "tenancy", "analytics", "oppy_ai"],
        role_grants=[
            "holding.hub.view",
            "holding.plans.manage",
            "holding.credits.distribute",
        ],
        accessible_tenants=[str(holding_seed_data["tenant_1_id"]), str(holding_seed_data["tenant_2_id"])],
    )


@pytest.fixture
def viewer_only_token(holding_seed_data: dict[str, Any]) -> str:
    """Token JWT con permiso exclusivo de solo lectura (`holding.hub.view`)."""
    h_id = str(holding_seed_data["holding_id"])
    return create_access_token(
        user_id=702,
        holding_id=h_id,
        tenant_id=str(holding_seed_data["tenant_1_id"]),
        hierarchy_rank=20,
        is_holding_owner=False,
        contracted_modules=["holding"],
        role_grants=["holding.hub.view"],
        accessible_tenants=[str(holding_seed_data["tenant_1_id"])],
    )


@pytest.fixture
def rival_holding_token() -> str:
    """Token JWT perteneciente a un holding ajeno (para pruebas de aislamiento anti-IDOR)."""
    rival_id = str(uuid.uuid4())
    return create_access_token(
        user_id=999,
        holding_id=rival_id,
        tenant_id=str(uuid.uuid4()),
        hierarchy_rank=0,
        is_holding_owner=True,
        contracted_modules=["holding"],
        role_grants=[
            "holding.hub.view",
            "holding.plans.manage",
            "holding.credits.distribute",
        ],
    )


# =============================================================================
# 1. PRUEBAS DE GET /summary
# =============================================================================


async def test_get_holding_summary_success(
    async_client: httpx.AsyncClient,
    holding_seed_data: dict[str, Any],
    holding_owner_token: str,
) -> None:
    """Verifica que GET /summary retorne el resumen completo con KPIs, tenants y serie de consumo."""
    h_id = str(holding_seed_data["holding_id"])

    resp = await async_client.get(
        "/api/v1/holding-hub/summary",
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["holding_id"] == h_id
    assert data["name"] == holding_seed_data["holding_name"]
    assert data["credit_balance"] == 10000
    assert data["total_credits"] == 10000
    assert data["distribution_mode"] == "shared"
    assert data["safety_status"] == "NORMAL"
    assert Decimal(str(data["usage_pct"])) >= Decimal("0.00")

    # Cero floats en métricas consolidadas
    metrics = data["metrics"]
    assert Decimal(str(metrics["total_sales"])) >= Decimal("0.00")
    assert Decimal(str(metrics["inventory_value"])) >= Decimal("0.00")
    assert Decimal(str(metrics["waste_pct"])) >= Decimal("0.00")

    # Sucursales asociadas
    tenants = data["tenants"]
    assert len(tenants) == 2
    tenant_names = {t["name"] for t in tenants}
    assert holding_seed_data["tenant_1_name"] in tenant_names
    assert holding_seed_data["tenant_2_name"] in tenant_names

    # Serie temporal continua (7 días)
    daily = data["daily_usage"]
    assert len(daily) == 7
    for point in daily:
        assert "date" in point
        assert point["credits"] >= 0
        assert point["tokens"] >= 0
        assert point["requests"] >= 0


async def test_get_holding_summary_cross_holding_rejection(
    async_client: httpx.AsyncClient,
    holding_seed_data: dict[str, Any],
    rival_holding_token: str,
) -> None:
    """Verifica que un usuario de otro holding sea rechazado con HTTP 403 (CrossTenantAccessError)."""
    h_id = str(holding_seed_data["holding_id"])

    resp = await async_client.get(
        "/api/v1/holding-hub/summary",
        headers={"Authorization": f"Bearer {rival_holding_token}", "X-Holding-ID": h_id},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"


async def test_get_holding_summary_missing_permission(
    async_client: httpx.AsyncClient,
    holding_seed_data: dict[str, Any],
) -> None:
    """Verifica que un usuario sin el permiso `holding.hub.view` reciba HTTP 403."""
    h_id = str(holding_seed_data["holding_id"])
    token_unauth = create_access_token(
        user_id=888,
        holding_id=h_id,
        tenant_id=str(holding_seed_data["tenant_1_id"]),
        hierarchy_rank=30,
        contracted_modules=["catalog"],
        role_grants=["catalog.products.read"],  # Sin holding.hub.view
    )

    resp = await async_client.get(
        "/api/v1/holding-hub/summary",
        headers={"Authorization": f"Bearer {token_unauth}", "X-Holding-ID": h_id},
    )
    assert resp.status_code == 403


# =============================================================================
# 2. PRUEBAS DE GET /tenants
# =============================================================================


async def test_get_holding_tenants_success(
    async_client: httpx.AsyncClient,
    holding_seed_data: dict[str, Any],
    holding_owner_token: str,
) -> None:
    """Verifica que GET /tenants retorne la lista de tarjetas de sucursales con telemetría."""
    h_id = str(holding_seed_data["holding_id"])

    resp = await async_client.get(
        "/api/v1/holding-hub/tenants",
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp.status_code == 200, resp.text
    tenants = resp.json()
    assert len(tenants) == 2
    for t in tenants:
        assert "id" in t
        assert "name" in t
        assert "schema_name" in t
        assert t["operational_status"] == "active"
        assert t["safety_status"] in ("NORMAL", "WARNING", "CRITICAL")
        assert Decimal(str(t["usage_pct"])) >= Decimal("0.00")


# =============================================================================
# 3. PRUEBAS DE GET /daily-credit-usage
# =============================================================================


async def test_get_daily_credit_usage_intervals_and_filtering(
    async_client: httpx.AsyncClient,
    holding_seed_data: dict[str, Any],
    holding_owner_token: str,
) -> None:
    """Verifica que GET /daily-credit-usage retorne la serie temporal para 7, 14 y 30 días con filtro de sucursal."""
    h_id = str(holding_seed_data["holding_id"])
    t_1_id = str(holding_seed_data["tenant_1_id"])

    # Intervalo 14 días sin filtro
    resp_14 = await async_client.get(
        "/api/v1/holding-hub/daily-credit-usage?days=14",
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp_14.status_code == 200
    assert len(resp_14.json()) == 14

    # Intervalo 30 días filtrado por tenant_1
    resp_30 = await async_client.get(
        f"/api/v1/holding-hub/daily-credit-usage?days=30&tenant_id={t_1_id}",
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp_30.status_code == 200
    assert len(resp_30.json()) == 30


# =============================================================================
# 4. PRUEBAS DE PUT /credit-distribution
# =============================================================================


async def test_update_credit_distribution_shared_and_allocated(
    async_client: httpx.AsyncClient,
    holding_seed_data: dict[str, Any],
    holding_owner_token: str,
) -> None:
    """Verifica la conmutación entre modo shared y allocated con persistencia de cupos."""
    h_id = str(holding_seed_data["holding_id"])
    t_1_id = str(holding_seed_data["tenant_1_id"])
    t_2_id = str(holding_seed_data["tenant_2_id"])

    # 1. Configurar en modo ALLOCATED con cupos válidos (4000 + 3000 <= 10000)
    payload_allocated = {
        "distribution_mode": "allocated",
        "allocations": {t_1_id: 4000, t_2_id: 3000},
    }
    resp_alloc = await async_client.put(
        "/api/v1/holding-hub/credit-distribution",
        json=payload_allocated,
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp_alloc.status_code == 200, resp_alloc.text
    data_alloc = resp_alloc.json()
    assert data_alloc["success"] is True
    assert data_alloc["distribution_mode"] == "allocated"
    assert data_alloc["total_allocated"] == 7000
    assert data_alloc["unallocated_credits"] == 3000

    # 2. Re-consultar summary para verificar que las tarjetas reflejen los cupos asignados
    resp_summary = await async_client.get(
        "/api/v1/holding-hub/summary",
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp_summary.status_code == 200
    summary_cards = {c["id"]: c["allocated_credits"] for c in resp_summary.json()["tenants"]}
    assert summary_cards[t_1_id] == 4000
    assert summary_cards[t_2_id] == 3000

    # 3. Intentar exceder el saldo disponible del holding (8000 + 4000 = 12000 > 10000) -> 400/422
    payload_exceeded = {
        "distribution_mode": "allocated",
        "allocations": {t_1_id: 8000, t_2_id: 4000},
    }
    resp_exceeded = await async_client.put(
        "/api/v1/holding-hub/credit-distribution",
        json=payload_exceeded,
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp_exceeded.status_code in (400, 422)

    # 4. Volver a modo SHARED
    payload_shared = {
        "distribution_mode": "shared",
        "allocations": {},
    }
    resp_shared = await async_client.put(
        "/api/v1/holding-hub/credit-distribution",
        json=payload_shared,
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp_shared.status_code == 200
    assert resp_shared.json()["distribution_mode"] == "shared"


async def test_credit_distribution_requires_specialized_permission(
    async_client: httpx.AsyncClient,
    holding_seed_data: dict[str, Any],
    viewer_only_token: str,
) -> None:
    """Verifica que un usuario sin `holding.credits.distribute` reciba HTTP 403 al intentar distribuir."""
    h_id = str(holding_seed_data["holding_id"])

    resp = await async_client.put(
        "/api/v1/holding-hub/credit-distribution",
        json={"distribution_mode": "shared", "allocations": {}},
        headers={"Authorization": f"Bearer {viewer_only_token}", "X-Holding-ID": h_id},
    )
    assert resp.status_code == 403


# =============================================================================
# 5. PRUEBAS DE POST /purchase-credits
# =============================================================================


async def test_purchase_credits_clp_and_usd(
    async_client: httpx.AsyncClient,
    holding_seed_data: dict[str, Any],
    holding_owner_token: str,
) -> None:
    """Verifica la recarga de créditos en CLP ($15/cr) y USD ($0.015/cr) en Decimal con registro en DB."""
    h_id = str(holding_seed_data["holding_id"])

    # 1. Compra de 2,000 créditos en CLP -> $30,000 CLP
    resp_clp = await async_client.post(
        "/api/v1/holding-hub/purchase-credits",
        json={
            "holding_id": h_id,
            "credits_amount": 2000,
            "currency": "CLP",
            "payment_method": "credit_card",
        },
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp_clp.status_code == 201, resp_clp.text
    data_clp = resp_clp.json()
    assert data_clp["success"] is True
    assert data_clp["credits_purchased"] == 2000
    assert data_clp["previous_balance"] == 10000
    assert data_clp["new_balance"] == 12000
    assert Decimal(str(data_clp["amount_paid"])) == Decimal("30000.00")
    assert data_clp["currency"] == "CLP"
    assert "TXN-CRED-" in data_clp["transaction_id"]

    # 2. Compra de 1,000 créditos en USD -> $15.00 USD
    resp_usd = await async_client.post(
        "/api/v1/holding-hub/purchase-credits",
        json={
            "holding_id": h_id,
            "credits_amount": 1000,
            "currency": "USD",
            "payment_method": "stripe",
        },
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp_usd.status_code == 201, resp_usd.text
    data_usd = resp_usd.json()
    assert data_usd["credits_purchased"] == 1000
    assert data_usd["previous_balance"] == 12000
    assert data_usd["new_balance"] == 13000
    assert Decimal(str(data_usd["amount_paid"])) == Decimal("15.00")
    assert data_usd["currency"] == "USD"


async def test_purchase_credits_anti_idor_rejection(
    async_client: httpx.AsyncClient,
    holding_seed_data: dict[str, Any],
    holding_owner_token: str,
) -> None:
    """Verifica que intentar comprar créditos para un holding ajeno sea rechazado con HTTP 403."""
    h_id = str(holding_seed_data["holding_id"])
    foreign_holding_id = str(uuid.uuid4())

    resp = await async_client.post(
        "/api/v1/holding-hub/purchase-credits",
        json={
            "holding_id": foreign_holding_id,  # Mismatch con el token
            "credits_amount": 1000,
            "currency": "CLP",
        },
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"


# =============================================================================
# 6. PRUEBAS DE POST /change-plan
# =============================================================================


async def test_change_holding_plan_success_and_validation(
    async_client: httpx.AsyncClient,
    holding_seed_data: dict[str, Any],
    holding_owner_token: str,
) -> None:
    """Verifica el cambio de plan corporativo a 'basic' y el rechazo de slugs inexistentes."""
    h_id = str(holding_seed_data["holding_id"])

    # 1. Cambio válido a 'basic'
    resp = await async_client.post(
        "/api/v1/holding-hub/change-plan",
        json={
            "holding_id": h_id,
            "new_plan_slug": "basic",
            "effective_immediately": True,
            "reason": "Redimensionamiento estacional",
        },
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["success"] is True
    assert data["previous_plan_slug"] == "enterprise"
    assert data["new_plan_slug"] == "basic"
    assert data["monthly_credits"] == 1000

    # 2. Plan inexistente -> 404
    resp_404 = await async_client.post(
        "/api/v1/holding-hub/change-plan",
        json={
            "holding_id": h_id,
            "new_plan_slug": "plan-inexistente-xyz",
        },
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp_404.status_code == 404


async def test_change_holding_plan_requires_specialized_permission(
    async_client: httpx.AsyncClient,
    holding_seed_data: dict[str, Any],
    viewer_only_token: str,
) -> None:
    """Verifica que un usuario sin `holding.plans.manage` reciba HTTP 403 al cambiar plan."""
    h_id = str(holding_seed_data["holding_id"])

    resp = await async_client.post(
        "/api/v1/holding-hub/change-plan",
        json={
            "holding_id": h_id,
            "new_plan_slug": "starter",
        },
        headers={"Authorization": f"Bearer {viewer_only_token}", "X-Holding-ID": h_id},
    )
    assert resp.status_code == 403


# =============================================================================
# 7. PRUEBAS DE GET /benchmarking
# =============================================================================


async def test_get_holding_benchmarking_success(
    async_client: httpx.AsyncClient,
    holding_seed_data: dict[str, Any],
    holding_owner_token: str,
) -> None:
    """Verifica el análisis comparativo (Benchmarking) con rankings y promedios."""
    h_id = str(holding_seed_data["holding_id"])

    resp = await async_client.get(
        "/api/v1/holding-hub/benchmarking",
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["holding_id"] == h_id
    assert data["benchmark_period"] == "last_30_days"
    assert Decimal(str(data["average_tenant_sales"])) >= Decimal("0.00")
    assert Decimal(str(data["average_waste_pct"])) >= Decimal("0.00")

    comparisons = data["tenant_comparisons"]
    assert len(comparisons) == 2
    for c in comparisons:
        assert "rank_sales" in c
        assert "rank_efficiency" in c
        assert "stock_turnover" in c
        assert Decimal(str(c["stock_turnover"])) >= Decimal("0.00")


# =============================================================================
# 8. PRUEBAS UNITARIAS PURAS DE DOMINIO Y SERVICIO
# =============================================================================


class TestHoldingHubDomainAndServiceUnit:
    """Pruebas unitarias de invariantes, regla de oro (0 float) y validaciones de servicio."""

    def test_calculate_usage_pct_and_safety_cap(self) -> None:
        assert calculate_holding_ai_usage_pct(0, 1000) == Decimal("0.00")
        assert calculate_holding_ai_usage_pct(799, 1000) == Decimal("79.90")
        assert compute_safety_cap_status(799, 1000) == "NORMAL"

        assert calculate_holding_ai_usage_pct(800, 1000) == Decimal("80.00")
        assert compute_safety_cap_status(800, 1000) == "WARNING"

        assert calculate_holding_ai_usage_pct(950, 1000) == Decimal("95.00")
        assert compute_safety_cap_status(950, 1000) == "CRITICAL"

    def test_validate_credit_distribution_sum_rules(self) -> None:
        # Válido: suma exactamente igual al total
        ok, err = validate_credit_distribution_sum(10000, {"t1": 5000, "t2": 5000})
        assert ok is True
        assert err is None

        # Válido: suma menor al total
        ok, err = validate_credit_distribution_sum(10000, {"t1": 3000, "t2": 2000})
        assert ok is True
        assert err is None

        # Inválido: suma excede total
        ok, err = validate_credit_distribution_sum(10000, {"t1": 6000, "t2": 5000})
        assert ok is False
        assert "exceeds holding total credits" in (err or "")

        # Inválido: asignación negativa
        ok, err = validate_credit_distribution_sum(10000, {"t1": -100, "t2": 5000})
        assert ok is False
        assert "cannot be negative" in (err or "")

    def test_parse_uuid_safely_deterministic(self) -> None:
        # UUID estándar
        raw_uuid = uuid.uuid4()
        assert parse_uuid_safely(str(raw_uuid)) == raw_uuid

        # String arbitrario
        gen_uuid = parse_uuid_safely("holding_genesis")
        assert isinstance(gen_uuid, uuid.UUID)
        # Idempotente y determinista
        assert parse_uuid_safely("holding_genesis") == gen_uuid


# =============================================================================
# 9. PRUEBAS DE GET /ai-briefing (Etapa 3 - Oppy Daily Holding Briefing)
# =============================================================================


async def test_get_holding_ai_briefing_success(
    async_client: httpx.AsyncClient,
    holding_seed_data: dict[str, Any],
    holding_owner_token: str,
) -> None:
    """Verifica que GET /ai-briefing genere el resumen inteligente de 2 párrafos y deducción de crédito."""
    h_id = str(holding_seed_data["holding_id"])

    resp = await async_client.get(
        "/api/v1/holding-hub/ai-briefing",
        headers={"Authorization": f"Bearer {holding_owner_token}", "X-Holding-ID": h_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["holding_id"] == h_id
    assert len(data["summary_paragraphs"]) == 2
    assert "Grupo Gastronómico Bellavista SpA" in data["summary_paragraphs"][0]
    assert len(data["key_achievements"]) >= 2
    assert len(data["cost_alerts"]) >= 1

    # Safety Cap predictivo
    pred = data["safety_cap_prediction"]
    assert pred["status"] == "NORMAL"
    assert Decimal(str(pred["burn_rate_daily"])) >= Decimal("0.00")
    assert pred["recommendation"]

    # Telemetría de tokens y créditos
    assert data["tokens_used"] > 100
    assert Decimal(str(data["credits_deducted"])) == Decimal("1.00")
    assert data["model_name"] == "gemini-1.5-flash"


async def test_get_holding_ai_briefing_viewer_role(
    async_client: httpx.AsyncClient,
    holding_seed_data: dict[str, Any],
    viewer_only_token: str,
) -> None:
    """Verifica que un usuario con permiso holding.hub.view pueda consultar el briefing."""
    h_id = str(holding_seed_data["holding_id"])

    resp = await async_client.get(
        "/api/v1/holding-hub/ai-briefing",
        headers={"Authorization": f"Bearer {viewer_only_token}", "X-Holding-ID": h_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["summary_paragraphs"]) == 2

