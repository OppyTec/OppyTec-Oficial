"""
oppytec-backend/src/modules/inventory/application/inventory_service.py
Servicio de Kardex por bodega: movimientos atómicos con saldo resultante,
orden canónico de locks (anti-deadlock), gestión de estados de stock,
política FEFO y soporte transaccional para revertir (undo) y reaplicar (redo).
Cumple con Clean Architecture y Regla Inmutable 02 (cero floats, precisión Decimal estricta).
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable, Sequence
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
    TransferSameWarehouseError,
)
from src.core.observability import get_tenant_telemetry_context, trace_span
from src.modules.inventory.domain.entities import StockItem
from src.modules.inventory.domain.kardex_math import apply_movement, canonical_lock_order
from src.modules.inventory.domain.value_objects import (
    MovementType,
    StockQuantity,
    StorageLocation,
)

logger = logging.getLogger("oppytec.inventory")
tracer = trace.get_tracer("oppytec.inventory")


@dataclass(frozen=True)
class LotStatusResult:
    """Detalle de lote físico en stock."""

    lote_codigo: str | None
    fecha_vencimiento: date | None
    cantidad: Decimal


@dataclass(frozen=True)
class StockStatusResult:
    """Snapshot consolidado de existencias y semáforos de un producto en bodega."""

    producto_id: int
    bodega_id: int
    stock_actual: Decimal
    stock_minimo: Decimal
    stock_maximo: Decimal | None
    punto_reorden: Decimal | None
    pasillo: str | None
    estante: str | None
    nivel: str | None
    is_below_minimum: bool
    is_critical: bool
    needs_reorder: bool
    lots: tuple[LotStatusResult, ...]


@dataclass(frozen=True)
class KardexEntry:
    """Movimiento append-only inmutable del Kardex con auditoría completa."""

    producto_id: int
    bodega_id: int
    movement_type: str
    quantity: Decimal
    resulting_balance: Decimal
    unit_cost: Decimal
    actor_user_id: int
    id: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    lote_codigo: str | None = None
    fecha_vencimiento_lote: date | None = None
    transfer_id: UUID | None = None
    documento_referencia: str | None = None
    is_undone: bool = False
    tenant_id: str | None = None


class InventoryService:
    """
    Servicio de aplicación transaccional de inventario y Kardex.
    Invariante estricta: todo cambio de existencias ocurre exclusivamente a través de Kardex.
    """

    def __init__(self) -> None:
        self._balances: dict[tuple[int, int], Decimal] = {}
        self._ledger: list[KardexEntry] = []
        self._next_id: int = 1
        self._stock_configs: dict[tuple[int, int], dict[str, Any]] = {}
        self._lots: dict[tuple[int, int], list[dict[str, Any]]] = {}
        self._undone_entry_ids: set[int] = set()

    def reset(self) -> None:
        """Limpia balances, configuraciones y ledger en memoria para aislamiento de pruebas."""
        self._balances.clear()
        self._ledger.clear()
        self._next_id = 1
        self._stock_configs.clear()
        self._lots.clear()
        self._undone_entry_ids.clear()

    def balance(self, producto_id: int, bodega_id: int) -> Decimal:
        """Saldo actual del producto en la bodega."""
        return self._balances.get((producto_id, bodega_id), Decimal(0))

    @staticmethod
    def lock_order(producto_ids: Iterable[int]) -> list[int]:
        """Orden determinista `ORDER BY id ASC` para adquisición anti-deadlock de locks."""
        return canonical_lock_order(producto_ids)

    def configure_stock_item(
        self,
        producto_id: int,
        bodega_id: int,
        *,
        stock_minimo: Decimal = Decimal("0.0000"),
        stock_maximo: Decimal | None = None,
        punto_reorden: Decimal | None = None,
        pasillo: str | None = None,
        estante: str | None = None,
        nivel: str | None = None,
    ) -> None:
        """Configura los límites de stock y ubicación física de un producto en bodega."""
        self._stock_configs[(producto_id, bodega_id)] = {
            "stock_minimo": stock_minimo,
            "stock_maximo": stock_maximo,
            "punto_reorden": punto_reorden,
            "pasillo": pasillo,
            "estante": estante,
            "nivel": nivel,
        }

    def register_movement(
        self,
        *,
        producto_id: int,
        bodega_id: int,
        movement_type: str,
        quantity: Decimal,
        unit_cost: Decimal,
        actor_user_id: int,
        lote_codigo: str | None = None,
        fecha_vencimiento_lote: date | None = None,
        documento_referencia: str | None = None,
        transfer_id: UUID | None = None,
        is_positive_adjustment: bool | None = None,
        tenant_id: str | None = None,
    ) -> KardexEntry:
        """
        Registra un movimiento Append-Only inmutable en el Kardex y actualiza el saldo atómicamente.
        Valida que ninguna salida deje saldo negativo.
        Instrumentado con OpenTelemetry span 'inventory.movement.register' y logs estructurados.
        """
        resolved_tenant = tenant_id or get_tenant_telemetry_context().tenant_id
        with trace_span(
            "inventory.movement.register",
            attributes={
                "tenant_id": resolved_tenant,
                "bodega_id": bodega_id,
                "producto_id": producto_id,
                "movement_type": movement_type,
                "quantity": str(quantity),
                "unit_cost": str(unit_cost),
                "actor_user_id": actor_user_id,
                "user_id": str(actor_user_id),
                "transfer_id": str(transfer_id) if transfer_id else None,
                "transfer_uuid": str(transfer_id) if transfer_id else None,
            },
            tracer_name="oppytec.inventory",
        ) as span_attrs:
            parsed_type = MovementType.from_str(movement_type)
            cur_balance = self.balance(producto_id, bodega_id)

            if parsed_type == MovementType.AJUSTE_AUDITORIA:
                # Determinación de dirección para ajuste de auditoría
                is_entry = is_positive_adjustment if is_positive_adjustment is not None else quantity >= Decimal(0)
                abs_qty = abs(quantity)
                if is_entry:
                    new_balance = cur_balance + abs_qty
                else:
                    if cur_balance < abs_qty:
                        raise InsufficientStockError(
                            f"Insufficient stock in warehouse {bodega_id} for product {producto_id}: "
                            f"available {cur_balance}, required {abs_qty}",
                            context={"bodega_id": bodega_id, "producto_id": producto_id},
                        )
                    new_balance = cur_balance - abs_qty
            else:
                new_balance = apply_movement(cur_balance, parsed_type, quantity)

            entry_id = self._next_id
            self._next_id += 1

            entry = KardexEntry(
                id=entry_id,
                producto_id=producto_id,
                bodega_id=bodega_id,
                movement_type=parsed_type.value,
                quantity=abs(quantity),
                resulting_balance=new_balance,
                unit_cost=unit_cost,
                actor_user_id=actor_user_id,
                lote_codigo=lote_codigo,
                fecha_vencimiento_lote=fecha_vencimiento_lote,
                documento_referencia=documento_referencia,
                transfer_id=transfer_id,
                tenant_id=resolved_tenant,
            )

            self._balances[(producto_id, bodega_id)] = new_balance
            self._ledger.append(entry)

            # Seguimiento de lotes si aplica
            if lote_codigo or fecha_vencimiento_lote:
                lots = self._lots.setdefault((producto_id, bodega_id), [])
                # Si es entrada, agregamos o incrementamos lote
                if parsed_type in (MovementType.ENTRADA, MovementType.COMPRA, MovementType.TRASPASO_IN, MovementType.AJUSTE_POSITIVO) or (
                    parsed_type == MovementType.AJUSTE_AUDITORIA and (is_positive_adjustment is True or quantity > 0)
                ):
                    matched = next((lot for lot in lots if lot.get("lote_codigo") == lote_codigo), None)
                    if matched:
                        matched["cantidad"] = matched.get("cantidad", Decimal(0)) + abs(quantity)
                    else:
                        lots.append({
                            "lote_codigo": lote_codigo,
                            "fecha_vencimiento": fecha_vencimiento_lote,
                            "cantidad": abs(quantity),
                        })
                elif parsed_type in (MovementType.SALIDA, MovementType.CONSUMO, MovementType.MERMA, MovementType.TRASPASO_OUT, MovementType.AJUSTE_NEGATIVO) or (
                    parsed_type == MovementType.AJUSTE_AUDITORIA and (is_positive_adjustment is False or quantity < 0)
                ):
                    matched = next((lot for lot in lots if lot.get("lote_codigo") == lote_codigo), None)
                    if matched:
                        matched["cantidad"] = max(Decimal(0), matched.get("cantidad", Decimal(0)) - abs(quantity))

            span_attrs["entry_id"] = entry.id
            span_attrs["resulting_balance"] = str(new_balance)
            return entry

    def transfer_stock_bulk(
        self,
        *,
        bodega_origen_id: int,
        bodega_destino_id: int,
        items: Sequence[Any],
        actor_user_id: int,
        transfer_uuid: UUID | None = None,
        notas: str | None = None,
        tenant_id: str | None = None,
    ) -> list[tuple[KardexEntry, KardexEntry]]:
        """
        Traslado atómico inter-bodega con validación de saldo previo y adquisición en orden canónico.
        Genera pares balanceados de movimientos en Kardex (`TRASPASO_OUT` y `TRASPASO_IN`)
        vinculados por el mismo `transfer_id`.
        Instrumentado con OpenTelemetry span 'inventory.transfer.execute' y logs estructurados.
        """
        resolved_tenant = tenant_id or get_tenant_telemetry_context().tenant_id
        resolved_transfer_id = transfer_uuid or uuid.uuid4()

        with trace_span(
            "inventory.transfer.execute",
            attributes={
                "tenant_id": resolved_tenant,
                "bodega_origen_id": bodega_origen_id,
                "bodega_destino_id": bodega_destino_id,
                "bodega_id": bodega_origen_id,
                "items_count": len(items),
                "transfer_uuid": str(resolved_transfer_id),
                "actor_user_id": actor_user_id,
                "user_id": str(actor_user_id),
            },
            tracer_name="oppytec.inventory",
        ) as span_attrs:
            if bodega_origen_id == bodega_destino_id:
                raise TransferSameWarehouseError(
                    f"Origin warehouse ({bodega_origen_id}) and destination warehouse ({bodega_destino_id}) cannot be the same.",
                    context={"origin_id": bodega_origen_id, "destination_id": bodega_destino_id},
                )

            # Extraer items soportando Pydantic models, diccionarios o tuplas
            parsed_items: list[tuple[int, Decimal]] = []
            for it in items:
                if hasattr(it, "producto_id") and hasattr(it, "cantidad"):
                    parsed_items.append((int(it.producto_id), Decimal(str(it.cantidad))))
                elif isinstance(it, dict):
                    parsed_items.append((int(it["producto_id"]), Decimal(str(it["cantidad"]))))
                elif isinstance(it, (tuple, list)) and len(it) == 2:
                    parsed_items.append((int(it[0]), Decimal(str(it[1]))))
                else:
                    raise ValueError(f"Unsupported item format in bulk transfer: {it}")

            span_attrs["parsed_items_count"] = len(parsed_items)

            # Bloqueo en orden canónico
            ordered_pids = self.lock_order([pid for pid, _ in parsed_items])
            items_by_pid = dict(parsed_items)

            # 1. Validación previa de existencia suficiente en origen para todos los ítems
            for pid in ordered_pids:
                qty = items_by_pid[pid]
                current_origin = self.balance(pid, bodega_origen_id)
                if current_origin < qty:
                    raise InsufficientStockError(
                        f"Insufficient stock for product {pid} in origin warehouse {bodega_origen_id}. Available: {current_origin}, Required: {qty}",
                        context={
                            "producto_id": pid,
                            "bodega_id": bodega_origen_id,
                            "available": str(current_origin),
                            "required": str(qty),
                        },
                    )

            # 2. Ejecución atómica de movimientos balanceados
            results: list[tuple[KardexEntry, KardexEntry]] = []
            for pid in ordered_pids:
                qty = items_by_pid[pid]
                out_entry = self.register_movement(
                    producto_id=pid,
                    bodega_id=bodega_origen_id,
                    movement_type="TRASPASO_OUT",
                    quantity=qty,
                    unit_cost=Decimal("0.00"),
                    actor_user_id=actor_user_id,
                    transfer_id=resolved_transfer_id,
                    documento_referencia=notas,
                    tenant_id=resolved_tenant,
                )
                in_entry = self.register_movement(
                    producto_id=pid,
                    bodega_id=bodega_destino_id,
                    movement_type="TRASPASO_IN",
                    quantity=qty,
                    unit_cost=Decimal("0.00"),
                    actor_user_id=actor_user_id,
                    transfer_id=resolved_transfer_id,
                    documento_referencia=notas,
                    tenant_id=resolved_tenant,
                )
                results.append((out_entry, in_entry))

            span_attrs["transferred_pairs_count"] = len(results)
            return results

    def get_stock_status(
        self,
        bodega_id: int,
        area_operativa_id: int | None = None,
    ) -> list[StockStatusResult]:
        """
        Retorna snapshot consolidado de existencias en bodega, desglosado por lotes,
        ubicaciones físicas y semáforos de stock (crítico, bajo mínimo, reorden).
        """
        _ = area_operativa_id
        product_ids = sorted(
            {pid for (pid, bid) in self._balances if bid == bodega_id}
            | {pid for (pid, bid) in self._stock_configs if bid == bodega_id}
        )

        results: list[StockStatusResult] = []
        for pid in product_ids:
            stock_act = self.balance(pid, bodega_id)
            cfg = self._stock_configs.get((pid, bodega_id), {})
            stock_min = cfg.get("stock_minimo", Decimal("0.0000"))
            stock_max = cfg.get("stock_maximo")
            reorder = cfg.get("punto_reorden")
            pasillo = cfg.get("pasillo")
            estante = cfg.get("estante")
            nivel = cfg.get("nivel")

            item = StockItem(
                producto_id=pid,
                bodega_id=bodega_id,
                stock_actual=StockQuantity(stock_act),
                stock_minimo=StockQuantity(stock_min),
                stock_maximo=StockQuantity(stock_max) if stock_max is not None else None,
                punto_reorden=StockQuantity(reorder) if reorder is not None else None,
                location=StorageLocation(pasillo=pasillo, estante=estante, nivel=nivel),
            )

            raw_lots = self._lots.get((pid, bodega_id), [])
            lots_list = tuple(
                LotStatusResult(
                    lote_codigo=lot.get("lote_codigo"),
                    fecha_vencimiento=lot.get("fecha_vencimiento"),
                    cantidad=Decimal(str(lot.get("cantidad", 0))),
                )
                for lot in raw_lots
                if Decimal(str(lot.get("cantidad", 0))) > Decimal(0)
            )

            results.append(
                StockStatusResult(
                    producto_id=pid,
                    bodega_id=bodega_id,
                    stock_actual=stock_act,
                    stock_minimo=stock_min,
                    stock_maximo=stock_max,
                    punto_reorden=reorder,
                    pasillo=pasillo,
                    estante=estante,
                    nivel=nivel,
                    is_below_minimum=item.is_below_minimum(),
                    is_critical=item.is_critical(),
                    needs_reorder=item.needs_reorder(),
                    lots=lots_list,
                )
            )

        return results

    def undo_movement(
        self,
        movement_id: int,
        actor_user_id: int,
        reason: str = "",
        tenant_id: str | None = None,
    ) -> KardexEntry:
        """
        Revierte transaccionalmente un movimiento previo del Kardex.
        Como el Kardex es inmutable (Append-Only), no elimina el registro original sino que
        aplica un asiento compensatorio inverso con trazabilidad de auditoría y aislamiento de tenant.
        """
        orig = next((e for e in self._ledger if e.id == movement_id), None)
        if orig is None:
            raise ResourceNotFoundError(
                f"Kardex movement {movement_id} not found.",
                i18n_key="inventory:errors.movement_not_found",
            )

        if tenant_id and orig.tenant_id and orig.tenant_id != tenant_id:
            raise CrossTenantAccessError(
                f"Cross-tenant access denied: movement {movement_id} belongs to a different tenant.",
                i18n_key="tenancy:errors.cross_tenant_forbidden",
            )

        if movement_id in self._undone_entry_ids:
            raise DomainValidationError(
                f"Movement {movement_id} has already been undone.",
                i18n_key="inventory:errors.movement_already_undone",
            )

        parsed_type = MovementType.from_str(orig.movement_type)
        is_entry = parsed_type in (
            MovementType.ENTRADA,
            MovementType.COMPRA,
            MovementType.TRASPASO_IN,
            MovementType.AJUSTE_POSITIVO,
        )

        compensating_type = "AJUSTE_NEGATIVO" if is_entry else "AJUSTE_POSITIVO"

        comp_entry = self.register_movement(
            producto_id=orig.producto_id,
            bodega_id=orig.bodega_id,
            movement_type=compensating_type,
            quantity=orig.quantity,
            unit_cost=orig.unit_cost,
            actor_user_id=actor_user_id,
            lote_codigo=orig.lote_codigo,
            fecha_vencimiento_lote=orig.fecha_vencimiento_lote,
            documento_referencia=f"UNDO:{movement_id} {reason}".strip(),
            tenant_id=orig.tenant_id or tenant_id,
        )

        self._undone_entry_ids.add(movement_id)
        return comp_entry

    def redo_movement(
        self,
        movement_id: int,
        actor_user_id: int,
        reason: str = "",
        tenant_id: str | None = None,
    ) -> KardexEntry:
        """
        Reaplica un movimiento que fue previamente revertido (`undo`).
        Genera un nuevo asiento en Kardex con referencia de reaplicación y aislamiento de tenant.
        """
        orig = next((e for e in self._ledger if e.id == movement_id), None)
        if orig is None:
            raise ResourceNotFoundError(
                f"Kardex movement {movement_id} not found.",
                i18n_key="inventory:errors.movement_not_found",
            )

        if tenant_id and orig.tenant_id and orig.tenant_id != tenant_id:
            raise CrossTenantAccessError(
                f"Cross-tenant access denied: movement {movement_id} belongs to a different tenant.",
                i18n_key="tenancy:errors.cross_tenant_forbidden",
            )

        if movement_id not in self._undone_entry_ids:
            raise DomainValidationError(
                f"Movement {movement_id} is not in undone state and cannot be redone.",
                i18n_key="inventory:errors.movement_not_undone",
            )

        redo_entry = self.register_movement(
            producto_id=orig.producto_id,
            bodega_id=orig.bodega_id,
            movement_type=orig.movement_type,
            quantity=orig.quantity,
            unit_cost=orig.unit_cost,
            actor_user_id=actor_user_id,
            lote_codigo=orig.lote_codigo,
            fecha_vencimiento_lote=orig.fecha_vencimiento_lote,
            documento_referencia=f"REDO:{movement_id} {reason}".strip(),
            tenant_id=orig.tenant_id or tenant_id,
        )

        self._undone_entry_ids.remove(movement_id)
        return redo_entry

    def get_movement(self, movement_id: int, tenant_id: str | None = None) -> KardexEntry:
        """Obtiene un movimiento individual por su identificador validando tenant."""
        entry = next((e for e in self._ledger if e.id == movement_id), None)
        if entry is None:
            raise ResourceNotFoundError(
                f"Kardex movement {movement_id} not found.",
                i18n_key="inventory:errors.movement_not_found",
            )
        if tenant_id and entry.tenant_id and entry.tenant_id != tenant_id:
            raise CrossTenantAccessError(
                f"Cross-tenant access denied: movement {movement_id} belongs to a different tenant.",
                i18n_key="tenancy:errors.cross_tenant_forbidden",
            )
        return entry

    def ledger(self, tenant_id: str | None = None) -> tuple[KardexEntry, ...]:
        """Libro mayor inmutable del Kardex filtrado opcionalmente por inquilino."""
        if tenant_id is not None:
            return tuple(e for e in self._ledger if e.tenant_id == tenant_id)
        return tuple(self._ledger)


__all__ = [
    "InventoryService",
    "KardexEntry",
    "LotStatusResult",
    "StockStatusResult",
]
