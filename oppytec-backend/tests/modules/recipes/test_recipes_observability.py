"""
oppytec-backend/tests/modules/recipes/test_recipes_observability.py
Suite de Pruebas de Observabilidad 4-Pilares para Recetas, Escandallos, Fichas de Cocina y Combos (Fase 7.3):
- Emisión y captura determinista de spans OpenTelemetry en InMemorySpanExporter:
  * `recipe.escandallo.calculate` (RecipeService)
  * `recipe.cycle_detection.run` (RecipeService / cycle_detector.py)
  * `recipe.kitchen_sheet.generate` (RecipeService.generate_kitchen_sheet)
  * `combo.availability.check` (ComboService)
- Verificación de atributos de contexto (`tenant_id`, `oppytec.tenant_id`, `recipe_id`, `combo_id`, `is_dynamic`, `allergen_count`).
- Verificación de métricas operativas (`RecipeOperationMetric`).
- Verificación estricta de enmascaramiento y ausencia de PII (emails, RUTs, teléfonos, tarjetas, tokens, contraseñas)
  en notas de ingredientes, instrucciones de preparación, metadatos de spans, logs estructurados y eventos Sentry.
"""
from __future__ import annotations

import json
from decimal import Decimal

import pytest
from pydantic import SecretStr

from src.core.observability import (
    REDACTED_MARKER,
    clear_in_memory_inventory_metrics,
    clear_in_memory_recipe_metrics,
    format_structured_log,
    get_in_memory_exporter,
    get_in_memory_recipe_metrics,
    scrub_pii_text,
    scrub_sentry_event,
    scrub_telemetry_payload,
)
from src.modules.recipes.application.combo_service import (
    ComboItemDTO,
    ComboOptionGroupLinkDTO,
    ComboService,
)
from src.modules.recipes.application.option_group_service import (
    OptionGroupItemDTO,
    OptionGroupService,
)
from src.modules.recipes.application.recipe_service import (
    RecipeIngredientDTO,
    RecipeOptionGroupLinkDTO,
    RecipeService,
)
from src.modules.recipes.domain.cycle_detector import check_recipe_cycles
from src.modules.recipes.domain.exceptions import (
    InvalidYieldError,
    RecipeCycleError,
)

pytestmark = pytest.mark.unit

TENANT_OBS_ID = "tenant_recipes_obs_01"


@pytest.fixture(autouse=True)
def _clean_observability_state() -> None:
    """Limpia los spans y métricas en memoria antes de cada test."""
    get_in_memory_exporter().clear()
    clear_in_memory_inventory_metrics()
    clear_in_memory_recipe_metrics()


class TestRecipesOpenTelemetrySpans:
    """Verifica la emisión, atributos de contexto y métricas de los 4 spans críticos del módulo."""

    def test_recipe_escandallo_calculate_span_and_context_attributes(self) -> None:
        """
        Verifica que `recipe.escandallo.calculate` se emita con `tenant_id`, `recipe_id`,
        `is_dynamic`, `allergen_count` y desglose financiero en Decimal.
        """
        opt_svc = OptionGroupService()
        rec_svc = RecipeService(option_group_service=opt_svc)
        exporter = get_in_memory_exporter()

        # Configurar insumos con costos PPP y alérgenos normados
        rec_svc.set_ingredient_cost(
            101, Decimal("5000.00"), "Harina panadera", "kg", allergens=["GLUTEN"]
        )
        rec_svc.set_ingredient_cost(
            102, Decimal("1200.00"), "Leche entera", "lt", allergens=["MILK"]
        )
        rec_svc.set_ingredient_cost(
            103, Decimal("800.00"), "Maní tostado", "gr", allergens=["PEANUTS"]
        )

        # Crear grupo de opciones dinámico
        grp = opt_svc.create_option_group(
            nombre="Topping Elección",
            seleccion_minima=1,
            seleccion_maxima=1,
            items=[
                OptionGroupItemDTO(
                    producto_id=102,
                    nombre="Extra Leche",
                    cantidad=Decimal("0.2000"),
                    es_opcion_default=True,
                ),
                OptionGroupItemDTO(
                    producto_id=103,
                    nombre="Extra Maní",
                    cantidad=Decimal("0.5000"),
                    es_opcion_default=False,
                    recargo_precio=Decimal("500.00"),
                ),
            ],
            tenant_id=TENANT_OBS_ID,
        )
        exporter.clear()
        clear_in_memory_recipe_metrics()

        recipe = rec_svc.create_recipe(
            codigo="REC-OBS-001",
            nombre="Pan Brioche Especial",
            porciones_rendimiento=Decimal("2.0000"),
            precio_venta_neto=Decimal("6000.00"),
            ingredientes=[
                RecipeIngredientDTO(
                    producto_id=101,
                    cantidad_receta=Decimal("0.5000"),
                    porcentaje_merma=Decimal("10.00"),
                )
            ],
            grupos_opciones=[
                RecipeOptionGroupLinkDTO(grupo_id=grp.id, orden=1, es_requerido=True)
            ],
            tenant_id=TENANT_OBS_ID,
        )

        spans = exporter.get_finished_spans()
        escandallo_spans = [s for s in spans if s.name == "recipe.escandallo.calculate"]
        assert len(escandallo_spans) == 1

        span = escandallo_spans[0]
        assert span.status_code == 200
        assert span.attributes["tenant_id"] == TENANT_OBS_ID
        assert span.attributes["oppytec.tenant_id"] == TENANT_OBS_ID
        assert span.attributes["recipe_id"] == recipe.id
        assert span.attributes["is_dynamic"] is True
        assert span.attributes["allergen_count"] == 3  # GLUTEN, MILK, PEANUTS
        assert span.attributes["ingredients_count"] == 1
        assert span.attributes["option_groups_count"] == 1
        assert "costo_total_calculado" in span.attributes
        assert "costo_porcion" in span.attributes
        assert "costo_peor_caso" in span.attributes
        assert "costo_mejor_caso" in span.attributes

        # Verificar métrica operativa registrada
        metrics = get_in_memory_recipe_metrics()
        esc_metrics = [m for m in metrics if m.operation == "recipe.escandallo.calculate"]
        assert len(esc_metrics) == 1
        assert esc_metrics[0].status == "SUCCESS"
        assert esc_metrics[0].tenant_id == TENANT_OBS_ID
        assert esc_metrics[0].recipe_id == recipe.id
        assert esc_metrics[0].is_dynamic is True
        assert esc_metrics[0].allergen_count == 3

    def test_recipe_cycle_detection_run_span_success_and_cycle_error(self) -> None:
        """
        Verifica que `recipe.cycle_detection.run` se emita tanto en validaciones DAG exitosas
        como cuando se detecta una dependencia cíclica (registrando status 422 y ruta del ciclo).
        """
        rec_svc = RecipeService()
        exporter = get_in_memory_exporter()

        rec_svc.set_ingredient_cost(201, Decimal("1000.00"), "Agua filtrada", "lt")

        # Crear Subreceta A y Subreceta B (A -> B válido)
        sub_b = rec_svc.create_recipe(
            codigo="SUB-B",
            nombre="Base Caldo B",
            es_subreceta=True,
            ingredientes=[
                RecipeIngredientDTO(producto_id=201, cantidad_receta=Decimal("1.0000"))
            ],
            tenant_id=TENANT_OBS_ID,
        )
        exporter.clear()
        clear_in_memory_recipe_metrics()

        sub_a = rec_svc.create_recipe(
            codigo="SUB-A",
            nombre="Salsa Madre A",
            es_subreceta=True,
            ingredientes=[
                RecipeIngredientDTO(subreceta_id=sub_b.id, cantidad_receta=Decimal("1.0000"))
            ],
            tenant_id=TENANT_OBS_ID,
        )

        spans = exporter.get_finished_spans()
        cycle_spans = [s for s in spans if s.name == "recipe.cycle_detection.run"]
        assert len(cycle_spans) == 1
        ok_span = cycle_spans[0]
        assert ok_span.status_code == 200
        assert ok_span.attributes["tenant_id"] == TENANT_OBS_ID
        assert ok_span.attributes["oppytec.tenant_id"] == TENANT_OBS_ID
        assert ok_span.attributes["recipe_id"] == sub_a.id
        assert ok_span.attributes["cycle_detected"] is False
        assert int(ok_span.attributes["visited_nodes_count"]) >= 2

        # Ahora intentar crear un ciclo B -> A (cuando A ya depende de B)
        exporter.clear()
        clear_in_memory_recipe_metrics()

        with pytest.raises(RecipeCycleError):
            rec_svc.update_recipe(
                sub_b.id,
                ingredientes=[
                    RecipeIngredientDTO(subreceta_id=sub_a.id, cantidad_receta=Decimal("1.0000"))
                ],
                tenant_id=TENANT_OBS_ID,
            )

        err_spans = [s for s in exporter.get_finished_spans() if s.name == "recipe.cycle_detection.run"]
        assert len(err_spans) == 1
        err_span = err_spans[0]
        assert err_span.status_code == 422
        assert err_span.attributes["tenant_id"] == TENANT_OBS_ID
        assert err_span.attributes["recipe_id"] == sub_b.id
        assert err_span.attributes["cycle_detected"] is True
        assert "->" in str(err_span.attributes["cycle_path"])

        # Verificar invocación directa a check_recipe_cycles
        exporter.clear()
        check_recipe_cycles(10, {10: [20], 20: [30], 30: []}, tenant_id=TENANT_OBS_ID)
        direct_spans = [s for s in exporter.get_finished_spans() if s.name == "recipe.cycle_detection.run"]
        assert len(direct_spans) == 1
        assert direct_spans[0].attributes["recipe_id"] == 10
        assert direct_spans[0].attributes["tenant_id"] == TENANT_OBS_ID

    def test_recipe_kitchen_sheet_generate_span_and_attributes(self) -> None:
        """
        Verifica que `recipe.kitchen_sheet.generate` se emita al generar la ficha técnica
        de cocina, incluyendo `tenant_id`, `recipe_id`, `is_dynamic`, `allergen_count` y escalamiento.
        """
        rec_svc = RecipeService()
        exporter = get_in_memory_exporter()

        rec_svc.set_ingredient_cost(
            301, Decimal("4500.00"), "Filete Salmón", "kg", allergens=["FISH"]
        )
        rec_svc.set_ingredient_cost(
            302, Decimal("2200.00"), "Crema Fresca", "lt", allergens=["MILK"]
        )

        recipe = rec_svc.create_recipe(
            codigo="REC-SALMON",
            nombre="Salmón a la Crema",
            porciones_rendimiento=Decimal("4.0000"),
            precio_venta_neto=Decimal("12900.00"),
            preparacion="Sellar el salmón 4 min por lado y reducir con crema.",
            tiempo_preparacion_minutos=20,
            ingredientes=[
                RecipeIngredientDTO(
                    producto_id=301,
                    cantidad_receta=Decimal("0.8000"),
                    porcentaje_merma=Decimal("12.00"),
                ),
                RecipeIngredientDTO(
                    producto_id=302,
                    cantidad_receta=Decimal("0.4000"),
                    porcentaje_merma=Decimal("0.00"),
                ),
            ],
            tenant_id=TENANT_OBS_ID,
        )

        exporter.clear()
        clear_in_memory_recipe_metrics()

        sheet = rec_svc.generate_kitchen_sheet(
            recipe_id=recipe.id,
            servings=Decimal("20.0000"),
            tenant_id=TENANT_OBS_ID,
        )
        assert sheet.recipe_id == recipe.id
        assert sheet.factor_escalamiento == Decimal("5.0000")
        assert len(sheet.alergenos_consolidados) == 2

        spans = exporter.get_finished_spans()
        ks_spans = [s for s in spans if s.name == "recipe.kitchen_sheet.generate"]
        assert len(ks_spans) == 1
        span = ks_spans[0]

        assert span.status_code == 200
        assert span.attributes["tenant_id"] == TENANT_OBS_ID
        assert span.attributes["oppytec.tenant_id"] == TENANT_OBS_ID
        assert span.attributes["recipe_id"] == recipe.id
        assert span.attributes["is_dynamic"] is False
        assert span.attributes["allergen_count"] == 2
        assert span.attributes["porciones_base"] == "4.0000"
        assert span.attributes["porciones_solicitadas"] == "20.0000"
        assert span.attributes["factor_escalamiento"] == "5.0000"
        assert span.attributes["ingredients_count"] == 2

        # Verificar captura de excepción ante porciones inválidas (<= 0)
        exporter.clear()
        with pytest.raises(InvalidYieldError):
            rec_svc.generate_kitchen_sheet(
                recipe_id=recipe.id,
                servings=Decimal("0"),
                tenant_id=TENANT_OBS_ID,
            )
        err_spans = [s for s in exporter.get_finished_spans() if s.name == "recipe.kitchen_sheet.generate"]
        assert len(err_spans) == 1
        assert err_spans[0].status_code == 422

    def test_combo_availability_check_span_and_attributes(self) -> None:
        """
        Verifica que `combo.availability.check` se emita con `tenant_id`, `combo_id`,
        `is_dynamic`, `allergen_count`, `available_portions` e `is_available`.
        """
        opt_svc = OptionGroupService()
        rec_svc = RecipeService(option_group_service=opt_svc)
        combo_svc = ComboService(recipe_service=rec_svc, option_group_service=opt_svc)
        exporter = get_in_memory_exporter()

        rec_svc.set_ingredient_cost(
            401, Decimal("1500.00"), "Pan Brioche Burger", "und", allergens=["GLUTEN", "EGGS"]
        )
        rec_svc.set_ingredient_cost(
            402, Decimal("800.00"), "Bebida Lata 350ml", "und"
        )

        burger_rec = rec_svc.create_recipe(
            codigo="REC-BURGER",
            nombre="Hamburguesa Clásica",
            ingredientes=[
                RecipeIngredientDTO(producto_id=401, cantidad_receta=Decimal("1.0000"))
            ],
            tenant_id=TENANT_OBS_ID,
        )

        opt_grp = opt_svc.create_option_group(
            nombre="Bebida del Combo",
            seleccion_minima=1,
            seleccion_maxima=1,
            items=[
                OptionGroupItemDTO(
                    producto_id=402,
                    nombre="Cola Regular",
                    cantidad=Decimal("1.0000"),
                    es_opcion_default=True,
                )
            ],
            tenant_id=TENANT_OBS_ID,
        )

        # Configurar stock disponible en bodega: 12 panes, 20 bebidas
        combo_svc.set_product_stock_balance(401, Decimal("12.0000"))
        combo_svc.set_product_stock_balance(402, Decimal("20.0000"))

        exporter.clear()
        clear_in_memory_recipe_metrics()

        combo = combo_svc.create_combo(
            nombre="Combo Burger Dinámico",
            codigo="CMB-BURGER-01",
            precio_venta_neto=Decimal("7500.00"),
            items=[
                ComboItemDTO(receta_id=burger_rec.id, cantidad=Decimal("1.0000"))
            ],
            grupos_opciones=[
                ComboOptionGroupLinkDTO(grupo_id=opt_grp.id, orden=1, es_requerido=True)
            ],
            tenant_id=TENANT_OBS_ID,
        )

        spans = [s for s in exporter.get_finished_spans() if s.name == "combo.availability.check"]
        assert len(spans) == 1
        span = spans[0]
        assert span.status_code == 200
        assert span.attributes["tenant_id"] == TENANT_OBS_ID
        assert span.attributes["oppytec.tenant_id"] == TENANT_OBS_ID
        assert span.attributes["combo_id"] == combo.id
        assert span.attributes["is_dynamic"] is True
        assert span.attributes["allergen_count"] == 2  # GLUTEN, EGGS
        assert span.attributes["items_count"] == 1
        assert span.attributes["available_portions"] == 12
        assert span.attributes["is_available"] is True

        # Simular agotamiento de stock (0 unidades de pan) y verificar check_availability
        exporter.clear()
        avail_portions, is_avail = combo_svc.check_availability(
            combo.id,
            tenant_id=TENANT_OBS_ID,
            stock_balances={401: Decimal("0.0000"), 402: Decimal("10.0000")},
        )
        assert avail_portions == 0
        assert is_avail is False

        check_spans = [s for s in exporter.get_finished_spans() if s.name == "combo.availability.check"]
        assert len(check_spans) == 1
        assert check_spans[0].attributes["combo_id"] == combo.id
        assert check_spans[0].attributes["available_portions"] == 0
        assert check_spans[0].attributes["is_available"] is False


class TestRecipesPIIScrubbingAndDataProtection:
    """
    Verifica la ausencia y enmascaramiento determinista de PII (emails, RUTs, teléfonos,
    tarjetas de crédito y secretos) en notas de recetas/combos, spans OTel, logs y Sentry.
    """

    def test_pii_scrubbing_in_recipe_notes_kitchen_sheet_and_otel_spans(self) -> None:
        """
        Verifica que si las notas de un ingrediente, la preparación o la descripción contienen
        datos personales (email, RUT chileno, teléfono, password/token), los spans OpenTelemetry
        y la ficha técnica de cocina enmascaren el 100% del PII con `[REDACTED_PII]`.
        """
        rec_svc = RecipeService()
        exporter = get_in_memory_exporter()

        rec_svc.set_ingredient_cost(
            501, Decimal("9000.00"), "Pollo King Marinado", "kg", allergens=["SOY"]
        )

        raw_ing_note = (
            "Comprar a Pollo King contacto ventas.secreto@polloking.cl "
            "RUT 76.543.210-K tel +56 9 8765 4321 password=SuperSecretChef123"
        )
        raw_prep_note = (
            "Marinar por 2 horas. Dudas al chef.ejecutivo@oppytec.cl o RUT 12.345.678-9."
        )

        recipe = rec_svc.create_recipe(
            codigo="REC-PII-TEST",
            nombre="Pollo King al Horno",
            descripcion="Receta autorizada por gerencia@oppytec.cl",
            preparacion=raw_prep_note,
            porciones_rendimiento=Decimal("1.0000"),
            precio_venta_neto=Decimal("10000.00"),
            ingredientes=[
                RecipeIngredientDTO(
                    producto_id=501,
                    cantidad_receta=Decimal("1.0000"),
                    porcentaje_merma=Decimal("5.00"),
                    notas=raw_ing_note,
                )
            ],
            tenant_id=TENANT_OBS_ID,
        )

        sheet = rec_svc.generate_kitchen_sheet(
            recipe_id=recipe.id,
            servings=Decimal("2.0000"),
            tenant_id=TENANT_OBS_ID,
        )

        # 1. Verificar ausencia total de PII en todos los spans exportados
        spans = exporter.get_finished_spans()
        assert len(spans) >= 2
        for span in spans:
            serialized_attrs = json.dumps(span.attributes, ensure_ascii=False)
            assert "ventas.secreto@polloking.cl" not in serialized_attrs
            assert "chef.ejecutivo@oppytec.cl" not in serialized_attrs
            assert "gerencia@oppytec.cl" not in serialized_attrs
            assert "76.543.210-K" not in serialized_attrs
            assert "12.345.678-9" not in serialized_attrs
            assert "+56 9 8765 4321" not in serialized_attrs
            assert "SuperSecretChef123" not in serialized_attrs

        # 2. Verificar presencia de marcador [REDACTED_PII] y preservación de nombre comercial "Pollo King"
        esc_span = next(s for s in spans if s.name == "recipe.escandallo.calculate")
        assert REDACTED_MARKER in str(esc_span.attributes.get("notes_scrubbed", ""))
        assert "Pollo King" in str(esc_span.attributes.get("notes_scrubbed", ""))

        ks_span = next(s for s in spans if s.name == "recipe.kitchen_sheet.generate")
        assert REDACTED_MARKER in str(ks_span.attributes.get("notes_scrubbed", ""))

        # 3. Verificar que la ficha técnica de cocina también tenga notas e instrucciones sanitizadas
        assert sheet.ingredientes_fijos[0].notas is not None
        assert "ventas.secreto@polloking.cl" not in sheet.ingredientes_fijos[0].notas
        assert "76.543.210-K" not in sheet.ingredientes_fijos[0].notas
        assert REDACTED_MARKER in sheet.ingredientes_fijos[0].notas
        assert "Pollo King" in sheet.ingredientes_fijos[0].notas

        assert sheet.preparacion is not None
        assert "chef.ejecutivo@oppytec.cl" not in sheet.preparacion
        assert "12.345.678-9" not in sheet.preparacion
        assert REDACTED_MARKER in sheet.preparacion

    def test_pii_scrubbing_in_combo_availability_and_sentry_payloads(self) -> None:
        """
        Verifica que `combo.availability.check`, `scrub_telemetry_payload`, `scrub_sentry_event`
        y `format_structured_log` enmascaren PII en metadatos y notas de combos.
        """
        rec_svc = RecipeService()
        combo_svc = ComboService(recipe_service=rec_svc)
        exporter = get_in_memory_exporter()

        rec_svc.set_ingredient_cost(601, Decimal("2000.00"), "Empanada Pino", "und")
        combo_svc.set_product_stock_balance(601, Decimal("50.0000"))

        combo = combo_svc.create_combo(
            nombre="Combo Dieciochero",
            codigo="CMB-PII-01",
            descripcion="Contacto proveedor: proveedor@empanadas.cl RUT 15.432.198-7",
            precio_venta_neto=Decimal("5000.00"),
            items=[ComboItemDTO(producto_id=601, cantidad=Decimal("2.0000"))],
            tenant_id=TENANT_OBS_ID,
        )

        combo_spans = [s for s in exporter.get_finished_spans() if s.name == "combo.availability.check"]
        assert len(combo_spans) == 1
        c_span = combo_spans[0]
        serialized = json.dumps(c_span.attributes, ensure_ascii=False)
        assert "proveedor@empanadas.cl" not in serialized
        assert "15.432.198-7" not in serialized
        assert REDACTED_MARKER in str(c_span.attributes.get("notes_scrubbed", ""))
        assert c_span.attributes["combo_id"] == combo.id

        # Validar scrub_sentry_event y format_structured_log con metadatos sensibles de recetas
        sentry_event: dict[str, object] = {
            "event_id": "evt_recipe_001",
            "tenant_id": TENANT_OBS_ID,
            "recipe_id": 99,
            "extra": {
                "supplier_name": "Pollo King",
                "email_contacto": "contacto@polloking.cl",
                "rut": "76.111.222-3",
                "api_key": SecretStr("sk-live-secret-recipe-key"),
                "kitchen_note": "Llamar a supervisor@cocina.cl o al +56 9 1234 5678",
            },
        }
        scrubbed_event = scrub_sentry_event(sentry_event)
        extra = scrubbed_event["extra"]
        assert isinstance(extra, dict)
        assert extra["supplier_name"] == "Pollo King"
        assert extra["email_contacto"] == REDACTED_MARKER
        assert extra["rut"] == REDACTED_MARKER
        assert extra["api_key"] == REDACTED_MARKER
        assert "supervisor@cocina.cl" not in str(extra["kitchen_note"])
        assert "+56 9 1234 5678" not in str(extra["kitchen_note"])
        assert REDACTED_MARKER in str(extra["kitchen_note"])

        structured_log = format_structured_log("INFO", "recipe.escandallo.calculate", sentry_event)
        assert "contacto@polloking.cl" not in structured_log
        assert "76.111.222-3" not in structured_log
        assert "sk-live-secret-recipe-key" not in structured_log
        assert "supervisor@cocina.cl" not in structured_log
        assert scrub_pii_text("Sin PII en texto culinario") == "Sin PII en texto culinario"
