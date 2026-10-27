"""
oppytec-backend/src/modules/recipes/application/recipe_service.py
Servicio de Aplicación para Gestión Transaccional de Recetas Gastronómicas, Escandallos Dinámicos,
Árbol de Sub-recetas, Detección de Ciclos DAG y Cálculo de Márgenes al PPP.
Cumple Clean Architecture, Regla Inmutable 02 (Decimal estricto, 0 floats) y RBAC de 3 niveles.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from src.core.observability import scrub_pii_text, trace_span
from src.modules.recipes.application.option_group_service import (
    OptionGroupDTO,
    OptionGroupService,
)
from src.modules.recipes.domain.allergens import (
    STANDARD_ALLERGENS,
    AllergenDefinition,
    get_allergen_definition,
    normalize_allergen_code,
    resolve_allergen_definitions,
)
from src.modules.recipes.domain.cycle_detector import check_recipe_cycles
from src.modules.recipes.domain.entities import (
    Receta as DomainReceta,
    RecetaGrupoOpcion as DomainRecetaGrupoOpcion,
    RecetaIngrediente as DomainRecetaIngrediente,
)
from src.modules.recipes.domain.exceptions import (
    InvalidOptionSelectionError,
    InvalidQuantityError,
    InvalidYieldError,
    PolymorphicReferenceError,
    RecipeCycleError,
    RecipeInUseError,
    RecipeNotFoundError,
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
    ServingYield,
)


@dataclass
class RecipeCategoryDTO:
    """DTO para categoría clasificatoria de recetas."""

    id: int
    nombre: str
    color: str | None = "#f59e0b"
    icono: str | None = "ChefHat"
    orden: int = 0
    tenant_id: str = "default"
    is_deleted: bool = False


@dataclass
class RecipeIngredientDTO:
    """DTO para ingrediente fijo del escandallo."""

    id: int | None = None
    producto_id: int | None = None
    subreceta_id: int | None = None
    cantidad_receta: Decimal = Decimal("1.0000")
    porcentaje_merma: Decimal = Decimal("0.00")
    bodega_consumo_id: int | None = None
    notas: str | None = None
    nombre: str | None = None
    unidad: str = "und"
    costo_unitario: Decimal = Decimal("0.00")
    costo_total: Decimal = Decimal("0.00")

    @property
    def target_type(self) -> str:
        return "subreceta" if self.subreceta_id is not None else "producto"


@dataclass
class RecipeOptionGroupLinkDTO:
    """DTO para vinculación de grupo de opciones a una receta."""

    grupo_id: int
    orden: int = 0
    es_requerido: bool = True
    grupo: OptionGroupDTO | None = None


@dataclass
class RecipeDTO:
    """DTO completo de receta gastronómica con escandallo calculado."""

    id: int
    codigo: str
    nombre: str
    descripcion: str | None = None
    categoria_receta_id: int | None = None
    categoria_nombre: str | None = None
    es_subreceta: bool = False
    es_dinamica: bool = False
    porciones_rendimiento: Decimal = Decimal("1.0000")
    costo_total_calculado: Decimal = Decimal("0.00")
    costo_porcion: Decimal = Decimal("0.00")
    costo_peor_caso: Decimal = Decimal("0.00")
    costo_mejor_caso: Decimal = Decimal("0.00")
    precio_venta_neto: Decimal = Decimal("0.00")
    precio_venta_bruto: Decimal = Decimal("0.00")
    iva_porcentaje: Decimal = Decimal("19.00")
    iva_incluido: bool = True
    margen_neto: Decimal = Decimal("0.00")
    margen_bruto: Decimal = Decimal("0.00")
    margen_pct: Decimal = Decimal("0.00")
    food_cost_pct: Decimal = Decimal("0.00")
    imagen_url: str | None = None
    preparacion: str | None = None
    video_url: str | None = None
    documento_url: str | None = None
    tiempo_preparacion_minutos: int | None = None
    ingredientes_fijos: list[RecipeIngredientDTO] = field(default_factory=list)
    grupos_opciones: list[RecipeOptionGroupLinkDTO] = field(default_factory=list)
    alergenos: list[AllergenDefinition] = field(default_factory=list)
    tenant_id: str = "default"
    is_deleted: bool = False


@dataclass
class KitchenSheetItemDTO:
    """Línea de ingrediente o subreceta en la ficha técnica de cocina con escalamiento y merma."""

    ingrediente_id: int | None = None
    producto_id: int | None = None
    subreceta_id: int | None = None
    nombre: str = ""
    target_type: str = "producto"
    unidad: str = "und"
    cantidad_neta_base: Decimal = Decimal("0.0000")
    cantidad_neta_escalada: Decimal = Decimal("0.0000")
    porcentaje_merma: Decimal = Decimal("0.00")
    cantidad_bruta_escalada: Decimal = Decimal("0.0000")
    notas: str | None = None
    alergenos: list[AllergenDefinition] = field(default_factory=list)
    subreceta_desglose: list[KitchenSheetItemDTO] = field(default_factory=list)


@dataclass
class KitchenSheetOptionItemDTO:
    """Opción individual dentro de un grupo dinámico en la ficha técnica de cocina."""

    item_id: int | None = None
    producto_id: int | None = None
    receta_id: int | None = None
    nombre: str = ""
    target_type: str = "producto"
    cantidad_base: Decimal = Decimal("1.0000")
    cantidad_escalada: Decimal = Decimal("1.0000")
    unidad: str = "und"
    es_opcion_default: bool = False
    recargo_precio: Decimal = Decimal("0.00")
    alergenos: list[AllergenDefinition] = field(default_factory=list)


@dataclass
class KitchenSheetOptionGroupDTO:
    """Grupo de modificadores u opciones dinámicas para la preparación en cocina."""

    grupo_id: int = 0
    grupo_nombre: str = ""
    seleccion_minima: int = 1
    seleccion_maxima: int = 1
    es_requerido: bool = True
    opciones: list[KitchenSheetOptionItemDTO] = field(default_factory=list)


@dataclass
class KitchenSheetDTO:
    """Ficha técnica de cocina escalada matemáticamente en Decimal estricto."""

    recipe_id: int
    codigo: str
    nombre: str
    descripcion: str | None = None
    categoria_nombre: str | None = None
    porciones_base: Decimal = Decimal("1.0000")
    porciones_solicitadas: Decimal = Decimal("1.0000")
    factor_escalamiento: Decimal = Decimal("1.0000")
    tiempo_preparacion_minutos: int | None = None
    preparacion: str | None = None
    video_url: str | None = None
    documento_url: str | None = None
    ingredientes_fijos: list[KitchenSheetItemDTO] = field(default_factory=list)
    grupos_opciones: list[KitchenSheetOptionGroupDTO] = field(default_factory=list)
    alergenos_consolidados: list[AllergenDefinition] = field(default_factory=list)


class RecipeService:
    """
    Servicio de Aplicación de Recetas y Escandallos Gastronómicos.
    Garantiza cálculo recursivo exacto en `Decimal`, autodetección de receta dinámica,
    prevención de dependencias cíclicas en DAG y control de borrado seguro.
    """

    def __init__(self, option_group_service: OptionGroupService | None = None) -> None:
        self.option_group_service = option_group_service or OptionGroupService()
        self._recipes: dict[tuple[str, int], RecipeDTO] = {}
        self._categories: dict[tuple[str, int], RecipeCategoryDTO] = {}
        self._ingredient_costs: dict[int, Decimal] = {}  # producto_id -> unit_cost PPP
        self._product_names: dict[int, str] = {}
        self._product_units: dict[int, str] = {}
        self._product_allergens: dict[int, list[str]] = {}  # producto_id -> [allergen_code, ...]
        self._recipe_allergens: dict[int, list[str]] = {}  # recipe_id -> [allergen_code, ...]
        self._next_recipe_id: int = 1
        self._next_category_id: int = 1
        self._next_ingredient_id: int = 1

    def reset(self) -> None:
        """Limpia todo el estado en memoria para pruebas."""
        self._recipes.clear()
        self._categories.clear()
        self._ingredient_costs.clear()
        self._product_names.clear()
        self._product_units.clear()
        self._product_allergens.clear()
        self._recipe_allergens.clear()
        self._next_recipe_id = 1
        self._next_category_id = 1
        self._next_ingredient_id = 1

    def set_ingredient_cost(
        self,
        producto_id: int,
        unit_cost: Decimal | str | int,
        nombre: str | None = None,
        unidad: str = "und",
        allergens: Sequence[str] | None = None,
    ) -> None:
        """Configura el costo PPP vigente, unidad, nombre y alérgenos de un producto."""
        dec_cost = Decimal(str(unit_cost))
        self._ingredient_costs[producto_id] = dec_cost
        if nombre:
            self._product_names[producto_id] = nombre
        self._product_units[producto_id] = unidad
        if allergens is not None:
            self.set_product_allergens(producto_id, allergens)

    def set_product_allergens(self, producto_id: int, allergens: Sequence[str]) -> None:
        """Asocia alérgenos normados a un insumo/producto del catálogo."""
        valid_codes = [normalize_allergen_code(a) for a in allergens]
        self._product_allergens[producto_id] = [c for c in valid_codes if c is not None]

    def get_product_allergens(self, producto_id: int) -> list[str]:
        """Obtiene los códigos de alérgenos registrados para un producto."""
        return list(self._product_allergens.get(producto_id, []))

    def set_recipe_allergens(self, recipe_id: int, allergens: Sequence[str]) -> None:
        """Asocia alérgenos explícitos adicionales a una receta."""
        valid_codes = [normalize_allergen_code(a) for a in allergens]
        self._recipe_allergens[recipe_id] = [c for c in valid_codes if c is not None]

    def get_ingredient_cost(self, producto_id: int) -> Decimal:
        """Devuelve el costo PPP vigente o Decimal('0.00')."""
        return self._ingredient_costs.get(producto_id, Decimal("0.00"))

    # =========================================================================
    # CATEGORÍAS DE RECETAS
    # =========================================================================

    def create_category(
        self,
        *,
        nombre: str,
        color: str | None = "#f59e0b",
        icono: str | None = "ChefHat",
        orden: int = 0,
        tenant_id: str = "default",
    ) -> RecipeCategoryDTO:
        cid = self._next_category_id
        self._next_category_id += 1
        cat = RecipeCategoryDTO(
            id=cid,
            nombre=nombre.strip(),
            color=color,
            icono=icono,
            orden=orden,
            tenant_id=tenant_id,
        )
        self._categories[(tenant_id, cid)] = cat
        return cat

    def list_categories(self, tenant_id: str = "default") -> list[RecipeCategoryDTO]:
        cats = [
            c for (t_id, _), c in self._categories.items()
            if t_id == tenant_id and not c.is_deleted
        ]
        cats.sort(key=lambda c: (c.orden, c.nombre))
        return cats

    def get_category(self, category_id: int, tenant_id: str = "default") -> RecipeCategoryDTO | None:
        cat = self._categories.get((tenant_id, category_id))
        if cat and not cat.is_deleted:
            return cat
        return None

    # =========================================================================
    # DETECCIÓN DE CICLOS Y ÁRBOL DE DEPENDENCIAS
    # =========================================================================

    def _get_subrecipe_ids_tree(self, tenant_id: str) -> dict[int, list[int]]:
        """Construye el grafo actual de dependencias {recipe_id: [subreceta_id, ...]} para el tenant."""
        tree: dict[int, list[int]] = {}
        for (t_id, r_id), r in self._recipes.items():
            if t_id == tenant_id and not r.is_deleted:
                sub_ids: list[int] = []
                for ing in r.ingredientes_fijos:
                    if ing.subreceta_id is not None:
                        sub_ids.append(ing.subreceta_id)
                tree[r_id] = sub_ids
        return tree

    def _validate_cycles_for_recipe(
        self,
        recipe_id: int,
        ingredientes: Sequence[RecipeIngredientDTO],
        tenant_id: str,
    ) -> None:
        """Verifica que la asignación de ingredientes no introduzca dependencias cíclicas en el DAG."""
        current_tree = self._get_subrecipe_ids_tree(tenant_id)
        # Reemplazamos las subrecetas de recipe_id con las nuevas propuestas
        proposed_sub_ids = [
            ing.subreceta_id for ing in ingredientes if ing.subreceta_id is not None
        ]
        current_tree[recipe_id] = proposed_sub_ids

        # Verificamos ciclos desde el nodo modificado
        check_recipe_cycles(recipe_id, current_tree, tenant_id=tenant_id)

    def build_subrecipes_tree(self, recipe_id: int, tenant_id: str = "default") -> list[dict[str, Any]]:
        """Construye la representación jerárquica del árbol de sub-recetas alcanzables."""
        recipe = self.get_recipe(recipe_id, tenant_id)
        tree: list[dict[str, Any]] = []

        for ing in recipe.ingredientes_fijos:
            if ing.subreceta_id is not None:
                try:
                    sub = self.get_recipe(ing.subreceta_id, tenant_id)
                    node = {
                        "recipe_id": sub.id,
                        "codigo": sub.codigo,
                        "nombre": sub.nombre,
                        "cantidad": ing.cantidad_receta,
                        "unidad": ing.unidad,
                        "costo_porcion": sub.costo_porcion,
                        "costo_total": ing.costo_total,
                        "subrecipes": self.build_subrecipes_tree(sub.id, tenant_id),
                    }
                    tree.append(node)
                except RecipeNotFoundError:
                    continue
        return tree

    # =========================================================================
    # CÁLCULO DE ESCANDALLO
    # =========================================================================

    def _resolve_allergen_count_for_components(
        self,
        recipe_id: int | None,
        ingredientes: Sequence[RecipeIngredientDTO],
        grupos_links: Sequence[RecipeOptionGroupLinkDTO],
        tenant_id: str,
    ) -> int:
        """Calcula el conteo de alérgenos únicos presentes en los componentes para telemetría."""
        codes: set[str] = set()
        if recipe_id is not None:
            for c in self._recipe_allergens.get(recipe_id, []):
                codes.add(c)
        for ing in ingredientes:
            if ing.producto_id is not None:
                for c in self._product_allergens.get(ing.producto_id, []):
                    codes.add(c)
            elif ing.subreceta_id is not None:
                try:
                    for a_def in self._compute_recipe_allergens(ing.subreceta_id, tenant_id):
                        codes.add(a_def.code)
                except Exception:
                    continue
        for link in grupos_links:
            try:
                grp = self.option_group_service.get_option_group(link.grupo_id, tenant_id)
                for item in grp.items:
                    if item.producto_id is not None:
                        for c in self._product_allergens.get(item.producto_id, []):
                            codes.add(c)
                    elif item.receta_id is not None:
                        try:
                            for a_def in self._compute_recipe_allergens(item.receta_id, tenant_id):
                                codes.add(a_def.code)
                        except Exception:
                            continue
            except Exception:
                continue
        return len(resolve_allergen_definitions(list(codes)))

    def _calculate_escandallo_costs(
        self,
        recipe_id: int | None,
        ingredientes: list[RecipeIngredientDTO],
        grupos_links: list[RecipeOptionGroupLinkDTO],
        porciones_rendimiento: Decimal,
        precio_venta_neto: Decimal,
        precio_venta_bruto: Decimal,
        iva_porcentaje: Decimal,
        tenant_id: str,
        *,
        es_dinamica: bool = False,
    ) -> tuple[
        Decimal,  # costo_total_calculado
        Decimal,  # costo_porcion
        Decimal,  # costo_peor_caso
        Decimal,  # costo_mejor_caso
        Decimal,  # precio_neto_final
        Decimal,  # precio_bruto_final
        Decimal,  # margen_neto
        Decimal,  # margen_bruto
        Decimal,  # margen_pct
        Decimal,  # food_cost_pct
    ]:
        """Calcula de forma atómica y recursiva los costos base, peor caso, mejor caso y márgenes."""
        is_dyn = bool(es_dinamica or len(grupos_links) > 0)
        allergen_count = self._resolve_allergen_count_for_components(
            recipe_id, ingredientes, grupos_links, tenant_id
        )
        raw_notes = " | ".join(ing.notas for ing in ingredientes if ing.notas)
        scrubbed_notes = scrub_pii_text(raw_notes) if raw_notes else ""

        with trace_span(
            "recipe.escandallo.calculate",
            attributes={
                "tenant_id": tenant_id,
                "recipe_id": recipe_id if recipe_id is not None else 0,
                "is_dynamic": is_dyn,
                "allergen_count": allergen_count,
                "ingredients_count": len(ingredientes),
                "option_groups_count": len(grupos_links),
                "porciones_rendimiento": str(porciones_rendimiento),
                "notes_scrubbed": scrubbed_notes,
            },
            tracer_name="oppytec.recipes",
        ) as span_attrs:
            if porciones_rendimiento <= ZERO:
                raise InvalidYieldError(f"Yield portions must be strictly > 0, got {porciones_rendimiento}.")

            fixed_lot_cost = Decimal("0.00")

            # 1. Costeo de ingredientes fijos
            for ing in ingredientes:
                factor = ONE + (ing.porcentaje_merma / HUNDRED)
                gross_qty = ing.cantidad_receta * factor

                if ing.producto_id is not None:
                    unit_cost = self.get_ingredient_cost(ing.producto_id)
                    ing.costo_unitario = unit_cost.quantize(PRECISION_COST, ROUND_HALF_UP)
                    ing.costo_total = (gross_qty * unit_cost).quantize(PRECISION_COST, ROUND_HALF_UP)
                    if not ing.nombre:
                        ing.nombre = self._product_names.get(ing.producto_id, f"Producto #{ing.producto_id}")
                    ing.unidad = self._product_units.get(ing.producto_id, ing.unidad)
                elif ing.subreceta_id is not None:
                    sub = self.get_recipe(ing.subreceta_id, tenant_id)
                    unit_cost = sub.costo_porcion
                    ing.costo_unitario = unit_cost.quantize(PRECISION_COST, ROUND_HALF_UP)
                    ing.costo_total = (gross_qty * unit_cost).quantize(PRECISION_COST, ROUND_HALF_UP)
                    if not ing.nombre:
                        ing.nombre = sub.nombre
                    ing.unidad = "porcion"
                else:
                    raise PolymorphicReferenceError("Recipe ingredient must specify either 'producto_id' or 'subreceta_id'.")

                fixed_lot_cost += ing.costo_total

            # 2. Costeo de grupos de opciones dinámicos
            options_base_cost = Decimal("0.00")
            options_worst_cost = Decimal("0.00")
            options_best_cost = Decimal("0.00")

            for link in grupos_links:
                group = self.option_group_service.get_option_group(link.grupo_id, tenant_id)
                link.grupo = group

                if not group.items:
                    continue

                # Evaluar costo de cada ítem de opción
                item_costs: list[Decimal] = []
                default_item_costs: list[Decimal] = []

                for item in group.items:
                    it_cost = Decimal("0.00")
                    if item.producto_id is not None:
                        u_cost = self.get_ingredient_cost(item.producto_id)
                        it_cost = (item.cantidad * u_cost).quantize(PRECISION_COST, ROUND_HALF_UP)
                    elif item.receta_id is not None:
                        try:
                            sub_rec = self.get_recipe(item.receta_id, tenant_id)
                            it_cost = (item.cantidad * sub_rec.costo_porcion).quantize(PRECISION_COST, ROUND_HALF_UP)
                        except Exception:
                            it_cost = item.costo_referencial
                    else:
                        it_cost = item.costo_referencial

                    item.costo_referencial = it_cost
                    item_costs.append(it_cost)
                    if item.es_opcion_default:
                        default_item_costs.append(it_cost)

                # Costo base: suma de los defaults (o el primero si no hay default)
                if default_item_costs:
                    options_base_cost += sum(default_item_costs)
                elif item_costs:
                    options_base_cost += min(item_costs)

                # Peor caso: ítems más caros hasta seleccion_maxima
                sorted_desc = sorted(item_costs, reverse=True)
                k_max = min(group.seleccion_maxima, len(sorted_desc)) if not group.permite_repetir else group.seleccion_maxima
                if group.permite_repetir and sorted_desc:
                    worst_for_group = sorted_desc[0] * group.seleccion_maxima
                else:
                    worst_for_group = sum(sorted_desc[:k_max])
                options_worst_cost += worst_for_group

                # Mejor caso: ítems más económicos hasta seleccion_minima
                if link.es_requerido and group.seleccion_minima > 0:
                    sorted_asc = sorted(item_costs)
                    k_min = min(group.seleccion_minima, len(sorted_asc)) if not group.permite_repetir else group.seleccion_minima
                    if group.permite_repetir and sorted_asc:
                        best_for_group = sorted_asc[0] * group.seleccion_minima
                    else:
                        best_for_group = sum(sorted_asc[:k_min])
                    options_best_cost += best_for_group
                else:
                    options_best_cost += Decimal("0.00")

            costo_total_lote = (fixed_lot_cost + options_base_cost).quantize(PRECISION_COST, ROUND_HALF_UP)
            costo_porcion = (costo_total_lote / porciones_rendimiento).quantize(PRECISION_COST, ROUND_HALF_UP)

            worst_lot = (fixed_lot_cost + options_worst_cost).quantize(PRECISION_COST, ROUND_HALF_UP)
            best_lot = (fixed_lot_cost + options_best_cost).quantize(PRECISION_COST, ROUND_HALF_UP)
            costo_peor_caso = (worst_lot / porciones_rendimiento).quantize(PRECISION_COST, ROUND_HALF_UP)
            costo_mejor_caso = (best_lot / porciones_rendimiento).quantize(PRECISION_COST, ROUND_HALF_UP)

            # Si costo_peor_caso < costo_porcion, ajustamos
            if costo_peor_caso < costo_porcion:
                costo_peor_caso = costo_porcion
            if costo_mejor_caso > costo_porcion:
                costo_mejor_caso = costo_porcion

            # Precios
            neto = precio_venta_neto
            bruto = precio_venta_bruto
            tax_factor = ONE + (iva_porcentaje / HUNDRED)

            if neto > ZERO and bruto == ZERO:
                bruto = (neto * tax_factor).quantize(PRECISION_MONEY, ROUND_HALF_UP)
            elif bruto > ZERO and neto == ZERO:
                neto = (bruto / tax_factor).quantize(PRECISION_MONEY, ROUND_HALF_UP)

            margen_neto = (neto - costo_porcion).quantize(PRECISION_MONEY, ROUND_HALF_UP)
            margen_bruto = (bruto - (costo_porcion * tax_factor)).quantize(PRECISION_MONEY, ROUND_HALF_UP)

            margen_pct = (
                ((neto - costo_porcion) / neto * HUNDRED).quantize(PRECISION_PERCENTAGE, ROUND_HALF_UP)
                if neto > ZERO
                else ZERO
            )
            food_cost_pct = (
                (costo_porcion / neto * HUNDRED).quantize(PRECISION_PERCENTAGE, ROUND_HALF_UP)
                if neto > ZERO
                else ZERO
            )

            span_attrs["costo_total_calculado"] = str(costo_total_lote)
            span_attrs["costo_porcion"] = str(costo_porcion)
            span_attrs["costo_peor_caso"] = str(costo_peor_caso)
            span_attrs["costo_mejor_caso"] = str(costo_mejor_caso)
            span_attrs["margen_pct"] = str(margen_pct)
            span_attrs["food_cost_pct"] = str(food_cost_pct)

            return (
                costo_total_lote,
                costo_porcion,
                costo_peor_caso,
                costo_mejor_caso,
                neto,
                bruto,
                margen_neto,
                margen_bruto,
                margen_pct,
                food_cost_pct,
            )

    def calculate_escandallo(self, recipe_id: int, tenant_id: str = "default") -> RecipeDTO:
        """Recalcula el escandallo y márgenes de una receta existente emitiendo el span OpenTelemetry."""
        rec = self.get_recipe(recipe_id, tenant_id)
        (
            costo_total,
            costo_porcion,
            costo_peor,
            costo_mejor,
            neto_final,
            bruto_final,
            margen_neto,
            margen_bruto,
            margen_pct,
            food_cost_pct,
        ) = self._calculate_escandallo_costs(
            recipe_id=rec.id,
            ingredientes=rec.ingredientes_fijos,
            grupos_links=rec.grupos_opciones,
            porciones_rendimiento=rec.porciones_rendimiento,
            precio_venta_neto=rec.precio_venta_neto,
            precio_venta_bruto=rec.precio_venta_bruto,
            iva_porcentaje=rec.iva_porcentaje,
            tenant_id=tenant_id,
            es_dinamica=rec.es_dinamica,
        )
        rec.costo_total_calculado = costo_total
        rec.costo_porcion = costo_porcion
        rec.costo_peor_caso = costo_peor
        rec.costo_mejor_caso = costo_mejor
        rec.precio_venta_neto = neto_final
        rec.precio_venta_bruto = bruto_final
        rec.margen_neto = margen_neto
        rec.margen_bruto = margen_bruto
        rec.margen_pct = margen_pct
        rec.food_cost_pct = food_cost_pct
        rec.alergenos = self._compute_recipe_allergens(recipe_id, tenant_id)
        return rec

    # =========================================================================
    # CRUD DE RECETAS
    # =========================================================================

    def create_recipe(
        self,
        *,
        codigo: str,
        nombre: str,
        descripcion: str | None = None,
        categoria_receta_id: int | None = None,
        es_subreceta: bool = False,
        es_dinamica: bool = False,
        porciones_rendimiento: Decimal = Decimal("1.0000"),
        precio_venta_neto: Decimal = Decimal("0.00"),
        precio_venta_bruto: Decimal = Decimal("0.00"),
        iva_porcentaje: Decimal = Decimal("19.00"),
        iva_incluido: bool = True,
        imagen_url: str | None = None,
        preparacion: str | None = None,
        video_url: str | None = None,
        documento_url: str | None = None,
        tiempo_preparacion_minutos: int | None = None,
        ingredientes: list[RecipeIngredientDTO] | None = None,
        grupos_opciones: list[RecipeOptionGroupLinkDTO] | None = None,
        tenant_id: str = "default",
    ) -> RecipeDTO:
        """Crea una receta atómica con ingredientes fijos, grupos de opciones y costeo."""
        if not codigo or not codigo.strip():
            raise ValueError("Recipe 'codigo' cannot be empty.")
        if not nombre or not nombre.strip():
            raise ValueError("Recipe 'nombre' cannot be empty.")

        clean_codigo = codigo.strip().upper()
        # Verificar unicidad de código dentro del tenant
        for (t_id, _), r in self._recipes.items():
            if t_id == tenant_id and not r.is_deleted and r.codigo == clean_codigo:
                raise ValueError(f"Recipe with codigo '{clean_codigo}' already exists in tenant '{tenant_id}'.")

        rid = self._next_recipe_id
        self._next_recipe_id += 1

        raw_ing = ingredientes or []
        raw_grp = grupos_opciones or []

        # Validar ingredientes
        for idx, ing in enumerate(raw_ing):
            if ing.id is None:
                ing.id = self._next_ingredient_id
                self._next_ingredient_id += 1
            has_prod = ing.producto_id is not None
            has_sub = ing.subreceta_id is not None
            if has_prod == has_sub:
                raise PolymorphicReferenceError(
                    "Recipe ingredient must reference exactly one target: either 'producto_id' or 'subreceta_id'."
                )
            if ing.cantidad_receta <= ZERO:
                raise InvalidQuantityError("Ingredient quantity must be strictly greater than 0.")
            if ing.porcentaje_merma < ZERO or ing.porcentaje_merma >= HUNDRED:
                raise InvalidQuantityError("Ingredient waste percentage must satisfy 0 <= waste < 100.")

        # Detección de ciclos
        self._validate_cycles_for_recipe(rid, raw_ing, tenant_id)

        # Autodetección de es_dinamica
        auto_dinamica = bool(es_dinamica or len(raw_grp) > 0)

        # Calcular escandallo
        (
            costo_total,
            costo_porcion,
            costo_peor,
            costo_mejor,
            neto_final,
            bruto_final,
            margen_neto,
            margen_bruto,
            margen_pct,
            food_cost_pct,
        ) = self._calculate_escandallo_costs(
            recipe_id=rid,
            ingredientes=raw_ing,
            grupos_links=raw_grp,
            porciones_rendimiento=porciones_rendimiento,
            precio_venta_neto=precio_venta_neto,
            precio_venta_bruto=precio_venta_bruto,
            iva_porcentaje=iva_porcentaje,
            tenant_id=tenant_id,
            es_dinamica=auto_dinamica,
        )

        cat_nombre = None
        if categoria_receta_id is not None:
            cat = self.get_category(categoria_receta_id, tenant_id)
            if cat:
                cat_nombre = cat.nombre

        dto = RecipeDTO(
            id=rid,
            codigo=clean_codigo,
            nombre=nombre.strip(),
            descripcion=descripcion.strip() if descripcion else None,
            categoria_receta_id=categoria_receta_id,
            categoria_nombre=cat_nombre,
            es_subreceta=es_subreceta,
            es_dinamica=auto_dinamica,
            porciones_rendimiento=porciones_rendimiento,
            costo_total_calculado=costo_total,
            costo_porcion=costo_porcion,
            costo_peor_caso=costo_peor,
            costo_mejor_caso=costo_mejor,
            precio_venta_neto=neto_final,
            precio_venta_bruto=bruto_final,
            iva_porcentaje=iva_porcentaje,
            iva_incluido=iva_incluido,
            margen_neto=margen_neto,
            margen_bruto=margen_bruto,
            margen_pct=margen_pct,
            food_cost_pct=food_cost_pct,
            imagen_url=imagen_url,
            preparacion=preparacion,
            video_url=video_url,
            documento_url=documento_url,
            tiempo_preparacion_minutos=tiempo_preparacion_minutos,
            ingredientes_fijos=raw_ing,
            grupos_opciones=raw_grp,
            tenant_id=tenant_id,
        )
        self._recipes[(tenant_id, rid)] = dto

        # Registrar uso en OptionGroupService
        for grp in raw_grp:
            self.option_group_service.register_usage(grp.grupo_id, recipe_id=rid)

        # Poblar alérgenos consolidados
        dto.alergenos = self._compute_recipe_allergens(rid, tenant_id)

        return dto

    def get_recipe(self, recipe_id: int, tenant_id: str = "default") -> RecipeDTO:
        """Obtiene la ficha técnica completa de una receta."""
        dto = self._recipes.get((tenant_id, recipe_id))
        if dto is None or dto.is_deleted:
            raise RecipeNotFoundError(
                f"Recipe ID {recipe_id} not found in tenant '{tenant_id}'.",
                context={"recipe_id": recipe_id, "tenant_id": tenant_id},
            )
        dto.alergenos = self._compute_recipe_allergens(recipe_id, tenant_id)
        return dto

    def list_recipes(
        self,
        tenant_id: str = "default",
        *,
        tipo: str | None = None,  # todas, estaticas, dinamicas, subrecetas
        categoria_id: int | None = None,
        search: str | None = None,
    ) -> list[RecipeDTO]:
        """Lista recetas aplicando filtros por tipo gastronómico, categoría y búsqueda."""
        results: list[RecipeDTO] = []
        q = search.lower().strip() if search else None

        for (t_id, _), r in self._recipes.items():
            if t_id != tenant_id or r.is_deleted:
                continue

            if categoria_id is not None and r.categoria_receta_id != categoria_id:
                continue

            if tipo == "estaticas" and (r.es_dinamica or r.es_subreceta):
                continue
            elif tipo == "dinamicas" and not r.es_dinamica:
                continue
            elif tipo == "subrecetas" and not r.es_subreceta:
                continue

            if q:
                match = (
                    q in r.nombre.lower()
                    or q in r.codigo.lower()
                    or (r.descripcion and q in r.descripcion.lower())
                )
                if not match:
                    continue

            results.append(r)

        results.sort(key=lambda x: x.nombre)
        return results

    def update_recipe(
        self,
        recipe_id: int,
        *,
        nombre: str | None = None,
        descripcion: str | None = None,
        categoria_receta_id: int | None = None,
        es_subreceta: bool | None = None,
        es_dinamica: bool | None = None,
        porciones_rendimiento: Decimal | None = None,
        precio_venta_neto: Decimal | None = None,
        precio_venta_bruto: Decimal | None = None,
        iva_porcentaje: Decimal | None = None,
        iva_incluido: bool | None = None,
        imagen_url: str | None = None,
        preparacion: str | None = None,
        video_url: str | None = None,
        documento_url: str | None = None,
        tiempo_preparacion_minutos: int | None = None,
        ingredientes: list[RecipeIngredientDTO] | None = None,
        grupos_opciones: list[RecipeOptionGroupLinkDTO] | None = None,
        tenant_id: str = "default",
    ) -> RecipeDTO:
        """Actualiza una receta y regenera sus cálculos de escandallo y detección de ciclos."""
        current = self.get_recipe(recipe_id, tenant_id)

        new_name = nombre if nombre is not None else current.nombre
        new_desc = descripcion if descripcion is not None else current.descripcion
        new_cat = categoria_receta_id if categoria_receta_id is not None else current.categoria_receta_id
        new_sub = es_subreceta if es_subreceta is not None else current.es_subreceta
        new_yield = porciones_rendimiento if porciones_rendimiento is not None else current.porciones_rendimiento
        new_net = precio_venta_neto if precio_venta_neto is not None else current.precio_venta_neto
        new_bruto = precio_venta_bruto if precio_venta_bruto is not None else current.precio_venta_bruto
        new_iva = iva_porcentaje if iva_porcentaje is not None else current.iva_porcentaje
        new_iva_inc = iva_incluido if iva_incluido is not None else current.iva_incluido
        new_img = imagen_url if imagen_url is not None else current.imagen_url
        new_prep = preparacion if preparacion is not None else current.preparacion
        new_vid = video_url if video_url is not None else current.video_url
        new_doc = documento_url if documento_url is not None else current.documento_url
        new_time = tiempo_preparacion_minutos if tiempo_preparacion_minutos is not None else current.tiempo_preparacion_minutos

        raw_ing = ingredientes if ingredientes is not None else current.ingredientes_fijos
        raw_grp = grupos_opciones if grupos_opciones is not None else current.grupos_opciones

        # Validar ingredientes
        for idx, ing in enumerate(raw_ing):
            if ing.id is None:
                ing.id = self._next_ingredient_id
                self._next_ingredient_id += 1
            has_prod = ing.producto_id is not None
            has_sub = ing.subreceta_id is not None
            if has_prod == has_sub:
                raise PolymorphicReferenceError(
                    "Recipe ingredient must reference exactly one target: either 'producto_id' or 'subreceta_id'."
                )
            if ing.cantidad_receta <= ZERO:
                raise InvalidQuantityError("Ingredient quantity must be strictly greater than 0.")
            if ing.porcentaje_merma < ZERO or ing.porcentaje_merma >= HUNDRED:
                raise InvalidQuantityError("Ingredient waste percentage must satisfy 0 <= waste < 100.")

        # Detección de ciclos
        self._validate_cycles_for_recipe(recipe_id, raw_ing, tenant_id)

        # Autodetección de dinámica
        explicit_dyn = es_dinamica if es_dinamica is not None else current.es_dinamica
        auto_dinamica = bool(explicit_dyn or len(raw_grp) > 0)

        # Calcular escandallo
        (
            costo_total,
            costo_porcion,
            costo_peor,
            costo_mejor,
            neto_final,
            bruto_final,
            margen_neto,
            margen_bruto,
            margen_pct,
            food_cost_pct,
        ) = self._calculate_escandallo_costs(
            recipe_id=recipe_id,
            ingredientes=raw_ing,
            grupos_links=raw_grp,
            porciones_rendimiento=new_yield,
            precio_venta_neto=new_net,
            precio_venta_bruto=new_bruto,
            iva_porcentaje=new_iva,
            tenant_id=tenant_id,
            es_dinamica=auto_dinamica,
        )

        cat_nombre = None
        if new_cat is not None:
            cat = self.get_category(new_cat, tenant_id)
            if cat:
                cat_nombre = cat.nombre

        # Desvincular grupos anteriores del registro de uso y vincular los nuevos
        for old_grp in current.grupos_opciones:
            self.option_group_service.unregister_usage(old_grp.grupo_id, recipe_id=recipe_id)
        for grp in raw_grp:
            self.option_group_service.register_usage(grp.grupo_id, recipe_id=recipe_id)

        updated = RecipeDTO(
            id=recipe_id,
            codigo=current.codigo,
            nombre=new_name.strip(),
            descripcion=new_desc.strip() if new_desc else None,
            categoria_receta_id=new_cat,
            categoria_nombre=cat_nombre,
            es_subreceta=new_sub,
            es_dinamica=auto_dinamica,
            porciones_rendimiento=new_yield,
            costo_total_calculado=costo_total,
            costo_porcion=costo_porcion,
            costo_peor_caso=costo_peor,
            costo_mejor_caso=costo_mejor,
            precio_venta_neto=neto_final,
            precio_venta_bruto=bruto_final,
            iva_porcentaje=new_iva,
            iva_incluido=new_iva_inc,
            margen_neto=margen_neto,
            margen_bruto=margen_bruto,
            margen_pct=margen_pct,
            food_cost_pct=food_cost_pct,
            imagen_url=new_img,
            preparacion=new_prep,
            video_url=new_vid,
            documento_url=new_doc,
            tiempo_preparacion_minutos=new_time,
            ingredientes_fijos=raw_ing,
            grupos_opciones=raw_grp,
            tenant_id=tenant_id,
        )
        self._recipes[(tenant_id, recipe_id)] = updated
        updated.alergenos = self._compute_recipe_allergens(recipe_id, tenant_id)
        return updated

    def delete_recipe(self, recipe_id: int, tenant_id: str = "default") -> None:
        """Soft-delete de receta con verificación estricta de uso en otras subrecetas o combos."""
        recipe = self.get_recipe(recipe_id, tenant_id)

        # 1. Verificar si alguna otra receta activa usa esta receta como subreceta
        for (t_id, other_id), other_r in self._recipes.items():
            if t_id == tenant_id and not other_r.is_deleted and other_id != recipe_id:
                for ing in other_r.ingredientes_fijos:
                    if ing.subreceta_id == recipe_id:
                        raise RecipeInUseError(
                            f"Cannot delete Recipe ID {recipe_id}: it is currently used as a sub-recipe in Recipe '{other_r.nombre}'.",
                            context={"recipe_id": recipe_id, "dependent_recipe_id": other_id},
                        )

        # Desvincular grupos de opciones
        for grp in recipe.grupos_opciones:
            self.option_group_service.unregister_usage(grp.grupo_id, recipe_id=recipe_id)

        recipe.is_deleted = True

    # =========================================================================
    # ALÉRGENOS ALIMENTARIOS Y FICHA TÉCNICA DE COCINA
    # =========================================================================

    def _compute_recipe_allergens(
        self,
        recipe_id: int,
        tenant_id: str = "default",
        _visited: set[int] | None = None,
    ) -> list[AllergenDefinition]:
        """Calcula de forma interna y recursiva el conjunto único de alérgenos normados."""
        dto = self._recipes.get((tenant_id, recipe_id))
        if dto is None or dto.is_deleted:
            raise RecipeNotFoundError(
                f"Recipe ID {recipe_id} not found in tenant '{tenant_id}'.",
                context={"recipe_id": recipe_id, "tenant_id": tenant_id},
            )

        visited = set(_visited or set())
        if recipe_id in visited:
            return []
        visited.add(recipe_id)

        collected_codes: set[str] = set()

        # 1. Alérgenos explícitos configurados a nivel de receta
        for code in self._recipe_allergens.get(recipe_id, []):
            collected_codes.add(code)

        # 2. Insumos fijos
        for ing in dto.ingredientes_fijos:
            if ing.producto_id is not None:
                for a_code in self._product_allergens.get(ing.producto_id, []):
                    collected_codes.add(a_code)
            elif ing.subreceta_id is not None:
                sub_defs = self._compute_recipe_allergens(ing.subreceta_id, tenant_id, _visited=visited)
                for a_def in sub_defs:
                    collected_codes.add(a_def.code)

        # 3. Opciones dinámicas en grupos de opciones
        for link in dto.grupos_opciones:
            try:
                group = self.option_group_service.get_option_group(link.grupo_id, tenant_id)
            except Exception:
                continue

            for item in group.items:
                if item.producto_id is not None:
                    for a_code in self._product_allergens.get(item.producto_id, []):
                        collected_codes.add(a_code)
                elif item.receta_id is not None:
                    sub_defs = self._compute_recipe_allergens(item.receta_id, tenant_id, _visited=visited)
                    for a_def in sub_defs:
                        collected_codes.add(a_def.code)

        return resolve_allergen_definitions(list(collected_codes))

    def get_recipe_allergens(self, recipe_id: int, tenant_id: str = "default") -> list[AllergenDefinition]:
        """Calcula y consolida el conjunto único de alérgenos normados de la receta."""
        return self._compute_recipe_allergens(recipe_id, tenant_id)

    def generate_kitchen_sheet(
        self,
        recipe_id: int,
        servings: Decimal | int | str | None = None,
        tenant_id: str = "default",
    ) -> KitchenSheetDTO:
        """
        Genera la ficha técnica de cocina escalada matemáticamente con porciones exactas,
        cantidades netas, cantidades brutas (con merma técnica en Decimal),
        desglose de subrecetas, opciones dinámicas, instrucciones de preparación y lista de alérgenos.
        """
        with trace_span(
            "recipe.kitchen_sheet.generate",
            attributes={
                "tenant_id": tenant_id,
                "recipe_id": recipe_id,
                "is_dynamic": False,
                "allergen_count": 0,
            },
            tracer_name="oppytec.recipes",
        ) as span_attrs:
            recipe = self.get_recipe(recipe_id, tenant_id)
            span_attrs["is_dynamic"] = recipe.es_dinamica

            if servings is None:
                porciones_solicitadas = recipe.porciones_rendimiento
            else:
                porciones_solicitadas = Decimal(str(servings)).quantize(PRECISION_QUANTITY, ROUND_HALF_UP)

            if porciones_solicitadas <= ZERO:
                raise InvalidYieldError(
                    f"Requested servings for kitchen sheet must be strictly > 0, got {porciones_solicitadas}."
                )

            factor = porciones_solicitadas / recipe.porciones_rendimiento

            sheet_items: list[KitchenSheetItemDTO] = []
            collected_notes: list[str] = []
            if recipe.descripcion:
                collected_notes.append(recipe.descripcion)
            if recipe.preparacion:
                collected_notes.append(recipe.preparacion)

            for ing in recipe.ingredientes_fijos:
                if ing.notas:
                    collected_notes.append(ing.notas)
                net_base = ing.cantidad_receta
                net_scaled = (net_base * factor).quantize(PRECISION_QUANTITY, ROUND_HALF_UP)
                waste_factor = ONE + (ing.porcentaje_merma / HUNDRED)
                gross_scaled = (net_scaled * waste_factor).quantize(PRECISION_QUANTITY, ROUND_HALF_UP)

                ing_allergens: list[AllergenDefinition] = []
                sub_breakdown: list[KitchenSheetItemDTO] = []

                if ing.producto_id is not None:
                    p_codes = self._product_allergens.get(ing.producto_id, [])
                    ing_allergens = resolve_allergen_definitions(p_codes)
                    t_type = "producto"
                    unit = self._product_units.get(ing.producto_id, ing.unidad)
                    name = ing.nombre or self._product_names.get(ing.producto_id, f"Producto #{ing.producto_id}")
                elif ing.subreceta_id is not None:
                    ing_allergens = self.get_recipe_allergens(ing.subreceta_id, tenant_id)
                    t_type = "subreceta"
                    unit = "porcion"
                    name = ing.nombre or f"Subreceta #{ing.subreceta_id}"
                    # Desglose recursivo de la subreceta requerida
                    try:
                        sub_sheet = self.generate_kitchen_sheet(
                            recipe_id=ing.subreceta_id,
                            servings=net_scaled,
                            tenant_id=tenant_id,
                        )
                        sub_breakdown = sub_sheet.ingredientes_fijos
                    except Exception:
                        sub_breakdown = []
                else:
                    raise PolymorphicReferenceError("Kitchen sheet ingredient must reference producto_id or subreceta_id.")

                sheet_items.append(
                    KitchenSheetItemDTO(
                        ingrediente_id=ing.id,
                        producto_id=ing.producto_id,
                        subreceta_id=ing.subreceta_id,
                        nombre=name,
                        target_type=t_type,
                        unidad=unit,
                        cantidad_neta_base=net_base,
                        cantidad_neta_escalada=net_scaled,
                        porcentaje_merma=ing.porcentaje_merma,
                        cantidad_bruta_escalada=gross_scaled,
                        notas=scrub_pii_text(ing.notas),
                        alergenos=ing_allergens,
                        subreceta_desglose=sub_breakdown,
                    )
                )

            # Grupos de opciones
            sheet_groups: list[KitchenSheetOptionGroupDTO] = []
            for link in recipe.grupos_opciones:
                try:
                    group = self.option_group_service.get_option_group(link.grupo_id, tenant_id)
                except Exception:
                    continue

                option_items: list[KitchenSheetOptionItemDTO] = []
                for item in group.items:
                    opt_scaled = (item.cantidad * factor).quantize(PRECISION_QUANTITY, ROUND_HALF_UP)
                    opt_allergens: list[AllergenDefinition] = []

                    if item.producto_id is not None:
                        opt_target = "producto"
                        opt_unit = self._product_units.get(item.producto_id, "und")
                        opt_name = item.nombre or self._product_names.get(item.producto_id, f"Producto #{item.producto_id}")
                        p_codes = self._product_allergens.get(item.producto_id, [])
                        opt_allergens = resolve_allergen_definitions(p_codes)
                    elif item.receta_id is not None:
                        opt_target = "receta"
                        opt_unit = "porcion"
                        try:
                            sub_r = self.get_recipe(item.receta_id, tenant_id)
                            opt_name = item.nombre or sub_r.nombre
                            opt_allergens = self.get_recipe_allergens(item.receta_id, tenant_id)
                        except Exception:
                            opt_name = item.nombre or f"Receta #{item.receta_id}"
                    else:
                        opt_target = "desconocido"
                        opt_unit = "und"
                        opt_name = item.nombre or "Opción"

                    option_items.append(
                        KitchenSheetOptionItemDTO(
                            item_id=item.id,
                            producto_id=item.producto_id,
                            receta_id=item.receta_id,
                            nombre=opt_name,
                            target_type=opt_target,
                            cantidad_base=item.cantidad,
                            cantidad_escalada=opt_scaled,
                            unidad=opt_unit,
                            es_opcion_default=item.es_opcion_default,
                            recargo_precio=item.recargo_precio,
                            alergenos=opt_allergens,
                        )
                    )

                sheet_groups.append(
                    KitchenSheetOptionGroupDTO(
                        grupo_id=group.id,
                        grupo_nombre=group.nombre,
                        seleccion_minima=group.seleccion_minima,
                        seleccion_maxima=group.seleccion_maxima,
                        es_requerido=link.es_requerido,
                        opciones=option_items,
                    )
                )

            consolidated_allergens = self.get_recipe_allergens(recipe_id, tenant_id)
            scaled_factor = factor.quantize(PRECISION_QUANTITY, ROUND_HALF_UP)

            span_attrs["allergen_count"] = len(consolidated_allergens)
            span_attrs["porciones_base"] = str(recipe.porciones_rendimiento)
            span_attrs["porciones_solicitadas"] = str(porciones_solicitadas)
            span_attrs["factor_escalamiento"] = str(scaled_factor)
            span_attrs["ingredients_count"] = len(sheet_items)
            span_attrs["option_groups_count"] = len(sheet_groups)
            if collected_notes:
                span_attrs["notes_scrubbed"] = scrub_pii_text(" | ".join(collected_notes)) or ""

            return KitchenSheetDTO(
                recipe_id=recipe.id,
                codigo=recipe.codigo,
                nombre=recipe.nombre,
                descripcion=scrub_pii_text(recipe.descripcion),
                categoria_nombre=recipe.categoria_nombre,
                porciones_base=recipe.porciones_rendimiento,
                porciones_solicitadas=porciones_solicitadas,
                factor_escalamiento=scaled_factor,
                tiempo_preparacion_minutos=recipe.tiempo_preparacion_minutos,
                preparacion=scrub_pii_text(recipe.preparacion),
                video_url=recipe.video_url,
                documento_url=recipe.documento_url,
                ingredientes_fijos=sheet_items,
                grupos_opciones=sheet_groups,
                alergenos_consolidados=consolidated_allergens,
            )

