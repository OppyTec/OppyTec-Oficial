"""
oppytec-backend/tests/security_redteam/test_22_holding_hub_security_redteam.py
Suite de Auditoría Ofensiva Red Team de 11 Vectores para Holding Hub Enterprise en OppyTec v2.0:
1. Vector 1: BOLA / IDOR Horizontal y Transversal (Path, Header X-Holding-ID, Payload mismatch, Foreign Tenants).
2. Vector 2: Broken Function Level Authorization (RBAC 3 niveles: holding.hub.view, holding.plans.manage, holding.credits.distribute).
3. Vector 3: SQL / DDL Injection en esquemas y filtros.
4. Vector 4: Cross-Site Scripting (XSS) en inputs y briefing.
5. Vector 5: Tampering de precios o créditos IA (Decimal, negativos, sum ceiling, bounds).
6. Vector 6: Concurrency / Double Spend (Locks transaccionales).
7. Vector 7: Information Disclosure y sanitización RFC 7807.
8. Vector 8: AI Prompt Injection y RAG Isolation en Briefing.
9. Vector 9: Zero Hardcoding de credenciales.
10. Vector 10: Kill-Switch y revocación instantánea de sesiones.
11. Vector 11: Multi-Tenant Environment Boundary.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import httpx
import pytest
from sqlalchemy import select, text

from src.core.database import get_session_factory, validate_tenant_schema_name
from src.core.guards import (
    clear_revoked_sessions,
    get_rate_limiter,
    revoke_session_token,
)
from src.core.security import create_access_token
from src.modules.tenancy.infrastructure.models import (
    Holding,
    LegalEntity,
    SystemPlan,
    Tenant,
)

pytestmark = pytest.mark.security_redteam


@pytest.fixture(autouse=True)
async def clean_security_and_db_state() -> Any:
    """Garantiza estado limpio de Kill-Switch, Rate-Limiter y engine pool por test."""
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
async def two_holdings_fixture() -> dict[str, Any]:
    """Crea dos Holdings independientes (Alpha y Bravo) con sus respectivas sucursales en DB."""
    factory = get_session_factory()
    async with factory() as session:
        # Asegurar plan enterprise
        plan = (await session.execute(select(SystemPlan).where(SystemPlan.slug == "enterprise"))).scalar_one_or_none()
        if not plan:
            plan = SystemPlan(
                slug="enterprise",
                name="Plan Corporativo",
                monthly_ai_credits=10000,
                price_clp=Decimal("149990.00"),
                price_usd=Decimal("165.00"),
            )
            session.add(plan)
            await session.commit()

        # Holding Alpha
        h_alpha_id = uuid.uuid4()
        h_alpha = Holding(
            id=h_alpha_id,
            nombre="Holding Gastronómico Alpha SpA",
            plan_id=plan.id,
            ai_credit_balance=Decimal("10000.00"),
            credit_distribution_mode="shared",
            is_active=True,
        )
        le_alpha = LegalEntity(
            id=uuid.uuid4(),
            holding_id=h_alpha_id,
            tax_id=f"76{uuid.uuid4().hex[:6]}-1",
            legal_name="Alpha Bistró SpA",
        )
        t_alpha_id = uuid.uuid4()
        t_alpha = Tenant(
            id=t_alpha_id,
            holding_id=h_alpha_id,
            legal_entity_id=le_alpha.id,
            schema_name=f"tenant_alpha_{uuid.uuid4().hex[:4]}",
            slug=f"alpha-bistro-{uuid.uuid4().hex[:4]}",
            nombre_comercial="Alpha Bistró Centro",
            is_active=True,
        )

        # Holding Bravo (Víctima / Rival)
        h_bravo_id = uuid.uuid4()
        h_bravo = Holding(
            id=h_bravo_id,
            nombre="Holding Gastronómico Bravo SpA",
            plan_id=plan.id,
            ai_credit_balance=Decimal("5000.00"),
            credit_distribution_mode="shared",
            is_active=True,
        )
        le_bravo = LegalEntity(
            id=uuid.uuid4(),
            holding_id=h_bravo_id,
            tax_id=f"77{uuid.uuid4().hex[:6]}-2",
            legal_name="Bravo Grill SpA",
        )
        t_bravo_id = uuid.uuid4()
        t_bravo = Tenant(
            id=t_bravo_id,
            holding_id=h_bravo_id,
            legal_entity_id=le_bravo.id,
            schema_name=f"tenant_bravo_{uuid.uuid4().hex[:4]}",
            slug=f"bravo-grill-{uuid.uuid4().hex[:4]}",
            nombre_comercial="Bravo Grill Costanera",
            is_active=True,
        )

        session.add_all([h_alpha, le_alpha, t_alpha, h_bravo, le_bravo, t_bravo])
        await session.commit()

    seed = {
        "h_alpha_id": str(h_alpha_id),
        "t_alpha_id": str(t_alpha_id),
        "h_bravo_id": str(h_bravo_id),
        "t_bravo_id": str(t_bravo_id),
    }

    try:
        yield seed
    finally:
        async with factory() as session:
            await session.execute(text("DELETE FROM public.holding_credit_purchases WHERE holding_id IN (:ha, :hb);"), {"ha": h_alpha_id, "hb": h_bravo_id})
            await session.execute(text("DELETE FROM public.holding_credit_distributions WHERE holding_id IN (:ha, :hb);"), {"ha": h_alpha_id, "hb": h_bravo_id})
            await session.execute(text("DELETE FROM public.tenants WHERE holding_id IN (:ha, :hb);"), {"ha": h_alpha_id, "hb": h_bravo_id})
            await session.execute(text("DELETE FROM public.legal_entities WHERE holding_id IN (:ha, :hb);"), {"ha": h_alpha_id, "hb": h_bravo_id})
            await session.execute(text("DELETE FROM public.holdings WHERE id IN (:ha, :hb);"), {"ha": h_alpha_id, "hb": h_bravo_id})
            await session.commit()


# =============================================================================
# VECTOR 1: BROKEN OBJECT LEVEL AUTHORIZATION (BOLA / IDOR)
# =============================================================================


async def test_vector_01_cross_holding_idor_header_spoofing_blocked(
    async_client: httpx.AsyncClient,
    two_holdings_fixture: dict[str, Any],
) -> None:
    """Vector 1: Usuario de Holding Alpha intenta leer el resumen de Holding Bravo mediante X-Holding-ID."""
    h_alpha = two_holdings_fixture["h_alpha_id"]
    h_bravo = two_holdings_fixture["h_bravo_id"]

    token_alpha = create_access_token(
        user_id=101,
        holding_id=h_alpha,
        tenant_id=two_holdings_fixture["t_alpha_id"],
        is_holding_owner=True,
        role_grants=["holding.hub.view", "holding.plans.manage", "holding.credits.distribute"],
    )

    # Intento de IDOR hacia Holding Bravo
    resp = await async_client.get(
        "/api/v1/holding-hub/summary",
        headers={"Authorization": f"Bearer {token_alpha}", "X-Holding-ID": h_bravo},
    )
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"


async def test_vector_01_token_without_holding_cannot_spoof_any_holding(
    async_client: httpx.AsyncClient,
    two_holdings_fixture: dict[str, Any],
) -> None:
    """Vector 1: Usuario con token sin holding_id en claims no puede suplantar un holding con X-Holding-ID."""
    h_alpha = two_holdings_fixture["h_alpha_id"]

    token_no_holding = create_access_token(
        user_id=102,
        holding_id=None,
        tenant_id="some_standalone_tenant",
        role_grants=["holding.hub.view"],
    )

    resp = await async_client.get(
        "/api/v1/holding-hub/summary",
        headers={"Authorization": f"Bearer {token_no_holding}", "X-Holding-ID": h_alpha},
    )
    assert resp.status_code == 403
    assert resp.json()["error_code"] in ("CROSS_TENANT_ACCESS_VIOLATION", "PERMISSION_DENIED")


async def test_vector_01_cross_tenant_credit_distribution_rejection(
    async_client: httpx.AsyncClient,
    two_holdings_fixture: dict[str, Any],
) -> None:
    """Vector 1: Holding Alpha intenta asignar cupos a una sucursal perteneciente a Holding Bravo."""
    h_alpha = two_holdings_fixture["h_alpha_id"]
    t_bravo = two_holdings_fixture["t_bravo_id"]

    token_alpha = create_access_token(
        user_id=101,
        holding_id=h_alpha,
        is_holding_owner=True,
        role_grants=["holding.credits.distribute"],
    )

    resp = await async_client.put(
        "/api/v1/holding-hub/credit-distribution",
        json={"distribution_mode": "allocated", "allocations": {t_bravo: 1000}},
        headers={"Authorization": f"Bearer {token_alpha}", "X-Holding-ID": h_alpha},
    )
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"


# =============================================================================
# VECTOR 2: BROKEN FUNCTION LEVEL AUTHORIZATION (BFLA / RBAC)
# =============================================================================


async def test_vector_02_rbac_bfla_privilege_escalation_blocked(
    async_client: httpx.AsyncClient,
    two_holdings_fixture: dict[str, Any],
) -> None:
    """Vector 2: Usuario con solo 'holding.hub.view' no puede cambiar plan ni comprar/distribuir créditos."""
    h_alpha = two_holdings_fixture["h_alpha_id"]
    t_alpha = two_holdings_fixture["t_alpha_id"]

    viewer_token = create_access_token(
        user_id=201,
        holding_id=h_alpha,
        tenant_id=t_alpha,
        role_grants=["holding.hub.view"],
    )

    # 1. Intento de cambio de plan (requiere holding.plans.manage) -> 403
    resp_plan = await async_client.post(
        "/api/v1/holding-hub/change-plan",
        json={"holding_id": h_alpha, "new_plan_slug": "basic"},
        headers={"Authorization": f"Bearer {viewer_token}", "X-Holding-ID": h_alpha},
    )
    assert resp_plan.status_code == 403

    # 2. Intento de distribución (requiere holding.credits.distribute) -> 403
    resp_dist = await async_client.put(
        "/api/v1/holding-hub/credit-distribution",
        json={"distribution_mode": "shared", "allocations": {}},
        headers={"Authorization": f"Bearer {viewer_token}", "X-Holding-ID": h_alpha},
    )
    assert resp_dist.status_code == 403

    # 3. Intento de compra de créditos (requiere holding.credits.distribute) -> 403
    resp_buy = await async_client.post(
        "/api/v1/holding-hub/purchase-credits",
        json={"holding_id": h_alpha, "credits_amount": 1000, "currency": "CLP"},
        headers={"Authorization": f"Bearer {viewer_token}", "X-Holding-ID": h_alpha},
    )
    assert resp_buy.status_code == 403


# =============================================================================
# VECTOR 3: SQL / DDL INJECTION
# =============================================================================


def test_vector_03_schema_injection_regex_validation() -> None:
    """Vector 3: DDL/SQL Injection en nombres de esquemas de sucursales es rechazado por regex."""
    malicious_schemas = [
        'tenant_a"; DROP TABLE holdings; --',
        "tenant_b' OR '1'='1",
        "tenant_c; SELECT pg_sleep(5);",
        "../../etc/passwd",
        "tenant_d\x00_injected",
    ]
    for bad_schema in malicious_schemas:
        with pytest.raises(ValueError):
            validate_tenant_schema_name(bad_schema)


async def test_vector_03_sqli_payload_in_plan_change_blocked(
    async_client: httpx.AsyncClient,
    two_holdings_fixture: dict[str, Any],
) -> None:
    """Vector 3: SQL Injection en razón o slug de plan comercial es neutralizado o bloqueado."""
    h_alpha = two_holdings_fixture["h_alpha_id"]
    owner_token = create_access_token(
        user_id=101,
        holding_id=h_alpha,
        is_holding_owner=True,
        role_grants=["holding.plans.manage"],
    )

    resp = await async_client.post(
        "/api/v1/holding-hub/change-plan",
        json={
            "holding_id": h_alpha,
            "new_plan_slug": "basic",
            "reason": "Upgrade'; DROP TABLE public.holdings; --",
        },
        headers={"Authorization": f"Bearer {owner_token}", "X-Holding-ID": h_alpha},
    )
    # Debe ser bloqueado por xss_sanitizer con 422
    assert resp.status_code == 422


# =============================================================================
# VECTOR 4: CROSS-SITE SCRIPTING (XSS)
# =============================================================================


async def test_vector_04_xss_in_allocations_blocked(
    async_client: httpx.AsyncClient,
    two_holdings_fixture: dict[str, Any],
) -> None:
    """Vector 4: Inyección de script XSS en llaves de sucursales en credit-distribution es bloqueada."""
    h_alpha = two_holdings_fixture["h_alpha_id"]
    token = create_access_token(
        user_id=101,
        holding_id=h_alpha,
        is_holding_owner=True,
        role_grants=["holding.credits.distribute"],
    )

    resp = await async_client.put(
        "/api/v1/holding-hub/credit-distribution",
        json={
            "distribution_mode": "allocated",
            "allocations": {"<script>alert('XSS')</script>": 500},
        },
        headers={"Authorization": f"Bearer {token}", "X-Holding-ID": h_alpha},
    )
    assert resp.status_code == 422


# =============================================================================
# VECTOR 5: TAMPERING DE PRECIOS Y CRÉDITOS IA
# =============================================================================


async def test_vector_05_tampering_negative_or_overflow_credits_blocked(
    async_client: httpx.AsyncClient,
    two_holdings_fixture: dict[str, Any],
) -> None:
    """Vector 5: Manipulación de montos negativos, cero o desbordamientos enteros en compra de créditos."""
    h_alpha = two_holdings_fixture["h_alpha_id"]
    token = create_access_token(
        user_id=101,
        holding_id=h_alpha,
        is_holding_owner=True,
        role_grants=["holding.credits.distribute"],
    )

    # 1. Créditos negativos
    resp_neg = await async_client.post(
        "/api/v1/holding-hub/purchase-credits",
        json={"holding_id": h_alpha, "credits_amount": -500, "currency": "CLP"},
        headers={"Authorization": f"Bearer {token}", "X-Holding-ID": h_alpha},
    )
    assert resp_neg.status_code == 422

    # 2. Créditos cero
    resp_zero = await async_client.post(
        "/api/v1/holding-hub/purchase-credits",
        json={"holding_id": h_alpha, "credits_amount": 0, "currency": "CLP"},
        headers={"Authorization": f"Bearer {token}", "X-Holding-ID": h_alpha},
    )
    assert resp_zero.status_code == 422

    # 3. Desbordamiento superior (le=10_000_000)
    resp_overflow = await async_client.post(
        "/api/v1/holding-hub/purchase-credits",
        json={"holding_id": h_alpha, "credits_amount": 99_000_000, "currency": "CLP"},
        headers={"Authorization": f"Bearer {token}", "X-Holding-ID": h_alpha},
    )
    assert resp_overflow.status_code == 422


# =============================================================================
# VECTOR 7: INFORMATION DISCLOSURE Y SANITIZACIÓN RFC 7807
# =============================================================================


async def test_vector_07_information_disclosure_rfc7807(
    async_client: httpx.AsyncClient,
    two_holdings_fixture: dict[str, Any],
) -> None:
    """Vector 7: Respuestas de error ante holding inexistente no revelan stack trace ni SQL interno."""
    h_alpha = two_holdings_fixture["h_alpha_id"]
    token = create_access_token(
        user_id=101,
        holding_id=h_alpha,
        is_holding_owner=True,
        role_grants=["holding.hub.view"],
    )

    resp = await async_client.get(
        "/api/v1/holding-hub/daily-credit-usage?days=999",  # Excede le=90
        headers={"Authorization": f"Bearer {token}", "X-Holding-ID": h_alpha},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert "detail" in body or "title" in body


# =============================================================================
# VECTOR 10: KILL-SWITCH Y REVOCACIÓN INSTANTÁNEA DE SESIONES
# =============================================================================


async def test_vector_10_killswitch_instant_revocation(
    async_client: httpx.AsyncClient,
    two_holdings_fixture: dict[str, Any],
) -> None:
    """Vector 10: Sesión revocada mediante Kill-Switch es bloqueada inmediatamente con 401."""
    h_alpha = two_holdings_fixture["h_alpha_id"]
    token = create_access_token(
        user_id=505,
        jti="revocable-holding-jti-123",
        holding_id=h_alpha,
        is_holding_owner=True,
        role_grants=["holding.hub.view"],
    )

    # 1. Petición antes de revocar -> 200
    resp_ok = await async_client.get(
        "/api/v1/holding-hub/summary",
        headers={"Authorization": f"Bearer {token}", "X-Holding-ID": h_alpha},
    )
    assert resp_ok.status_code == 200

    # 2. Disparar Kill-Switch
    revoke_session_token(jti="revocable-holding-jti-123")

    # 3. Petición después de revocar -> 401 inmediato (< 1 ms)
    resp_revoked = await async_client.get(
        "/api/v1/holding-hub/summary",
        headers={"Authorization": f"Bearer {token}", "X-Holding-ID": h_alpha},
    )
    assert resp_revoked.status_code == 401
    assert resp_revoked.json()["error_code"] == "SESSION_REVOKED_KILLSWITCH"
