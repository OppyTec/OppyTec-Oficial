"""
oppytec-backend/tests/domain/test_kardex_parity.py
Suite de Pruebas de Paridad 5D: Kardex, PPP, Márgenes, Food Cost e Inflación
frente a OppyTec-Legacy y PRODUCTOS_Y_COSTOS_SPEC.md.

Dimensiones 5D:
1. Nivel de Abstracción: Pruebas unitarias analíticas con casos borde y valores exactos.
2. Basada en Propiedades (Hypothesis): Invariantes algebraicos de Food Cost, Márgenes y PPP.
3. Paridad 1:1 con Casos Reales Legacy: Potes, Jurel, Compras escalonadas, Embalajes.
4. Robustez de Frontera (Caja Blanca): Protección ante divisiones por cero y cantidades negativas.
5. Certificación Decimal Estricta: Prohibición total de IEEE 754 float en cálculos.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.modules.inventory.domain.kardex_math import (
    PurchaseLayer,
    calculate_days_of_coverage,
    calculate_food_cost_pct,
    calculate_gross_margin_pct,
    calculate_inflation_variance_pct,
    calculate_inventory_ppp,
    calculate_monthly_turnover_index,
    calculate_moving_average_10,
    calculate_net_margin_pct,
    calculate_weighted_average_cost,
    gross_from_net,
    net_from_gross,
    packaging_cost,
)

pytestmark = [pytest.mark.unit]

dec_pos = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("100000"), places=4)
dec_stock = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("50000"), places=2)


# ============================================================================
# DIMENSIÓN 1: PRUEBAS UNITARIAS ANALÍTICAS CON CASOS BORDE
# ============================================================================


class TestUnitaryFormulas:
    """Pruebas unitarias de las 7 fórmulas requeridas con casos canónicos."""

    def test_ppp_empty_stock(self) -> None:
        """Si stock_actual <= 0, el valor de inventario es 0 y PPP cae a fallback."""
        val_inv, ppp = calculate_inventory_ppp(
            stock_actual=Decimal(0),
            purchases=[],
            base_cost=Decimal("150.00"),
            last_cost=Decimal("180.00"),
        )
        assert val_inv == Decimal("0.00")
        assert ppp == Decimal("180.0000")

    def test_ppp_no_purchases_fallback_to_base(self) -> None:
        """Si no hay compras registradas, se valoriza al costo base configurado."""
        val_inv, ppp = calculate_inventory_ppp(
            stock_actual=Decimal(10),
            purchases=[],
            base_cost=Decimal("250.50"),
        )
        assert val_inv == Decimal("2505.00")
        assert ppp == Decimal("250.5000")

    def test_ppp_dynamic_layers_fifo_exact(self) -> None:
        """
        Capas dinámicas FIFO:
        Stock actual = 15 unidades.
        Compras disponibles:
          - Compra 1 (más reciente): 10 unidades a $100
          - Compra 2: 10 unidades a $80
        Consumo de capas:
          - 10 unidades a $100 = $1.000
          - 5 unidades a $80 = $400
        Total valor inventario = $1.400
        PPP = 1400 / 15 = $93.3333
        """
        purchases = [
            PurchaseLayer(quantity=Decimal(10), unit_cost=Decimal(100)),
            PurchaseLayer(quantity=Decimal(10), unit_cost=Decimal(80)),
        ]
        val_inv, ppp = calculate_inventory_ppp(Decimal(15), purchases, base_cost=Decimal(50))
        assert val_inv == Decimal("1400.00")
        assert ppp == Decimal("93.3333")

    def test_ppp_with_unbacked_stock_remnant(self) -> None:
        """
        Stock actual = 25 unidades.
        Compras registradas: 15 unidades a $200 = $3.000.
        Remanente = 10 unidades valorizadas al costo base $150 = $1.500.
        Total valor = $4.500.
        PPP = 4500 / 25 = $180.0000.
        """
        purchases = [
            PurchaseLayer(quantity=Decimal(15), unit_cost=Decimal(200)),
        ]
        val_inv, ppp = calculate_inventory_ppp(Decimal(25), purchases, base_cost=Decimal(150))
        assert val_inv == Decimal("4500.00")
        assert ppp == Decimal("180.0000")

    def test_moving_average_10_exact(self) -> None:
        """Promedio histórico toma las últimas 10 compras exactas."""
        costs = [Decimal(i * 10) for i in range(1, 15)]  # 14 compras: 10, 20, ..., 140
        # Primeras 10 en lista (más recientes): 10, 20, 30, 40, 50, 60, 70, 80, 90, 100
        # Suma = 550 / 10 = 55.0000
        avg_10 = calculate_moving_average_10(costs)
        assert avg_10 == Decimal("55.0000")

    def test_moving_average_10_fewer_than_10(self) -> None:
        """Si hay menos de 10 compras, promedia las existentes."""
        costs = [Decimal(100), Decimal(200)]
        avg = calculate_moving_average_10(costs)
        assert avg == Decimal("150.0000")

    def test_moving_average_10_empty_fallback(self) -> None:
        """Si la lista está vacía, devuelve el costo de fallback."""
        avg = calculate_moving_average_10([], fallback_cost=Decimal("75.50"))
        assert avg == Decimal("75.5000")

    def test_food_cost_and_gross_margin_formulas(self) -> None:
        """
        Food Cost % = (costo_bruto / precio_venta_bruto) * 100
        Margen Bruto % = ((precio_venta_bruto - costo_bruto) / precio_venta_bruto) * 100
        """
        costo_bruto = Decimal("3000.00")
        pv_bruto = Decimal("10000.00")
        fc = calculate_food_cost_pct(costo_bruto, pv_bruto)
        mb = calculate_gross_margin_pct(pv_bruto, costo_bruto)
        assert fc == Decimal("30.00")
        assert mb == Decimal("70.00")
        assert fc + mb == Decimal("100.00")

    def test_net_margin_formula(self) -> None:
        """Margen Neto % = ((pv_neto - costo_neto) / pv_neto) * 100."""
        costo_neto = Decimal("2521.01")
        pv_neto = Decimal("8403.36")
        mn = calculate_net_margin_pct(pv_neto, costo_neto)
        # (8403.36 - 2521.01) / 8403.36 * 100 = 70.00%
        assert mn == Decimal("70.00")

    def test_inflation_variance_formula(self) -> None:
        """Variación inflacionaria % = ((ultimo - penultimo) / penultimo) * 100."""
        ultimo = Decimal("1200.00")
        penultimo = Decimal("1000.00")
        var = calculate_inflation_variance_pct(ultimo, penultimo)
        assert var == Decimal("20.00")

        # Variación negativa (deflación / descuento)
        ultimo_menor = Decimal("900.00")
        var_neg = calculate_inflation_variance_pct(ultimo_menor, penultimo)
        assert var_neg == Decimal("-10.00")

    def test_days_of_coverage_cases(self) -> None:
        """Casos de días de cobertura según especificación legacy."""
        # 1. Consumo diario activo: 100 unidades / 10 unidades/día = 10 días
        assert calculate_days_of_coverage(Decimal(100), Decimal(10)) == Decimal(10)
        # Redondeo exacto: 100 unidades / 3 unidades/día = 33 días
        assert calculate_days_of_coverage(Decimal(100), Decimal(3)) == Decimal(33)
        # 2. Sin consumo registrado pero con stock: fallback a 30 días
        assert calculate_days_of_coverage(Decimal(50), Decimal(0)) == Decimal(30)
        # 3. Sin stock: 0 días
        assert calculate_days_of_coverage(Decimal(0), Decimal(10)) == Decimal(0)
        assert calculate_days_of_coverage(Decimal(0), Decimal(0)) == Decimal(0)

    def test_monthly_turnover_index_cases(self) -> None:
        """Índice de rotación = ventas_mes / max(stock, 1)."""
        # 200 ventas / 50 stock = 4.0x / mes
        assert calculate_monthly_turnover_index(Decimal(200), Decimal(50)) == Decimal("4.0")
        # Sin stock: divisor es 1 para evitar ZeroDivisionError
        assert calculate_monthly_turnover_index(Decimal(5), Decimal(0)) == Decimal("5.0")
        assert calculate_monthly_turnover_index(Decimal(0), Decimal(10)) == Decimal("0.0")


# ============================================================================
# DIMENSIÓN 2: BASADA EN PROPIEDADES (HYPOTHESIS PROPERTY TESTING)
# ============================================================================


class TestHypothesisParityProperties:
    """Invariantes algebraicos e inmutabilidad de leyes económicas."""

    @given(cost=dec_pos, pv=dec_pos)
    def test_food_cost_and_gross_margin_complement(self, cost: Decimal, pv: Decimal) -> None:
        """Food Cost % + Margen Bruto % es estrictamente 100.00% (invariante de partición)."""
        fc = calculate_food_cost_pct(cost, pv)
        mb = calculate_gross_margin_pct(pv, cost)
        assert (fc + mb) == Decimal("100.00")

    @given(c1=dec_pos, c2=dec_pos, q1=dec_pos, q2=dec_pos)
    def test_weighted_average_bounded_between_extremes(
        self, c1: Decimal, c2: Decimal, q1: Decimal, q2: Decimal
    ) -> None:
        """El costo ponderado resultante siempre reside entre el costo menor y mayor de entrada."""
        wacc = calculate_weighted_average_cost(q1, c1, q2, c2)
        min_c = min(c1, c2)
        max_c = max(c1, c2)
        assert min_c - Decimal("0.0001") <= wacc <= max_c + Decimal("0.0001")

    @given(net=dec_pos, iva=st.decimals(min_value=Decimal(10), max_value=Decimal(25), places=2))
    def test_gross_net_roundtrip_precision(self, net: Decimal, iva: Decimal) -> None:
        """Neto -> Bruto -> Neto conserva la exactitud sin deriva decimal."""
        gross = gross_from_net(net, iva_pct=iva)
        recovered_net = net_from_gross(gross, iva_pct=iva)
        assert abs(recovered_net - net.quantize(Decimal("0.01"))) <= Decimal("0.01")

    @given(stock=dec_stock, c1=dec_pos, c2=dec_pos)
    def test_days_coverage_decreases_with_higher_consumption(
        self, stock: Decimal, c1: Decimal, c2: Decimal
    ) -> None:
        """A mayor consumo diario, los días de cobertura deben ser menores o iguales."""
        low_c = min(c1, c2)
        high_c = max(c1, c2)
        days_low = calculate_days_of_coverage(stock, low_c)
        days_high = calculate_days_of_coverage(stock, high_c)
        assert days_high <= days_low


# ============================================================================
# DIMENSIÓN 3: PARIDAD 1:1 CON CASOS REALES DE OPPYTEC-LEGACY
# ============================================================================


class TestLegacySpecParityCases:
    """Casos de prueba extraídos directamente de PRODUCTOS_Y_COSTOS_SPEC.md."""

    def test_spec_caja_x192_potes(self) -> None:
        """
        Ejemplo oficial spec sección 1.0:
        Caja x192 Potes a $30.128 Neto.
        Costo Unitario por Pote = 30128 / 192 = 156.9167 (se redondea a $156.92 en display).
        Con IVA 19%: 156.9167 * 1.19 = 186.7308 ($186.73).
        """
        net_embalaje = Decimal(30128)
        cant_envases = Decimal(192)

        costo_unitario_neto = (net_embalaje / cant_envases).quantize(Decimal("0.0001"))
        assert costo_unitario_neto == Decimal("156.9167")

        costo_unitario_bruto = gross_from_net(costo_unitario_neto, iva_pct=Decimal(19))
        assert costo_unitario_bruto == Decimal("186.73")

        # Embalaje inverso
        emb_calc = packaging_cost(costo_unitario_neto, cant_envases)
        assert abs(emb_calc - net_embalaje) <= Decimal("0.01")

    def test_spec_conserva_jurel_peso_drenado(self) -> None:
        """
        Ejemplo oficial spec sección 1.0:
        Tarro de Jurel 800g bruto a $2.000, Peso Drenado = 425g comestibles.
        - Rendimiento % = (425 / 800) * 100 = 53.125% -> 53.1%
        - Costo Real por Gramo en Recetas = $2.000 / 425g = $4.7059 / g.
        """
        costo_tarro = Decimal("2000.00")
        peso_bruto = Decimal(800)
        peso_drenado = Decimal(425)

        rendimiento_pct = ((peso_drenado / peso_bruto) * Decimal(100)).quantize(Decimal("0.1"))
        assert rendimiento_pct == Decimal("53.1")

        costo_gramo_drenado = (costo_tarro / peso_drenado).quantize(Decimal("0.0001"))
        assert costo_gramo_drenado == Decimal("4.7059")

    def test_spec_clp_legal_currency_rounding(self) -> None:
        """
        Ejemplo oficial spec sección 4.5:
        Valor Inventario Neto y Bruto en Moneda Legal CLP (redondeo al entero más cercano).
        Ejemplo: Valor Neto = $86.306, Valor Bruto con IVA = $102.704.
        """
        net_inv = Decimal(86306)
        bruto_inv = gross_from_net(net_inv, iva_pct=Decimal(19), as_clp_integer=True)
        # 86306 * 1.19 = 102704.14 -> 102704
        assert bruto_inv == Decimal(102704)


# ============================================================================
# DIMENSIÓN 4: ROBUSTEZ Y LÍMITES DE FRONTERA (CAJA BLANCA)
# ============================================================================


class TestBoundaryAndFaultTolerance:
    """Verificación de excepciones y blindaje ante datos anómalos."""

    def test_division_by_zero_guards(self) -> None:
        """Precios de venta cero o negativos lanzan ValueError controlado."""
        with pytest.raises(ValueError, match="precio_venta_bruto must be strictly positive"):
            calculate_food_cost_pct(Decimal(100), Decimal(0))

        with pytest.raises(ValueError, match="precio_venta_bruto must be strictly positive"):
            calculate_gross_margin_pct(Decimal(0), Decimal(100))

        with pytest.raises(ValueError, match="precio_venta_neto must be strictly positive"):
            calculate_net_margin_pct(Decimal(0), Decimal(50))

        with pytest.raises(ValueError, match="penultimo_costo must be strictly positive"):
            calculate_inflation_variance_pct(Decimal(100), Decimal(0))

    def test_negative_purchases_rejected(self) -> None:
        """Cantidades negativas en capas de compra o recepción son rechazadas."""
        with pytest.raises(ValueError, match="purchase quantity must be non-negative"):
            PurchaseLayer(quantity=Decimal(-5), unit_cost=Decimal(100))

        with pytest.raises(ValueError, match="incoming quantity must be non-negative"):
            calculate_weighted_average_cost(Decimal(10), Decimal(100), Decimal(-1), Decimal(120))


# ============================================================================
# DIMENSIÓN 5: CERTIFICACIÓN DECIMAL ESTRICTA (CERO FLOATS)
# ============================================================================


class TestStrictDecimalCertification:
    """Comprueba que ninguna función del dominio opere o devuelva floats IEEE 754."""

    def test_all_returns_are_decimal_instances(self) -> None:
        """Cada función del módulo debe retornar rigurosamente objetos Decimal."""
        p_layers = [PurchaseLayer(Decimal(10), Decimal(100))]
        val_inv, ppp = calculate_inventory_ppp(Decimal(5), p_layers)
        assert isinstance(val_inv, Decimal)
        assert isinstance(ppp, Decimal)

        wacc = calculate_weighted_average_cost(Decimal(5), Decimal(100), Decimal(5), Decimal(120))
        assert isinstance(wacc, Decimal)

        ma10 = calculate_moving_average_10([Decimal(10), Decimal(20)])
        assert isinstance(ma10, Decimal)

        fc = calculate_food_cost_pct(Decimal(30), Decimal(100))
        assert isinstance(fc, Decimal)

        mb = calculate_gross_margin_pct(Decimal(100), Decimal(30))
        assert isinstance(mb, Decimal)

        mn = calculate_net_margin_pct(Decimal(100), Decimal(30))
        assert isinstance(mn, Decimal)

        var = calculate_inflation_variance_pct(Decimal(120), Decimal(100))
        assert isinstance(var, Decimal)

        cov = calculate_days_of_coverage(Decimal(100), Decimal(10))
        assert isinstance(cov, Decimal)

        turn = calculate_monthly_turnover_index(Decimal(50), Decimal(10))
        assert isinstance(turn, Decimal)

        gross = gross_from_net(Decimal(100))
        assert isinstance(gross, Decimal)

        net = net_from_gross(Decimal(119))
        assert isinstance(net, Decimal)
