"""
oppytec-backend/tests/unit/test_holding_hub_observability.py
Certificación de Observabilidad 4-Pilares para Holding Hub Enterprise (Etapa 3):
1. OpenTelemetry: Spans distribuidos explícitos (`holding_hub.get_summary`, `holding_hub.get_tenants`,
   `holding_hub.daily_credit_usage`, `holding_hub.purchase_credits`, `holding_hub.update_distribution`).
2. Atributos OTel: `holding.id`, `tenants.count`, `credits.total`, `credits.used`, `plan.tier`.
3. Sentry / GlitchTip: Enriquecimiento de contexto con tags obligatorios `holding_id`, `tenant_id` y `user_role`,
   con sanitización determinista de PII y secretos vía `scrub_sentry_event`.
4. Métricas operativas en memoria: `HoldingHubOperationMetric` con retención acotada y ciclo de vida limpio.
5. Auditoría de Latencia y Rendimiento: Certificación de SLA p95 < 200ms en operaciones agregadas del servicio.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import json
import statistics
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from src.core.guards import clear_revoked_sessions
from src.core.security import create_access_token

from src.core.observability import (
    HoldingHubOperationMetric,
    SpanRecord,
    TenantTelemetryContext,
    bind_tenant_telemetry_context,
    clear_in_memory_holding_hub_metrics,
    enrich_sentry_telemetry_context,
    get_current_trace_id,
    get_in_memory_exporter,
    get_in_memory_holding_hub_metrics,
    reset_tenant_telemetry_context,
    scrub_sentry_event,
    trace_span,
)
from src.modules.tenancy.application.holding_hub_service import (
    HoldingHubService,
)
from src.modules.tenancy.domain.holding_hub import (
    CreditDistributionMode,
)
from src.modules.tenancy.infrastructure.models import (
    Holding,
    SystemPlan,
    Tenant,
)
from src.modules.tenancy.presentation.schemas_holding_hub import (
    HoldingCreditDistributionRequest,
    HoldingMetricsSchema,
    HoldingPurchaseCreditsRequest,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clean_observability_state() -> None:
    """Limpia el exportador de spans y las métricas en memoria antes y después de cada test."""
    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_holding_hub_metrics()
    yield
    exporter.clear()
    clear_in_memory_holding_hub_metrics()


def _build_mock_holding(holding_id: uuid.UUID) -> Holding:
    holding = MagicMock(spec=Holding)
    holding.id = holding_id
    holding.nombre = "Holding Gastronómico Pacífico"
    holding.plan_id = uuid.uuid4()
    holding.ai_credit_balance = Decimal("4500.00")
    holding.credit_distribution_mode = "shared"
    return holding


def _build_mock_plan(plan_id: uuid.UUID) -> SystemPlan:
    plan = MagicMock(spec=SystemPlan)
    plan.id = plan_id
    plan.slug = "enterprise"
    plan.name = "Plan Enterprise Corporativo"
    plan.monthly_ai_credits = 10000
    return plan


def _build_mock_tenants(holding_id: uuid.UUID, count: int = 3) -> list[Tenant]:
    tenants = []
    for i in range(1, count + 1):
        t = MagicMock(spec=Tenant)
        t.id = uuid.uuid4()
        t.holding_id = holding_id
        t.nombre_comercial = f"Sucursal Local #{i}"
        t.schema_name = f"tenant_local_{i}"
        t.is_active = True
        tenants.append(t)
    return tenants


# =============================================================================
# 1. OPENTELEMETRY SPANS Y ATRIBUTOS DISTRIBUIDOS
# =============================================================================


@pytest.mark.asyncio
async def test_holding_hub_get_summary_opentelemetry_span_and_attributes() -> None:
    """
    Certifica la emisión del span 'holding_hub.get_summary' y la inyección de atributos:
    - holding.id
    - tenants.count
    - credits.total
    - credits.used
    - plan.tier
    """
    holding_id = uuid.uuid4()
    mock_holding = _build_mock_holding(holding_id)
    mock_plan = _build_mock_plan(mock_holding.plan_id)
    mock_tenants = _build_mock_tenants(holding_id, count=3)

    service = HoldingHubService()
    service._get_holding_or_raise = AsyncMock(return_value=mock_holding)  # type: ignore[method-assign]
    service._get_plan_for_holding = AsyncMock(return_value=mock_plan)  # type: ignore[method-assign]
    service._get_tenants_for_holding = AsyncMock(return_value=mock_tenants)  # type: ignore[method-assign]
    service._get_allocations_map = AsyncMock(return_value={})  # type: ignore[method-assign]
    service._get_tenants_ai_usage = AsyncMock(  # type: ignore[method-assign]
        return_value={
            mock_tenants[0].id: {"credits": 500, "requests": 25},
            mock_tenants[1].id: {"credits": 750, "requests": 40},
            mock_tenants[2].id: {"credits": 250, "requests": 15},
        }
    )
    service._compute_daily_usage = AsyncMock(return_value=[])  # type: ignore[method-assign]
    service._consolidate_holding_metrics = AsyncMock(  # type: ignore[method-assign]
        return_value=HoldingMetricsSchema(total_sales=Decimal("150000.00"), inventory_value=Decimal("80000.00"), waste_pct=Decimal("3.50"))
    )

    tokens = bind_tenant_telemetry_context(
        holding_id=str(holding_id),
        user_role="holding_owner",
        user_id="42",
    )
    try:
        summary = await service.get_holding_summary(holding_id)
        assert summary.holding_id == str(holding_id)
        assert summary.total_credits == 10000
        assert summary.used_credits == 1500

        # Inspección en memoria de OpenTelemetry Spans
        exporter = get_in_memory_exporter()
        spans = exporter.get_finished_spans()
        summary_spans = [s for s in spans if s.name == "holding_hub.get_summary"]
        assert len(summary_spans) == 1
        span = summary_spans[0]

        assert span.status_code == 200
        assert span.duration_ms >= 0.0

        attrs = span.attributes
        assert attrs.get("holding.id") == str(holding_id)
        assert attrs.get("tenants.count") == 3
        assert attrs.get("credits.total") == 10000
        assert attrs.get("credits.used") == 1500
        assert attrs.get("plan.tier") == "enterprise"
    finally:
        reset_tenant_telemetry_context(tokens)


@pytest.mark.asyncio
async def test_holding_hub_get_tenants_opentelemetry_span_and_attributes() -> None:
    """Certifica la emisión de 'holding_hub.get_tenants' con atributos tenants.count y plan.tier."""
    holding_id = uuid.uuid4()
    mock_holding = _build_mock_holding(holding_id)
    mock_plan = _build_mock_plan(mock_holding.plan_id)
    mock_tenants = _build_mock_tenants(holding_id, count=4)

    service = HoldingHubService()
    service._get_holding_or_raise = AsyncMock(return_value=mock_holding)  # type: ignore[method-assign]
    service._get_plan_for_holding = AsyncMock(return_value=mock_plan)  # type: ignore[method-assign]
    service._get_tenants_for_holding = AsyncMock(return_value=mock_tenants)  # type: ignore[method-assign]
    service._get_allocations_map = AsyncMock(return_value={})  # type: ignore[method-assign]
    service._get_tenants_ai_usage = AsyncMock(return_value={})  # type: ignore[method-assign]

    cards = await service.get_holding_tenants(holding_id)
    assert len(cards) == 4

    spans = get_in_memory_exporter().get_finished_spans()
    tenants_spans = [s for s in spans if s.name == "holding_hub.get_tenants"]
    assert len(tenants_spans) == 1
    attrs = tenants_spans[0].attributes
    assert attrs.get("holding.id") == str(holding_id)
    assert attrs.get("tenants.count") == 4
    assert attrs.get("credits.total") == 10000
    assert attrs.get("plan.tier") == "enterprise"


@pytest.mark.asyncio
async def test_holding_hub_daily_credit_usage_opentelemetry_span() -> None:
    """Certifica la emisión del span 'holding_hub.daily_credit_usage' con atributos de ventana y tenant."""
    holding_id = uuid.uuid4()
    tenant_filter = uuid.uuid4()

    service = HoldingHubService()
    service._get_holding_or_raise = AsyncMock(return_value=_build_mock_holding(holding_id))  # type: ignore[method-assign]
    service._get_tenants_for_holding = AsyncMock(return_value=[MagicMock(id=tenant_filter)])  # type: ignore[method-assign]
    service._compute_daily_usage = AsyncMock(return_value=[MagicMock(date="2026-11-01", credits=100, tokens=5000, requests=10)])  # type: ignore[method-assign]

    items = await service.get_daily_credit_usage(holding_id, days=14, tenant_id=tenant_filter)
    assert len(items) == 1

    spans = get_in_memory_exporter().get_finished_spans()
    daily_spans = [s for s in spans if s.name == "holding_hub.daily_credit_usage"]
    assert len(daily_spans) == 1
    attrs = daily_spans[0].attributes
    assert attrs.get("holding.id") == str(holding_id)
    assert attrs.get("days") == 14
    assert attrs.get("tenant_id") == str(tenant_filter)


@pytest.mark.asyncio
async def test_holding_hub_update_distribution_opentelemetry_span() -> None:
    """Certifica la emisión de 'holding_hub.update_distribution' y atributos credits.total y allocated."""
    holding_id = uuid.uuid4()
    mock_holding = _build_mock_holding(holding_id)
    mock_plan = _build_mock_plan(mock_holding.plan_id)

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    service = HoldingHubService(session=mock_session)
    service._get_holding_or_raise = AsyncMock(return_value=mock_holding)  # type: ignore[method-assign]
    service._get_plan_for_holding = AsyncMock(return_value=mock_plan)  # type: ignore[method-assign]

    t1, t2 = str(uuid.uuid4()), str(uuid.uuid4())
    service._get_tenants_for_holding = AsyncMock(  # type: ignore[method-assign]
        return_value=[MagicMock(id=uuid.UUID(t1)), MagicMock(id=uuid.UUID(t2))]
    )
    req = HoldingCreditDistributionRequest(
        distribution_mode=CreditDistributionMode.ALLOCATED,
        allocations={t1: 3000, t2: 4000},
    )

    resp = await service.update_credit_distribution(holding_id, req)
    assert resp.success is True
    assert resp.total_allocated == 7000
    assert resp.unallocated_credits == 3000

    spans = get_in_memory_exporter().get_finished_spans()
    dist_spans = [s for s in spans if s.name == "holding_hub.update_distribution"]
    assert len(dist_spans) == 1
    attrs = dist_spans[0].attributes
    assert attrs.get("holding.id") == str(holding_id)
    assert attrs.get("credits.total") == 10000
    assert attrs.get("credits.used") == 7000
    assert attrs.get("tenants.count") == 2


@pytest.mark.asyncio
async def test_holding_hub_purchase_credits_opentelemetry_span() -> None:
    """Certifica la emisión de 'holding_hub.purchase_credits' y atributos financieros en Decimal."""
    holding_id = uuid.uuid4()
    mock_holding = _build_mock_holding(holding_id)
    mock_holding.ai_credit_balance = Decimal("1000.00")

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=1)))

    service = HoldingHubService(session=mock_session)
    service._get_holding_or_raise = AsyncMock(return_value=mock_holding)  # type: ignore[method-assign]

    req = HoldingPurchaseCreditsRequest(
        holding_id=str(holding_id),
        credits_amount=5000,
        currency="CLP",
    )

    resp = await service.purchase_credits(holding_id, req, user_id=1)
    assert resp.success is True
    assert resp.previous_balance == 1000
    assert resp.new_balance == 6000
    assert resp.amount_paid == Decimal("75000.00")

    spans = get_in_memory_exporter().get_finished_spans()
    purch_spans = [s for s in spans if s.name == "holding_hub.purchase_credits"]
    assert len(purch_spans) == 1
    attrs = purch_spans[0].attributes
    assert attrs.get("holding.id") == str(holding_id)
    assert attrs.get("credits.total") == 6000
    assert attrs.get("credits.used") == 1000
    assert attrs.get("amount_paid") == "75000.00"


# =============================================================================
# 2. SENTRY CONTEXT ENRICHMENT & PII SCRUBBING
# =============================================================================


def test_enrich_sentry_telemetry_context_tags() -> None:
    """
    Certifica que `enrich_sentry_telemetry_context` construya las etiquetas obligatorias
    `holding_id`, `tenant_id` y `user_role` sin fallar si sentry_sdk no está activo.
    """
    h_id = "h-pacifico-uuid-001"
    t_id = "t-vina-del-mar-002"
    role = "holding_owner"

    tags = enrich_sentry_telemetry_context(
        holding_id=h_id,
        tenant_id=t_id,
        user_role=role,
        user_id="99",
    )
    assert tags["holding_id"] == h_id
    assert tags["tenant_id"] == t_id
    assert tags["user_role"] == role
    assert tags["user_id"] == "99"


def test_scrub_sentry_event_preserves_hub_tags_and_scrubs_pii() -> None:
    """
    Certifica que el hook determinista `scrub_sentry_event`:
    1. Higienice PII estricto (RUT, contraseñas, tarjetas, secretos inline).
    2. Inyecte y preserve automáticamente las etiquetas `holding_id`, `tenant_id` y `user_role`.
    3. Conserve intacto el nombre comercial inmutable ("Holding Gastronómico").
    """
    tokens = bind_tenant_telemetry_context(
        holding_id="h-genesis-holding-999",
        tenant_id="t-central-santiago-001",
        user_role="holding_admin",
        user_id="55",
    )
    try:
        raw_event: dict[str, Any] = {
            "event_id": "sentry-holding-hub-error-001",
            "message": "Error al calcular Safety Cap para RUT 12.345.678-5 con clave password=MySecret123!",
            "tags": {
                "environment": "production",
                "custom_scope": "holding_hub_kpis",
            },
            "extra": {
                "credit_card": "4532-0000-1111-2222",
                "api_key": "sk_live_verysecrettokenxyz",
                "holding_name": "Holding Gastronómico Pacífico",
                "secret_credential": SecretStr("super_vault_key"),
            },
        }

        clean_event = scrub_sentry_event(raw_event)
        serialized = json.dumps(clean_event, ensure_ascii=False)

        # 1. PII y Secretos censurados
        assert "12.345.678-5" not in serialized
        assert "MySecret123!" not in serialized
        assert "4532-0000-1111-2222" not in serialized
        assert "sk_live_verysecrettokenxyz" not in serialized
        assert "super_vault_key" not in serialized
        assert "[REDACTED_PII]" in serialized

        # 2. Razón social preservada
        assert "Holding Gastronómico Pacífico" in serialized

        # 3. Tags obligatorios enriquecidos desde el contexto activo
        tags = clean_event["tags"]
        assert isinstance(tags, dict)
        assert tags.get("holding_id") == "h-genesis-holding-999"
        assert tags.get("tenant_id") == "t-central-santiago-001"
        assert tags.get("user_role") == "holding_admin"
        assert tags.get("environment") == "production"
    finally:
        reset_tenant_telemetry_context(tokens)


# =============================================================================
# 3. MÉTRICAS OPERATIVAS EN MEMORIA: HoldingHubOperationMetric
# =============================================================================


def test_holding_hub_operation_metric_recording_and_clearing() -> None:
    """
    Certifica la captura determinista de `HoldingHubOperationMetric`
    a través de `trace_span` y su limpieza controlada.
    """
    clear_in_memory_holding_hub_metrics()
    assert len(get_in_memory_holding_hub_metrics()) == 0

    h_id = str(uuid.uuid4())
    with trace_span(
        "holding_hub.get_summary",
        attributes={
            "holding.id": h_id,
            "tenants.count": 5,
            "credits.total": 20000,
            "credits.used": 4500,
            "plan.tier": "enterprise_plus",
            "user_role": "holding_owner",
        },
        tracer_name="oppytec.tenancy.holding_hub",
    ):
        pass

    metrics = get_in_memory_holding_hub_metrics()
    assert len(metrics) == 1
    m = metrics[0]

    assert m.operation == "holding_hub.get_summary"
    assert m.status == "SUCCESS"
    assert m.holding_id == h_id
    assert m.tenants_count == 5
    assert m.credits_total == 20000
    assert m.credits_used == 4500
    assert m.plan_tier == "enterprise_plus"
    assert m.user_role == "holding_owner"
    assert m.duration_ms >= 0.0

    clear_in_memory_holding_hub_metrics()
    assert len(get_in_memory_holding_hub_metrics()) == 0


# =============================================================================
# 4. AUDITORÍA DE LATENCIA Y RENDIMIENTO (SLA p95 < 200ms)
# =============================================================================


@pytest.mark.asyncio
async def test_holding_hub_latency_sla_p95_under_200ms() -> None:
    """
    Auditoría de Rendimiento:
    Ejecuta 60 iteraciones de operaciones consolidadas del Holding Hub
    y certifica matemáticamente que el percentil 95 (p95) sea estrictamente menor a 200 ms.
    """
    holding_id = uuid.uuid4()
    mock_holding = _build_mock_holding(holding_id)
    mock_plan = _build_mock_plan(mock_holding.plan_id)
    mock_tenants = _build_mock_tenants(holding_id, count=10)

    service = HoldingHubService()
    service._get_holding_or_raise = AsyncMock(return_value=mock_holding)  # type: ignore[method-assign]
    service._get_plan_for_holding = AsyncMock(return_value=mock_plan)  # type: ignore[method-assign]
    service._get_tenants_for_holding = AsyncMock(return_value=mock_tenants)  # type: ignore[method-assign]
    service._get_allocations_map = AsyncMock(return_value={t.id: 1000 for t in mock_tenants})  # type: ignore[method-assign]
    service._get_tenants_ai_usage = AsyncMock(return_value={t.id: {"credits": 150, "requests": 8} for t in mock_tenants})  # type: ignore[method-assign]
    service._compute_daily_usage = AsyncMock(return_value=[])  # type: ignore[method-assign]
    service._consolidate_holding_metrics = AsyncMock(  # type: ignore[method-assign]
        return_value=HoldingMetricsSchema(total_sales=Decimal("500000.00"), inventory_value=Decimal("120000.00"), waste_pct=Decimal("2.40"))
    )

    latencies_ms: list[float] = []
    iterations = 60

    for _ in range(iterations):
        t_start = time.perf_counter()
        await service.get_holding_summary(holding_id)
        duration_ms = (time.perf_counter() - t_start) * 1000.0
        latencies_ms.append(duration_ms)

    latencies_ms.sort()
    # Percentil 95 determinista
    p95_index = int(0.95 * len(latencies_ms))
    p95_latency = latencies_ms[p95_index]
    avg_latency = statistics.mean(latencies_ms)

    # SLA estricto: p95 < 200ms
    assert p95_latency < 200.0, f"SLA Violation: p95 latency {p95_latency:.2f}ms exceeds 200ms target"
    assert avg_latency < 100.0, f"Average latency {avg_latency:.2f}ms is unusually high"


# =============================================================================
# 5. ERROR RESILIENCE & SENTRY CAPTURE ON FAILURE
# =============================================================================


@pytest.mark.asyncio
async def test_holding_hub_error_span_and_sentry_tagging_on_failure() -> None:
    """
    Certifica que cuando ocurre un error en una operación del Hub:
    1. El Span OTel registre status ERROR con el código HTTP correspondiente.
    2. Las métricas operativas registren status 'ERROR'.
    3. La excepción no se trague y sea propagada al llamador limpiamente.
    """
    holding_id = uuid.uuid4()
    service = HoldingHubService()
    service._get_holding_or_raise = AsyncMock(side_effect=ValueError("Database connection timeout during KPI aggregation"))  # type: ignore[method-assign]

    tokens = bind_tenant_telemetry_context(
        holding_id=str(holding_id),
        user_role="holding_manager",
    )
    try:
        with pytest.raises(ValueError, match="Database connection timeout"):
            await service.get_holding_summary(holding_id)

        exporter = get_in_memory_exporter()
        spans = exporter.get_finished_spans()
        err_spans = [s for s in spans if s.name == "holding_hub.get_summary"]
        assert len(err_spans) == 1
        err_span = err_spans[0]
        assert err_span.status_code == 500

        metrics = get_in_memory_holding_hub_metrics()
        assert len(metrics) == 1
        assert metrics[0].status == "ERROR"
        assert metrics[0].holding_id == str(holding_id)
    finally:
        reset_tenant_telemetry_context(tokens)


# =============================================================================
# 6. FASTAPI ROUTER OBSERVABILITY & TRACE PROPAGATION
# =============================================================================


def _make_hub_headers(
    holding_id: str,
    permissions: list[str],
    user_id: int = 101,
    user_role: str = "holding_owner",
    trace_id: str | None = None,
) -> dict[str, str]:
    """Genera cabeceras HTTP con token JWT y X-Trace-ID para pruebas de router."""
    token = create_access_token(
        user_id=user_id,
        holding_id=holding_id,
        tenant_id="tenant_loc_01",
        hierarchy_rank=0,
        is_holding_owner=True,
        contracted_modules=["holding", "tenancy", "analytics", "oppy_ai"],
        role_grants=permissions,
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Holding-ID": holding_id,
    }
    if trace_id:
        headers["X-Trace-ID"] = trace_id
    return headers


@pytest.mark.asyncio
async def test_router_summary_span_and_trace_propagation(
    app: Any,
    async_client: httpx.AsyncClient,
) -> None:
    """
    Certifica a nivel de Router FastAPI:
    1. Propagación de X-Trace-ID en respuesta HTTP.
    2. Generación del span 'holding_hub.get_summary'.
    3. Inyección de user_role='holding_owner' y holding.id en el span y tags.
    """
    from src.modules.tenancy.presentation.holding_hub_router import get_holding_hub_service
    from src.modules.tenancy.presentation.schemas_holding_hub import (
        HoldingHubSummaryResponse,
        HoldingMetricsSchema,
    )

    holding_id = str(uuid.uuid4())
    client_trace = "trace-holding-hub-summary-test-999"

    mock_summary = HoldingHubSummaryResponse(
        holding_id=holding_id,
        name="Holding Mar y Tierra",
        credit_balance=5000,
        total_credits=10000,
        used_credits=2000,
        distribution_mode=CreditDistributionMode.SHARED,
        safety_status="safe",
        usage_pct=Decimal("20.00"),
        metrics=HoldingMetricsSchema(total_sales=Decimal("10000.00"), inventory_value=Decimal("5000.00"), waste_pct=Decimal("1.50")),
        tenants=[],
        daily_usage=[],
    )

    mock_service = AsyncMock()
    mock_service.get_holding_summary = AsyncMock(return_value=mock_summary)
    app.dependency_overrides[get_holding_hub_service] = lambda: mock_service

    try:
        headers = _make_hub_headers(
            holding_id=holding_id,
            permissions=["holding.hub.view"],
            user_id=88,
            trace_id=client_trace,
        )

        resp = await async_client.get("/api/v1/holding-hub/summary", headers=headers)
        assert resp.status_code == 200
        assert resp.headers.get("X-Trace-ID") == client_trace

        spans = get_in_memory_exporter().get_finished_spans()
        summary_spans = [s for s in spans if s.name == "holding_hub.get_summary"]
        assert len(summary_spans) >= 1
        span = summary_spans[0]
        assert span.trace_id == client_trace
        assert span.attributes.get("holding.id") == holding_id
        assert span.attributes.get("user_role") == "holding_owner"
    finally:
        app.dependency_overrides.pop(get_holding_hub_service, None)


@pytest.mark.asyncio
async def test_router_tenants_and_daily_usage_spans(
    app: Any,
    async_client: httpx.AsyncClient,
) -> None:
    """Certifica los spans 'holding_hub.get_tenants' y 'holding_hub.daily_credit_usage' en el Router."""
    from src.modules.tenancy.presentation.holding_hub_router import get_holding_hub_service

    holding_id = str(uuid.uuid4())
    mock_service = AsyncMock()
    mock_service.get_holding_tenants = AsyncMock(return_value=[])
    mock_service.get_daily_credit_usage = AsyncMock(return_value=[])
    app.dependency_overrides[get_holding_hub_service] = lambda: mock_service

    try:
        headers = _make_hub_headers(
            holding_id=holding_id,
            permissions=["holding.hub.view"],
            user_id=89,
        )

        resp1 = await async_client.get("/api/v1/holding-hub/tenants", headers=headers)
        assert resp1.status_code == 200

        resp2 = await async_client.get("/api/v1/holding-hub/daily-credit-usage?days=7", headers=headers)
        assert resp2.status_code == 200

        spans = get_in_memory_exporter().get_finished_spans()
        assert any(s.name == "holding_hub.get_tenants" for s in spans)
        assert any(s.name == "holding_hub.daily_credit_usage" for s in spans)
    finally:
        app.dependency_overrides.pop(get_holding_hub_service, None)


@pytest.mark.asyncio
async def test_router_credit_distribution_and_purchase_spans(
    app: Any,
    async_client: httpx.AsyncClient,
) -> None:
    """Certifica los spans 'holding_hub.update_distribution' y 'holding_hub.purchase_credits' en el Router."""
    from src.modules.tenancy.presentation.holding_hub_router import get_holding_hub_service
    from src.modules.tenancy.presentation.schemas_holding_hub import (
        HoldingCreditDistributionResponse,
        HoldingPurchaseCreditsResponse,
    )

    holding_id = str(uuid.uuid4())
    mock_service = AsyncMock()
    mock_service.update_credit_distribution = AsyncMock(
        return_value=HoldingCreditDistributionResponse(
            success=True,
            holding_id=holding_id,
            distribution_mode=CreditDistributionMode.SHARED,
            allocations={},
            total_allocated=0,
            unallocated_credits=5000,
            message="OK",
        )
    )
    mock_service.purchase_credits = AsyncMock(
        return_value=HoldingPurchaseCreditsResponse(
            success=True,
            holding_id=holding_id,
            credits_purchased=1000,
            previous_balance=5000,
            new_balance=6000,
            amount_paid=Decimal("15000.00"),
            currency="CLP",
            transaction_id="TXN-1234",
            purchased_at=datetime.now(UTC),
        )
    )
    app.dependency_overrides[get_holding_hub_service] = lambda: mock_service

    try:
        headers = _make_hub_headers(
            holding_id=holding_id,
            permissions=["holding.credits.distribute"],
            user_id=90,
        )

        resp1 = await async_client.put(
            "/api/v1/holding-hub/credit-distribution",
            json={"distribution_mode": "shared", "allocations": {}},
            headers=headers,
        )
        assert resp1.status_code == 200

        resp2 = await async_client.post(
            "/api/v1/holding-hub/purchase-credits",
            json={"holding_id": holding_id, "credits_amount": 1000, "currency": "CLP"},
            headers=headers,
        )
        assert resp2.status_code == 201

        spans = get_in_memory_exporter().get_finished_spans()
        assert any(s.name == "holding_hub.update_distribution" for s in spans)
        assert any(s.name == "holding_hub.purchase_credits" for s in spans)
    finally:
        app.dependency_overrides.pop(get_holding_hub_service, None)

