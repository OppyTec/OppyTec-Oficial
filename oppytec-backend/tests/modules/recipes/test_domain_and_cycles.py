"""
oppytec-backend/tests/modules/recipes/test_domain_and_cycles.py
Suite de pruebas unitarias exhaustivas para el Dominio de Recetas, Escandallos,
Value Objects con precisión Decimal estricta (0 floats), Entidades Polimórficas
y Algoritmo DAG Anti-Recursión Cíclica.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.recipes.domain.cycle_detector import (
    check_recipe_cycles,
    find_all_cycles,
    would_create_cycle,
)
from src.modules.recipes.domain.entities import (
    Combo,
    ComboGrupoOpcion,
    ComboItem,
    GrupoOpciones,
    GrupoOpcionesItem,
    Receta,
    RecetaGrupoOpcion,
    RecetaIngrediente,
)
from src.modules.recipes.domain.exceptions import (
    InvalidOptionSelectionError,
    InvalidQuantityError,
    InvalidYieldError,
    PolymorphicReferenceError,
    RecipeCycleError,
    RecipeDomainError,
)
from src.modules.recipes.domain.value_objects import (
    DynamicCostSummary,
    IngredientQuantity,
    OptionSelectionRule,
    ServingYield,
)


# ==============================================================================
# 1. PRUEBAS DE VALUE OBJECT: ServingYield
# ==============================================================================

class TestServingYield:
    """Pruebas para el Value Object de Rendimiento en Porciones."""

    def test_valid_serving_yield_creation(self) -> None:
        y1 = ServingYield(Decimal("4.0000"))
        assert y1.portions == Decimal("4.0000")

        # Admite int y str
        y2 = ServingYield(1)
        assert y2.portions == Decimal("1.0000")

        y3 = ServingYield("2.5")
        assert y3.portions == Decimal("2.5000")

    def test_default_serving_yield(self) -> None:
        y = ServingYield()
        assert y.portions == Decimal("1.0000")

    def test_invalid_portions_raise_error(self) -> None:
        with pytest.raises(InvalidYieldError, match="strictly greater than 0"):
            ServingYield(Decimal("0.0000"))

        with pytest.raises(InvalidYieldError, match="strictly greater than 0"):
            ServingYield(Decimal("-2.0"))

    def test_float_strictly_forbidden(self) -> None:
        bad_val = 4.5  # float
        with pytest.raises(TypeError, match="Floats are strictly forbidden"):
            ServingYield(bad_val)  # type: ignore

    def test_unit_cost_calculation(self) -> None:
        sy = ServingYield(Decimal("4.0000"))
        # Costo total 10.000 / 4 porciones = 2.5000
        cost = sy.unit_cost(Decimal("10000.00"))
        assert cost == Decimal("2500.0000")

        # Con decimales periódicos y redondeo HALF_UP
        sy3 = ServingYield(Decimal("3.0000"))
        cost3 = sy3.unit_cost(Decimal("10.00"))
        assert cost3 == Decimal("3.3333")

    def test_unit_cost_invalid_negative_or_float(self) -> None:
        sy = ServingYield(Decimal("2.0000"))
        with pytest.raises(ValueError, match="Total cost cannot be negative"):
            sy.unit_cost(Decimal("-50.00"))

        with pytest.raises(TypeError, match="Floats are strictly forbidden"):
            sy.unit_cost(10.5)  # type: ignore

    def test_scale_factor(self) -> None:
        sy_base = ServingYield(Decimal("2.0000"))
        sy_target = ServingYield(Decimal("6.0000"))
        assert sy_base.scale_factor(sy_target) == Decimal("3")
        assert sy_base.scale_factor(Decimal("1")) == Decimal("0.5")


# ==============================================================================
# 2. PRUEBAS DE VALUE OBJECT: IngredientQuantity
# ==============================================================================

class TestIngredientQuantity:
    """Pruebas para la cantidad física e índice de merma técnica."""

    def test_valid_ingredient_quantity(self) -> None:
        iq = IngredientQuantity(Decimal("0.5000"), Decimal("10.00"), unit="kg")
        assert iq.quantity == Decimal("0.5000")
        assert iq.waste_pct == Decimal("10.00")
        assert iq.unit == "kg"

    def test_quantity_must_be_positive(self) -> None:
        with pytest.raises(InvalidQuantityError, match="strictly greater than 0"):
            IngredientQuantity(Decimal("0.0000"))

        with pytest.raises(InvalidQuantityError, match="strictly greater than 0"):
            IngredientQuantity(Decimal("-1.5000"))

    def test_waste_percentage_bounds(self) -> None:
        # 0% es válido
        iq0 = IngredientQuantity(Decimal("1.0000"), Decimal("0.00"))
        assert iq0.waste_pct == Decimal("0.00")

        # 99.99% es válido
        iq99 = IngredientQuantity(Decimal("1.0000"), Decimal("99.99"))
        assert iq99.waste_pct == Decimal("99.99")

        # < 0 es inválido
        with pytest.raises(InvalidQuantityError, match="satisfy 0 <= waste_pct < 100"):
            IngredientQuantity(Decimal("1.0000"), Decimal("-0.01"))

        # >= 100 es inválido
        with pytest.raises(InvalidQuantityError, match="satisfy 0 <= waste_pct < 100"):
            IngredientQuantity(Decimal("1.0000"), Decimal("100.00"))

    def test_float_strictly_forbidden(self) -> None:
        with pytest.raises(TypeError, match="Floats are strictly forbidden"):
            IngredientQuantity(1.5, Decimal("0.00"))  # type: ignore

        with pytest.raises(TypeError, match="Floats are strictly forbidden"):
            IngredientQuantity(Decimal("1.0000"), 5.5)  # type: ignore

    def test_gross_quantity_and_cost_calculation(self) -> None:
        # 2 kg con 10% de merma técnica -> 2 * 1.10 = 2.2000 kg brutos
        iq = IngredientQuantity(Decimal("2.0000"), Decimal("10.00"), "kg")
        assert iq.gross_quantity() == Decimal("2.2000")

        # Costo unitario de $1.500 / kg -> 2.2000 * 1500 = $3.300
        cost = iq.calculate_cost(Decimal("1500.0000"))
        assert cost == Decimal("3300.0000")

    def test_scale_ingredient_quantity(self) -> None:
        iq = IngredientQuantity(Decimal("0.2500"), Decimal("5.00"), "lt")
        scaled = iq.scale(Decimal("4"))
        assert scaled.quantity == Decimal("1.0000")
        assert scaled.waste_pct == Decimal("5.00")
        assert scaled.unit == "lt"


# ==============================================================================
# 3. PRUEBAS DE VALUE OBJECT: DynamicCostSummary
# ==============================================================================

class TestDynamicCostSummary:
    """Pruebas para el resumen de costos tripartito de escandallo dinámico."""

    def test_valid_summary_creation(self) -> None:
        summary = DynamicCostSummary(
            costo_base=Decimal("1500.0000"),
            costo_peor_caso=Decimal("2000.0000"),
            costo_mejor_caso=Decimal("1200.0000"),
            currency="CLP",
        )
        assert summary.costo_base == Decimal("1500.0000")
        assert summary.costo_peor_caso == Decimal("2000.0000")
        assert summary.costo_mejor_caso == Decimal("1200.0000")
        assert summary.cost_spread() == Decimal("800.0000")

    def test_identical_costs_when_no_options(self) -> None:
        summary = DynamicCostSummary(
            costo_base=Decimal("1000.0000"),
            costo_peor_caso=Decimal("1000.0000"),
            costo_mejor_caso=Decimal("1000.0000"),
        )
        assert summary.cost_spread() == Decimal("0.0000")

    def test_invalid_order_or_negative_costs(self) -> None:
        # Negativo
        with pytest.raises(ValueError, match="cannot be negative"):
            DynamicCostSummary(Decimal("-10.00"), Decimal("100.00"), Decimal("50.00"))

        # mejor caso > peor caso
        with pytest.raises(ValueError, match="cannot exceed costo_peor_caso"):
            DynamicCostSummary(Decimal("150.00"), Decimal("100.00"), Decimal("200.00"))

        # base fuera de rango [mejor, peor]
        with pytest.raises(ValueError, match="must lie between"):
            DynamicCostSummary(Decimal("50.00"), Decimal("200.00"), Decimal("100.00"))

    def test_float_strictly_forbidden(self) -> None:
        with pytest.raises(TypeError, match="Floats are strictly forbidden"):
            DynamicCostSummary(1500.5, Decimal("2000.00"), Decimal("1000.00"))  # type: ignore

    def test_margin_and_food_cost_calculations(self) -> None:
        summary = DynamicCostSummary(
            costo_base=Decimal("3000.0000"),
            costo_peor_caso=Decimal("4000.0000"),
            costo_mejor_caso=Decimal("2500.0000"),
        )
        precio_neto = Decimal("10000.00")

        # Margen base: (10000 - 3000) / 10000 * 100 = 70.00%
        assert summary.margen_base(precio_neto) == Decimal("70.00")
        # Margen peor caso: (10000 - 4000) / 10000 * 100 = 60.00%
        assert summary.margen_peor_caso(precio_neto) == Decimal("60.00")
        # Margen mejor caso: (10000 - 2500) / 10000 * 100 = 75.00%
        assert summary.margen_mejor_caso(precio_neto) == Decimal("75.00")

        # Food Cost % base: 3000 / 10000 * 100 = 30.00%
        assert summary.food_cost_pct_base(precio_neto) == Decimal("30.00")
        # Food Cost % peor caso: 4000 / 10000 * 100 = 40.00%
        assert summary.food_cost_pct_peor_caso(precio_neto) == Decimal("40.00")


# ==============================================================================
# 4. PRUEBAS DE VALUE OBJECT: OptionSelectionRule
# ==============================================================================

class TestOptionSelectionRule:
    """Pruebas para las reglas de cardinalidad de selección."""

    def test_default_single_choice_rule(self) -> None:
        rule = OptionSelectionRule()
        assert rule.min_selections == 1
        assert rule.max_selections == 1
        assert not rule.allows_repeat
        assert rule.is_required
        assert not rule.is_optional
        assert rule.is_single_choice
        assert rule.validate_selection_count(1)
        assert not rule.validate_selection_count(0)
        assert not rule.validate_selection_count(2)

    def test_optional_multiple_choice_rule(self) -> None:
        rule = OptionSelectionRule(min_selections=0, max_selections=3, allows_repeat=True)
        assert rule.is_optional
        assert not rule.is_required
        assert not rule.is_single_choice
        assert rule.allows_repeat
        assert rule.validate_selection_count(0)
        assert rule.validate_selection_count(2)
        assert rule.validate_selection_count(3)
        assert not rule.validate_selection_count(4)

    def test_invalid_rules_raise_error(self) -> None:
        # min < 0
        with pytest.raises(InvalidOptionSelectionError, match="min_selections must be >= 0"):
            OptionSelectionRule(min_selections=-1, max_selections=2)

        # max < 1
        with pytest.raises(InvalidOptionSelectionError, match="max_selections must be >= 1"):
            OptionSelectionRule(min_selections=0, max_selections=0)

        # max < min
        with pytest.raises(InvalidOptionSelectionError, match="cannot be less than min_selections"):
            OptionSelectionRule(min_selections=3, max_selections=2)

    def test_ensure_valid_selection_count(self) -> None:
        rule = OptionSelectionRule(min_selections=1, max_selections=2)
        rule.ensure_valid_selection_count(1)
        rule.ensure_valid_selection_count(2)
        with pytest.raises(InvalidOptionSelectionError, match="is invalid. Required between"):
            rule.ensure_valid_selection_count(0)
        with pytest.raises(InvalidOptionSelectionError, match="is invalid. Required between"):
            rule.ensure_valid_selection_count(3)


# ==============================================================================
# 5. PRUEBAS DE DETECCIÓN DE CICLOS EN SUB-RECETAS (DAG)
# ==============================================================================

class TestRecipeCycleDetector:
    """Pruebas exhaustivas para el detector de ciclos en árboles de sub-recetas."""

    def test_acyclic_simple_tree(self) -> None:
        # 1 -> [2, 3], 2 -> [], 3 -> []
        tree = {1: [2, 3], 2: [], 3: []}
        check_recipe_cycles(1, tree)  # No lanza excepción

    def test_acyclic_diamond_dag(self) -> None:
        # Diamante clásico (DAG válido sin ciclos):
        # 1 -> [2, 3], 2 -> [4], 3 -> [4], 4 -> []
        tree = {
            1: [2, 3],
            2: [4],
            3: [4],
            4: [],
        }
        check_recipe_cycles(1, tree)

    def test_direct_self_recursion_cycle_a_to_a(self) -> None:
        # Recursión directa: A -> A
        tree = {1: [1]}
        with pytest.raises(RecipeCycleError) as exc_info:
            check_recipe_cycles(1, tree)
        assert "1 -> 1" in str(exc_info.value)

    def test_indirect_cycle_a_to_b_to_a(self) -> None:
        # Recursión indirecta corta: 1 -> 2 -> 1
        tree = {
            1: [2],
            2: [1],
        }
        with pytest.raises(RecipeCycleError) as exc_info:
            check_recipe_cycles(1, tree)
        assert "1 -> 2 -> 1" in str(exc_info.value)

    def test_deep_indirect_cycle(self) -> None:
        # Recursión profunda: 1 -> 2 -> 3 -> 4 -> 1
        tree = {
            1: [2],
            2: [3],
            3: [4],
            4: [1],
        }
        with pytest.raises(RecipeCycleError) as exc_info:
            check_recipe_cycles(1, tree)
        assert "1 -> 2 -> 3 -> 4 -> 1" in str(exc_info.value)

    def test_cycle_in_subbranch(self) -> None:
        # El ciclo no involucra a la raíz directamente, pero está en su árbol:
        # 1 -> [2], 2 -> [3], 3 -> [4], 4 -> [2]
        tree = {
            1: [2],
            2: [3],
            3: [4],
            4: [2],
        }
        with pytest.raises(RecipeCycleError) as exc_info:
            check_recipe_cycles(1, tree)
        assert "2 -> 3 -> 4 -> 2" in str(exc_info.value)

    def test_would_create_cycle(self) -> None:
        tree = {
            1: [2],
            2: [3],
            3: [],
        }
        # Intentar añadir 3 -> 1 cerraría el ciclo 1 -> 2 -> 3 -> 1
        assert would_create_cycle(3, 1, tree) is True

        # Auto-referencia directa 1 -> 1
        assert would_create_cycle(1, 1, tree) is True

        # Añadir 3 -> 4 (donde 4 es hoja nueva) es seguro
        assert would_create_cycle(3, 4, tree) is False

        # Añadir 1 -> 3 (atajo en DAG) es seguro
        assert would_create_cycle(1, 3, tree) is False

    def test_find_all_cycles(self) -> None:
        graph = {
            1: [2],
            2: [1],
            3: [4],
            4: [3],
        }
        cycles = find_all_cycles(graph)
        assert len(cycles) >= 2


# ==============================================================================
# 6. PRUEBAS DE ENTIDADES DE DOMINIO Y POLIMORFISMO
# ==============================================================================

class TestDomainEntities:
    """Pruebas para entidades puras Receta, Combo, GrupoOpciones e Items Polimórficos."""

    def test_receta_ingrediente_xor_polymorphism(self) -> None:
        qty = IngredientQuantity(Decimal("1.5000"), Decimal("0.00"), "kg")

        # Caso válido 1: Producto físico
        ing_prod = RecetaIngrediente(producto_id=101, cantidad=qty)
        assert ing_prod.is_product
        assert not ing_prod.is_subrecipe
        assert ing_prod.target_id == 101

        # Caso válido 2: Sub-receta gastronómica
        ing_sub = RecetaIngrediente(subreceta_id=202, cantidad=qty)
        assert ing_sub.is_subrecipe
        assert not ing_sub.is_product
        assert ing_sub.target_id == 202

        # Violación XOR: Ambos None
        with pytest.raises(PolymorphicReferenceError, match="must reference exactly one target"):
            RecetaIngrediente(cantidad=qty)

        # Violación XOR: Ambos con valor
        with pytest.raises(PolymorphicReferenceError, match="must reference exactly one target"):
            RecetaIngrediente(producto_id=101, subreceta_id=202, cantidad=qty)

    def test_grupo_opciones_item_xor_polymorphism(self) -> None:
        # Válido producto
        item_prod = GrupoOpcionesItem(
            producto_id=55,
            cantidad=Decimal("1.0000"),
            es_opcion_default=True,
            recargo_precio=Decimal("0.00"),
        )
        assert item_prod.is_product
        assert not item_prod.is_recipe
        assert item_prod.target_id == 55

        # Válido receta
        item_rec = GrupoOpcionesItem(
            receta_id=88,
            cantidad=Decimal("1.0000"),
            es_opcion_default=False,
            recargo_precio=Decimal("500.00"),
        )
        assert item_rec.is_recipe
        assert not item_rec.is_product
        assert item_rec.target_id == 88

        # Violación XOR
        with pytest.raises(PolymorphicReferenceError):
            GrupoOpcionesItem()

        with pytest.raises(PolymorphicReferenceError):
            GrupoOpcionesItem(producto_id=1, receta_id=2)

    def test_grupo_opciones_creation_and_defaults(self) -> None:
        item_def = GrupoOpcionesItem(producto_id=1, es_opcion_default=True)
        item_opt = GrupoOpcionesItem(producto_id=2, es_opcion_default=False)

        grupo = GrupoOpciones(
            nombre="Guarnición",
            regla=OptionSelectionRule(min_selections=1, max_selections=1),
            items=(item_def, item_opt),
        )

        assert grupo.item_count == 2
        assert grupo.has_default
        assert len(grupo.default_items) == 1
        assert grupo.default_items[0].target_id == 1

        # Nombre vacío inválido
        with pytest.raises(ValueError, match="name cannot be empty"):
            GrupoOpciones(nombre="   ")

    def test_receta_auto_detects_dynamic_mode(self) -> None:
        # Receta estática: sin grupos de opciones
        receta_fija = Receta(
            codigo="REC-001",
            nombre="Papas Fritas Clásicas",
            es_subreceta=False,
            es_dinamica=False,
            grupos_opciones=(),
        )
        assert not receta_fija.es_dinamica

        # Receta dinámica: vinculada a un grupo de opciones
        vinculo = RecetaGrupoOpcion(grupo_id=10, orden=0, es_requerido=True)
        receta_dinamica = Receta(
            codigo="REC-002",
            nombre="Hamburguesa Configurable",
            grupos_opciones=(vinculo,),
        )
        # Se auto-marca como dinámica
        assert receta_dinamica.es_dinamica

    def test_receta_subrecipes_and_margin_calculations(self) -> None:
        qty = IngredientQuantity(Decimal("1.0000"))
        ing_prod = RecetaIngrediente(producto_id=10, cantidad=qty)
        ing_sub1 = RecetaIngrediente(subreceta_id=20, cantidad=qty)
        ing_sub2 = RecetaIngrediente(subreceta_id=30, cantidad=qty)

        receta = Receta(
            codigo="REC-PLATO",
            nombre="Plato Gourmet",
            porciones_rendimiento=ServingYield(Decimal("2.0000")),
            ingredientes_fijos=(ing_prod, ing_sub1, ing_sub2),
            costo_total_calculado=Decimal("6000.00"),  # Costo lote
            precio_venta_neto=Decimal("8000.00"),      # Precio neto porción
        )

        assert receta.has_subrecipes
        assert receta.subrecipe_ids == {20, 30}

        # Costo unitario porción = 6000 / 2 = 3000.00
        assert receta.costo_unitario_porcion() == Decimal("3000.0000")

        # Margen monto porción = 8000 - 3000 = 5000.00
        assert receta.margin_amount() == Decimal("5000.00")

        # Margen % = 5000 / 8000 * 100 = 62.50%
        assert receta.margin_pct() == Decimal("62.50")

        # Food Cost % = 3000 / 8000 * 100 = 37.50%
        assert receta.food_cost_pct() == Decimal("37.50")

    def test_combo_polymorphism_and_auto_dynamics(self) -> None:
        # Combo Items
        item_prod = ComboItem(producto_id=1, cantidad=Decimal("2.0000"))
        item_rec = ComboItem(receta_id=5, cantidad=Decimal("1.0000"))

        combo_fijo = Combo(
            codigo="CMB-001",
            nombre="Dúo Clásico",
            items_fijos=(item_prod, item_rec),
            grupos_opciones=(),
            costo_total_calculado=Decimal("4000.00"),
            precio_venta_neto=Decimal("6000.00"),
        )
        assert not combo_fijo.es_dinamico
        assert combo_fijo.margin_amount() == Decimal("2000.00")
        assert combo_fijo.margin_pct() == Decimal("33.33")

        # Con grupo de opciones se auto-marca dinámico
        combo_din = Combo(
            codigo="CMB-002",
            nombre="Combo Personalizable",
            items_fijos=(item_prod,),
            grupos_opciones=(ComboGrupoOpcion(grupo_id=10),),
        )
        assert combo_din.es_dinamico
