"""
oppytec-backend/tests/modules/recipes/test_escandallo_invariants.py
Pruebas basadas en propiedades (Hypothesis) e invariantes matemáticas de escandallo:
- $0 <= C_{min} <= C_{base} <= C_{max}$ siempre se cumple.
- Exactitud de merma técnica en Decimal (gross = net * (1 + waste/100)).
- Escalamiento lineal de porciones en fichas de cocina (KitchenSheet).
- Cero pérdidas por coma flotante (estricta prohibición de floats y ausencia de drift numérico).
- Invariantes de Food Cost % y Margen comercial.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.modules.recipes.application.option_group_service import (
    OptionGroupDTO,
    OptionGroupService,
    OptionItemDTO,
)
from src.modules.recipes.application.recipe_service import (
    RecipeIngredientDTO,
    RecipeOptionGroupLinkDTO,
    RecipeService,
)
from src.modules.recipes.domain.entities import Receta, RecetaIngrediente
from src.modules.recipes.domain.escandallo_calculator import (
    Recipe as CalcRecipe,
    RecipeLine,
    food_cost_pct,
    margin_amount,
    margin_pct,
    recipe_portion_cost,
    recipe_total_cost,
)
from src.modules.recipes.domain.exceptions import (
    InvalidOptionSelectionError,
    InvalidQuantityError,
    InvalidYieldError,
)
from src.modules.recipes.domain.value_objects import (
    HUNDRED,
    ONE,
    PRECISION_COST,
    PRECISION_MONEY,
    PRECISION_PERCENTAGE,
    PRECISION_QUANTITY,
    ZERO,
    DynamicCostSummary,
    IngredientQuantity,
    OptionSelectionRule,
    ServingYield,
)

pytestmark = pytest.mark.unit

# ==============================================================================
# ESTRATEGIAS HYPOTHESIS PARA DOMINIO GOURMET Y PRECISION DECIMAL
# ==============================================================================

dec_cost = st.decimals(
    min_value=Decimal("0.0001"),
    max_value=Decimal("50000.0000"),
    places=4,
)

dec_qty = st.decimals(
    min_value=Decimal("0.0001"),
    max_value=Decimal("500.0000"),
    places=4,
)

dec_waste = st.decimals(
    min_value=Decimal("0.00"),
    max_value=Decimal("99.99"),
    places=2,
)

dec_yield = st.decimals(
    min_value=Decimal("0.1000"),
    max_value=Decimal("100.0000"),
    places=4,
)

dec_price = st.decimals(
    min_value=Decimal("10.00"),
    max_value=Decimal("100000.00"),
    places=2,
)


# ==============================================================================
# 1. INVARIANTE FUNDAMENTAL: 0 <= C_min <= C_base <= C_max
# ==============================================================================

class TestDynamicCostSummaryInvariants:
    """Pruebas de propiedades para el resumen tripartito de costos dinámicos."""

    @settings(max_examples=60, deadline=None)
    @given(c1=dec_cost, c2=dec_cost, c3=dec_cost, price=dec_price)
    def test_cost_ordering_and_margin_invariants(
        self, c1: Decimal, c2: Decimal, c3: Decimal, price: Decimal
    ) -> None:
        """
        Para cualesquiera 3 costos ordenados, C_min <= C_base <= C_max,
        se verifica:
        1. Resumen es válido y cost_spread() >= 0.
        2. Margen mejor caso >= Margen base >= Margen peor caso.
        3. Food Cost % mejor caso <= Food Cost % base <= Food Cost % peor caso.
        4. Margen % + Food Cost % == 100% (tolerancia +-0.02% por redondeos).
        """
        sorted_costs = sorted([c1, c2, c3])
        c_min, c_base, c_max = sorted_costs[0], sorted_costs[1], sorted_costs[2]

        summary = DynamicCostSummary(
            costo_base=c_base,
            costo_peor_caso=c_max,
            costo_mejor_caso=c_min,
            currency="CLP",
        )

        # Invariante de costos
        assert ZERO <= summary.costo_mejor_caso <= summary.costo_base <= summary.costo_peor_caso
        assert summary.cost_spread() == (c_max - c_min).quantize(PRECISION_COST, ROUND_HALF_UP)
        assert summary.cost_spread() >= ZERO

        # Invariante de márgenes si el precio supera o no el costo
        m_best = summary.margen_mejor_caso(price)
        m_base = summary.margen_base(price)
        m_worst = summary.margen_peor_caso(price)
        assert m_best >= m_base >= m_worst

        # Invariante de Food Cost %
        fc_best = (summary.costo_mejor_caso / price * HUNDRED).quantize(PRECISION_PERCENTAGE, ROUND_HALF_UP)
        fc_base = summary.food_cost_pct_base(price)
        fc_worst = summary.food_cost_pct_peor_caso(price)
        assert fc_best <= fc_base <= fc_worst

        # Invariante de suma complementaria 100%
        # Margen % + Food Cost % = ((Price - Cost) / Price + Cost / Price) * 100 = 100%
        sum_pct = m_base + fc_base
        assert abs(sum_pct - Decimal("100.00")) <= Decimal("0.02")

    def test_rejects_violation_of_c_base_between_min_and_max(self) -> None:
        """Rechaza de forma estricta cuando C_base no cae dentro de [C_min, C_max]."""
        # C_base menor que C_min
        with pytest.raises(ValueError, match="must lie between"):
            DynamicCostSummary(
                costo_base=Decimal("80.00"),
                costo_peor_caso=Decimal("200.00"),
                costo_mejor_caso=Decimal("100.00"),
            )

        # C_base mayor que C_max
        with pytest.raises(ValueError, match="must lie between"):
            DynamicCostSummary(
                costo_base=Decimal("250.00"),
                costo_peor_caso=Decimal("200.00"),
                costo_mejor_caso=Decimal("100.00"),
            )

        # C_min > C_max
        with pytest.raises(ValueError, match="cannot exceed costo_peor_caso"):
            DynamicCostSummary(
                costo_base=Decimal("150.00"),
                costo_peor_caso=Decimal("100.00"),
                costo_mejor_caso=Decimal("200.00"),
            )

    def test_rejects_negative_costs(self) -> None:
        """Costos negativos deben ser rechazados sin excepción."""
        with pytest.raises(ValueError, match="cannot be negative"):
            DynamicCostSummary(
                costo_base=Decimal("-1.00"),
                costo_peor_caso=Decimal("100.00"),
                costo_mejor_caso=Decimal("10.00"),
            )


# ==============================================================================
# 2. EXACTITUD DE MERMA TÉCNICA EN DECIMAL
# ==============================================================================

class TestTechnicalWasteInvariants:
    """Pruebas de invariantes para el factor de merma técnica y masa bruta."""

    @settings(max_examples=60, deadline=None)
    @given(qty=dec_qty, waste=dec_waste, unit_cost=dec_cost)
    def test_gross_quantity_and_cost_axioms(
        self, qty: Decimal, waste: Decimal, unit_cost: Decimal
    ) -> None:
        """
        Para toda cantidad neta > 0 y porcentaje de merma 0 <= waste < 100:
        1. gross_quantity >= net_quantity
        2. gross_quantity == net_quantity si y solo si waste == 0
        3. cost == gross_quantity * unit_cost sin drift
        """
        iq = IngredientQuantity(quantity=qty, waste_pct=waste, unit="kg")
        gross = iq.gross_quantity()

        assert gross >= iq.quantity

        if waste == ZERO:
            assert gross == iq.quantity
        else:
            # gross_quantity >= net_quantity siempre, y si la merma supera el umbral de redondeo es estrictamente mayor
            assert gross >= iq.quantity
            expected_factor = ONE + (waste / HUNDRED)
            unrounded_gross = qty * expected_factor
            if unrounded_gross - qty >= Decimal("0.00005"):
                assert gross > iq.quantity

        expected_factor = ONE + (waste / HUNDRED)
        expected_gross = (qty * expected_factor).quantize(PRECISION_QUANTITY, ROUND_HALF_UP)
        assert gross == expected_gross

        calculated_cost = iq.calculate_cost(unit_cost)
        expected_cost = (gross * unit_cost).quantize(PRECISION_COST, ROUND_HALF_UP)
        assert calculated_cost == expected_cost

    def test_waste_boundary_conditions(self) -> None:
        """Verifica límites [0, 100) para la merma técnica."""
        # 0% es válido (sin desperdicio)
        iq_zero = IngredientQuantity(Decimal("5.0000"), Decimal("0.00"))
        assert iq_zero.gross_quantity() == Decimal("5.0000")

        # 99.99% es válido (merma extrema pero legal)
        iq_extreme = IngredientQuantity(Decimal("1.0000"), Decimal("99.99"))
        assert iq_extreme.gross_quantity() == Decimal("1.9999")

        # < 0% es inválido
        with pytest.raises(InvalidQuantityError, match="0 <= waste_pct < 100"):
            IngredientQuantity(Decimal("1.0000"), Decimal("-0.01"))

        # >= 100% es inválido (materia prima absorbida por completo)
        with pytest.raises(InvalidQuantityError, match="0 <= waste_pct < 100"):
            IngredientQuantity(Decimal("1.0000"), Decimal("100.00"))

        with pytest.raises(InvalidQuantityError, match="0 <= waste_pct < 100"):
            IngredientQuantity(Decimal("1.0000"), Decimal("150.00"))

    @settings(max_examples=40, deadline=None)
    @given(qty=dec_qty, waste=dec_waste, factor=st.decimals(min_value=Decimal("0.1"), max_value=Decimal("10.0"), places=2))
    def test_scale_preserves_waste_percentage(
        self, qty: Decimal, waste: Decimal, factor: Decimal
    ) -> None:
        """El escalamiento de un ingrediente conserva exactamente su porcentaje de merma."""
        iq = IngredientQuantity(quantity=qty, waste_pct=waste, unit="kg")
        scaled = iq.scale(factor)

        assert scaled.waste_pct == iq.waste_pct
        assert scaled.unit == iq.unit
        expected_qty = (qty * factor).quantize(PRECISION_QUANTITY, ROUND_HALF_UP)
        assert scaled.quantity == expected_qty


# ==============================================================================
# 3. ESCALAMIENTO LINEAL DE PORCIONES EN FICHAS DE COCINA
# ==============================================================================

class TestKitchenSheetLinearScalingInvariants:
    """Pruebas de propiedades para el escalamiento lineal de fichas de cocina."""

    def _setup_service(self) -> tuple[RecipeService, int]:
        og_svc = OptionGroupService()
        svc = RecipeService(option_group_service=og_svc)

        # Insumos
        svc.set_ingredient_cost(101, Decimal("1000.0000"))  # Carne molida
        svc.set_ingredient_cost(102, Decimal("500.0000"))   # Cebolla

        # Crear receta base rindiendo 4 porciones
        receta = svc.create_recipe(
            codigo="FICHA-TEST-01",
            nombre="Lasaña Boloñesa",
            porciones_rendimiento=Decimal("4.0000"),
            precio_venta_neto=Decimal("6000.00"),
            ingredientes=[
                RecipeIngredientDTO(
                    producto_id=101,
                    cantidad_receta=Decimal("0.8000"),  # 800g netos
                    porcentaje_merma=Decimal("10.00"), # 10% merma
                    notas="Picar fino",
                ),
                RecipeIngredientDTO(
                    producto_id=102,
                    cantidad_receta=Decimal("0.2000"),  # 200g netos
                    porcentaje_merma=Decimal("15.00"), # 15% merma
                    notas="Brunoise",
                ),
            ],
            tenant_id="tenant_linear",
        )
        return svc, receta.id

    @settings(max_examples=50, deadline=None)
    @given(servings=st.decimals(min_value=Decimal("0.5000"), max_value=Decimal("80.0000"), places=4))
    def test_linear_scaling_portion_invariance(self, servings: Decimal) -> None:
        """
        Para cualquier cantidad de porciones solicitada S:
        - factor_escalamiento = S / porciones_base
        - cantidad_neta_escalada == round(base_qty * factor)
        - cantidad_bruta_escalada == round(net_scaled * (1 + waste/100))
        """
        svc, recipe_id = self._setup_service()
        sheet = svc.generate_kitchen_sheet(
            recipe_id=recipe_id,
            servings=servings,
            tenant_id="tenant_linear",
        )

        base_yield = Decimal("4.0000")
        raw_factor = servings / base_yield
        expected_scaled_factor = raw_factor.quantize(PRECISION_QUANTITY, ROUND_HALF_UP)

        assert sheet.porciones_solicitadas == servings.quantize(PRECISION_QUANTITY, ROUND_HALF_UP)
        assert sheet.porciones_base == base_yield
        assert sheet.factor_escalamiento == expected_scaled_factor

        for item in sheet.ingredientes_fijos:
            expected_net = (item.cantidad_neta_base * raw_factor).quantize(PRECISION_QUANTITY, ROUND_HALF_UP)
            assert item.cantidad_neta_escalada == expected_net

            waste_factor = ONE + (item.porcentaje_merma / HUNDRED)
            expected_gross = (expected_net * waste_factor).quantize(PRECISION_QUANTITY, ROUND_HALF_UP)
            assert item.cantidad_bruta_escalada == expected_gross

    def test_identity_scaling_when_servings_equals_base_yield(self) -> None:
        """Escalar a la misma cantidad de porciones base rinde cantidades netas idénticas."""
        svc, recipe_id = self._setup_service()
        sheet = svc.generate_kitchen_sheet(
            recipe_id=recipe_id,
            servings=Decimal("4.0000"),
            tenant_id="tenant_linear",
        )

        assert sheet.factor_escalamiento == Decimal("1.0000")
        for item in sheet.ingredientes_fijos:
            assert item.cantidad_neta_escalada == item.cantidad_neta_base

    def test_double_servings_doubles_quantities_linearly(self) -> None:
        """Escalar al doble de porciones duplica exactamente las cantidades netas."""
        svc, recipe_id = self._setup_service()
        sheet_base = svc.generate_kitchen_sheet(recipe_id=recipe_id, servings=Decimal("4.0000"), tenant_id="tenant_linear")
        sheet_double = svc.generate_kitchen_sheet(recipe_id=recipe_id, servings=Decimal("8.0000"), tenant_id="tenant_linear")

        for item_base, item_double in zip(sheet_base.ingredientes_fijos, sheet_double.ingredientes_fijos):
            assert item_double.cantidad_neta_escalada == item_base.cantidad_neta_escalada * Decimal("2")

    def test_rejects_zero_or_negative_servings_in_kitchen_sheet(self) -> None:
        """Solicitar 0 o porciones negativas debe ser rechazado."""
        svc, recipe_id = self._setup_service()
        with pytest.raises(InvalidYieldError, match="strictly > 0"):
            svc.generate_kitchen_sheet(recipe_id=recipe_id, servings=Decimal("0.0000"), tenant_id="tenant_linear")

        with pytest.raises(InvalidYieldError, match="strictly > 0"):
            svc.generate_kitchen_sheet(recipe_id=recipe_id, servings=Decimal("-5.0000"), tenant_id="tenant_linear")


# ==============================================================================
# 4. CERO PERDIDAS POR COMA FLOTANTE (ESTRICTO ANTI-FLOAT)
# ==============================================================================

class TestStrictZeroFloatLossesInvariants:
    """Verificación de que ningún float contamina los cálculos y que la acumulación Decimal es 100% exacta."""

    def test_floats_are_strictly_forbidden_across_all_value_objects(self) -> None:
        """El intento de instanciar value objects con floats lanza TypeError."""
        with pytest.raises(TypeError, match="Floats are strictly forbidden"):
            ServingYield(4.0)  # type: ignore

        with pytest.raises(TypeError, match="Floats are strictly forbidden"):
            IngredientQuantity(1.5, Decimal("0.00"))  # type: ignore

        with pytest.raises(TypeError, match="Floats are strictly forbidden"):
            IngredientQuantity(Decimal("1.0000"), 10.5)  # type: ignore

        with pytest.raises(TypeError, match="Floats are strictly forbidden"):
            DynamicCostSummary(100.0, Decimal("200.00"), Decimal("50.00"))  # type: ignore

        with pytest.raises(TypeError, match="Floats are strictly forbidden"):
            DynamicCostSummary(Decimal("100.00"), 200.0, Decimal("50.00"))  # type: ignore

    def test_zero_floating_point_drift_in_cumulative_sum(self) -> None:
        """
        En IEEE 754 float: sum([0.0001] * 10000) != 1.0 (drift acumulativo).
        En Decimal estricto de OppyTec: sum == 1.0000 con exactitud infinita.
        """
        step = Decimal("0.0001")
        total = Decimal("0.0000")
        for _ in range(10000):
            total += step

        assert total == Decimal("1.0000")
        assert (total / Decimal("3.0000")).quantize(PRECISION_COST, ROUND_HALF_UP) == Decimal("0.3333")

    @settings(max_examples=50, deadline=None)
    @given(items=st.lists(dec_cost, min_size=5, max_size=30))
    def test_associative_and_commutative_lot_cost_addition(self, items: list[Decimal]) -> None:
        """La suma de costos de ingredientes es conmutativa e independiente del orden de adición."""
        direct_sum = sum(items, ZERO).quantize(PRECISION_COST, ROUND_HALF_UP)
        reversed_sum = sum(reversed(items), ZERO).quantize(PRECISION_COST, ROUND_HALF_UP)
        sorted_sum = sum(sorted(items), ZERO).quantize(PRECISION_COST, ROUND_HALF_UP)

        assert direct_sum == reversed_sum == sorted_sum


# ==============================================================================
# 5. INVARIANTES DE COSTEO DINÁMICO EN RECIPE SERVICE (LÍMITES C_min <= C_base <= C_max)
# ==============================================================================

class TestRecipeServiceDynamicCostOrdering:
    """Verificación de que RecipeService siempre preserva C_min <= C_base <= C_max ante opciones complejas."""

    def test_dynamic_recipe_preserves_cost_bounds(self) -> None:
        og_svc = OptionGroupService()
        svc = RecipeService(option_group_service=og_svc)

        # Insumos fijos
        svc.set_ingredient_cost(1, Decimal("1000.0000"))
        svc.set_ingredient_cost(2, Decimal("500.0000"))

        # Insumos de opciones con costos variados
        svc.set_ingredient_cost(10, Decimal("200.0000"))   # Papa regular (default)
        svc.set_ingredient_cost(11, Decimal("600.0000"))   # Camote rústico (más caro)
        svc.set_ingredient_cost(12, Decimal("100.0000"))   # Ensalada fresca (más barato)

        # Grupo: Guarnición obligatoria (min=1, max=1)
        grupo_dto = og_svc.create_option_group(
            nombre="Guarnición",
            seleccion_minima=1,
            seleccion_maxima=1,
            permite_repetir=False,
            items=[
                OptionItemDTO(producto_id=10, cantidad=Decimal("1.0000"), es_opcion_default=True),
                OptionItemDTO(producto_id=11, cantidad=Decimal("1.0000"), es_opcion_default=False),
                OptionItemDTO(producto_id=12, cantidad=Decimal("1.0000"), es_opcion_default=False),
            ],
            tenant_id="tenant_dyn",
        )

        receta = svc.create_recipe(
            codigo="REC-DYN-01",
            nombre="Plato Configurable",
            porciones_rendimiento=Decimal("1.0000"),
            precio_venta_neto=Decimal("5000.00"),
            ingredientes=[
                RecipeIngredientDTO(producto_id=1, cantidad_receta=Decimal("1.0000")),
                RecipeIngredientDTO(producto_id=2, cantidad_receta=Decimal("1.0000")),
            ],
            grupos_opciones=[
                RecipeOptionGroupLinkDTO(grupo_id=grupo_dto.id, es_requerido=True),
            ],
            tenant_id="tenant_dyn",
        )

        assert receta.es_dinamica is True
        # Insumos fijos = 1000 + 500 = 1500
        # Opciones: default=200, peor=600, mejor=100
        # Base = 1500 + 200 = 1700
        # Peor = 1500 + 600 = 2100
        # Mejor = 1500 + 100 = 1600
        assert receta.costo_porcion == Decimal("1700.0000")
        assert receta.costo_peor_caso == Decimal("2100.0000")
        assert receta.costo_mejor_caso == Decimal("1600.0000")

        # Invariante matemático estricto: 0 <= C_min <= C_base <= C_max
        assert ZERO <= receta.costo_mejor_caso <= receta.costo_porcion <= receta.costo_peor_caso
