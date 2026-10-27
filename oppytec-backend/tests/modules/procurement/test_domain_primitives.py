"""
oppytec-backend/tests/modules/procurement/test_domain_primitives.py
Pruebas unitarias de dominio puro para las primitivas DDD de Procurement:
- Value Objects: RutTaxId (validación Módulo 11 chileno e internacional), MoneyAmount (no negatividad, 0% float).
- Enums estricto: PurchaseStatus, IncidenceType, IncidenceResolution.
- Algoritmo matemático determinista de Costo Promedio Ponderado (PPP).
- Invariante de nombres propios no traducibles ("Pollo King").
- Entidades puras y máquina de estados de órdenes de compra.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.core.exceptions import ProperNounImmutabilityError
from src.modules.procurement.domain import (
    DocLine,
    IncidenceResolution,
    IncidenceType,
    InvalidPurchaseStatusTransitionError,
    InvalidRutError,
    MatchStatus,
    MoneyAmount,
    NegativeMoneyError,
    NegativeQuantityError,
    PurchaseIncidence,
    PurchaseItem,
    PurchaseOrder,
    PurchaseStatus,
    RutTaxId,
    Supplier,
    assert_supplier_name_immutable,
    calculate_chilean_dv,
    calculate_reception_ppp,
    reconcile_three_way,
)

pytestmark = pytest.mark.unit


# ==============================================================================
# 1. Pruebas de RutTaxId y Validación Módulo 11
# ==============================================================================


class TestRutTaxIdValidation:
    """Verifica el cálculo de Módulo 11 y el comportamiento del Value Object RutTaxId."""

    @pytest.mark.parametrize(
        ("body", "expected_dv"),
        [
            ("76543210", "3"),
            ("11111111", "1"),
            ("21345675", "K"),
            ("28", "0"),
            ("6", "K"),
            ("1", "9"),
        ],
    )
    def test_calculate_chilean_dv_deterministic(self, body: str, expected_dv: str) -> None:
        """Verifica que el algoritmo Módulo 11 retorne exactamente el DV chileno esperado."""
        assert calculate_chilean_dv(body) == expected_dv

    def test_rut_tax_id_valid_chilean_formats(self) -> None:
        """Valida que acepte formatos con o sin puntos, con o sin guión, y normalice."""
        rut1 = RutTaxId("76.543.210-3")
        assert rut1.formatted == "76.543.210-3"
        assert rut1.clean == "76543210-3"
        assert rut1.body == "76543210"
        assert rut1.dv == "3"
        assert rut1.is_chilean is True
        assert str(rut1) == "76.543.210-3"

        rut_no_dots = RutTaxId("76543210-3")
        assert rut_no_dots == rut1
        assert rut_no_dots.clean == "76543210-3"

        rut_k_lower = RutTaxId("21.345.675-k")
        assert rut_k_lower.dv == "K"
        assert rut_k_lower.clean == "21345675-K"

    def test_rut_tax_id_invalid_dv_raises_error(self) -> None:
        """Un dígito verificador incorrecto debe disparar InvalidRutError (hereda de ValueError)."""
        with pytest.raises(InvalidRutError, match="Invalid Chilean RUT check digit"):
            RutTaxId("76.543.210-4")

        with pytest.raises(InvalidRutError, match="Invalid Chilean RUT check digit"):
            RutTaxId("11.111.111-K")

    def test_rut_tax_id_invalid_syntax_raises_error(self) -> None:
        """Cuerpos con caracteres no numéricos o vacíos deben fallar la validación."""
        with pytest.raises(InvalidRutError):
            RutTaxId("76.54A.210-3")

        with pytest.raises(InvalidRutError):
            RutTaxId("")

        with pytest.raises(InvalidRutError):
            RutTaxId("   ")

    def test_rut_tax_id_international_support(self) -> None:
        """Valida identificadores tributarios internacionales (ej. US EIN, EU VAT)."""
        us_tax = RutTaxId.from_international("US-123456789", country="US")
        assert us_tax.is_chilean is False
        assert us_tax.value == "US-123456789"
        assert us_tax.country == "US"
        assert us_tax.dv == ""

        eu_vat = RutTaxId("DE-123456789", country="DE")
        assert eu_vat.country == "DE"
        assert eu_vat.clean == "DE-123456789"

        with pytest.raises(InvalidRutError, match="Invalid international Tax ID format"):
            RutTaxId("TAX$$$###INV", country="US")


# ==============================================================================
# 2. Pruebas de PurchaseStatus, IncidenceType e IncidenceResolution
# ==============================================================================


class TestProcurementEnumsAndStateTransitions:
    """Verifica Enums estrictos y máquina de estados transaccionales."""

    def test_purchase_status_values_and_terminal(self) -> None:
        """Verifica los valores definidos y las propiedades terminal/receivable."""
        assert PurchaseStatus.BORRADOR == "BORRADOR"
        assert PurchaseStatus.SOLICITADA == "SOLICITADA"
        assert PurchaseStatus.EN_CAMINO == "EN_CAMINO"
        assert PurchaseStatus.RECIBIDA_PARCIAL == "RECIBIDA_PARCIAL"
        assert PurchaseStatus.RECIBIDA_TOTAL == "RECIBIDA_TOTAL"
        assert PurchaseStatus.CANCELADA == "CANCELADA"

        assert PurchaseStatus.BORRADOR.is_terminal is False
        assert PurchaseStatus.RECIBIDA_TOTAL.is_terminal is True
        assert PurchaseStatus.CANCELADA.is_terminal is True

        assert PurchaseStatus.EN_CAMINO.is_receivable is True
        assert PurchaseStatus.RECIBIDA_PARCIAL.is_receivable is True
        assert PurchaseStatus.BORRADOR.is_receivable is False

    def test_purchase_status_valid_lifecycle_transitions(self) -> None:
        """Verifica transiciones permitidas a lo largo del ciclo de vida."""
        assert PurchaseStatus.BORRADOR.can_transition_to(PurchaseStatus.SOLICITADA) is True
        assert PurchaseStatus.BORRADOR.can_transition_to(PurchaseStatus.CANCELADA) is True

        assert PurchaseStatus.SOLICITADA.can_transition_to(PurchaseStatus.EN_CAMINO) is True
        assert PurchaseStatus.SOLICITADA.can_transition_to(PurchaseStatus.CANCELADA) is True

        assert PurchaseStatus.EN_CAMINO.can_transition_to(PurchaseStatus.RECIBIDA_PARCIAL) is True
        assert PurchaseStatus.EN_CAMINO.can_transition_to(PurchaseStatus.RECIBIDA_TOTAL) is True

        assert PurchaseStatus.RECIBIDA_PARCIAL.can_transition_to(PurchaseStatus.RECIBIDA_TOTAL) is True

    def test_purchase_status_forbidden_transitions(self) -> None:
        """Transiciones ilegales deben disparar InvalidPurchaseStatusTransitionError."""
        with pytest.raises(InvalidPurchaseStatusTransitionError):
            PurchaseStatus.BORRADOR.validate_transition(PurchaseStatus.RECIBIDA_TOTAL)

        with pytest.raises(InvalidPurchaseStatusTransitionError):
            PurchaseStatus.RECIBIDA_TOTAL.validate_transition(PurchaseStatus.CANCELADA)

        with pytest.raises(InvalidPurchaseStatusTransitionError):
            PurchaseStatus.CANCELADA.validate_transition(PurchaseStatus.SOLICITADA)

    def test_incidence_enums(self) -> None:
        """Verifica enums de incidencias y sus resoluciones."""
        expected_types = {
            "DIFERENCIA_CANTIDAD",
            "PRODUCTO_DANADO",
            "FECHA_CADUCADA",
            "PRODUCTO_EQUIVOCADO",
            "OTRO",
        }
        assert {e.value for e in IncidenceType} == expected_types

        expected_resolutions = {
            "PENDIENTE",
            "NOTA_CREDITO",
            "REEMPLAZO",
            "ACEPTADO_CON_DESCUENTO",
            "DESESTIMADO",
        }
        assert {r.value for r in IncidenceResolution} == expected_resolutions


# ==============================================================================
# 3. Pruebas de MoneyAmount (Precisión Decimal y 0% Float)
# ==============================================================================


class TestMoneyAmountPrecisionAndAntiFloat:
    """Verifica la precisión bancaria en Decimal(14, 2) y rechazo categórico de IEEE-754 float."""

    def test_money_amount_quantization_and_string(self) -> None:
        m = MoneyAmount("125000.556")
        assert m.amount == Decimal("125000.56")
        assert m.currency == "CLP"
        assert str(m) == "125000.56 CLP"
        assert m.to_decimal() == Decimal("125000.56")

    def test_money_amount_rejects_float_and_bool(self) -> None:
        # Floats are rejected via TypeError
        with pytest.raises(TypeError, match="IEEE-754 float is strictly forbidden"):
            MoneyAmount(12.50)  # type: ignore[arg-type]

        with pytest.raises(TypeError, match="Boolean values cannot be converted"):
            MoneyAmount(True)  # type: ignore[arg-type]

    def test_money_amount_rejects_negative_by_default(self) -> None:
        with pytest.raises(NegativeMoneyError, match="MoneyAmount cannot be negative"):
            MoneyAmount("-50.00")

    def test_money_amount_arithmetic_operations(self) -> None:
        m1 = MoneyAmount("1000.50")
        m2 = MoneyAmount("500.25")

        added = m1 + m2
        assert added.amount == Decimal("1500.75")

        subtracted = m1 - m2
        assert subtracted.amount == Decimal("500.25")

        with pytest.raises(NegativeMoneyError):
            _ = m2 - m1

        multiplied = m1 * Decimal("2")
        assert multiplied.amount == Decimal("2001.00")

    def test_money_amount_comparisons(self) -> None:
        m1 = MoneyAmount("100.00")
        m2 = MoneyAmount("200.00")
        assert m1 < m2
        assert m1 <= m2
        assert m2 > m1
        assert m2 >= m1
        assert m1 == MoneyAmount("100.00")
        assert m1 == Decimal("100.00")


# ==============================================================================
# 4. Pruebas del Algoritmo de Costo Promedio Ponderado (PPP)
# ==============================================================================


class TestWeightedAverageCostRecalculation:
    """Verifica el recálculo determinista de PPP bajo diversas condiciones operativas."""

    def test_standard_reception_recalculates_ppp(self) -> None:
        """
        Stock anterior: 100 unidades @ $1,000.00 ($100,000)
        Recepción: 50 unidades @ $1,300.00 ($65,000)
        Total unidades: 150
        Valor total: $165,000
        Nuevo PPP: $165,000 / 150 = $1,100.00
        """
        nuevo_ppp = calculate_reception_ppp(
            stock_actual=Decimal("100"),
            costo_ppp_ant=Decimal("1000.00"),
            cant_recibida=Decimal("50"),
            precio_compra=Decimal("1300.00"),
        )
        assert nuevo_ppp == Decimal("1100.00")

    def test_first_purchase_when_stock_is_zero(self) -> None:
        """
        Stock anterior: 0 unidades
        Recepción: 20 unidades @ $5,432.10
        Nuevo PPP debe ser exactamente el precio de compra.
        """
        nuevo_ppp = calculate_reception_ppp(
            stock_actual=Decimal("0"),
            costo_ppp_ant=Decimal("0.00"),
            cant_recibida=Decimal("20"),
            precio_compra=Decimal("5432.10"),
        )
        assert nuevo_ppp == Decimal("5432.10")

    def test_zero_reception_preserves_previous_ppp(self) -> None:
        """Recepción de 0 unidades no altera el PPP anterior."""
        nuevo_ppp = calculate_reception_ppp(
            stock_actual=Decimal("50"),
            costo_ppp_ant=Decimal("2500.00"),
            cant_recibida=Decimal("0"),
            precio_compra=Decimal("3000.00"),
        )
        assert nuevo_ppp == Decimal("2500.00")

    def test_zero_division_safe_avoidance(self) -> None:
        """Si tanto stock como cantidad recibida son 0, retorna costo previo sin fallar."""
        nuevo_ppp = calculate_reception_ppp(
            stock_actual=Decimal("0"),
            costo_ppp_ant=Decimal("1500.00"),
            cant_recibida=Decimal("0"),
            precio_compra=Decimal("0.00"),
        )
        assert nuevo_ppp == Decimal("1500.00")

    def test_rejects_negative_parameters(self) -> None:
        """Parámetros negativos deben disparar excepciones tipadas de dominio."""
        with pytest.raises(NegativeQuantityError, match="Received quantity cannot be negative"):
            calculate_reception_ppp(
                stock_actual="10",
                costo_ppp_ant="100",
                cant_recibida="-5",
                precio_compra="100",
            )

        with pytest.raises(NegativeMoneyError, match="Purchase price cannot be negative"):
            calculate_reception_ppp(
                stock_actual="10",
                costo_ppp_ant="100",
                cant_recibida="5",
                precio_compra="-100",
            )

        with pytest.raises(NegativeMoneyError, match="Previous PPP cost cannot be negative"):
            calculate_reception_ppp(
                stock_actual="10",
                costo_ppp_ant="-100",
                cant_recibida="5",
                precio_compra="100",
            )

        with pytest.raises(NegativeQuantityError, match="Current stock cannot be negative"):
            calculate_reception_ppp(
                stock_actual="-10",
                costo_ppp_ant="100",
                cant_recibida="5",
                precio_compra="100",
                allow_negative_stock=False,
            )

    def test_allow_negative_stock_clamps_to_zero(self) -> None:
        """Con allow_negative_stock=True, un stock negativo se trata como 0 de existencias."""
        nuevo_ppp = calculate_reception_ppp(
            stock_actual="-10",
            costo_ppp_ant="1000.00",
            cant_recibida="10",
            precio_compra="2000.00",
            allow_negative_stock=True,
        )
        assert nuevo_ppp == Decimal("2000.00")

    def test_rejects_float_arguments(self) -> None:
        """Cualquier argumento float debe ser rechazado inmediatamente por tipado defensivo."""
        with pytest.raises(TypeError):
            calculate_reception_ppp(
                stock_actual=10.5,  # type: ignore[arg-type]
                costo_ppp_ant=Decimal("100"),
                cant_recibida=Decimal("5"),
                precio_compra=Decimal("100"),
            )


# ==============================================================================
# 5. Invariante "Pollo King" (Nombres Propios No Traducibles)
# ==============================================================================


class TestProperNounImmutabilityPolloKing:
    """Verifica que los nombres de proveedores no puedan ser alterados ni traducidos."""

    def test_assert_supplier_name_immutable_function(self) -> None:
        """La función de conciliación rechaza cambios de nombre."""
        assert_supplier_name_immutable("Pollo King", "Pollo King")

        with pytest.raises(ProperNounImmutabilityError, match="Pollo King"):
            assert_supplier_name_immutable("Pollo King", "Chicken King")

        with pytest.raises(ProperNounImmutabilityError):
            assert_supplier_name_immutable("Savory", "Savory Ice Cream Ltd")

    def test_supplier_domain_entity_immutability(self) -> None:
        """La entidad de dominio Supplier tiene translatable=False y valida inmutabilidad."""
        supplier = Supplier(
            rut_tax_id=RutTaxId("76.543.210-3"),
            razon_social="Pollo King",
            nombre_fantasia="Pollo King SpA",
            lead_time_dias=2,
        )
        assert Supplier.translatable is False
        assert supplier.translatable is False

        # Nombre legítimo es admitido
        supplier.assert_proper_noun_immutable("Pollo King")
        supplier.assert_proper_noun_immutable("Pollo King SpA")

        # Intento de traducción o alteración levanta error
        with pytest.raises(ProperNounImmutabilityError):
            supplier.assert_proper_noun_immutable("Chicken King Corp")


# ==============================================================================
# 6. Ciclo de Vida de PurchaseOrder y Manejo de Incidencias
# ==============================================================================


class TestPurchaseOrderLifecycleAndIncidences:
    """Verifica la agregación de órdenes de compra, cálculo de totales e incidencias."""

    def test_order_lifecycle_from_draft_to_reception(self) -> None:
        order = PurchaseOrder(
            numero_orden="OC-2026-001",
            proveedor_id=1,
            bodega_destino_id=1,
            monto_neto=MoneyAmount("100000.00"),
            monto_impuestos=MoneyAmount("19000.00"),
            monto_total=MoneyAmount("119000.00"),
        )
        assert order.estado == PurchaseStatus.BORRADOR

        order.submit()
        assert order.estado == PurchaseStatus.SOLICITADA

        order.mark_in_transit()
        assert order.estado == PurchaseStatus.EN_CAMINO

        order.receive_delivery(fully_received=False)
        assert order.estado == PurchaseStatus.RECIBIDA_PARCIAL

        order.receive_delivery(fully_received=True)
        assert order.estado == PurchaseStatus.RECIBIDA_TOTAL
        assert order.estado.is_terminal is True

    def test_order_incidence_registration_and_resolution(self) -> None:
        order = PurchaseOrder(
            numero_orden="OC-2026-002",
            proveedor_id=1,
            bodega_destino_id=1,
            monto_neto=MoneyAmount("50000.00"),
            monto_impuestos=MoneyAmount("9500.00"),
            monto_total=MoneyAmount("59500.00"),
        )
        incidence = PurchaseIncidence(
            compra_id=1,
            tipo_incidencia=IncidenceType.DIFERENCIA_CANTIDAD,
            cantidad_afectada=Decimal("5.0000"),
            descripcion="Llegaron 15 de 20 cajas solicitadas",
            monto_disputa=MoneyAmount("12500.00"),
        )
        assert incidence.resolucion == IncidenceResolution.PENDIENTE

        order.add_incidence(incidence)
        assert len(order.incidencias) == 1

        incidence.resolve(IncidenceResolution.NOTA_CREDITO)
        assert incidence.resolucion == IncidenceResolution.NOTA_CREDITO

    def test_reconciliation_integration(self) -> None:
        """Garantiza interoperabilidad con el algoritmo 3-way reconciliation existente."""
        lines_oc = [DocLine(producto_id=10, quantity=Decimal("10"), unit_cost=Decimal("5000.00"))]
        lines_rec = [DocLine(producto_id=10, quantity=Decimal("10"), unit_cost=Decimal("5000.00"))]
        lines_inv = [DocLine(producto_id=10, quantity=Decimal("10"), unit_cost=Decimal("5000.00"))]

        result = reconcile_three_way(lines_oc, lines_rec, lines_inv)
        assert result.status == MatchStatus.MATCHED
        assert result.invoice_total_diff == Decimal(0)
