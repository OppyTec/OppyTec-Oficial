"""
oppytec-backend/tests/unit/test_holding_briefing.py
Suite de pruebas unitarias para el servicio Oppy Daily Holding Briefing:
1. Generación de resumen ejecutivo inteligente de exactamente 2 párrafos.
2. Cumplimiento de la Regla de Oro: Cero floats (exclusivamente Decimal e int).
3. Estados predictivos de Safety Cap (NORMAL, WARNING, CRITICAL) y tasa de quemado (burn rate).
4. Detección de aciertos operacionales y alertas de merma/costos.
5. Cálculo de consumo de tokens y deducción atómica de créditos.
6. Compatibilidad síncrona y awaitable (`await service.generate_holding_briefing(...)`).
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.ai.jev_adapter import InMemoryTelemetrySink
from src.modules.oppy_ai.application.holding_briefing_service import (
    HoldingBriefingService,
)
from src.modules.tenancy.domain.holding_hub import CreditDistributionMode
from src.modules.tenancy.infrastructure.models import Holding
from src.modules.tenancy.presentation.schemas_holding_hub import (
    HoldingBriefingResponse,
    HoldingDailyCreditUsageItem,
    HoldingHubSummaryResponse,
    HoldingMetricsSchema,
    HoldingTenantCardResponse,
    SafetyCapPredictiveStatus,
)


@pytest.fixture
def sample_summary() -> HoldingHubSummaryResponse:
    """Fixture de resumen consolidado de holding con métricas estándar y 2 sucursales."""
    h_id = str(uuid.uuid4())
    t1_id = str(uuid.uuid4())
    t2_id = str(uuid.uuid4())

    return HoldingHubSummaryResponse(
        holding_id=h_id,
        name="Holding Gastronómico Cordillera SpA",
        credit_balance=15000,
        total_credits=20000,
        used_credits=5000,
        distribution_mode=CreditDistributionMode.ALLOCATED,
        safety_status="NORMAL",
        usage_pct=Decimal("25.00"),
        metrics=HoldingMetricsSchema(
            total_sales=Decimal("120500000.00"),
            inventory_value=Decimal("35000000.00"),
            waste_pct=Decimal("2.40"),
        ),
        tenants=[
            HoldingTenantCardResponse(
                id=t1_id,
                name="Cordillera Grill Vitacura",
                schema_name="tenant_cordillera_vitacura",
                operational_status="active",
                used_credits=3200,
                allocated_credits=10000,
                bot_requests=450,
                usage_pct=Decimal("32.00"),
                safety_status="NORMAL",
            ),
            HoldingTenantCardResponse(
                id=t2_id,
                name="Cordillera Bistró Providencia",
                schema_name="tenant_cordillera_provi",
                operational_status="active",
                used_credits=1800,
                allocated_credits=10000,
                bot_requests=210,
                usage_pct=Decimal("18.00"),
                safety_status="NORMAL",
            ),
        ],
        daily_usage=[
            HoldingDailyCreditUsageItem(date="2026-11-01", credits=250, tokens=60000, requests=30),
            HoldingDailyCreditUsageItem(date="2026-11-02", credits=280, tokens=70000, requests=35),
            HoldingDailyCreditUsageItem(date="2026-11-03", credits=270, tokens=65000, requests=32),
            HoldingDailyCreditUsageItem(date="2026-11-04", credits=300, tokens=75000, requests=38),
        ],
    )


def test_generate_holding_briefing_exact_two_paragraphs(
    sample_summary: HoldingHubSummaryResponse,
) -> None:
    """Verifica que el briefing contenga exactamente 2 párrafos inteligentes."""
    sink = InMemoryTelemetrySink()
    service = HoldingBriefingService(telemetry_sink=sink)
    holding_uuid = uuid.UUID(sample_summary.holding_id)

    briefing = service.generate_holding_briefing(holding_uuid, sample_summary)

    assert isinstance(briefing, HoldingBriefingResponse)
    assert len(briefing.summary_paragraphs) == 2

    # Párrafo 1: Ventas, inventario y análisis de mermas
    p1 = briefing.summary_paragraphs[0]
    assert "Holding Gastronómico Cordillera SpA" in p1
    assert "120.500.000" in p1
    assert "35.000.000" in p1
    assert "2.4%" in p1

    # Párrafo 2: Bolsa de créditos IA, semáforo predictivo y recomendación
    p2 = briefing.summary_paragraphs[1]
    assert "15,000 créditos restantes" in p2
    assert "20,000" in p2
    assert "25.0% consumido" in p2
    assert "Safety Cap" in p2
    assert "NORMAL" in p2


def test_holding_briefing_zero_floats_rule(
    sample_summary: HoldingHubSummaryResponse,
) -> None:
    """Garantiza la Regla de Oro: Cero uso de float en todas las métricas de briefing."""
    service = HoldingBriefingService()
    holding_uuid = uuid.UUID(sample_summary.holding_id)

    briefing = service.generate_holding_briefing(holding_uuid, sample_summary)

    # Validar tipos estrictos (Decimal e int, nunca float)
    assert isinstance(briefing.credits_deducted, Decimal)
    assert isinstance(briefing.tokens_used, int)
    assert not isinstance(briefing.credits_deducted, float)
    assert not isinstance(briefing.tokens_used, float)

    pred = briefing.safety_cap_prediction
    assert isinstance(pred.burn_rate_daily, Decimal)
    assert not isinstance(pred.burn_rate_daily, float)
    if pred.estimated_days_remaining is not None:
        assert isinstance(pred.estimated_days_remaining, int)
        assert not isinstance(pred.estimated_days_remaining, float)


def test_holding_briefing_safety_cap_normal(
    sample_summary: HoldingHubSummaryResponse,
) -> None:
    """Verifica predicción NORMAL cuando el consumo está por debajo del 80% y autonomía holgada."""
    service = HoldingBriefingService()
    holding_uuid = uuid.UUID(sample_summary.holding_id)

    briefing = service.generate_holding_briefing(holding_uuid, sample_summary)

    pred = briefing.safety_cap_prediction
    assert pred.status == "NORMAL"
    assert pred.burn_rate_daily > Decimal("0.00")
    assert pred.estimated_days_remaining is not None
    assert pred.estimated_days_remaining > 30
    assert "holgada" in pred.recommendation.lower()


def test_holding_briefing_safety_cap_warning(
    sample_summary: HoldingHubSummaryResponse,
) -> None:
    """Verifica predicción WARNING cuando el consumo supera el 80% o autonomía baja a 4-7 días."""
    h_id = str(uuid.uuid4())
    warning_summary = HoldingHubSummaryResponse(
        holding_id=h_id,
        name="Holding En Alerta SpA",
        credit_balance=1800,
        total_credits=10000,
        used_credits=8200,
        distribution_mode=CreditDistributionMode.SHARED,
        safety_status="WARNING",
        usage_pct=Decimal("82.00"),
        metrics=HoldingMetricsSchema(
            total_sales=Decimal("50000000.00"),
            inventory_value=Decimal("10000000.00"),
            waste_pct=Decimal("3.20"),
        ),
        tenants=[],
        daily_usage=[
            HoldingDailyCreditUsageItem(date="2026-11-01", credits=350, tokens=80000, requests=40),
            HoldingDailyCreditUsageItem(date="2026-11-02", credits=400, tokens=90000, requests=45),
        ],
    )

    service = HoldingBriefingService()
    briefing = service.generate_holding_briefing(uuid.UUID(h_id), warning_summary)

    pred = briefing.safety_cap_prediction
    assert pred.status == "WARNING"
    assert "acelerado" in pred.recommendation.lower() or "preventiva" in pred.recommendation.lower()


def test_holding_briefing_safety_cap_critical(
    sample_summary: HoldingHubSummaryResponse,
) -> None:
    """Verifica predicción CRITICAL cuando el consumo supera el 95% o autonomía <= 3 días."""
    h_id = str(uuid.uuid4())
    critical_summary = HoldingHubSummaryResponse(
        holding_id=h_id,
        name="Holding Crítico SpA",
        credit_balance=300,
        total_credits=10000,
        used_credits=9700,
        distribution_mode=CreditDistributionMode.SHARED,
        safety_status="CRITICAL",
        usage_pct=Decimal("97.00"),
        metrics=HoldingMetricsSchema(
            total_sales=Decimal("50000000.00"),
            inventory_value=Decimal("10000000.00"),
            waste_pct=Decimal("4.50"),
        ),
        tenants=[],
        daily_usage=[
            HoldingDailyCreditUsageItem(date="2026-11-01", credits=300, tokens=70000, requests=35),
            HoldingDailyCreditUsageItem(date="2026-11-02", credits=350, tokens=80000, requests=40),
        ],
    )

    service = HoldingBriefingService()
    briefing = service.generate_holding_briefing(uuid.UUID(h_id), critical_summary)

    pred = briefing.safety_cap_prediction
    assert pred.status == "CRITICAL"
    assert "urgente" in pred.recommendation.lower() or "crítico" in pred.recommendation.lower()


def test_holding_briefing_achievements_and_alerts(
    sample_summary: HoldingHubSummaryResponse,
) -> None:
    """Verifica que se generen aciertos operacionales y alertas cuando hay sucursales con alto consumo."""
    # Modificar una sucursal para tener WARNING
    sample_summary.tenants[0].safety_status = "WARNING"
    sample_summary.tenants[0].usage_pct = Decimal("85.00")

    service = HoldingBriefingService()
    briefing = service.generate_holding_briefing(uuid.UUID(sample_summary.holding_id), sample_summary)

    assert len(briefing.key_achievements) >= 2
    assert len(briefing.cost_alerts) >= 1
    # Verifica que la sucursal en warning fue detectada
    assert any("Cordillera Grill Vitacura" in alert for alert in briefing.cost_alerts)


def test_holding_briefing_tokens_and_telemetry(
    sample_summary: HoldingHubSummaryResponse,
) -> None:
    """Verifica cálculo de tokens LLM y emisión del registro de telemetría."""
    sink = InMemoryTelemetrySink()
    service = HoldingBriefingService(telemetry_sink=sink)
    holding_uuid = uuid.UUID(sample_summary.holding_id)

    briefing = service.generate_holding_briefing(holding_uuid, sample_summary)

    assert briefing.tokens_used > 100
    assert briefing.credits_deducted == Decimal("1.00")
    assert briefing.model_name == "gemini-1.5-flash"

    # Verificar que el sink de telemetría recibió el registro
    assert len(sink.records) == 1
    rec = sink.records[0]
    assert rec.holding_id == holding_uuid
    assert rec.caller_feature == "holding_daily_briefing"
    assert rec.model_name == "gemini-1.5-flash"
    assert rec.credits_deducted == Decimal("1.00")
    assert rec.api_success is True


@pytest.mark.asyncio
async def test_holding_briefing_awaitable_and_sync(
    sample_summary: HoldingHubSummaryResponse,
) -> None:
    """Verifica que generate_holding_briefing se pueda invocar sincrónicamente O con await."""
    service = HoldingBriefingService()
    holding_uuid = uuid.UUID(sample_summary.holding_id)

    # 1. Llamada sincrónica directa
    sync_res = service.generate_holding_briefing(holding_uuid, sample_summary)
    assert isinstance(sync_res, HoldingBriefingResponse)
    assert len(sync_res.summary_paragraphs) == 2

    # 2. Llamada asincrónica con await
    async_res = await service.generate_holding_briefing(holding_uuid, sample_summary)
    assert isinstance(async_res, HoldingBriefingResponse)
    assert async_res.tokens_used == sync_res.tokens_used


@pytest.mark.asyncio
async def test_holding_briefing_async_db_deduction(
    sample_summary: HoldingHubSummaryResponse,
) -> None:
    """Verifica deducción atómica de créditos corporativos en DB."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    holding_uuid = uuid.UUID(sample_summary.holding_id)

    mock_holding = MagicMock(spec=Holding)
    mock_holding.id = holding_uuid
    mock_holding.ai_credit_balance = Decimal("15000.00")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_holding
    mock_session.execute.return_value = mock_result

    service = HoldingBriefingService()
    briefing = await service.generate_holding_briefing_async(
        holding_id=holding_uuid,
        summary=sample_summary,
        session=mock_session,
        user_id=42,
    )

    assert isinstance(briefing, HoldingBriefingResponse)
    # Deducción atómica: 15000 - 1.00 = 14999.00
    assert mock_holding.ai_credit_balance == Decimal("14999.00")
    assert mock_session.add.called
    assert mock_session.commit.called
