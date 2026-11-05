"""
oppytec-backend/tests/unit/test_holding_hub_domain.py
Suite de pruebas unitarias exhaustivas para Holding Hub Enterprise (Etapa 1):
1. Invariantes de Value Objects: Cero float, inmutabilidad y validaciones.
2. Modos de distribución de créditos: SHARED vs ALLOCATED.
3. Reglas de negocio puras:
   - validate_credit_distribution_sum
   - calculate_holding_ai_usage_pct
   - compute_safety_cap_status
4. Esquemas Pydantic V2 de presentación y contratos OpenAPI:
   - HoldingHubSummaryResponse, HoldingTenantCardResponse, HoldingDailyCreditUsageItem,
     HoldingCreditDistributionRequest/Response, HoldingPurchaseCreditsRequest/Response,
     HoldingPlanChangeRequest/Response, HoldingBenchmarkingResponse.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.exceptions import DomainValidationError
from src.modules.tenancy.domain.holding_hub import (
    CreditDistributionMode,
    DailyUsagePointVO,
    HoldingMetricsVO,
    HoldingSummaryVO,
    TenantCardVO,
    calculate_holding_ai_usage_pct,
    compute_safety_cap_status,
    validate_credit_distribution_sum,
)
from src.modules.tenancy.presentation.schemas_holding_hub import (
    HoldingBenchmarkingResponse,
    HoldingCreditDistributionRequest,
    HoldingCreditDistributionResponse,
    HoldingDailyCreditUsageItem,
    HoldingHubSummaryResponse,
    HoldingMetricsSchema,
    HoldingPlanChangeRequest,
    HoldingPlanChangeResponse,
    HoldingPurchaseCreditsRequest,
    HoldingPurchaseCreditsResponse,
    HoldingTenantCardResponse,
)

pytestmark = pytest.mark.unit


# ============================================================================
# 1. ENUMS Y VALUE OBJECTS DE DOMINIO PURO
# ============================================================================


class TestCreditDistributionMode:
    """Pruebas del Enum de distribución de créditos."""

    def test_enum_values(self) -> None:
        assert CreditDistributionMode.SHARED.value == "shared"
        assert CreditDistributionMode.ALLOCATED.value == "allocated"
        assert CreditDistributionMode("shared") == CreditDistributionMode.SHARED
        assert CreditDistributionMode("allocated") == CreditDistributionMode.ALLOCATED


class TestHoldingMetricsVO:
    """Pruebas de invariantes y regla de oro (0 float) para HoldingMetricsVO."""

    def test_valid_metrics_creation(self) -> None:
        metrics = HoldingMetricsVO(
            total_sales=Decimal("1500000.50"),
            inventory_value=Decimal("450000.00"),
            waste_pct=Decimal("3.25"),
        )
        assert metrics.total_sales == Decimal("1500000.50")
        assert metrics.inventory_value == Decimal("450000.00")
        assert metrics.waste_pct == Decimal("3.25")
        # Aliases en español
        assert metrics.ventas_totales == Decimal("1500000.50")
        assert metrics.valor_inventario == Decimal("450000.00")
        assert metrics.merma_porcentual == Decimal("3.25")

    def test_float_strictly_forbidden(self) -> None:
        with pytest.raises(DomainValidationError, match="Prohibido el uso de float"):
            HoldingMetricsVO(
                total_sales=1500000.50,  # type: ignore[arg-type]
                inventory_value=Decimal("450000.00"),
                waste_pct=Decimal("3.25"),
            )

        with pytest.raises(DomainValidationError, match="Prohibido el uso de float"):
            HoldingMetricsVO(
                total_sales=Decimal("1000.00"),
                inventory_value=450.0,  # type: ignore[arg-type]
                waste_pct=Decimal("3.25"),
            )

        with pytest.raises(DomainValidationError, match="Prohibido el uso de float"):
            HoldingMetricsVO(
                total_sales=Decimal("1000.00"),
                inventory_value=Decimal("450.00"),
                waste_pct=3.25,  # type: ignore[arg-type]
            )

    def test_negative_values_rejected(self) -> None:
        with pytest.raises(DomainValidationError, match="total_sales cannot be negative"):
            HoldingMetricsVO(
                total_sales=Decimal("-10.00"),
                inventory_value=Decimal("100.00"),
                waste_pct=Decimal("5.00"),
            )

        with pytest.raises(DomainValidationError, match="inventory_value cannot be negative"):
            HoldingMetricsVO(
                total_sales=Decimal("10.00"),
                inventory_value=Decimal("-100.00"),
                waste_pct=Decimal("5.00"),
            )

        with pytest.raises(DomainValidationError, match="waste_pct must be between"):
            HoldingMetricsVO(
                total_sales=Decimal("10.00"),
                inventory_value=Decimal("100.00"),
                waste_pct=Decimal("-0.01"),
            )

        with pytest.raises(DomainValidationError, match="waste_pct must be between"):
            HoldingMetricsVO(
                total_sales=Decimal("10.00"),
                inventory_value=Decimal("100.00"),
                waste_pct=Decimal("100.01"),
            )

    def test_immutability(self) -> None:
        metrics = HoldingMetricsVO(
            total_sales=Decimal("100.00"),
            inventory_value=Decimal("50.00"),
            waste_pct=Decimal("2.00"),
        )
        with pytest.raises(FrozenInstanceError):
            metrics.total_sales = Decimal("200.00")  # type: ignore[misc]


class TestTenantCardVO:
    """Pruebas de la ficha de sucursal TenantCardVO."""

    def test_creation_spanish_and_english_kwargs(self) -> None:
        card_es = TenantCardVO(
            id="ten-001",
            nombre="Restaurante Providencia",
            schema_name="tenant_providencia",
            estado_operativo="active",
            creditos_usados=120,
            creditos_asignados=500,
            solicitudes_bot=45,
        )
        assert card_es.id == "ten-001"
        assert card_es.nombre == "Restaurante Providencia"
        assert card_es.schema_name == "tenant_providencia"
        assert card_es.estado_operativo == "active"
        assert card_es.creditos_usados == 120
        assert card_es.creditos_asignados == 500
        assert card_es.solicitudes_bot == 45
        # English properties
        assert card_es.tenant_id == "ten-001"
        assert card_es.name == "Restaurante Providencia"
        assert card_es.operational_status == "active"
        assert card_es.used_credits == 120
        assert card_es.allocated_credits == 500
        assert card_es.bot_requests == 45

        card_en = TenantCardVO(
            tenant_id="ten-002",
            name="Restaurante Las Condes",
            schema_name="tenant_las_condes",
            operational_status="active",
            used_credits=300,
            allocated_credits=600,
            bot_requests=90,
        )
        assert card_en.id == "ten-002"
        assert card_en.name == "Restaurante Las Condes"
        assert card_en.creditos_usados == 300

    def test_float_forbidden_in_credits(self) -> None:
        with pytest.raises(DomainValidationError, match="Prohibido el uso de float"):
            TenantCardVO(
                id="ten-001",
                nombre="Local",
                schema_name="tenant_local",
                creditos_usados=120.5,  # type: ignore[arg-type]
            )

    def test_negative_credits_rejected(self) -> None:
        with pytest.raises(DomainValidationError, match="no puede ser negativo"):
            TenantCardVO(
                id="ten-001",
                nombre="Local",
                schema_name="tenant_local",
                creditos_usados=-5,
            )

    def test_immutability(self) -> None:
        card = TenantCardVO(
            id="ten-001",
            nombre="Local",
            schema_name="tenant_local",
        )
        with pytest.raises(FrozenInstanceError):
            card.creditos_usados = 50  # type: ignore[misc]


class TestHoldingSummaryVO:
    """Pruebas del agregado / VO HoldingSummaryVO."""

    def test_creation_success(self) -> None:
        metrics = HoldingMetricsVO(
            total_sales=Decimal("5000000.00"),
            inventory_value=Decimal("800000.00"),
            waste_pct=Decimal("2.50"),
        )
        tenant1 = TenantCardVO(
            id="ten-001",
            nombre="Sucursal 1",
            schema_name="tenant_s1",
            creditos_usados=100,
            creditos_asignados=500,
            solicitudes_bot=25,
        )

        summary = HoldingSummaryVO(
            holding_id="hold-999",
            nombre="Grupo Gastronómico Central",
            balance_creditos=2500,
            modo_distribucion=CreditDistributionMode.ALLOCATED,
            sucursales=[tenant1],
            kpis_globales=metrics,
        )

        assert summary.holding_id == "hold-999"
        assert summary.nombre == "Grupo Gastronómico Central"
        assert summary.name == "Grupo Gastronómico Central"
        assert summary.balance_creditos == 2500
        assert summary.credit_balance == 2500
        assert summary.modo_distribucion == CreditDistributionMode.ALLOCATED
        assert summary.distribution_mode == CreditDistributionMode.ALLOCATED
        assert len(summary.sucursales) == 1
        assert len(summary.tenants) == 1
        assert summary.metrics == metrics
        assert isinstance(summary.sucursales, tuple)

    def test_rejection_of_float_balance(self) -> None:
        metrics = HoldingMetricsVO(
            total_sales=Decimal("0.00"),
            inventory_value=Decimal("0.00"),
            waste_pct=Decimal("0.00"),
        )
        with pytest.raises(DomainValidationError, match="Prohibido el uso de float"):
            HoldingSummaryVO(
                holding_id="hold-1",
                nombre="Holding",
                balance_creditos=100.5,  # type: ignore[arg-type]
                kpis_globales=metrics,
            )

    def test_rejection_of_negative_balance(self) -> None:
        metrics = HoldingMetricsVO(
            total_sales=Decimal("0.00"),
            inventory_value=Decimal("0.00"),
            waste_pct=Decimal("0.00"),
        )
        with pytest.raises(DomainValidationError, match="balance_creditos cannot be negative"):
            HoldingSummaryVO(
                holding_id="hold-1",
                nombre="Holding",
                balance_creditos=-10,
                kpis_globales=metrics,
            )


class TestDailyUsagePointVO:
    """Pruebas del punto de serie temporal DailyUsagePointVO."""

    def test_valid_creation(self) -> None:
        point = DailyUsagePointVO(
            date="2026-11-01",
            credits=150,
            tokens=150000,
            requests=32,
        )
        assert point.date == "2026-11-01"
        assert point.credits == 150
        assert point.tokens == 150000
        assert point.requests == 32

    def test_float_forbidden(self) -> None:
        with pytest.raises(DomainValidationError, match="Prohibido el uso de float"):
            DailyUsagePointVO(
                date="2026-11-01",
                credits=150.5,  # type: ignore[arg-type]
                tokens=100,
                requests=5,
            )

    def test_negative_rejected(self) -> None:
        with pytest.raises(DomainValidationError, match="no puede ser negativo"):
            DailyUsagePointVO(
                date="2026-11-01",
                credits=10,
                tokens=-5,
                requests=1,
            )


# ============================================================================
# 2. REGLAS PURAS DE DOMINIO
# ============================================================================


class TestCreditDistributionRules:
    """Pruebas para validate_credit_distribution_sum."""

    def test_valid_allocations_within_limit(self) -> None:
        total = 1000
        allocations = {
            "ten-001": 300,
            "ten-002": 400,
            "ten-003": 300,
        }
        ok, error = validate_credit_distribution_sum(total, allocations)
        assert ok is True
        assert error is None

    def test_allocations_sum_less_than_total(self) -> None:
        total = 2000
        allocations = {"ten-001": 500, "ten-002": 500}
        ok, error = validate_credit_distribution_sum(total, allocations)
        assert ok is True
        assert error is None

    def test_empty_allocations_valid(self) -> None:
        ok, error = validate_credit_distribution_sum(1000, {})
        assert ok is True
        assert error is None

    def test_allocations_exceeding_total(self) -> None:
        total = 500
        allocations = {"ten-001": 300, "ten-002": 300}
        ok, error = validate_credit_distribution_sum(total, allocations)
        assert ok is False
        assert "exceeds holding total credits" in str(error)

    def test_negative_allocation_rejected(self) -> None:
        total = 1000
        allocations = {"ten-001": -50, "ten-002": 200}
        ok, error = validate_credit_distribution_sum(total, allocations)
        assert ok is False
        assert "cannot be negative" in str(error)

    def test_negative_total_credits_rejected(self) -> None:
        ok, error = validate_credit_distribution_sum(-100, {"ten-001": 50})
        assert ok is False
        assert "Total holding credits cannot be negative" in str(error)

    def test_float_strictly_raises_domain_error(self) -> None:
        with pytest.raises(DomainValidationError, match="Prohibido el uso de float"):
            validate_credit_distribution_sum(100.5, {})  # type: ignore[arg-type]

        with pytest.raises(DomainValidationError, match="Prohibido el uso de float"):
            validate_credit_distribution_sum(1000, {"ten-1": 50.5})  # type: ignore[arg-type]


class TestHoldingAIUsagePct:
    """Pruebas de calculate_holding_ai_usage_pct."""

    def test_exact_calculation(self) -> None:
        # 250 / 1000 = 25.00%
        pct = calculate_holding_ai_usage_pct(250, 1000)
        assert pct == Decimal("25.00")
        assert isinstance(pct, Decimal)

    def test_rounding_half_up(self) -> None:
        # 1 / 3 = 33.33%
        pct = calculate_holding_ai_usage_pct(1, 3)
        assert pct == Decimal("33.33")

        # 2 / 3 = 66.67%
        pct2 = calculate_holding_ai_usage_pct(2, 3)
        assert pct2 == Decimal("66.67")

    def test_zero_total_credits(self) -> None:
        # Si total_credits == 0 y used_credits == 0 -> 0.00%
        assert calculate_holding_ai_usage_pct(0, 0) == Decimal("0.00")
        # Si total_credits == 0 y used_credits > 0 -> 100.00%
        assert calculate_holding_ai_usage_pct(50, 0) == Decimal("100.00")

    def test_full_and_over_capacity(self) -> None:
        assert calculate_holding_ai_usage_pct(1000, 1000) == Decimal("100.00")
        assert calculate_holding_ai_usage_pct(1200, 1000) == Decimal("120.00")

    def test_negative_credits_rejected(self) -> None:
        with pytest.raises(DomainValidationError, match="cannot be negative"):
            calculate_holding_ai_usage_pct(-10, 100)

        with pytest.raises(DomainValidationError, match="cannot be negative"):
            calculate_holding_ai_usage_pct(10, -100)

    def test_float_strictly_rejected(self) -> None:
        with pytest.raises(DomainValidationError, match="Prohibido el uso de float"):
            calculate_holding_ai_usage_pct(10.5, 100)  # type: ignore[arg-type]


class TestSafetyCapStatus:
    """Pruebas de compute_safety_cap_status (NORMAL, WARNING, CRITICAL)."""

    def test_status_thresholds(self) -> None:
        # < 80.00% -> NORMAL
        assert compute_safety_cap_status(0, 100) == "NORMAL"
        assert compute_safety_cap_status(50, 100) == "NORMAL"
        assert compute_safety_cap_status(79, 100) == "NORMAL"

        # 80.00% <= usage < 95.00% -> WARNING
        assert compute_safety_cap_status(80, 100) == "WARNING"
        assert compute_safety_cap_status(90, 100) == "WARNING"
        assert compute_safety_cap_status(94, 100) == "WARNING"

        # >= 95.00% -> CRITICAL
        assert compute_safety_cap_status(95, 100) == "CRITICAL"
        assert compute_safety_cap_status(99, 100) == "CRITICAL"
        assert compute_safety_cap_status(100, 100) == "CRITICAL"
        assert compute_safety_cap_status(120, 100) == "CRITICAL"


# ============================================================================
# 3. ESQUEMAS PYDANTIC V2 Y CONTRATOS OPENAPI
# ============================================================================


class TestHoldingHubSchemasPydanticV2:
    """Pruebas de serialización, validación y sanitización en Pydantic V2."""

    def test_daily_usage_item(self) -> None:
        item = HoldingDailyCreditUsageItem(
            date="2026-11-05",
            credits=200,
            tokens=200000,
            requests=50,
        )
        data = item.model_dump()
        assert data["credits"] == 200
        assert data["tokens"] == 200000

        with pytest.raises(ValidationError):
            HoldingDailyCreditUsageItem(
                date="2026-11-05",
                credits=-1,
                tokens=100,
                requests=1,
            )

    def test_metrics_schema_and_from_domain(self) -> None:
        vo = HoldingMetricsVO(
            total_sales=Decimal("950000.00"),
            inventory_value=Decimal("120000.00"),
            waste_pct=Decimal("4.50"),
        )
        schema = HoldingMetricsSchema.from_domain(vo)
        assert schema.total_sales == Decimal("950000.00")
        assert schema.waste_pct == Decimal("4.50")

    def test_tenant_card_response_and_from_domain(self) -> None:
        vo = TenantCardVO(
            id="ten-abc",
            nombre="Sucursal Santiago",
            schema_name="tenant_santiago",
            estado_operativo="active",
            creditos_usados=400,
            creditos_asignados=500,
            solicitudes_bot=80,
        )
        card = HoldingTenantCardResponse.from_domain(
            vo,
            usage_pct=Decimal("80.00"),
            safety_status="WARNING",
        )
        assert card.id == "ten-abc"
        assert card.name == "Sucursal Santiago"
        assert card.used_credits == 400
        assert card.usage_pct == Decimal("80.00")
        assert card.safety_status == "WARNING"

    def test_hub_summary_response_validation(self) -> None:
        summary = HoldingHubSummaryResponse(
            holding_id="hold-uuid-1",
            name="Holding Corporativo Gastronómico",
            credit_balance=1000,
            total_credits=2000,
            used_credits=1000,
            distribution_mode=CreditDistributionMode.SHARED,
            safety_status="NORMAL",
            usage_pct=Decimal("50.00"),
            metrics=HoldingMetricsSchema(
                total_sales=Decimal("10000000.00"),
                inventory_value=Decimal("2000000.00"),
                waste_pct=Decimal("1.80"),
            ),
            tenants=[],
            daily_usage=[],
        )
        assert summary.holding_id == "hold-uuid-1"
        assert summary.distribution_mode == CreditDistributionMode.SHARED

    def test_credit_distribution_request_response(self) -> None:
        req = HoldingCreditDistributionRequest(
            distribution_mode=CreditDistributionMode.ALLOCATED,
            allocations={"ten-1": 500, "ten-2": 300},
        )
        assert req.allocations["ten-1"] == 500

        with pytest.raises(ValidationError):
            HoldingCreditDistributionRequest(
                distribution_mode=CreditDistributionMode.ALLOCATED,
                allocations={"ten-1": -50},
            )

        res = HoldingCreditDistributionResponse(
            success=True,
            holding_id="hold-1",
            distribution_mode=CreditDistributionMode.ALLOCATED,
            allocations={"ten-1": 500, "ten-2": 300},
            total_allocated=800,
            unallocated_credits=200,
            message="Distribución actualizada con éxito",
        )
        assert res.success is True
        assert res.unallocated_credits == 200

    def test_purchase_credits_request_response(self) -> None:
        req = HoldingPurchaseCreditsRequest(
            holding_id="hold-1",
            credits_amount=5000,
            currency="CLP",
            payment_method="webpay",
            idempotency_key="tx-idem-12345",
        )
        assert req.credits_amount == 5000

        # Currency validation
        with pytest.raises(ValidationError):
            HoldingPurchaseCreditsRequest(
                holding_id="hold-1",
                credits_amount=100,
                currency="INVALID_CURRENCY",
            )

        res = HoldingPurchaseCreditsResponse(
            success=True,
            holding_id="hold-1",
            credits_purchased=5000,
            previous_balance=1000,
            new_balance=6000,
            amount_paid=Decimal("75000.00"),
            currency="CLP",
            transaction_id="tx_webpay_9988",
            purchased_at=datetime.now(timezone.utc),
        )
        assert res.new_balance == 6000

    def test_plan_change_request_response(self) -> None:
        req = HoldingPlanChangeRequest(
            holding_id="hold-1",
            new_plan_slug="enterprise-tier3",
            reason="Expansion to 5 new restaurants",
        )
        assert req.new_plan_slug == "enterprise-tier3"

        res = HoldingPlanChangeResponse(
            success=True,
            holding_id="hold-1",
            previous_plan_slug="pro-tier2",
            new_plan_slug="enterprise-tier3",
            monthly_credits=10000,
            effective_date=datetime.now(timezone.utc),
            message="Plan cambiado a enterprise-tier3 exitosamente",
        )
        assert res.success is True

    def test_benchmarking_response(self) -> None:
        bench = HoldingBenchmarkingResponse(
            holding_id="hold-1",
            benchmark_period="last_30_days",
            top_performing_tenant="Restaurante Providencia",
            highest_ai_consumer="Restaurante Las Condes",
            average_tenant_sales=Decimal("4500000.00"),
            average_waste_pct=Decimal("2.10"),
            tenant_comparisons=[
                {"tenant_id": "ten-1", "sales": 5000000, "waste_pct": 1.9},
                {"tenant_id": "ten-2", "sales": 4000000, "waste_pct": 2.3},
            ],
        )
        assert bench.top_performing_tenant == "Restaurante Providencia"
        assert bench.average_waste_pct == Decimal("2.10")

    def test_extra_forbid_on_all_schemas(self) -> None:
        """Verifica que extra='forbid' impida inyecciones no deseadas."""
        with pytest.raises(ValidationError):
            HoldingDailyCreditUsageItem(
                date="2026-11-05",
                credits=100,
                tokens=100000,
                requests=20,
                malicious_field="attack",  # type: ignore[call-arg]
            )
