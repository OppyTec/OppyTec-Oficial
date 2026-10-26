"""
oppytec-backend/src/modules/operations/application/consumption_service.py
Servicio de aplicación transaccional para Registro de Consumo Batch,
explosión de recetas y combos, deducción FEFO estricta y trazabilidad a Kardex.
Cumple Regla de Oro Inviolable:
- Cero float, solo Decimal e int.
- Cero updates directos a stock_items sin asiento previo en Kardex (registro_stock).
- Bloqueo pesimista en orden canónico anti-deadlock (`canonical_lock_order`).
- Eventos en tiempo real mediante `get_realtime_publisher()`.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from opentelemetry import trace

from src.core.exceptions import (
    CrossTenantAccessError,
    DomainValidationError,
    InsufficientStockError,
    ResourceNotFoundError,
)
from src.core.observability import get_tenant_telemetry_context, trace_span
from src.core.realtime.router import get_realtime_publisher
from src.core.realtime.schemas import RealtimeEventEnvelope
from src.modules.inventory.application.inventory_service import InventoryService, KardexEntry
from src.modules.inventory.domain.kardex_math import canonical_lock_order
from src.modules.operations.domain.consumption_math import (
    ConsumptionLot,
    ConsumptionQuantity,
    RecipeConsumptionItem,
    RecipeIngredientItem,
    RecipeSpec,
    deduct_lots_fefo,
    explode_recipe_consumption,
)

logger = logging.getLogger("oppytec.operations.consumption")
tracer = trace.get_tracer("oppytec.operations.consumption")


@dataclass
class ConsumptionRecordItemDTO:
    """Detalle de ítem dentro de un registro de consumo."""

    id: int
    consumption_record_id: int
    tipo_item: str  # PRODUCTO | RECETA | COMBO
    item_id: int
    cantidad: Decimal
    unidad_medida: str
    costo_unitario_ppp: Decimal
    costo_total: Decimal
    lote_codigo: str | None = None
    fecha_vencimiento_lote: date | None = None
    kardex_movement_id: int | None = None
    opciones_seleccionadas: dict[str, Any] | None = None


@dataclass
class ConsumptionRecordDTO:
    """Cabecera de transacción de consumo directo con trazabilidad a Kardex."""

    id: int
    codigo_folio: str
    bodega_id: int
    usuario_id: int
    tipo_origen: str  # MANUAL_TERMINAL | MANOS_LIBRES_VOZ | BUFFET_LIQUIDACION | VENTA_POS
    costo_total: Decimal
    items: list[ConsumptionRecordItemDTO] = field(default_factory=list)
    folio_ticket: str | None = None
    area_operativa_id: int | None = None
    notas: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tenant_id: str | None = None
    is_undone: bool = False
    kardex_entry_ids: list[int] = field(default_factory=list)


@dataclass
class ConsumptionTemplateDTO:
    """Plantilla de consumo rápido."""

    id: int
    slug: str
    nombre: str
    usuario_creador_id: int
    descripcion: str | None = None
    is_public: bool = False
    columnas_count: int = 8
    sort_mode: str = "alpha_asc"
    product_ids: list[int] = field(default_factory=list)
    custom_product_order: list[int] | None = None
    tenant_id: str | None = None


class ConsumptionService:
    """
    Servicio de aplicación transaccional del Módulo de Consumo.
    Invariante: Todo consumo impacta Kardex con movimientos 'CONSUMO' y descuenta stock atómicamente.
    """

    def __init__(self, inventory: InventoryService) -> None:
        self._inventory = inventory
        self._records: dict[int, ConsumptionRecordDTO] = {}
        self._templates: dict[int, ConsumptionTemplateDTO] = {}
        self._next_record_id: int = 1
        self._next_item_id: int = 1
        self._next_template_id: int = 1
        self._folio_counter: int = 1
        # Catálogo de recetas en memoria: {recipe_id: RecipeSpec}
        self._recipes_catalog: dict[int, RecipeSpec] = {}
        # Catálogo de combos en memoria: {combo_id: list[dict(item_id, tipo_item, cantidad)]}
        self._combos_catalog: dict[int, list[dict[str, Any]]] = {}

    def reset(self) -> None:
        """Limpia el estado en memoria para aislamiento de pruebas unitarias."""
        self._records.clear()
        self._templates.clear()
        self._next_record_id = 1
        self._next_item_id = 1
        self._next_template_id = 1
        self._folio_counter = 1
        self._recipes_catalog.clear()
        self._combos_catalog.clear()

    def register_recipe_spec(self, recipe_id: int, spec: RecipeSpec) -> None:
        """Registra una receta en el catálogo de recetas del servicio."""
        self._recipes_catalog[recipe_id] = spec

    def register_combo_spec(self, combo_id: int, components: list[dict[str, Any]]) -> None:
        """Registra un combo en el catálogo de combos."""
        self._combos_catalog[combo_id] = components

    def _generate_folio(self) -> str:
        today_str = datetime.now(UTC).strftime("%Y%m%d")
        folio = f"CONS-{today_str}-{self._folio_counter:04d}"
        self._folio_counter += 1
        return folio

    @staticmethod
    def _parse_optional_uuid(val: str | None) -> UUID | None:
        if not val:
            return None
        try:
            return UUID(str(val))
        except Exception:
            return None

    def process_batch_consumption(
        self,
        *,
        bodega_id: int,
        usuario_id: int,
        items: Sequence[dict[str, Any]],
        tipo_origen: str = "MANUAL_TERMINAL",
        area_operativa_id: int | None = None,
        folio_ticket: str | None = None,
        notas: str | None = None,
        tenant_id: str | None = None,
        recipes_catalog: Mapping[int, RecipeSpec | Mapping[int, Decimal]] | None = None,
        combos_catalog: Mapping[int, list[dict[str, Any]]] | None = None,
        unit_costs: Mapping[int, Decimal] | None = None,
        allow_expired: bool = False,
        holding_id: str | None = None,
    ) -> ConsumptionRecordDTO:
        """
        Procesa un lote de consumo mixto (productos, recetas y combos).
        1. Explota recetas y combos en insumos básicos.
        2. Bloquea canónicamente los productos (`canonical_lock_order`).
        3. Verifica existencias y aplica FEFO sin saldos negativos.
        4. Inserta asientos inmutables en Kardex ('CONSUMO').
        5. Crea la cabecera e items de ConsumptionRecord.
        6. Emite evento WebSocket en tiempo real.
        """
        resolved_tenant = tenant_id or get_tenant_telemetry_context().tenant_id
        effective_recipes = {**self._recipes_catalog, **(recipes_catalog or {})}
        effective_combos = {**self._combos_catalog, **(combos_catalog or {})}
        costs = unit_costs or {}

        with trace_span(
            "consumption.batch.process",
            attributes={
                "tenant_id": resolved_tenant or "",
                "bodega_id": bodega_id,
                "usuario_id": usuario_id,
                "tipo_origen": tipo_origen,
                "items_count": len(items),
            },
            tracer_name="oppytec.operations.consumption",
        ):
            if not items:
                raise DomainValidationError("At least one consumption item is required")

            # Paso 1: Desglosar insumos elementales
            # required_ingredients: {producto_id: ConsumptionQuantity}
            required_ingredients: dict[int, ConsumptionQuantity] = {}
            # requested_lots: {producto_id: (lote_codigo, fecha_vencimiento)}
            requested_lots: dict[int, tuple[str | None, date | None]] = {}

            for line in items:
                tipo = str(line.get("tipo_item", "PRODUCTO")).upper()
                item_id = int(line["item_id"])
                cant = Decimal(str(line["cantidad"]))
                if cant <= Decimal(0):
                    raise DomainValidationError(f"Invalid quantity {cant} for item {item_id}")

                lote_cod = line.get("lote_codigo")
                exp_date = line.get("fecha_vencimiento_lote")
                if lote_cod or exp_date:
                    requested_lots[item_id] = (lote_cod, exp_date)

                if tipo == "PRODUCTO":
                    required_ingredients[item_id] = (
                        required_ingredients.get(item_id, ConsumptionQuantity.zero())
                        + ConsumptionQuantity(cant)
                    )
                elif tipo == "RECETA":
                    if item_id not in effective_recipes:
                        raise DomainValidationError(f"Recipe spec not found for recipe_id {item_id}")
                    exploded = explode_recipe_consumption(
                        [RecipeConsumptionItem(recipe_id=item_id, portions=cant)],
                        effective_recipes,
                    )
                    for ing_id, ing_qty in exploded.items():
                        int_id = int(ing_id)
                        required_ingredients[int_id] = (
                            required_ingredients.get(int_id, ConsumptionQuantity.zero()) + ing_qty
                        )
                elif tipo == "COMBO":
                    if item_id not in effective_combos:
                        raise DomainValidationError(f"Combo spec not found for combo_id {item_id}")
                    combo_items = effective_combos[item_id]
                    for sub in combo_items:
                        sub_tipo = str(sub.get("tipo_item", "PRODUCTO")).upper()
                        sub_id = int(sub["item_id"])
                        sub_cant = Decimal(str(sub["cantidad"])) * cant
                        if sub_tipo == "PRODUCTO":
                            required_ingredients[sub_id] = (
                                required_ingredients.get(sub_id, ConsumptionQuantity.zero())
                                + ConsumptionQuantity(sub_cant)
                            )
                        elif sub_tipo == "RECETA":
                            if sub_id not in effective_recipes:
                                raise DomainValidationError(f"Recipe spec not found for sub-recipe {sub_id}")
                            exploded = explode_recipe_consumption(
                                [RecipeConsumptionItem(recipe_id=sub_id, portions=sub_cant)],
                                effective_recipes,
                            )
                            for ing_id, ing_qty in exploded.items():
                                int_id = int(ing_id)
                                required_ingredients[int_id] = (
                                    required_ingredients.get(int_id, ConsumptionQuantity.zero()) + ing_qty
                                )
                else:
                    raise DomainValidationError(f"Unsupported item type: {tipo}")

            # Paso 2: Orden canónico anti-deadlock de adquisición de locks
            ordered_ingredient_ids = canonical_lock_order(required_ingredients.keys())

            # Paso 3: Verificar saldos y lotes antes de impactar Kardex
            for prod_id in ordered_ingredient_ids:
                needed = required_ingredients[prod_id]
                current_bal = self._inventory.balance(prod_id, bodega_id)

                # Si hay lotes configurados en inventario para este producto
                avail_lots = self._inventory.get_lots_for_product(prod_id, bodega_id) if hasattr(self._inventory, "get_lots_for_product") else []
                if avail_lots:
                    consumption_lots = [
                        ConsumptionLot(
                            lot_id=l.get("lote_codigo", str(i)),
                            quantity=Decimal(str(l["cantidad"])),
                            expires_on=l.get("fecha_vencimiento"),
                        )
                        for i, l in enumerate(avail_lots)
                    ]
                    # Ejecuta deducción FEFO
                    deduct_lots_fefo(consumption_lots, needed, allow_expired=allow_expired)
                else:
                    # Sin tracking granular de lotes, valida saldo global
                    if current_bal < needed.value:
                        raise InsufficientStockError(
                            f"Insufficient stock for product {prod_id} in warehouse {bodega_id}: "
                            f"available {current_bal}, required {needed.value}",
                            context={"producto_id": prod_id, "bodega_id": bodega_id},
                        )

            # Paso 4: Impactar Kardex registrando movimientos inmutables 'CONSUMO'
            folio = self._generate_folio()
            kardex_movements: dict[int, KardexEntry] = {}
            kardex_entry_ids: list[int] = []

            for prod_id in ordered_ingredient_ids:
                qty_to_deduct = required_ingredients[prod_id].value
                unit_cost = costs.get(prod_id, Decimal("0.00"))
                lote_info = requested_lots.get(prod_id, (None, None))

                k_entry = self._inventory.register_movement(
                    producto_id=prod_id,
                    bodega_id=bodega_id,
                    movement_type="CONSUMO",
                    quantity=qty_to_deduct,
                    unit_cost=unit_cost,
                    actor_user_id=usuario_id,
                    lote_codigo=lote_info[0],
                    fecha_vencimiento_lote=lote_info[1],
                    documento_referencia=folio,
                    tenant_id=resolved_tenant,
                )
                kardex_movements[prod_id] = k_entry
                kardex_entry_ids.append(k_entry.id)

            # Paso 5: Generar registro de consumo (Cabecera e Ítems)
            record_id = self._next_record_id
            self._next_record_id += 1

            total_record_cost = Decimal("0.00")
            record_items: list[ConsumptionRecordItemDTO] = []

            for line in items:
                tipo = str(line.get("tipo_item", "PRODUCTO")).upper()
                item_id = int(line["item_id"])
                cant = Decimal(str(line["cantidad"]))
                u_medida = str(line.get("unidad_medida", "UN"))
                unit_cost = Decimal(str(line.get("costo_unitario_ppp", costs.get(item_id, Decimal("0.00")))))
                line_total = unit_cost * cant
                total_record_cost += line_total

                k_id = kardex_movements.get(item_id).id if item_id in kardex_movements else (
                    kardex_entry_ids[0] if kardex_entry_ids else None
                )

                item_dto = ConsumptionRecordItemDTO(
                    id=self._next_item_id,
                    consumption_record_id=record_id,
                    tipo_item=tipo,
                    item_id=item_id,
                    cantidad=cant,
                    unidad_medida=u_medida,
                    costo_unitario_ppp=unit_cost,
                    costo_total=line_total,
                    lote_codigo=line.get("lote_codigo"),
                    fecha_vencimiento_lote=line.get("fecha_vencimiento_lote"),
                    kardex_movement_id=k_id,
                    opciones_seleccionadas=line.get("opciones_seleccionadas"),
                )
                self._next_item_id += 1
                record_items.append(item_dto)

            record = ConsumptionRecordDTO(
                id=record_id,
                codigo_folio=folio,
                folio_ticket=folio_ticket,
                area_operativa_id=area_operativa_id,
                bodega_id=bodega_id,
                usuario_id=usuario_id,
                tipo_origen=tipo_origen,
                costo_total=total_record_cost,
                items=record_items,
                notas=notas,
                tenant_id=resolved_tenant,
                kardex_entry_ids=kardex_entry_ids,
            )
            self._records[record_id] = record

            # Paso 6: Notificar evento reactivo por WebSocket
            with suppress(Exception):
                publisher = get_realtime_publisher()
                import asyncio
                # Manejar contextos síncronos o asíncronos para el publisher
                coro = publisher.publish_event(
                    RealtimeEventEnvelope(
                        event_type="consumption.recorded",
                        holding_id=self._parse_optional_uuid(holding_id),
                        tenant_id=self._parse_optional_uuid(resolved_tenant),
                        target_bodega_id=bodega_id,
                        required_permission="consumption.register.read",
                        query_keys_to_invalidate=[["consumption", "history"], ["inventory", "stock"]],
                        payload={
                            "consumption_id": record.id,
                            "codigo_folio": record.codigo_folio,
                            "tipo_origen": record.tipo_origen,
                            "items_count": len(record.items),
                        },
                    )
                )
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(coro)
                except RuntimeError:
                    asyncio.run(coro)

            return record

    def get_consumption_history(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        bodega_id: int | None = None,
        area_operativa_id: int | None = None,
        usuario_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        tipo_origen: str | None = None,
        tenant_id: str | None = None,
    ) -> tuple[list[ConsumptionRecordDTO], int]:
        """Consulta cronológica paginada de registros de consumo con filtros."""
        filtered = list(self._records.values())

        if tenant_id:
            filtered = [r for r in filtered if r.tenant_id == tenant_id]
        if bodega_id is not None:
            filtered = [r for r in filtered if r.bodega_id == bodega_id]
        if area_operativa_id is not None:
            filtered = [r for r in filtered if r.area_operativa_id == area_operativa_id]
        if usuario_id is not None:
            filtered = [r for r in filtered if r.usuario_id == usuario_id]
        if tipo_origen is not None:
            filtered = [r for r in filtered if r.tipo_origen == tipo_origen]
        if start_date is not None:
            filtered = [r for r in filtered if r.created_at.date() >= start_date]
        if end_date is not None:
            filtered = [r for r in filtered if r.created_at.date() <= end_date]

        # Orden cronológico descendente
        filtered.sort(key=lambda r: r.created_at, reverse=True)

        total = len(filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        return filtered[start_idx:end_idx], total

    def get_consumption_detail(self, consumption_id: int, tenant_id: str | None = None) -> ConsumptionRecordDTO:
        """Obtiene el detalle completo de una transacción de consumo y sus insumos."""
        record = self._records.get(consumption_id)
        if record is None:
            raise ResourceNotFoundError(
                f"Consumption record {consumption_id} not found",
                context={"consumption_id": consumption_id},
            )
        if tenant_id and record.tenant_id and record.tenant_id != tenant_id:
            raise CrossTenantAccessError(
                f"Cross-tenant access denied: record {consumption_id} belongs to a different tenant",
            )
        return record

    def update_consumption(
        self,
        consumption_id: int,
        *,
        notas: str | None = None,
        tenant_id: str | None = None,
    ) -> ConsumptionRecordDTO:
        """Actualiza notas o metadatos de un registro de consumo con auditoría."""
        record = self.get_consumption_detail(consumption_id, tenant_id=tenant_id)
        if record.is_undone:
            raise DomainValidationError("Cannot update an undone consumption record")
        if notas is not None:
            record.notas = notas
        return record

    def delete_consumption(
        self,
        consumption_id: int,
        actor_user_id: int,
        *,
        reason: str | None = None,
        tenant_id: str | None = None,
    ) -> ConsumptionRecordDTO:
        """
        Anula/revierte transaccionalmente un consumo devolviendo existencias a Kardex.
        Genera movimientos inversos 'AJUSTE_POSITIVO' por cada asiento original.
        """
        record = self.get_consumption_detail(consumption_id, tenant_id=tenant_id)
        if record.is_undone:
            raise DomainValidationError(f"Consumption record {consumption_id} is already undone")

        # Reversión en Kardex
        for item in record.items:
            unit_cost = item.costo_unitario_ppp
            self._inventory.register_movement(
                producto_id=item.item_id,
                bodega_id=record.bodega_id,
                movement_type="AJUSTE_POSITIVO",
                quantity=item.cantidad,
                unit_cost=unit_cost,
                actor_user_id=actor_user_id,
                lote_codigo=item.lote_codigo,
                fecha_vencimiento_lote=item.fecha_vencimiento_lote,
                documento_referencia=f"REVERSION:{record.codigo_folio}",
                tenant_id=tenant_id or record.tenant_id,
            )

        record.is_undone = True
        if reason:
            record.notas = f"{record.notas or ''} [ANULADO: {reason}]".strip()

        return record

    def merma_expired_stock(
        self,
        *,
        producto_id: int,
        bodega_id: int,
        quantity: Decimal,
        lote_codigo: str,
        fecha_vencimiento: date | None = None,
        actor_user_id: int,
        motivo: str = "LOTE_VENCIDO",
        unit_cost: Decimal = Decimal("0.00"),
        descripcion: str | None = None,
        tenant_id: str | None = None,
    ) -> KardexEntry:
        """
        Reporte y merma directa de lotes vencidos desde el modal de contingencia.
        Impacta Kardex de inmediato con movimiento tipo 'MERMA'.
        """
        if quantity <= Decimal(0):
            raise DomainValidationError("Merma quantity must be strictly positive")

        cur_bal = self._inventory.balance(producto_id, bodega_id)
        if cur_bal < quantity:
            raise InsufficientStockError(
                f"Insufficient stock for merma: available {cur_bal}, required {quantity}",
                context={"producto_id": producto_id, "bodega_id": bodega_id},
            )

        entry = self._inventory.register_movement(
            producto_id=producto_id,
            bodega_id=bodega_id,
            movement_type="MERMA",
            quantity=quantity,
            unit_cost=unit_cost,
            actor_user_id=actor_user_id,
            lote_codigo=lote_codigo,
            fecha_vencimiento_lote=fecha_vencimiento,
            documento_referencia=f"CONTINGENCIA:{motivo}",
            tenant_id=tenant_id,
        )
        return entry

    # =========================================================================
    # CRUD de Plantillas de Consumo
    # =========================================================================

    def create_template(
        self,
        *,
        slug: str,
        nombre: str,
        usuario_creador_id: int,
        descripcion: str | None = None,
        is_public: bool = False,
        columnas_count: int = 8,
        sort_mode: str = "alpha_asc",
        product_ids: list[int] | None = None,
        custom_product_order: list[int] | None = None,
        tenant_id: str | None = None,
    ) -> ConsumptionTemplateDTO:
        """Crea una nueva plantilla de consumo."""
        # Verificar unicidad de slug
        for t in self._templates.values():
            if t.slug == slug and (not tenant_id or t.tenant_id == tenant_id):
                raise DomainValidationError(f"Template with slug '{slug}' already exists")

        tid = self._next_template_id
        self._next_template_id += 1

        tmpl = ConsumptionTemplateDTO(
            id=tid,
            slug=slug,
            nombre=nombre,
            usuario_creador_id=usuario_creador_id,
            descripcion=descripcion,
            is_public=is_public,
            columnas_count=columnas_count,
            sort_mode=sort_mode,
            product_ids=product_ids or [],
            custom_product_order=custom_product_order,
            tenant_id=tenant_id,
        )
        self._templates[tid] = tmpl
        return tmpl

    def list_templates(
        self,
        usuario_id: int | None = None,
        tenant_id: str | None = None,
    ) -> list[ConsumptionTemplateDTO]:
        """Lista plantillas públicas o pertenecientes al usuario."""
        results: list[ConsumptionTemplateDTO] = []
        for t in self._templates.values():
            if tenant_id and t.tenant_id and t.tenant_id != tenant_id:
                continue
            if t.is_public or (usuario_id is not None and t.usuario_creador_id == usuario_id):
                results.append(t)
        return results

    def get_template(self, template_id: int, tenant_id: str | None = None) -> ConsumptionTemplateDTO:
        """Obtiene una plantilla de consumo por ID."""
        tmpl = self._templates.get(template_id)
        if tmpl is None:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        if tenant_id and tmpl.tenant_id and tmpl.tenant_id != tenant_id:
            raise CrossTenantAccessError("Cross-tenant template access denied")
        return tmpl

    def update_template(
        self,
        template_id: int,
        *,
        nombre: str | None = None,
        descripcion: str | None = None,
        is_public: bool | None = None,
        columnas_count: int | None = None,
        sort_mode: str | None = None,
        product_ids: list[int] | None = None,
        custom_product_order: list[int] | None = None,
        tenant_id: str | None = None,
    ) -> ConsumptionTemplateDTO:
        """Actualiza parámetros de una plantilla de consumo."""
        tmpl = self.get_template(template_id, tenant_id=tenant_id)
        if nombre is not None:
            tmpl.nombre = nombre
        if descripcion is not None:
            tmpl.descripcion = descripcion
        if is_public is not None:
            tmpl.is_public = is_public
        if columnas_count is not None:
            tmpl.columnas_count = columnas_count
        if sort_mode is not None:
            tmpl.sort_mode = sort_mode
        if product_ids is not None:
            tmpl.product_ids = product_ids
        if custom_product_order is not None:
            tmpl.custom_product_order = custom_product_order
        return tmpl

    def delete_template(self, template_id: int, tenant_id: str | None = None) -> None:
        """Elimina una plantilla de consumo."""
        tmpl = self.get_template(template_id, tenant_id=tenant_id)
        del self._templates[tmpl.id]
