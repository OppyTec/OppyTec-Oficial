"""
oppytec-backend/src/modules/recipes/application/combo_service.py
Servicio de Aplicación para Gestión Transaccional de Combos Comerciales y Menús Promocionales.
Calcula costos base, disponibilidad teórica de stock en bodegas, autodetección de combo dinámico
y márgenes comerciales en Decimal estricto.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from src.core.observability import scrub_pii_text, trace_span
from src.modules.recipes.application.option_group_service import (
    OptionGroupDTO,
    OptionGroupService,
)
from src.modules.recipes.application.recipe_service import RecipeDTO, RecipeService
from src.modules.recipes.domain.entities import (
    Combo as DomainCombo,
    ComboGrupoOpcion as DomainComboGrupoOpcion,
    ComboItem as DomainComboItem,
)
from src.modules.recipes.domain.exceptions import (
    ComboNotFoundError,
    InvalidOptionSelectionError,
    InvalidQuantityError,
    PolymorphicReferenceError,
)
from src.modules.recipes.domain.value_objects import (
    HUNDRED,
    ONE,
    PRECISION_COST,
    PRECISION_MONEY,
    PRECISION_PERCENTAGE,
    PRECISION_QUANTITY,
    ZERO,
)


@dataclass
class ComboCategoryDTO:
    """DTO para categoría clasificatoria de combos."""

    id: int
    nombre: str
    color: str | None = "#ec4899"
    icono: str | None = "Boxes"
    orden: int = 0
    tenant_id: str = "default"
    is_deleted: bool = False


@dataclass
class ComboItemDTO:
    """DTO para componente fijo de un combo."""

    id: int | None = None
    producto_id: int | None = None
    receta_id: int | None = None
    cantidad: Decimal = Decimal("1.0000")
    nombre: str | None = None
    costo_unitario: Decimal = Decimal("0.00")
    costo_total: Decimal = Decimal("0.00")

    @property
    def target_type(self) -> str:
        return "receta" if self.receta_id is not None else "producto"


@dataclass
class ComboOptionGroupLinkDTO:
    """DTO para vinculación de grupo de opciones a un combo."""

    grupo_id: int
    orden: int = 0
    es_requerido: bool = True
    grupo: OptionGroupDTO | None = None


@dataclass
class ComboDTO:
    """DTO completo de combo gastronómico con costeo y disponibilidad de stock."""

    id: int
    codigo: str | None
    nombre: str
    descripcion: str | None = None
    categoria_combo_id: int | None = None
    categoria_nombre: str | None = None
    es_dinamico: bool = False
    precio_venta_neto: Decimal = Decimal("0.00")
    precio_venta_bruto: Decimal = Decimal("0.00")
    iva_porcentaje: Decimal = Decimal("19.00")
    iva_incluido: bool = True
    costo_total_calculado: Decimal = Decimal("0.00")
    margen_amount: Decimal = Decimal("0.00")
    margen_pct: Decimal = Decimal("0.00")
    food_cost_pct: Decimal = Decimal("0.00")
    disponibilidad_stock_porciones: int | None = None
    esta_disponible: bool = True
    imagen_url: str | None = None
    items_fijos: list[ComboItemDTO] = field(default_factory=list)
    grupos_opciones: list[ComboOptionGroupLinkDTO] = field(default_factory=list)
    tenant_id: str = "default"
    is_deleted: bool = False


class ComboService:
    """
    Servicio de Aplicación de Combos Promocionales.
    Garantiza consistencia polimórfica, cálculo de costos base y disponibilidad en inventario.
    """

    def __init__(
        self,
        recipe_service: RecipeService,
        option_group_service: OptionGroupService | None = None,
    ) -> None:
        self.recipe_service = recipe_service
        self.option_group_service = option_group_service or recipe_service.option_group_service
        self._combos: dict[tuple[str, int], ComboDTO] = {}
        self._categories: dict[tuple[str, int], ComboCategoryDTO] = {}
        self._next_combo_id: int = 1
        self._next_category_id: int = 1
        self._next_item_id: int = 1
        self._product_stock_balances: dict[int, Decimal] = {}

    def reset(self) -> None:
        """Limpia todo el estado en memoria para pruebas."""
        self._combos.clear()
        self._categories.clear()
        self._next_combo_id = 1
        self._next_category_id = 1
        self._next_item_id = 1
        self._product_stock_balances.clear()

    def set_product_stock_balance(self, producto_id: int, available_stock: Decimal | int | str) -> None:
        """Configura el stock físico disponible en bodega para un producto (útil en simulaciones)."""
        self._product_stock_balances[producto_id] = Decimal(str(available_stock))

    # =========================================================================
    # CATEGORÍAS DE COMBOS
    # =========================================================================

    def create_category(
        self,
        *,
        nombre: str,
        color: str | None = "#ec4899",
        icono: str | None = "Boxes",
        orden: int = 0,
        tenant_id: str = "default",
    ) -> ComboCategoryDTO:
        cid = self._next_category_id
        self._next_category_id += 1
        cat = ComboCategoryDTO(
            id=cid,
            nombre=nombre.strip(),
            color=color,
            icono=icono,
            orden=orden,
            tenant_id=tenant_id,
        )
        self._categories[(tenant_id, cid)] = cat
        return cat

    def list_categories(self, tenant_id: str = "default") -> list[ComboCategoryDTO]:
        cats = [
            c for (t_id, _), c in self._categories.items()
            if t_id == tenant_id and not c.is_deleted
        ]
        cats.sort(key=lambda c: (c.orden, c.nombre))
        return cats

    def get_category(self, category_id: int, tenant_id: str = "default") -> ComboCategoryDTO | None:
        cat = self._categories.get((tenant_id, category_id))
        if cat and not cat.is_deleted:
            return cat
        return None

    # =========================================================================
    # DISPONIBILIDAD DE STOCK Y COSTEO
    # =========================================================================

    def _calculate_theoretical_stock(
        self,
        items: list[ComboItemDTO],
        tenant_id: str,
        stock_balances: Mapping[int, Decimal] | None = None,
        *,
        combo_id: int | None = None,
        is_dynamic: bool = False,
        notes: str | None = None,
    ) -> tuple[int | None, bool]:
        """
        Calcula la disponibilidad teórica de stock en porciones evaluando los ítems fijos del combo
        y las recetas asociadas contra el saldo actual en bodegas.
        """
        allergen_codes: set[str] = set()
        for item in items:
            if item.producto_id is not None:
                for code in self.recipe_service.get_product_allergens(item.producto_id):
                    allergen_codes.add(code)
            elif item.receta_id is not None:
                try:
                    for a_def in self.recipe_service.get_recipe_allergens(item.receta_id, tenant_id):
                        allergen_codes.add(a_def.code)
                except Exception:
                    continue

        with trace_span(
            "combo.availability.check",
            attributes={
                "tenant_id": tenant_id,
                "combo_id": combo_id if combo_id is not None else 0,
                "is_dynamic": bool(is_dynamic),
                "allergen_count": len(allergen_codes),
                "items_count": len(items),
                "notes_scrubbed": scrub_pii_text(notes) or "" if notes else "",
            },
            tracer_name="oppytec.recipes",
        ) as span_attrs:
            active_balances = stock_balances if stock_balances is not None else self._product_stock_balances
            if not active_balances:
                # Si no hay balances de inventario inyectados, se asume disponibilidad sin límite
                span_attrs["available_portions"] = -1
                span_attrs["is_available"] = True
                return None, True

            min_portions = math.inf

            for item in items:
                if item.producto_id is not None:
                    avail = active_balances.get(item.producto_id, Decimal("0.00"))
                    if item.cantidad <= ZERO:
                        continue
                    portions = int(avail // item.cantidad)
                    if portions < min_portions:
                        min_portions = portions

                elif item.receta_id is not None:
                    try:
                        rec = self.recipe_service.get_recipe(item.receta_id, tenant_id)
                        for ing in rec.ingredientes_fijos:
                            if ing.producto_id is not None:
                                factor = ONE + (ing.porcentaje_merma / HUNDRED)
                                gross_needed = ing.cantidad_receta * factor * item.cantidad
                                if gross_needed <= ZERO:
                                    continue
                                avail = active_balances.get(ing.producto_id, Decimal("0.00"))
                                portions = int(avail // gross_needed)
                                if portions < min_portions:
                                    min_portions = portions
                    except Exception:
                        continue

            if min_portions == math.inf:
                span_attrs["available_portions"] = -1
                span_attrs["is_available"] = True
                return None, True

            res_portions = max(0, int(min_portions))
            is_avail = res_portions > 0
            span_attrs["available_portions"] = res_portions
            span_attrs["is_available"] = is_avail
            return res_portions, is_avail

    def check_availability(
        self,
        combo_id: int,
        tenant_id: str = "default",
        stock_balances: Mapping[int, Decimal] | None = None,
    ) -> tuple[int | None, bool]:
        """Verifica la disponibilidad teórica de stock de un combo y emite el span `combo.availability.check`."""
        dto = self._combos.get((tenant_id, combo_id))
        if dto is None or dto.is_deleted:
            raise ComboNotFoundError(
                f"Combo ID {combo_id} not found in tenant '{tenant_id}'.",
                context={"combo_id": combo_id, "tenant_id": tenant_id},
            )
        stock_avail, is_avail = self._calculate_theoretical_stock(
            dto.items_fijos,
            tenant_id,
            stock_balances,
            combo_id=dto.id,
            is_dynamic=dto.es_dinamico,
            notes=dto.descripcion,
        )
        dto.disponibilidad_stock_porciones = stock_avail
        dto.esta_disponible = is_avail
        return stock_avail, is_avail

    def _calculate_combo_costs(
        self,
        items: list[ComboItemDTO],
        grupos_links: list[ComboOptionGroupLinkDTO],
        precio_venta_neto: Decimal,
        precio_venta_bruto: Decimal,
        iva_porcentaje: Decimal,
        tenant_id: str,
    ) -> tuple[
        Decimal,  # costo_total
        Decimal,  # neto_final
        Decimal,  # bruto_final
        Decimal,  # margen_amount
        Decimal,  # margen_pct
        Decimal,  # food_cost_pct
    ]:
        """Calcula costo base del combo (componentes fijos + opciones default) y márgenes."""
        total_cost = Decimal("0.00")

        # 1. Componentes fijos
        for it in items:
            if it.producto_id is not None:
                u_cost = self.recipe_service.get_ingredient_cost(it.producto_id)
                it.costo_unitario = u_cost.quantize(PRECISION_COST, ROUND_HALF_UP)
                it.costo_total = (it.cantidad * u_cost).quantize(PRECISION_COST, ROUND_HALF_UP)
                if not it.nombre:
                    it.nombre = self.recipe_service._product_names.get(
                        it.producto_id, f"Producto #{it.producto_id}"
                    )
            elif it.receta_id is not None:
                sub_r = self.recipe_service.get_recipe(it.receta_id, tenant_id)
                u_cost = sub_r.costo_porcion
                it.costo_unitario = u_cost.quantize(PRECISION_COST, ROUND_HALF_UP)
                it.costo_total = (it.cantidad * u_cost).quantize(PRECISION_COST, ROUND_HALF_UP)
                if not it.nombre:
                    it.nombre = sub_r.nombre
            else:
                raise PolymorphicReferenceError("ComboItem must specify either 'producto_id' or 'receta_id'.")

            total_cost += it.costo_total

        # 2. Grupos de opciones: sumar opciones default
        for link in grupos_links:
            grp = self.option_group_service.get_option_group(link.grupo_id, tenant_id)
            link.grupo = grp

            for opt in grp.items:
                if opt.es_opcion_default:
                    if opt.producto_id is not None:
                        opt_cost = self.recipe_service.get_ingredient_cost(opt.producto_id)
                        total_cost += (opt.cantidad * opt_cost).quantize(PRECISION_COST, ROUND_HALF_UP)
                    elif opt.receta_id is not None:
                        try:
                            sub_r = self.recipe_service.get_recipe(opt.receta_id, tenant_id)
                            total_cost += (opt.cantidad * sub_r.costo_porcion).quantize(
                                PRECISION_COST, ROUND_HALF_UP
                            )
                        except Exception:
                            total_cost += opt.costo_referencial
                    else:
                        total_cost += opt.costo_referencial

        total_cost = total_cost.quantize(PRECISION_COST, ROUND_HALF_UP)

        # Precios
        neto = precio_venta_neto
        bruto = precio_venta_bruto
        tax_factor = ONE + (iva_porcentaje / HUNDRED)

        if neto > ZERO and bruto == ZERO:
            bruto = (neto * tax_factor).quantize(PRECISION_MONEY, ROUND_HALF_UP)
        elif bruto > ZERO and neto == ZERO:
            neto = (bruto / tax_factor).quantize(PRECISION_MONEY, ROUND_HALF_UP)

        margen_amount = (neto - total_cost).quantize(PRECISION_MONEY, ROUND_HALF_UP)
        margen_pct = (
            ((neto - total_cost) / neto * HUNDRED).quantize(PRECISION_PERCENTAGE, ROUND_HALF_UP)
            if neto > ZERO
            else ZERO
        )
        food_cost_pct = (
            (total_cost / neto * HUNDRED).quantize(PRECISION_PERCENTAGE, ROUND_HALF_UP)
            if neto > ZERO
            else ZERO
        )

        return (
            total_cost,
            neto,
            bruto,
            margen_amount,
            margen_pct,
            food_cost_pct,
        )

    # =========================================================================
    # CRUD DE COMBOS
    # =========================================================================

    def create_combo(
        self,
        *,
        nombre: str,
        codigo: str | None = None,
        descripcion: str | None = None,
        categoria_combo_id: int | None = None,
        es_dinamico: bool = False,
        precio_venta_neto: Decimal = Decimal("0.00"),
        precio_venta_bruto: Decimal = Decimal("0.00"),
        iva_porcentaje: Decimal = Decimal("19.00"),
        iva_incluido: bool = True,
        imagen_url: str | None = None,
        items: list[ComboItemDTO] | None = None,
        grupos_opciones: list[ComboOptionGroupLinkDTO] | None = None,
        tenant_id: str = "default",
    ) -> ComboDTO:
        """Crea un combo promocional atómico con cálculo de costo base y disponibilidad."""
        if not nombre or not nombre.strip():
            raise ValueError("Combo 'nombre' cannot be empty.")

        clean_codigo = codigo.strip().upper() if codigo else None
        if clean_codigo:
            for (t_id, _), c in self._combos.items():
                if t_id == tenant_id and not c.is_deleted and c.codigo == clean_codigo:
                    raise ValueError(f"Combo with codigo '{clean_codigo}' already exists in tenant '{tenant_id}'.")

        cid = self._next_combo_id
        self._next_combo_id += 1

        raw_items = items or []
        raw_grp = grupos_opciones or []

        # Validar ítems
        for idx, it in enumerate(raw_items):
            if it.id is None:
                it.id = self._next_item_id
                self._next_item_id += 1
            has_prod = it.producto_id is not None
            has_rec = it.receta_id is not None
            if has_prod == has_rec:
                raise PolymorphicReferenceError(
                    "ComboItem must reference exactly one target: either 'producto_id' or 'receta_id'."
                )
            if it.cantidad <= ZERO:
                raise InvalidQuantityError("Combo item quantity must be strictly greater than 0.")

        auto_dinamico = bool(es_dinamico or len(raw_grp) > 0)

        (
            costo_total,
            neto_final,
            bruto_final,
            margen_amount,
            margen_pct,
            food_cost_pct,
        ) = self._calculate_combo_costs(
            items=raw_items,
            grupos_links=raw_grp,
            precio_venta_neto=precio_venta_neto,
            precio_venta_bruto=precio_venta_bruto,
            iva_porcentaje=iva_porcentaje,
            tenant_id=tenant_id,
        )

        stock_avail, is_avail = self._calculate_theoretical_stock(
            raw_items,
            tenant_id,
            combo_id=cid,
            is_dynamic=auto_dinamico,
            notes=descripcion,
        )

        cat_nombre = None
        if categoria_combo_id is not None:
            cat = self.get_category(categoria_combo_id, tenant_id)
            if cat:
                cat_nombre = cat.nombre

        dto = ComboDTO(
            id=cid,
            codigo=clean_codigo,
            nombre=nombre.strip(),
            descripcion=descripcion.strip() if descripcion else None,
            categoria_combo_id=categoria_combo_id,
            categoria_nombre=cat_nombre,
            es_dinamico=auto_dinamico,
            precio_venta_neto=neto_final,
            precio_venta_bruto=bruto_final,
            iva_porcentaje=iva_porcentaje,
            iva_incluido=iva_incluido,
            costo_total_calculado=costo_total,
            margen_amount=margen_amount,
            margen_pct=margen_pct,
            food_cost_pct=food_cost_pct,
            disponibilidad_stock_porciones=stock_avail,
            esta_disponible=is_avail,
            imagen_url=imagen_url,
            items_fijos=raw_items,
            grupos_opciones=raw_grp,
            tenant_id=tenant_id,
        )
        self._combos[(tenant_id, cid)] = dto

        # Registrar uso en OptionGroupService
        for grp in raw_grp:
            self.option_group_service.register_usage(grp.grupo_id, combo_id=cid)

        return dto

    def get_combo(
        self,
        combo_id: int,
        tenant_id: str = "default",
        stock_balances: Mapping[int, Decimal] | None = None,
    ) -> ComboDTO:
        """Obtiene el detalle completo de un combo activo."""
        dto = self._combos.get((tenant_id, combo_id))
        if dto is None or dto.is_deleted:
            raise ComboNotFoundError(
                f"Combo ID {combo_id} not found in tenant '{tenant_id}'.",
                context={"combo_id": combo_id, "tenant_id": tenant_id},
            )

        # Actualizar disponibilidad con el balance actual
        stock_avail, is_avail = self._calculate_theoretical_stock(
            dto.items_fijos,
            tenant_id,
            stock_balances,
            combo_id=dto.id,
            is_dynamic=dto.es_dinamico,
            notes=dto.descripcion,
        )
        dto.disponibilidad_stock_porciones = stock_avail
        dto.esta_disponible = is_avail
        return dto

    def list_combos(
        self,
        tenant_id: str = "default",
        *,
        categoria_id: int | None = None,
        search: str | None = None,
        stock_balances: Mapping[int, Decimal] | None = None,
    ) -> list[ComboDTO]:
        """Lista combos aplicando filtros por categoría y búsqueda."""
        results: list[ComboDTO] = []
        q = search.lower().strip() if search else None

        for (t_id, _), c in self._combos.items():
            if t_id != tenant_id or c.is_deleted:
                continue

            if categoria_id is not None and c.categoria_combo_id != categoria_id:
                continue

            if q:
                match = (
                    q in c.nombre.lower()
                    or (c.codigo and q in c.codigo.lower())
                    or (c.descripcion and q in c.descripcion.lower())
                )
                if not match:
                    continue

            # Actualizar stock dinámicamente
            stock_avail, is_avail = self._calculate_theoretical_stock(
                c.items_fijos,
                tenant_id,
                stock_balances,
                combo_id=c.id,
                is_dynamic=c.es_dinamico,
                notes=c.descripcion,
            )
            c.disponibilidad_stock_porciones = stock_avail
            c.esta_disponible = is_avail
            results.append(c)

        results.sort(key=lambda x: x.nombre)
        return results

    def update_combo(
        self,
        combo_id: int,
        *,
        nombre: str | None = None,
        codigo: str | None = None,
        descripcion: str | None = None,
        categoria_combo_id: int | None = None,
        es_dinamico: bool | None = None,
        precio_venta_neto: Decimal | None = None,
        precio_venta_bruto: Decimal | None = None,
        iva_porcentaje: Decimal | None = None,
        iva_incluido: bool | None = None,
        imagen_url: str | None = None,
        items: list[ComboItemDTO] | None = None,
        grupos_opciones: list[ComboOptionGroupLinkDTO] | None = None,
        tenant_id: str = "default",
    ) -> ComboDTO:
        """Actualiza un combo y regenera sus cálculos de costo y disponibilidad."""
        current = self.get_combo(combo_id, tenant_id)

        new_name = nombre if nombre is not None else current.nombre
        new_code = codigo.strip().upper() if codigo is not None else current.codigo
        new_desc = descripcion if descripcion is not None else current.descripcion
        new_cat = categoria_combo_id if categoria_combo_id is not None else current.categoria_combo_id
        new_net = precio_venta_neto if precio_venta_neto is not None else current.precio_venta_neto
        new_bruto = precio_venta_bruto if precio_venta_bruto is not None else current.precio_venta_bruto
        new_iva = iva_porcentaje if iva_porcentaje is not None else current.iva_porcentaje
        new_iva_inc = iva_incluido if iva_incluido is not None else current.iva_incluido
        new_img = imagen_url if imagen_url is not None else current.imagen_url

        raw_items = items if items is not None else current.items_fijos
        raw_grp = grupos_opciones if grupos_opciones is not None else current.grupos_opciones

        # Validar ítems
        for idx, it in enumerate(raw_items):
            if it.id is None:
                it.id = self._next_item_id
                self._next_item_id += 1
            has_prod = it.producto_id is not None
            has_rec = it.receta_id is not None
            if has_prod == has_rec:
                raise PolymorphicReferenceError(
                    "ComboItem must reference exactly one target: either 'producto_id' or 'receta_id'."
                )
            if it.cantidad <= ZERO:
                raise InvalidQuantityError("Combo item quantity must be strictly greater than 0.")

        explicit_dyn = es_dinamico if es_dinamico is not None else current.es_dinamico
        auto_dinamico = bool(explicit_dyn or len(raw_grp) > 0)

        (
            costo_total,
            neto_final,
            bruto_final,
            margen_amount,
            margen_pct,
            food_cost_pct,
        ) = self._calculate_combo_costs(
            items=raw_items,
            grupos_links=raw_grp,
            precio_venta_neto=new_net,
            precio_venta_bruto=new_bruto,
            iva_porcentaje=new_iva,
            tenant_id=tenant_id,
        )

        stock_avail, is_avail = self._calculate_theoretical_stock(
            raw_items,
            tenant_id,
            combo_id=combo_id,
            is_dynamic=auto_dinamico,
            notes=new_desc,
        )

        cat_nombre = None
        if new_cat is not None:
            cat = self.get_category(new_cat, tenant_id)
            if cat:
                cat_nombre = cat.nombre

        # Actualizar registros de uso en OptionGroupService
        for old_grp in current.grupos_opciones:
            self.option_group_service.unregister_usage(old_grp.grupo_id, combo_id=combo_id)
        for grp in raw_grp:
            self.option_group_service.register_usage(grp.grupo_id, combo_id=combo_id)

        updated = ComboDTO(
            id=combo_id,
            codigo=new_code,
            nombre=new_name.strip(),
            descripcion=new_desc.strip() if new_desc else None,
            categoria_combo_id=new_cat,
            categoria_nombre=cat_nombre,
            es_dinamico=auto_dinamico,
            precio_venta_neto=neto_final,
            precio_venta_bruto=bruto_final,
            iva_porcentaje=new_iva,
            iva_incluido=new_iva_inc,
            costo_total_calculado=costo_total,
            margen_amount=margen_amount,
            margen_pct=margen_pct,
            food_cost_pct=food_cost_pct,
            disponibilidad_stock_porciones=stock_avail,
            esta_disponible=is_avail,
            imagen_url=new_img,
            items_fijos=raw_items,
            grupos_opciones=raw_grp,
            tenant_id=tenant_id,
        )
        self._combos[(tenant_id, combo_id)] = updated
        return updated

    def delete_combo(self, combo_id: int, tenant_id: str = "default") -> None:
        """Soft-delete de combo."""
        combo = self.get_combo(combo_id, tenant_id)
        for grp in combo.grupos_opciones:
            self.option_group_service.unregister_usage(grp.grupo_id, combo_id=combo_id)
        combo.is_deleted = True
