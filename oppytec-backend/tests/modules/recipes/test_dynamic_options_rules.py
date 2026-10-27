"""
oppytec-backend/tests/modules/recipes/test_dynamic_options_rules.py
Suite de pruebas para Reglas de Opciones Dinámicas, Cardinalidad Mín/Máx,
Validación de Defaults y Recargos de Precios en Recetas y Combos Gourmet:
- Cardinalidad Mín/Máx con OptionSelectionRule y OptionGroupService.
- Validación obligatoria de opciones por defecto en grupos requeridos.
- Restricción de selección repetida (permite_repetir=True/False).
- Recargos de precios, cálculo financiero en simulación y rechazo de recargos negativos.
- Autodetección de dinamismo en combos y protección de borrado si está en uso.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.recipes.application.combo_service import (
    ComboItemDTO,
    ComboOptionGroupLinkDTO,
    ComboService,
)
from src.modules.recipes.application.option_group_service import (
    OptionGroupDTO,
    OptionGroupService,
    OptionItemDTO,
)
from src.modules.recipes.application.recipe_cost_simulator_service import (
    RecipeCostSimulatorService,
)
from src.modules.recipes.application.recipe_service import (
    RecipeIngredientDTO,
    RecipeOptionGroupLinkDTO,
    RecipeService,
)
from src.modules.recipes.domain.entities import (
    Combo,
    ComboGrupoOpcion,
    ComboItem,
    GrupoOpciones,
    GrupoOpcionesItem,
)
from src.modules.recipes.domain.exceptions import (
    InvalidOptionSelectionError,
    InvalidQuantityError,
    OptionGroupInUseError,
    PolymorphicReferenceError,
)
from src.modules.recipes.domain.value_objects import OptionSelectionRule

pytestmark = pytest.mark.unit


# ==============================================================================
# 1. PRUEBAS DE CARDINALIDAD MÍN/MÁX (OptionSelectionRule)
# ==============================================================================

class TestOptionCardinalityRules:
    """Pruebas para las reglas de cardinalidad y repetibilidad de selección."""

    def test_single_choice_mandatory_rule(self) -> None:
        """Elección única obligatoria: min=1, max=1, permite_repetir=False."""
        rule = OptionSelectionRule(min_selections=1, max_selections=1, allows_repeat=False)

        assert rule.is_required is True
        assert rule.is_optional is False
        assert rule.is_single_choice is True
        assert rule.allows_repeat is False

        # Conteo exacto
        assert rule.validate_selection_count(1) is True
        assert rule.validate_selection_count(0) is False
        assert rule.validate_selection_count(2) is False

        # ensure_valid_selection_count
        rule.ensure_valid_selection_count(1)
        with pytest.raises(InvalidOptionSelectionError, match="is invalid. Required between 1 and 1"):
            rule.ensure_valid_selection_count(0)
        with pytest.raises(InvalidOptionSelectionError, match="is invalid. Required between 1 and 1"):
            rule.ensure_valid_selection_count(2)

    def test_optional_multiple_choice_rule(self) -> None:
        """Elección opcional múltiple: min=0, max=3, permite_repetir=True."""
        rule = OptionSelectionRule(min_selections=0, max_selections=3, allows_repeat=True)

        assert rule.is_required is False
        assert rule.is_optional is True
        assert rule.is_single_choice is False
        assert rule.allows_repeat is True

        assert rule.validate_selection_count(0) is True
        assert rule.validate_selection_count(1) is True
        assert rule.validate_selection_count(3) is True
        assert rule.validate_selection_count(4) is False

        rule.ensure_valid_selection_count(0)
        rule.ensure_valid_selection_count(3)
        with pytest.raises(InvalidOptionSelectionError, match="is invalid. Required between 0 and 3"):
            rule.ensure_valid_selection_count(4)

    def test_required_range_selection_rule(self) -> None:
        """Rango obligatorio: min=2, max=4."""
        rule = OptionSelectionRule(min_selections=2, max_selections=4)

        assert rule.validate_selection_count(1) is False
        assert rule.validate_selection_count(2) is True
        assert rule.validate_selection_count(3) is True
        assert rule.validate_selection_count(4) is True
        assert rule.validate_selection_count(5) is False

    def test_invalid_rule_parameters_raise_error(self) -> None:
        """Parámetros incompatibles o negativos son estrictamente rechazados."""
        # min < 0
        with pytest.raises(InvalidOptionSelectionError, match="min_selections must be >= 0"):
            OptionSelectionRule(min_selections=-1, max_selections=2)

        # max < 1
        with pytest.raises(InvalidOptionSelectionError, match="max_selections must be >= 1"):
            OptionSelectionRule(min_selections=0, max_selections=0)

        # max < min
        with pytest.raises(InvalidOptionSelectionError, match="cannot be less than min_selections"):
            OptionSelectionRule(min_selections=3, max_selections=2)

        # Tipos no enteros
        with pytest.raises(InvalidOptionSelectionError, match="must be an integer"):
            OptionSelectionRule(min_selections="1", max_selections=2)  # type: ignore

        with pytest.raises(InvalidOptionSelectionError, match="must be an integer"):
            OptionSelectionRule(min_selections=True, max_selections=2)  # type: ignore


# ==============================================================================
# 2. VALIDACIÓN DE OPCIONES DEFAULT EN GRUPOS DE OPCIONES
# ==============================================================================

class TestOptionGroupDefaultsValidation:
    """Verificación de que los grupos requeridos exigen al menos una opción default."""

    def test_required_group_missing_default_raises_error(self) -> None:
        """Un grupo con seleccion_minima >= 1 sin opción default es rechazado."""
        og_svc = OptionGroupService()

        with pytest.raises(InvalidOptionSelectionError) as exc_info:
            og_svc.create_option_group(
                nombre="Guarniciones Sin Default",
                seleccion_minima=1,
                seleccion_maxima=2,
                items=[
                    OptionItemDTO(producto_id=10, es_opcion_default=False),
                    OptionItemDTO(producto_id=11, es_opcion_default=False),
                ],
                tenant_id="tenant_def_test",
            )
        assert "must have at least one default option" in str(exc_info.value)

    def test_required_group_with_default_succeeds(self) -> None:
        """Un grupo requerido con al menos un default es creado correctamente."""
        og_svc = OptionGroupService()
        grp = og_svc.create_option_group(
            nombre="Guarniciones Con Default",
            seleccion_minima=1,
            seleccion_maxima=2,
            items=[
                OptionItemDTO(producto_id=10, es_opcion_default=True),
                OptionItemDTO(producto_id=11, es_opcion_default=False),
            ],
            tenant_id="tenant_def_test",
        )
        assert grp.id is not None
        assert grp.seleccion_minima == 1
        assert any(it.es_opcion_default for it in grp.items)

    def test_optional_group_can_omit_defaults(self) -> None:
        """Un grupo enteramente opcional (min=0) no está forzado a tener default."""
        og_svc = OptionGroupService()
        grp = og_svc.create_option_group(
            nombre="Toppings Extras Opcionales",
            seleccion_minima=0,
            seleccion_maxima=3,
            items=[
                OptionItemDTO(producto_id=20, es_opcion_default=False),
                OptionItemDTO(producto_id=21, es_opcion_default=False),
            ],
            tenant_id="tenant_def_test",
        )
        assert grp.id is not None
        assert grp.seleccion_minima == 0
        assert not any(it.es_opcion_default for it in grp.items)


# ==============================================================================
# 3. RESTRICCIÓN DE REPETICIÓN (permite_repetir) EN SIMULACIÓN
# ==============================================================================

class TestOptionRepeatabilityRestriction:
    """Verificación del control de selecciones duplicadas según permite_repetir."""

    def _setup_simulator(self, permite_repetir: bool) -> tuple[RecipeCostSimulatorService, int, list[int]]:
        og_svc = OptionGroupService()
        recipe_svc = RecipeService(option_group_service=og_svc)
        sim_svc = RecipeCostSimulatorService(recipe_service=recipe_svc)
        tenant = "tenant_repeat_test"

        recipe_svc.set_ingredient_cost(101, Decimal("100.0000"))
        recipe_svc.set_ingredient_cost(201, Decimal("300.0000"))
        recipe_svc.set_ingredient_cost(202, Decimal("400.0000"))

        grp = og_svc.create_option_group(
            nombre="Salsas Adicionales",
            seleccion_minima=0,
            seleccion_maxima=3,
            permite_repetir=permite_repetir,
            items=[
                OptionItemDTO(producto_id=201, es_opcion_default=False, recargo_precio=Decimal("500.00")),
                OptionItemDTO(producto_id=202, es_opcion_default=False, recargo_precio=Decimal("600.00")),
            ],
            tenant_id=tenant,
        )

        receta = recipe_svc.create_recipe(
            codigo="REC-BASE-REPEAT",
            nombre="Alitas Crujientes",
            precio_venta_neto=Decimal("4000.00"),
            ingredientes=[
                RecipeIngredientDTO(producto_id=101, cantidad_receta=Decimal("2.0000")),
            ],
            grupos_opciones=[
                RecipeOptionGroupLinkDTO(grupo_id=grp.id, es_requerido=False),
            ],
            tenant_id=tenant,
        )

        item_ids = [it.id for it in grp.items if it.id is not None]
        return sim_svc, receta.id, item_ids

    def test_disallow_repeat_blocks_duplicate_selection(self) -> None:
        """Cuando permite_repetir=False, seleccionar el mismo ítem 2 veces lanza error."""
        sim_svc, recipe_id, item_ids = self._setup_simulator(permite_repetir=False)
        item1 = item_ids[0]

        # Seleccionar dos veces item1
        with pytest.raises(InvalidOptionSelectionError, match="cannot be selected multiple times"):
            sim_svc.simulate_cost(
                recipe_id=recipe_id,
                selected_option_item_ids=[item1, item1],
                tenant_id="tenant_repeat_test",
            )

    def test_allow_repeat_permits_duplicate_selection(self) -> None:
        """Cuando permite_repetir=True, seleccionar el mismo ítem repetido pasa exitosamente."""
        sim_svc, recipe_id, item_ids = self._setup_simulator(permite_repetir=True)
        item1 = item_ids[0]

        # Seleccionar 3 veces item1 (hasta seleccion_maxima=3)
        res = sim_svc.simulate_cost(
            recipe_id=recipe_id,
            selected_option_item_ids=[item1, item1, item1],
            tenant_id="tenant_repeat_test",
        )
        assert res.recipe_id == recipe_id
        # Cada item1 tiene recargo de 500 -> total surcharge = 1500
        assert res.total_surcharge == Decimal("1500.00")
        assert len(res.selected_options) == 3

    def test_allow_repeat_exceeding_max_selections_raises_error(self) -> None:
        """Aunque permita repetir, superar seleccion_maxima lanza error."""
        sim_svc, recipe_id, item_ids = self._setup_simulator(permite_repetir=True)
        item1 = item_ids[0]

        # Seleccionar 4 veces (max es 3)
        with pytest.raises(InvalidOptionSelectionError, match="allows at most 3 selection"):
            sim_svc.simulate_cost(
                recipe_id=recipe_id,
                selected_option_item_ids=[item1, item1, item1, item1],
                tenant_id="tenant_repeat_test",
            )


# ==============================================================================
# 4. RECARGOS DE PRECIOS Y CÁLCULOS FINANCIEROS EN SIMULACIÓN
# ==============================================================================

class TestOptionSurchargesAndFinancialImpact:
    """Pruebas de recargos de precios en opciones dinámicas y cálculo de precios netos y brutos."""

    def test_reject_negative_price_surcharges(self) -> None:
        """Un recargo negativo debe ser rechazado en la creación del ítem del grupo."""
        og_svc = OptionGroupService()
        with pytest.raises(InvalidOptionSelectionError, match="surcharge cannot be negative"):
            og_svc.create_option_group(
                nombre="Grupo Con Recargo Negativo",
                seleccion_minima=0,
                seleccion_maxima=1,
                items=[
                    OptionItemDTO(
                        producto_id=1,
                        recargo_precio=Decimal("-200.00"),  # Inválido
                    ),
                ],
                tenant_id="tenant_surcharges",
            )

    def test_surcharges_correctly_increase_net_and_gross_prices(self) -> None:
        """
        Verificación de que los recargos aumentan el precio neto y el precio bruto con IVA (19%):
        Precio base neto: $5.000
        Recargo ítem 1: $800
        Recargo ítem 2: $400
        Precio neto efectivo: $6.200
        Precio bruto efectivo: round(6.200 * 1.19) = $7.378
        Margen monto: precio neto efectivo - costo porcion
        """
        og_svc = OptionGroupService()
        recipe_svc = RecipeService(option_group_service=og_svc)
        sim_svc = RecipeCostSimulatorService(recipe_service=recipe_svc)
        tenant = "tenant_fin_test"

        recipe_svc.set_ingredient_cost(1, Decimal("1000.0000"))
        recipe_svc.set_ingredient_cost(10, Decimal("500.0000"))
        recipe_svc.set_ingredient_cost(20, Decimal("300.0000"))

        grp = og_svc.create_option_group(
            nombre="Proteínas y Quesos",
            seleccion_minima=1,
            seleccion_maxima=2,
            permite_repetir=False,
            items=[
                OptionItemDTO(producto_id=10, es_opcion_default=True, recargo_precio=Decimal("800.00")),
                OptionItemDTO(producto_id=20, es_opcion_default=False, recargo_precio=Decimal("400.00")),
            ],
            tenant_id=tenant,
        )

        receta = recipe_svc.create_recipe(
            codigo="REC-HAMBURGER",
            nombre="Hamburguesa Especial",
            precio_venta_neto=Decimal("5000.00"),
            iva_porcentaje=Decimal("19.00"),
            porciones_rendimiento=Decimal("1.0000"),
            ingredientes=[
                RecipeIngredientDTO(producto_id=1, cantidad_receta=Decimal("1.0000")),
            ],
            grupos_opciones=[
                RecipeOptionGroupLinkDTO(grupo_id=grp.id, es_requerido=True),
            ],
            tenant_id=tenant,
        )

        items_map = {it.producto_id: it.id for it in grp.items}
        item_10 = items_map[10]
        item_20 = items_map[20]

        # Simular con ambas opciones seleccionadas
        res = sim_svc.simulate_cost(
            recipe_id=receta.id,
            selected_option_item_ids=[item_10, item_20],
            tenant_id=tenant,
        )

        # Recargos: 800 + 400 = 1200
        assert res.total_surcharge == Decimal("1200.00")
        assert res.effective_net_price == Decimal("6200.00")
        assert res.effective_gross_price == Decimal("7378.00")

        # Costos: fijo=1000, opciones=500+300=800 -> total=1800
        assert res.total_cost == Decimal("1800.0000")
        assert res.portion_cost == Decimal("1800.0000")

        # Margen: 6200 - 1800 = 4400.00
        assert res.margin_amount == Decimal("4400.00")
        # Margen %: 4400 / 6200 * 100 = 70.97%
        assert res.margin_pct == Decimal("70.97")
        # Food Cost %: 1800 / 6200 * 100 = 29.03%
        assert res.food_cost_pct == Decimal("29.03")

        # Invariante 100%: 70.97 + 29.03 == 100.00
        assert res.margin_pct + res.food_cost_pct == Decimal("100.00")

    def test_foreign_option_item_is_rejected_in_simulation(self) -> None:
        """Seleccionar un ítem que no pertenece a ningún grupo de la receta lanza error controlado."""
        og_svc = OptionGroupService()
        recipe_svc = RecipeService(option_group_service=og_svc)
        sim_svc = RecipeCostSimulatorService(recipe_service=recipe_svc)
        tenant = "tenant_foreign"

        receta = recipe_svc.create_recipe(
            codigo="REC-SIMPLE",
            nombre="Receta Simple",
            precio_venta_neto=Decimal("1000.00"),
            tenant_id=tenant,
        )

        with pytest.raises(InvalidOptionSelectionError, match="does not belong to any option group"):
            sim_svc.simulate_cost(
                recipe_id=receta.id,
                selected_option_item_ids=[99999],
                tenant_id=tenant,
            )


# ==============================================================================
# 5. COMBOS DINÁMICOS Y CONTROL DE USO DE GRUPOS DE OPCIONES
# ==============================================================================

class TestDynamicCombosAndOptionGroupUsage:
    """Pruebas de Combos con grupos de opciones y protección de eliminación en uso."""

    def test_combo_with_option_groups_is_automatically_dynamic(self) -> None:
        """Un combo que contiene vínculos a grupos de opciones se marca es_dinamico=True."""
        og_svc = OptionGroupService()
        recipe_svc = RecipeService(option_group_service=og_svc)
        combo_svc = ComboService(recipe_service=recipe_svc, option_group_service=og_svc)
        tenant = "tenant_combo_dyn"

        grp = og_svc.create_option_group(
            nombre="Bebida a Elección",
            seleccion_minima=1,
            seleccion_maxima=1,
            items=[
                OptionItemDTO(producto_id=50, es_opcion_default=True),
                OptionItemDTO(producto_id=51, es_opcion_default=False),
            ],
            tenant_id=tenant,
        )

        combo = combo_svc.create_combo(
            codigo="CMB-DYN-01",
            nombre="Menú Ejecutivo Dinámico",
            precio_venta_neto=Decimal("7500.00"),
            grupos_opciones=[
                ComboOptionGroupLinkDTO(grupo_id=grp.id, es_requerido=True),
            ],
            tenant_id=tenant,
        )

        assert combo.es_dinamico is True

    def test_option_group_in_use_cannot_be_deleted(self) -> None:
        """Un grupo de opciones vinculado a una receta o combo no puede ser eliminado."""
        og_svc = OptionGroupService()
        recipe_svc = RecipeService(option_group_service=og_svc)
        tenant = "tenant_in_use"

        grp = og_svc.create_option_group(
            nombre="Grupo Protegido",
            seleccion_minima=1,
            seleccion_maxima=1,
            items=[
                OptionItemDTO(producto_id=1, es_opcion_default=True),
            ],
            tenant_id=tenant,
        )

        # Vincular a receta
        recipe_svc.create_recipe(
            codigo="REC-PROTECTED",
            nombre="Receta con Grupo Protegido",
            grupos_opciones=[
                RecipeOptionGroupLinkDTO(grupo_id=grp.id),
            ],
            tenant_id=tenant,
        )

        assert og_svc.is_in_use(grp.id) is True

        with pytest.raises(OptionGroupInUseError, match="currently linked to active recipes or combos"):
            og_svc.delete_option_group(grp.id, tenant_id=tenant)
