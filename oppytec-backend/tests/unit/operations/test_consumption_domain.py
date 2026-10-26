"""
oppytec-backend/tests/unit/operations/test_consumption_domain.py
Suite de pruebas unitarias 100% pura para el dominio DDD de Consumo,
explosión de recetas, FEFO estricto y cálculo de costo Buffet por Pax.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.core.exceptions import DomainValidationError, InsufficientStockError
from src.modules.operations.domain.consumption_math import (
    BuffetPaxCost,
    ConsumptionLot,
    ConsumptionQuantity,
    LotDeduction,
    PaxCount,
    RecipeConsumptionItem,
    RecipeIngredientItem,
    RecipeSpec,
    calculate_buffet_pax_cost,
    deduct_lots_fefo,
    explode_recipe_consumption,
    sort_lots_fefo,
)

pytestmark = pytest.mark.unit


# ============================================================================
# 1. VALUE OBJECT: ConsumptionQuantity
# ============================================================================


class TestConsumptionQuantity:
    """Pruebas exhaustivas para el Value Object ConsumptionQuantity (4 decimales)."""

    def test_creation_valid_types(self) -> None:
        cq1 = ConsumptionQuantity(Decimal("12.3456"))
        cq2 = ConsumptionQuantity(15)
        cq3 = ConsumptionQuantity("8.5000")
        cq4 = ConsumptionQuantity(cq1)

        assert cq1.value == Decimal("12.3456")
        assert cq2.value == Decimal("15.0000")
        assert cq3.value == Decimal("8.5000")
        assert cq4.value == Decimal("12.3456")
        assert str(cq1) == "12.3456"
        assert repr(cq1) == "ConsumptionQuantity('12.3456')"

    def test_float_strictly_forbidden(self) -> None:
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            ConsumptionQuantity(12.3456)  # type: ignore[arg-type]

    def test_boolean_strictly_forbidden(self) -> None:
        with pytest.raises(TypeError, match="Boolean is forbidden"):
            ConsumptionQuantity(True)  # type: ignore[arg-type]

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(TypeError, match="Unsupported type"):
            ConsumptionQuantity([])  # type: ignore[arg-type]

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid decimal representation"):
            ConsumptionQuantity("not-a-number")

    def test_nan_or_infinite_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be NaN or infinite"):
            ConsumptionQuantity(Decimal("NaN"))
        with pytest.raises(ValueError, match="cannot be NaN or infinite"):
            ConsumptionQuantity(Decimal("Infinity"))

    def test_quantization_round_half_up(self) -> None:
        # 1.23455 se redondea a 1.2346 (ROUND_HALF_UP)
        cq = ConsumptionQuantity(Decimal("1.23455"))
        assert cq.value == Decimal("1.2346")
        # 1.23454 se redondea a 1.2345
        cq2 = ConsumptionQuantity(Decimal("1.23454"))
        assert cq2.value == Decimal("1.2345")

    def test_negative_prohibited_by_default(self) -> None:
        with pytest.raises(DomainValidationError, match="cannot be negative"):
            ConsumptionQuantity(Decimal("-0.0001"))

    def test_allow_negative_flag(self) -> None:
        cq = ConsumptionQuantity(Decimal("-5.0000"), allow_negative=True)
        assert cq.value == Decimal("-5.0000")
        assert cq.is_negative()

    def test_state_predicates(self) -> None:
        zero_cq = ConsumptionQuantity.zero()
        pos_cq = ConsumptionQuantity(Decimal("1.0000"))
        neg_cq = ConsumptionQuantity(Decimal("-1.0000"), allow_negative=True)

        assert zero_cq.is_zero()
        assert not zero_cq.is_positive()
        assert not zero_cq.is_negative()

        assert pos_cq.is_positive()
        assert not pos_cq.is_zero()
        assert not pos_cq.is_negative()

        assert neg_cq.is_negative()
        assert not neg_cq.is_positive()
        assert not neg_cq.is_zero()

        assert zero_cq.to_decimal() == Decimal("0.0000")

    def test_comparisons(self) -> None:
        cq1 = ConsumptionQuantity("10.0000")
        cq2 = ConsumptionQuantity("20.0000")
        cq3 = ConsumptionQuantity("10.0000")

        assert cq1 < cq2
        assert cq1 <= cq2
        assert cq1 <= cq3
        assert cq2 > cq1
        assert cq2 >= cq1
        assert cq1 == cq3
        assert cq1 == "10.0000"
        assert cq1 == 10
        assert cq1 == Decimal("10.0000")
        assert not (cq1 == "invalid")
        assert not (cq1 == object())

    def test_arithmetic_add_sub(self) -> None:
        cq1 = ConsumptionQuantity("15.5000")
        cq2 = ConsumptionQuantity("4.5000")

        added = cq1 + cq2
        assert added == ConsumptionQuantity("20.0000")

        radded = 10 + cq1
        assert radded == ConsumptionQuantity("25.5000")

        subbed = cq1 - cq2
        assert subbed == ConsumptionQuantity("11.0000")

    def test_subtraction_insufficient_stock_raises(self) -> None:
        cq1 = ConsumptionQuantity("5.0000")
        cq2 = ConsumptionQuantity("10.0000")

        with pytest.raises(InsufficientStockError, match="Insufficient stock"):
            _ = cq1 - cq2

    def test_arithmetic_mul_div(self) -> None:
        cq = ConsumptionQuantity("10.0000")

        mul = cq * Decimal("2.5")
        assert mul == ConsumptionQuantity("25.0000")

        rmul = 3 * cq
        assert rmul == ConsumptionQuantity("30.0000")

        div = cq / 2
        assert div == ConsumptionQuantity("5.0000")

        with pytest.raises(ZeroDivisionError):
            _ = cq / 0


# ============================================================================
# 2. VALUE OBJECT: PaxCount
# ============================================================================


class TestPaxCount:
    """Pruebas exhaustivas para el Value Object PaxCount (comensales >= 0)."""

    def test_creation_valid(self) -> None:
        pax1 = PaxCount(45)
        pax2 = PaxCount("120")
        pax3 = PaxCount(pax1)

        assert pax1.value == 45
        assert pax2.value == 120
        assert pax3.value == 45
        assert int(pax1) == 45
        assert str(pax1) == "45"
        assert repr(pax1) == "PaxCount(45)"

    def test_zero_pax_allowed(self) -> None:
        zero_pax = PaxCount(0)
        assert zero_pax.value == 0

    def test_negative_pax_forbidden(self) -> None:
        with pytest.raises(ValueError, match="PaxCount cannot be negative"):
            PaxCount(-1)

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(TypeError, match="Unsupported type for BuffetPaxCost"):
            BuffetPaxCost([])  # type: ignore[arg-type]

    def test_float_forbidden(self) -> None:
        with pytest.raises(TypeError, match="Float is forbidden for PaxCount"):
            PaxCount(10.5)  # type: ignore[arg-type]

    def test_boolean_forbidden(self) -> None:
        with pytest.raises(TypeError, match="Boolean is forbidden for PaxCount"):
            PaxCount(True)  # type: ignore[arg-type]

    def test_unsupported_type(self) -> None:
        with pytest.raises(TypeError, match="Unsupported type for PaxCount"):
            PaxCount([])  # type: ignore[arg-type]

    def test_invalid_string(self) -> None:
        with pytest.raises(ValueError, match="Invalid integer representation"):
            PaxCount("abc")

    def test_arithmetic_and_comparisons(self) -> None:
        p1 = PaxCount(20)
        p2 = PaxCount(30)

        assert p1 < p2
        assert p1 <= p2
        assert p2 > p1
        assert p2 >= p1
        assert p1 == 20
        assert p1 == PaxCount(20)
        assert p1 != 25
        assert not (p1 == "20")
        assert not (p1 == object())

        added = p1 + p2
        assert added == PaxCount(50)
        radded = 10 + p1
        assert radded == PaxCount(30)

        subbed = p2 - p1
        assert subbed == PaxCount(10)

        with pytest.raises(ValueError, match="PaxCount subtraction would result in negative count"):
            _ = p1 - p2


# ============================================================================
# 3. VALUE OBJECT: BuffetPaxCost
# ============================================================================


class TestBuffetPaxCost:
    """Pruebas exhaustivas para el Value Object BuffetPaxCost (2 decimales)."""

    def test_creation_valid(self) -> None:
        bpc1 = BuffetPaxCost(Decimal("1500.50"))
        bpc2 = BuffetPaxCost(2000)
        bpc3 = BuffetPaxCost("3450.75")
        bpc4 = BuffetPaxCost(bpc1)

        assert bpc1.value == Decimal("1500.50")
        assert bpc2.value == Decimal("2000.00")
        assert bpc3.value == Decimal("3450.75")
        assert bpc4.value == Decimal("1500.50")
        assert str(bpc1) == "1500.50"
        assert repr(bpc1) == "BuffetPaxCost('1500.50')"
        assert bpc1.to_decimal() == Decimal("1500.50")

    def test_zero_factory(self) -> None:
        zero = BuffetPaxCost.zero()
        assert zero.value == Decimal("0.00")

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(TypeError, match="Unsupported type for BuffetPaxCost"):
            BuffetPaxCost([])  # type: ignore[arg-type]

    def test_float_forbidden(self) -> None:
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            BuffetPaxCost(1500.5)  # type: ignore[arg-type]

    def test_boolean_forbidden(self) -> None:
        with pytest.raises(TypeError, match="Boolean is forbidden"):
            BuffetPaxCost(False)  # type: ignore[arg-type]

    def test_negative_forbidden(self) -> None:
        with pytest.raises(ValueError, match="BuffetPaxCost cannot be negative"):
            BuffetPaxCost(Decimal("-0.01"))

    def test_nan_or_inf_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be NaN or infinite"):
            BuffetPaxCost(Decimal("NaN"))

    def test_rounding_quantize(self) -> None:
        bpc = BuffetPaxCost(Decimal("123.455"))
        assert bpc.value == Decimal("123.46")

    def test_comparisons(self) -> None:
        b1 = BuffetPaxCost("100.00")
        b2 = BuffetPaxCost("200.00")

        assert b1 < b2
        assert b1 <= b2
        assert b2 > b1
        assert b2 >= b1
        assert b1 == "100.00"
        assert b1 == 100
        assert b1 == Decimal("100.00")
        assert not (b1 == "invalid")
        assert not (b1 == [1, 2, 3])
        assert not (b1 == object())


# ============================================================================
# 4. EXPLOSIÓN DE RECETAS A INSUMOS (Axioma 1)
# ============================================================================


class TestExplodeRecipeConsumption:
    """Pruebas del algoritmo de explosión de recetas por porción."""

    def test_explosion_with_recipe_spec(self) -> None:
        # Receta: 4 porciones
        # Insumo 101: 2.0000 kg (sin merma) -> por porción = 0.5000 kg
        # Insumo 102: 1.0000 kg (10% merma) -> bruto = 1.1000 kg -> por porción = 0.2750 kg
        recipes = {
            1: RecipeSpec(
                recipe_id=1,
                yield_portions=Decimal("4"),
                ingredients=[
                    RecipeIngredientItem(ingredient_id=101, quantity=Decimal("2.0000")),
                    RecipeIngredientItem(ingredient_id=102, quantity=Decimal("1.0000"), waste_pct=Decimal("10")),
                ],
            )
        }

        # Consumo de 8 porciones de la receta 1
        items = [RecipeConsumptionItem(recipe_id=1, portions=Decimal("8"))]
        totals = explode_recipe_consumption(items, recipes)

        # Insumo 101: 0.5 * 8 = 4.0000
        # Insumo 102: 0.2750 * 8 = 2.2000
        assert totals[101] == ConsumptionQuantity("4.0000")
        assert totals[102] == ConsumptionQuantity("2.2000")

    def test_explosion_with_multiple_recipes_overlapping_ingredients(self) -> None:
        recipes = {
            "r1": RecipeSpec(
                recipe_id="r1",
                yield_portions=Decimal("1"),
                ingredients=[RecipeIngredientItem(ingredient_id="harina", quantity=Decimal("0.2000"))],
            ),
            "r2": RecipeSpec(
                recipe_id="r2",
                yield_portions=Decimal("2"),
                ingredients=[
                    RecipeIngredientItem(ingredient_id="harina", quantity=Decimal("0.6000")),
                    RecipeIngredientItem(ingredient_id="azucar", quantity=Decimal("0.1000")),
                ],
            ),
        }

        items = {
            "r1": Decimal("3"),  # Harina: 0.2 * 3 = 0.6000
            "r2": Decimal("4"),  # Harina: (0.6 / 2) * 4 = 1.2000, Azucar: (0.1 / 2) * 4 = 0.2000
        }

        totals = explode_recipe_consumption(items, recipes)
        assert totals["harina"] == ConsumptionQuantity("1.8000")
        assert totals["azucar"] == ConsumptionQuantity("0.2000")

    def test_explosion_legacy_format_mapping(self) -> None:
        legacy_recipes = {
            10: {1001: Decimal("0.3500"), 1002: Decimal("0.1000")}
        }
        items = [RecipeConsumptionItem(recipe_id=10, portions=Decimal("2"))]
        totals = explode_recipe_consumption(items, legacy_recipes)

        assert totals[1001] == ConsumptionQuantity("0.7000")
        assert totals[1002] == ConsumptionQuantity("0.2000")

    def test_explosion_legacy_format_negative_raises(self) -> None:
        legacy_recipes = {10: {1001: Decimal("-0.3500")}}
        with pytest.raises(ValueError, match="ingredient quantity cannot be negative"):
            explode_recipe_consumption([RecipeConsumptionItem(recipe_id=10, portions=Decimal("1"))], legacy_recipes)

    def test_explosion_unsupported_spec_type_raises(self) -> None:
        with pytest.raises(TypeError, match="Unsupported recipe spec type"):
            explode_recipe_consumption([RecipeConsumptionItem(recipe_id=1, portions=Decimal("1"))], {1: "not_a_spec"})  # type: ignore[dict-item]

    def test_recipe_not_found_raises_keyerror(self) -> None:
        recipes = {1: RecipeSpec(recipe_id=1, yield_portions=Decimal("1"), ingredients=[])}
        with pytest.raises(KeyError, match="Recipe spec not found for recipe_id: 999"):
            explode_recipe_consumption([RecipeConsumptionItem(recipe_id=999, portions=Decimal("1"))], recipes)

    def test_invalid_yield_raises(self) -> None:
        with pytest.raises(ValueError, match="yield_portions must be strictly positive"):
            RecipeSpec(recipe_id=1, yield_portions=Decimal("0"))

    def test_invalid_portions_raises(self) -> None:
        with pytest.raises(ValueError, match="portions must be strictly positive"):
            RecipeConsumptionItem(recipe_id=1, portions=Decimal("-1"))

    def test_negative_quantity_raises(self) -> None:
        with pytest.raises(ValueError, match="ingredient quantity cannot be negative"):
            RecipeIngredientItem(ingredient_id=1, quantity=Decimal("-0.5"))

    def test_negative_waste_raises(self) -> None:
        with pytest.raises(ValueError, match="waste_pct cannot be negative"):
            RecipeIngredientItem(ingredient_id=1, quantity=Decimal("1"), waste_pct=Decimal("-5"))

    def test_float_in_recipe_spec_strictly_forbidden(self) -> None:
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            RecipeSpec(recipe_id=1, yield_portions=1.5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            RecipeIngredientItem(ingredient_id=1, quantity=2.5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            RecipeConsumptionItem(recipe_id=1, portions=3.5)  # type: ignore[arg-type]


# ============================================================================
# 5. DEDUCCIÓN ESTRICTA FEFO (Axioma 2 y 3)
# ============================================================================


class TestFefoDeduction:
    """Pruebas del ordenamiento y asignación estricta FEFO."""

    def test_sort_lots_fefo_priority(self) -> None:
        today = date(2026, 10, 25)
        lot_soon = ConsumptionLot(lot_id=1, quantity=Decimal("10"), expires_on=today + timedelta(days=2))
        lot_later = ConsumptionLot(lot_id=2, quantity=Decimal("10"), expires_on=today + timedelta(days=10))
        lot_no_exp_1 = ConsumptionLot(lot_id=3, quantity=Decimal("10"), expires_on=None)
        lot_no_exp_2 = ConsumptionLot(lot_id=4, quantity=Decimal("10"), expires_on=None)
        lot_tie_breaker = ConsumptionLot(lot_id=5, quantity=Decimal("10"), expires_on=today + timedelta(days=2))

        lots = [lot_no_exp_2, lot_later, lot_tie_breaker, lot_no_exp_1, lot_soon]
        sorted_lots = sort_lots_fefo(lots)

        # Esperado: lot_soon (id=1, exp+2), lot_tie_breaker (id=5, exp+2), lot_later (id=2, exp+10), lot_no_exp_1 (id=3), lot_no_exp_2 (id=4)
        assert [l.lot_id for l in sorted_lots] == [1, 5, 2, 3, 4]

    def test_deduct_lots_fefo_exact_and_partial(self) -> None:
        today = date(2026, 10, 25)
        lots = [
            ConsumptionLot(lot_id="L1", quantity=Decimal("10.0000"), expires_on=today + timedelta(days=1)),
            ConsumptionLot(lot_id="L2", quantity=Decimal("20.0000"), expires_on=today + timedelta(days=5)),
        ]

        # Consumo de 15 unidades: debe tomar 10 de L1 (dejándolo en 0) y 5 de L2 (dejándolo en 15)
        deductions, updated = deduct_lots_fefo(lots, "15.0000", reference_date=today)

        assert len(deductions) == 2
        assert deductions[0] == LotDeduction(
            lot_id="L1",
            deducted_quantity=ConsumptionQuantity("10.0000"),
            remaining_quantity=ConsumptionQuantity("0.0000"),
        )
        assert deductions[1] == LotDeduction(
            lot_id="L2",
            deducted_quantity=ConsumptionQuantity("5.0000"),
            remaining_quantity=ConsumptionQuantity("15.0000"),
        )

        l1_updated = next(l for l in updated if l.lot_id == "L1")
        l2_updated = next(l for l in updated if l.lot_id == "L2")
        assert l1_updated.quantity == Decimal("0.0000")
        assert l2_updated.quantity == Decimal("15.0000")

    def test_deduct_lots_insufficient_stock_raises(self) -> None:
        today = date(2026, 10, 25)
        lots = [
            ConsumptionLot(lot_id="L1", quantity=Decimal("5.0000"), expires_on=today + timedelta(days=2)),
        ]
        with pytest.raises(InsufficientStockError, match="Insufficient stock across lots"):
            deduct_lots_fefo(lots, "10.0000", reference_date=today)

    def test_expired_lots_rejected_by_default(self) -> None:
        today = date(2026, 10, 25)
        lots = [
            # Lote ya vencido ayer
            ConsumptionLot(lot_id="L_EXP", quantity=Decimal("10.0000"), expires_on=today - timedelta(days=1)),
            # Lote vigente
            ConsumptionLot(lot_id="L_VALID", quantity=Decimal("5.0000"), expires_on=today + timedelta(days=5)),
        ]

        # Intentar consumir 8 unidades: solo 5 disponibles porque el vencido es omitido
        with pytest.raises(InsufficientStockError, match="Insufficient stock across lots"):
            deduct_lots_fefo(lots, "8.0000", allow_expired=False, reference_date=today)

        # Si permitimos vencidos (por contingencia autorizada), sí debe procesar
        deductions, updated = deduct_lots_fefo(lots, "8.0000", allow_expired=True, reference_date=today)
        assert len(deductions) == 1
        assert deductions[0].lot_id == "L_EXP"
        assert deductions[0].deducted_quantity == ConsumptionQuantity("8.0000")

    def test_zero_or_negative_required_quantity_raises(self) -> None:
        today = date(2026, 10, 25)
        lots = [ConsumptionLot(lot_id=1, quantity=Decimal("10"), expires_on=today)]
        with pytest.raises(ValueError, match="required quantity must be strictly positive"):
            deduct_lots_fefo(lots, "0.0000", reference_date=today)

    def test_float_in_lot_strictly_forbidden(self) -> None:
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            ConsumptionLot(lot_id=1, quantity=10.5)  # type: ignore[arg-type]

    def test_negative_quantity_in_lot_raises(self) -> None:
        with pytest.raises(ValueError, match="lot quantity cannot be negative"):
            ConsumptionLot(lot_id=1, quantity=Decimal("-5.0000"))

    def test_deduct_lots_fefo_ignores_zero_lots_and_preserves_untouched(self) -> None:
        today = date(2026, 10, 25)
        lots = [
            ConsumptionLot(lot_id="L0", quantity=Decimal("0.0000"), expires_on=today),
            ConsumptionLot(lot_id="L1", quantity=Decimal("10.0000"), expires_on=today + timedelta(days=2)),
            ConsumptionLot(lot_id="L2", quantity=Decimal("10.0000"), expires_on=today + timedelta(days=5)),
        ]
        deductions, updated = deduct_lots_fefo(lots, "5.0000", reference_date=today)
        assert len(deductions) == 1
        assert deductions[0].lot_id == "L1"
        assert deductions[0].deducted_quantity == ConsumptionQuantity("5.0000")

        # L0 and L2 are preserved untouched in updated
        l0_updated = next(l for l in updated if l.lot_id == "L0")
        l2_updated = next(l for l in updated if l.lot_id == "L2")
        assert l0_updated.quantity == Decimal("0.0000")
        assert l2_updated.quantity == Decimal("10.0000")


# ============================================================================
# 6. CONCILIACIÓN BUFFET Y COSTO POR COMENSAL (Axioma 4)
# ============================================================================


class TestBuffetCostPerPax:
    """Pruebas del cálculo de costo de comensales en buffet."""

    def test_calculate_buffet_pax_cost_standard(self) -> None:
        # Montaje: 100,000 CLP, Sobrante reutilizable: 20,000 CLP, Comensales: 80
        # Costo neto: 80,000 / 80 = 1,000.00 CLP
        cost = calculate_buffet_pax_cost(
            total_montaje_cost=Decimal("100000.00"),
            pax=80,
            leftover_reusable_value=Decimal("20000.00"),
        )
        assert cost == BuffetPaxCost("1000.00")
        assert cost.value == Decimal("1000.00")

    def test_calculate_buffet_pax_cost_zero_leftover(self) -> None:
        # Montaje: 50,000, Comensales: 15
        # 50,000 / 15 = 3333.3333... -> 3333.33
        cost = calculate_buffet_pax_cost(
            total_montaje_cost="50000.00",
            pax="15",
            leftover_reusable_value="0.00",
        )
        assert cost == BuffetPaxCost("3333.33")

    def test_zero_pax_strictly_raises(self) -> None:
        with pytest.raises(ValueError, match="pax must be strictly positive"):
            calculate_buffet_pax_cost(
                total_montaje_cost=Decimal("10000.00"),
                pax=0,
            )

    def test_negative_pax_strictly_raises(self) -> None:
        with pytest.raises(ValueError):
            calculate_buffet_pax_cost(
                total_montaje_cost=Decimal("10000.00"),
                pax=-5,
            )

    def test_leftover_exceeding_montage_raises(self) -> None:
        with pytest.raises(ValueError, match="leftover_reusable_value .* cannot exceed total_montaje_cost"):
            calculate_buffet_pax_cost(
                total_montaje_cost=Decimal("10000.00"),
                pax=10,
                leftover_reusable_value=Decimal("12000.00"),
            )

    def test_negative_costs_raises(self) -> None:
        with pytest.raises(ValueError, match="total_montaje_cost cannot be negative"):
            calculate_buffet_pax_cost(
                total_montaje_cost=Decimal("-100.00"),
                pax=10,
            )
        with pytest.raises(ValueError, match="leftover_reusable_value cannot be negative"):
            calculate_buffet_pax_cost(
                total_montaje_cost=Decimal("100.00"),
                pax=10,
                leftover_reusable_value=Decimal("-10.00"),
            )

    def test_float_strictly_forbidden_in_buffet_cost(self) -> None:
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            calculate_buffet_pax_cost(total_montaje_cost=100.50, pax=10)  # type: ignore[arg-type]
