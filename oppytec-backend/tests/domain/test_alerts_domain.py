"""
oppytec-backend/tests/domain/test_alerts_domain.py
Suite de Pruebas 5D para el Dominio de Alertas de Inventario, Vencimientos y FEFO.

Dimensiones 5D:
1. Nivel de Abstracción: Pruebas unitarias analíticas con casos canónicos y bordes.
2. Basada en Propiedades (Hypothesis): Invariantes algebraicas de clamp, ratios y días.
3. Paridad 1:1 con Legacy: Fórmulas de salud cromática de existencias y urgencia de lote.
4. Robustez de Frontera: Divisiones por cero (stock_minimo=0), stocks negativos y números extremos.
5. Certificación Decimal Estricta: Prohibición total de IEEE 754 float en cálculos.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.modules.inventory.domain.alerts import (
    MONEY_QUANT,
    PERCENT_QUANT,
    QTY_QUANT,
    ZERO,
    AlertBadgeSummary,
    AlertSeverity,
    AlertType,
    AlertsConsolidatedSummary,
    AlertsRepositoryInterface,
    CriticalStockAlert,
    ExpiredLotAlert,
    ExpiryUrgency,
    StockHealthRatio,
    UpcomingExpiryAlert,
)

pytestmark = [pytest.mark.unit]


# ============================================================================
# DIMENSIÓN 1: PRUEBAS UNITARIAS ANALÍTICAS CON CASOS CANÓNICOS
# ============================================================================


class TestStockHealthRatioUnit:
    """Pruebas analíticas de StockHealthRatio con casos canónicos."""

    def test_stock_depleted_zero(self) -> None:
        """Stock actual 0 con stock mínimo 10 debe resultar en ratio 0% y status depleted."""
        ratio = StockHealthRatio.calculate(stock_actual=Decimal("0"), stock_minimo=Decimal("10"))
        assert ratio.stock_actual == Decimal("0.0000")
        assert ratio.stock_minimo == Decimal("10.0000")
        assert ratio.raw_ratio == Decimal("0.00")
        assert ratio.clamped_ratio == Decimal("0.00")
        assert ratio.status == "depleted"
        assert ratio.is_depleted is True
        assert ratio.is_critical is False

    def test_stock_depleted_negative(self) -> None:
        """Stock actual negativo (descuadre) debe resultar en ratio negativo raw, clamped 0% y status depleted."""
        ratio = StockHealthRatio.calculate(stock_actual=Decimal("-5.5"), stock_minimo=Decimal("10"))
        assert ratio.stock_actual == Decimal("-5.5000")
        assert ratio.raw_ratio == Decimal("-55.00")
        assert ratio.clamped_ratio == Decimal("0.00")
        assert ratio.status == "depleted"
        assert ratio.is_depleted is True

    def test_stock_critical_boundary(self) -> None:
        """Stock actual exactamente al 50% del mínimo debe ser critical."""
        ratio = StockHealthRatio.calculate(stock_actual=Decimal("5"), stock_minimo=Decimal("10"))
        assert ratio.raw_ratio == Decimal("50.00")
        assert ratio.clamped_ratio == Decimal("50.00")
        assert ratio.status == "critical"
        assert ratio.is_critical is True
        assert ratio.is_depleted is False

    def test_stock_warning_range(self) -> None:
        """Stock actual al 75% del mínimo debe ser warning."""
        ratio = StockHealthRatio.calculate(stock_actual=Decimal("7.5"), stock_minimo=Decimal("10"))
        assert ratio.raw_ratio == Decimal("75.00")
        assert ratio.clamped_ratio == Decimal("75.00")
        assert ratio.status == "warning"
        assert ratio.is_warning is True

    def test_stock_warning_at_minimum_exact(self) -> None:
        """Stock actual exactamente igual al mínimo (100%) debe ser warning."""
        ratio = StockHealthRatio.calculate(stock_actual=Decimal("10"), stock_minimo=Decimal("10"))
        assert ratio.raw_ratio == Decimal("100.00")
        assert ratio.clamped_ratio == Decimal("100.00")
        assert ratio.status == "warning"
        assert ratio.is_warning is True

    def test_stock_healthy_above_minimum(self) -> None:
        """Stock actual 150% del mínimo debe ser healthy con clamped_ratio en 100%."""
        ratio = StockHealthRatio.calculate(stock_actual=Decimal("15"), stock_minimo=Decimal("10"))
        assert ratio.raw_ratio == Decimal("150.00")
        assert ratio.clamped_ratio == Decimal("100.00")
        assert ratio.status == "healthy"
        assert ratio.is_healthy is True


class TestExpiryUrgencyUnit:
    """Pruebas analíticas de ExpiryUrgency con cálculo de días y severidad."""

    def test_lot_already_expired(self) -> None:
        """Lote expirado hace 5 días debe marcar is_expired=True, dias_vencido=5 y CRITICAL."""
        ref = date(2026, 10, 25)
        exp = date(2026, 10, 20)
        urgency = ExpiryUrgency.calculate(fecha_vencimiento=exp, reference_date=ref)
        assert urgency.is_expired is True
        assert urgency.dias_vencido == 5
        assert urgency.dias_restantes == 0
        assert urgency.severity == AlertSeverity.CRITICAL

    def test_lot_expiring_today(self) -> None:
        """Lote que expira hoy tiene 0 días restantes y severidad CRITICAL."""
        ref = date(2026, 10, 25)
        urgency = ExpiryUrgency.calculate(fecha_vencimiento=ref, reference_date=ref)
        assert urgency.is_expired is False
        assert urgency.dias_vencido == 0
        assert urgency.dias_restantes == 0
        assert urgency.severity == AlertSeverity.CRITICAL

    def test_lot_expiring_within_critical_threshold(self) -> None:
        """Lote que expira en 3 días (<= 7 días) tiene severidad CRITICAL."""
        ref = date(2026, 10, 25)
        exp = ref + timedelta(days=3)
        urgency = ExpiryUrgency.calculate(fecha_vencimiento=exp, reference_date=ref)
        assert urgency.is_expired is False
        assert urgency.dias_restantes == 3
        assert urgency.severity == AlertSeverity.CRITICAL

    def test_lot_expiring_within_warning_threshold(self) -> None:
        """Lote que expira en 20 días (<= 30 días) tiene severidad WARNING."""
        ref = date(2026, 10, 25)
        exp = ref + timedelta(days=20)
        urgency = ExpiryUrgency.calculate(fecha_vencimiento=exp, reference_date=ref)
        assert urgency.is_expired is False
        assert urgency.dias_restantes == 20
        assert urgency.severity == AlertSeverity.WARNING

    def test_lot_expiring_beyond_warning_threshold(self) -> None:
        """Lote que expira en 60 días (> 30 días) tiene severidad INFO."""
        ref = date(2026, 10, 25)
        exp = ref + timedelta(days=60)
        urgency = ExpiryUrgency.calculate(fecha_vencimiento=exp, reference_date=ref)
        assert urgency.is_expired is False
        assert urgency.dias_restantes == 60
        assert urgency.severity == AlertSeverity.INFO


class TestDomainEntitiesAndInvariants:
    """Pruebas de invariantes de las entidades de dominio de alertas."""

    def test_critical_stock_alert_creation_and_invariants(self) -> None:
        alert = CriticalStockAlert.create(
            producto_id=101,
            bodega_id=2,
            bodega_nombre="Bodega Central",
            producto_nombre="Harina de Fuerza",
            stock_actual=Decimal("5.0000"),
            stock_minimo=Decimal("20.0000"),
            unidad_medida="KG",
            bodega_color="#2563EB",
            bodega_icono="box",
            costo_promedio=Decimal("1250.50"),
        )
        assert alert.producto_id == 101
        assert alert.bodega_id == 2
        assert alert.stock_actual == Decimal("5.0000")
        assert alert.stock_minimo == Decimal("20.0000")
        assert alert.costo_promedio == Decimal("1250.50")
        assert alert.ratio.status == "critical"
        assert alert.is_depleted is False

    def test_critical_stock_alert_rejects_above_minimum(self) -> None:
        """Si stock_actual > stock_minimo, no es una alerta crítica y debe rechazarla."""
        with pytest.raises(ValueError, match="no constituye alerta de stock crítico"):
            CriticalStockAlert.create(
                producto_id=101,
                bodega_id=2,
                bodega_nombre="Bodega Central",
                producto_nombre="Harina de Fuerza",
                stock_actual=Decimal("25.0000"),
                stock_minimo=Decimal("20.0000"),
                unidad_medida="KG",
            )

    def test_critical_stock_alert_rejects_invalid_ids(self) -> None:
        with pytest.raises(ValueError, match="producto_id debe ser un entero positivo"):
            CriticalStockAlert.create(
                producto_id=0,
                bodega_id=2,
                bodega_nombre="Bodega Central",
                producto_nombre="Harina",
                stock_actual=Decimal("0"),
                stock_minimo=Decimal("10"),
                unidad_medida="KG",
            )

    def test_expired_lot_alert_financial_risk(self) -> None:
        alert = ExpiredLotAlert.create(
            producto_id=205,
            bodega_id=1,
            bodega_nombre="Cocina Caliente",
            producto_nombre="Crema de Leche",
            lote_codigo="LOT-2026-001",
            fecha_vencimiento=date(2026, 10, 1),
            cantidad_vencida=Decimal("12.5000"),
            dias_vencido=24,
            costo_ppp=Decimal("2400.00"),
            unidad_medida="LT",
        )
        # 12.5 * 2400 = 30000.00
        assert alert.valor_total_riesgo == Decimal("30000.00")

    def test_expired_lot_alert_rejects_negative_or_zero_qty(self) -> None:
        with pytest.raises(ValueError, match="cantidad_vencida debe ser estrictamente positiva"):
            ExpiredLotAlert.create(
                producto_id=205,
                bodega_id=1,
                bodega_nombre="Cocina",
                producto_nombre="Crema",
                lote_codigo="LOT-01",
                fecha_vencimiento=date(2026, 10, 1),
                cantidad_vencida=Decimal("0.0000"),
                dias_vencido=5,
                costo_ppp=Decimal("1000.00"),
                unidad_medida="LT",
            )

    def test_upcoming_expiry_alert_financial_risk(self) -> None:
        alert = UpcomingExpiryAlert.create(
            producto_id=301,
            bodega_id=3,
            bodega_nombre="Barra",
            producto_nombre="Jugo Natural",
            lote_codigo="JUGO-77",
            fecha_vencimiento=date(2026, 10, 30),
            cantidad_en_riesgo=Decimal("8.0000"),
            dias_restantes=5,
            costo_ppp=Decimal("1500.50"),
            unidad_medida="LT",
        )
        # 8.0 * 1500.50 = 12004.00
        assert alert.valor_total_riesgo == Decimal("12004.00")

    def test_consolidated_summary_aggregation(self) -> None:
        c1 = CriticalStockAlert.create(
            producto_id=1,
            bodega_id=1,
            bodega_nombre="B1",
            producto_nombre="Prod 1",
            stock_actual=Decimal("0"),
            stock_minimo=Decimal("10"),
            unidad_medida="UN",
        )
        e1 = ExpiredLotAlert.create(
            producto_id=2,
            bodega_id=1,
            bodega_nombre="B1",
            producto_nombre="Prod 2",
            lote_codigo="L1",
            fecha_vencimiento=date(2026, 10, 10),
            cantidad_vencida=Decimal("5.0000"),
            dias_vencido=15,
            costo_ppp=Decimal("1000.00"),
            unidad_medida="KG",
        )
        u1 = UpcomingExpiryAlert.create(
            producto_id=3,
            bodega_id=1,
            bodega_nombre="B1",
            producto_nombre="Prod 3",
            lote_codigo="L2",
            fecha_vencimiento=date(2026, 11, 1),
            cantidad_en_riesgo=Decimal("10.0000"),
            dias_restantes=7,
            costo_ppp=Decimal("2000.00"),
            unidad_medida="KG",
        )

        summary = AlertsConsolidatedSummary.create(
            critical_stock=[c1],
            expired_lots=[e1],
            upcoming_expiries=[u1],
        )

        assert summary.total_count == 3
        assert summary.critical_count == 1
        assert summary.expired_count == 1
        assert summary.upcoming_count == 1
        assert summary.has_critical is True
        # Total riesgo: 5*1000 (5000) + 10*2000 (20000) = 25000.00
        assert summary.total_financial_risk == Decimal("25000.00")

        badge = summary.to_badge_summary()
        assert badge.total_count == 3
        assert badge.has_critical is True
        assert badge.critical_stock_count == 1
        assert badge.expired_count == 1
        assert badge.upcoming_count == 1


# ============================================================================
# DIMENSIÓN 2: BASADA EN PROPIEDADES (HYPOTHESIS)
# ============================================================================


class TestAlertsPropertyInvariants:
    """Invariantes universales verificadas con Hypothesis."""

    @given(
        actual=st.decimals(min_value=Decimal("-1000"), max_value=Decimal("10000"), places=4),
        minimo=st.decimals(min_value=Decimal("0.0001"), max_value=Decimal("10000"), places=4),
    )
    def test_stock_health_ratio_clamp_invariant(self, actual: Decimal, minimo: Decimal) -> None:
        """El clamped_ratio debe ser siempre estrictamente confinable en [0.00, 100.00]."""
        ratio = StockHealthRatio.calculate(actual, minimo)
        assert Decimal("0.00") <= ratio.clamped_ratio <= Decimal("100.00")
        assert ratio.status in {"depleted", "critical", "warning", "healthy"}
        if actual <= Decimal("0.0000"):
            assert ratio.status == "depleted"
            assert ratio.clamped_ratio == Decimal("0.00")

    @given(
        days_offset=st.integers(min_value=-365, max_value=365),
    )
    def test_expiry_urgency_days_invariant(self, days_offset: int) -> None:
        """Invariante: dias_vencido >= 0 y dias_restantes >= 0, y uno de los dos es 0 salvo colisión."""
        ref = date(2026, 10, 25)
        exp = ref + timedelta(days=days_offset)
        urgency = ExpiryUrgency.calculate(fecha_vencimiento=exp, reference_date=ref)

        assert urgency.dias_vencido >= 0
        assert urgency.dias_restantes >= 0
        if days_offset < 0:
            assert urgency.is_expired is True
            assert urgency.dias_vencido == abs(days_offset)
            assert urgency.dias_restantes == 0
            assert urgency.severity == AlertSeverity.CRITICAL
        else:
            assert urgency.is_expired is False
            assert urgency.dias_vencido == 0
            assert urgency.dias_restantes == days_offset


# ============================================================================
# DIMENSIÓN 3: PARIDAD 1:1 CON LEGACY
# ============================================================================


class TestLegacyParityFormulas:
    """
    Paridad con StockCriticoTable.tsx y useAlertas.ts:
    Legacy:
      const ratio = prod.stock_minimo > 0 ? (prod.cantidad / prod.stock_minimo) * 100 : 0;
      const cappedRatio = Math.min(Math.max(ratio, 5), 100);
      const getProgressColor = (current, min) => {
        if (current <= 0) return "bg-destructive";
        if (current <= min * 0.5) return "bg-orange-500";
        return "bg-amber-500";
      };
    """

    @pytest.mark.parametrize(
        "current,min_stock,expected_status",
        [
            (Decimal("0"), Decimal("100"), "depleted"),
            (Decimal("-1"), Decimal("50"), "depleted"),
            (Decimal("25"), Decimal("100"), "critical"),
            (Decimal("50"), Decimal("100"), "critical"),
            (Decimal("50.0001"), Decimal("100"), "warning"),
            (Decimal("75"), Decimal("100"), "warning"),
            (Decimal("100"), Decimal("100"), "warning"),
            (Decimal("101"), Decimal("100"), "healthy"),
        ],
    )
    def test_color_and_status_parity_with_legacy(
        self,
        current: Decimal,
        min_stock: Decimal,
        expected_status: str,
    ) -> None:
        ratio = StockHealthRatio.calculate(current, min_stock)
        assert ratio.status == expected_status


# ============================================================================
# DIMENSIÓN 4: ROBUSTEZ DE FRONTERA (EDGE CASES)
# ============================================================================


class TestEdgeCasesAndBoundaryRobustness:
    """Casos de frontera: stock mínimo cero, inventarios vacíos y protocolo."""

    def test_zero_minimum_stock_positive_actual(self) -> None:
        """Si stock_minimo es 0 y stock_actual > 0, es healthy con ratio 100%."""
        ratio = StockHealthRatio.calculate(stock_actual=Decimal("10"), stock_minimo=Decimal("0"))
        assert ratio.raw_ratio == Decimal("100.00")
        assert ratio.clamped_ratio == Decimal("100.00")
        assert ratio.status == "healthy"

    def test_zero_minimum_stock_zero_actual(self) -> None:
        """Si stock_minimo es 0 y stock_actual es 0, es depleted."""
        ratio = StockHealthRatio.calculate(stock_actual=Decimal("0"), stock_minimo=Decimal("0"))
        assert ratio.raw_ratio == Decimal("0.00")
        assert ratio.clamped_ratio == Decimal("0.00")
        assert ratio.status == "depleted"

    def test_empty_alerts_consolidated_summary(self) -> None:
        summary = AlertsConsolidatedSummary.create([], [], [])
        assert summary.total_count == 0
        assert summary.critical_count == 0
        assert summary.expired_count == 0
        assert summary.upcoming_count == 0
        assert summary.has_critical is False
        assert summary.total_financial_risk == Decimal("0.00")

        badge = summary.to_badge_summary()
        assert badge.total_count == 0
        assert badge.has_critical is False

    def test_repository_interface_protocol(self) -> None:
        """Verifica que AlertsRepositoryInterface sea runtime_checkable."""
        assert isinstance(AlertsRepositoryInterface, type)


# ============================================================================
# DIMENSIÓN 5: CERTIFICACIÓN DECIMAL ESTRICTA (0% FLOAT)
# ============================================================================


class TestStrictDecimalCertification:
    """Prohibición categórica de float IEEE 754 en todos los value objects y constructores."""

    def test_stock_health_ratio_rejects_float_actual(self) -> None:
        with pytest.raises(TypeError, match="no admite tipo float"):
            StockHealthRatio.calculate(stock_actual=5.5, stock_minimo=Decimal("10"))  # type: ignore[arg-type]

    def test_stock_health_ratio_rejects_float_minimo(self) -> None:
        with pytest.raises(TypeError, match="no admite tipo float"):
            StockHealthRatio.calculate(stock_actual=Decimal("5"), stock_minimo=10.0)  # type: ignore[arg-type]

    def test_critical_stock_alert_rejects_float(self) -> None:
        with pytest.raises(TypeError, match="no admite tipo float"):
            CriticalStockAlert.create(
                producto_id=1,
                bodega_id=1,
                bodega_nombre="B1",
                producto_nombre="P1",
                stock_actual=5.0,  # type: ignore[arg-type]
                stock_minimo=Decimal("10"),
                unidad_medida="UN",
            )

    def test_expired_lot_alert_rejects_float(self) -> None:
        with pytest.raises(TypeError, match="no admite tipo float"):
            ExpiredLotAlert.create(
                producto_id=1,
                bodega_id=1,
                bodega_nombre="B1",
                producto_nombre="P1",
                lote_codigo="L1",
                fecha_vencimiento=date(2026, 10, 1),
                cantidad_vencida=10.5,  # type: ignore[arg-type]
                dias_vencido=10,
                costo_ppp=Decimal("100"),
                unidad_medida="UN",
            )

    def test_upcoming_expiry_alert_rejects_float(self) -> None:
        with pytest.raises(TypeError, match="no admite tipo float"):
            UpcomingExpiryAlert.create(
                producto_id=1,
                bodega_id=1,
                bodega_nombre="B1",
                producto_nombre="P1",
                lote_codigo="L1",
                fecha_vencimiento=date(2026, 10, 30),
                cantidad_en_riesgo=Decimal("10"),
                dias_restantes=5,
                costo_ppp=150.5,  # type: ignore[arg-type]
                unidad_medida="UN",
            )
