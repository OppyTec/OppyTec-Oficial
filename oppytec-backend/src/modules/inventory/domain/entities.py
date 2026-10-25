"""
oppytec-backend/src/modules/inventory/domain/entities.py
Entidades puras del dominio de inventario multi-bodega (Clean Architecture).
Aisladas al 100% de SQLAlchemy, Pydantic y FastAPI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from src.modules.inventory.domain.exceptions import (
    InsufficientStockError,
    TransferSameWarehouseError,
)
from src.modules.inventory.domain.value_objects import (
    MoneyAmount,
    MovementType,
    StockQuantity,
    StorageLocation,
)


@dataclass
class StockItem:
    """
    Entidad de inventario para un producto en una bodega específica.
    Encapsula los límites de stock, ubicación física y cálculo de semáforos.
    """

    producto_id: int
    bodega_id: int
    stock_actual: StockQuantity = field(default_factory=StockQuantity.zero)
    stock_minimo: StockQuantity = field(default_factory=StockQuantity.zero)
    stock_maximo: StockQuantity | None = None
    punto_reorden: StockQuantity | None = None
    location: StorageLocation = field(default_factory=StorageLocation)
    id: int | None = None
    tenant_id: str | None = None

    def is_below_minimum(self) -> bool:
        """Determina si el stock actual está por debajo del umbral mínimo de seguridad."""
        return self.stock_actual < self.stock_minimo

    def is_critical(self) -> bool:
        """
        Determina si el ítem está en situación crítica:
        stock agotado (0) o menor al 50% del stock mínimo.
        """
        if self.stock_actual.is_zero():
            return True
        half_minimum = self.stock_minimo * Decimal("0.5")
        return self.stock_actual <= half_minimum

    def needs_reorder(self) -> bool:
        """Determina si se debe emitir un pedido de reposición."""
        reorder_threshold = self.punto_reorden if self.punto_reorden is not None else self.stock_minimo
        return self.stock_actual <= reorder_threshold

    def apply_movement(
        self,
        movement_type: MovementType | str,
        quantity: StockQuantity | Decimal | int | str,
    ) -> StockQuantity:
        """
        Aplica un movimiento atómico sobre el stock actual del ítem.
        Retorna el nuevo saldo resultante o eleva `InsufficientStockError`.
        """
        parsed_type = MovementType.from_str(movement_type)
        qty = quantity if isinstance(quantity, StockQuantity) else StockQuantity(quantity)

        if qty.is_zero() or qty.is_negative():
            raise ValueError("Movement quantity must be strictly positive")

        if parsed_type.is_entry:
            new_balance = self.stock_actual + qty
        elif parsed_type.is_exit:
            if self.stock_actual < qty:
                raise InsufficientStockError(
                    f"Insufficient stock in warehouse {self.bodega_id} for product {self.producto_id}: "
                    f"current {self.stock_actual.value}, requested {qty.value}",
                    context={"warehouse_id": self.bodega_id, "product_id": self.producto_id},
                )
            new_balance = self.stock_actual - qty
        else:
            raise ValueError(f"Movement type {parsed_type.value} requires explicit directional handling")

        self.stock_actual = new_balance
        return self.stock_actual


@dataclass(frozen=True)
class KardexMovement:
    """
    Asiento inmutable de Kardex (Append-Only ledger).
    Registra el impacto físico y financiero de un movimiento de inventario.
    """

    producto_id: int
    bodega_id: int
    tipo_movimiento: MovementType
    cantidad: StockQuantity
    saldo_resultante: StockQuantity
    costo_unitario_ppp: MoneyAmount
    costo_total_movimiento: MoneyAmount
    actor_user_id: int
    id: int | None = None
    tenant_id: str | None = None
    created_at: datetime | None = None
    lote_codigo: str | None = None
    fecha_vencimiento_lote: date | None = None
    documento_referencia: str | None = None
    transfer_id: UUID | str | None = None

    def __post_init__(self) -> None:
        if self.producto_id <= 0:
            raise ValueError(f"Invalid producto_id: {self.producto_id}")
        if self.bodega_id <= 0:
            raise ValueError(f"Invalid bodega_id: {self.bodega_id}")
        if self.cantidad.is_zero() or self.cantidad.is_negative():
            raise ValueError(f"Kardex movement quantity must be strictly positive: {self.cantidad}")


@dataclass
class PhysicalCountItem:
    """
    Línea de recuento físico comparativa (teórico vs contado).
    Calcula la discrepancia en unidades y su valorización al PPP vigente.
    """

    producto_id: int
    stock_teorico_sistema: StockQuantity
    stock_fisico_contado: StockQuantity
    costo_unitario_ppp: MoneyAmount
    diferencia_unidades: StockQuantity = field(init=False)
    valorizacion_diferencia: MoneyAmount = field(init=False)
    lote_codigo: str | None = None
    fecha_vencimiento: date | None = None
    id: int | None = None
    tenant_id: str | None = None

    def __post_init__(self) -> None:
        # diferencia = contado - teorico (puede ser negativa si falta o positiva si sobra)
        diff_val = self.stock_fisico_contado.value - self.stock_teorico_sistema.value
        self.diferencia_unidades = StockQuantity(diff_val, allow_negative=True)
        # Valorización = diferencia * costo_unitario_ppp
        val_diff = self.costo_unitario_ppp.amount * diff_val
        self.valorizacion_diferencia = MoneyAmount(val_diff, currency=self.costo_unitario_ppp.currency)

    @property
    def has_discrepancy(self) -> bool:
        """Determina si existe diferencia entre lo contado físicamente y el stock del sistema."""
        return not self.diferencia_unidades.is_zero()

    @property
    def is_surplus(self) -> bool:
        """Determina si hay sobrante físico (contado > teórico)."""
        return self.diferencia_unidades.is_positive()

    @property
    def is_shortage(self) -> bool:
        """Determina si hay faltante físico (contado < teórico)."""
        return self.diferencia_unidades.is_negative()


@dataclass
class PhysicalCountSession:
    """
    Sesión de auditoría y recuento físico de inventario en bodega.
    Controla el ciclo de vida: EN_PROGRESO -> PENDIENTE_APROBACION -> APROBADO / RECHAZADO / ANULADO.
    """

    bodega_id: int
    responsable_user_id: int
    area_operativa_id: int | None = None
    estado: str = "EN_PROGRESO"
    aprobador_user_id: int | None = None
    notas: str | None = None
    id: int | None = None
    completed_at: datetime | None = None
    items: list[PhysicalCountItem] = field(default_factory=list)
    tenant_id: str | None = None

    VALID_STATES: frozenset[str] = frozenset(
        {"EN_PROGRESO", "PENDIENTE_APROBACION", "APROBADO", "RECHAZADO", "ANULADO"}
    )

    def __post_init__(self) -> None:
        if self.bodega_id <= 0:
            raise ValueError(f"Invalid bodega_id: {self.bodega_id}")
        if self.responsable_user_id <= 0:
            raise ValueError(f"Invalid responsable_user_id: {self.responsable_user_id}")
        if self.estado not in self.VALID_STATES:
            raise ValueError(f"Invalid session status: {self.estado}. Allowed: {sorted(self.VALID_STATES)}")

    def add_item(self, item: PhysicalCountItem) -> None:
        """Agrega o reemplaza un ítem en la sesión de recuento."""
        self.items.append(item)

    def total_discrepancy_units(self) -> StockQuantity:
        """Calcula la sumatoria neta de unidades discrepantes."""
        total = sum((item.diferencia_unidades.value for item in self.items), Decimal(0))
        return StockQuantity(total, allow_negative=True)

    def total_discrepancy_value(self, currency: str = "CLP") -> MoneyAmount:
        """Calcula el valor financiero neto total de las discrepancias."""
        total = sum((item.valorizacion_diferencia.amount for item in self.items), Decimal(0))
        return MoneyAmount(total, currency=currency)

    def transition_to(self, new_state: str, user_id: int | None = None) -> None:
        """Transición de estado con validación de reglas de auditoría."""
        if new_state not in self.VALID_STATES:
            raise ValueError(f"Invalid target state: {new_state}")

        if new_state == "APROBADO":
            if not user_id:
                raise ValueError("Approval requires an approver user_id")
            self.aprobador_user_id = user_id
            self.completed_at = datetime.now()

        self.estado = new_state


@dataclass
class StockTransfer:
    """
    Entidad de orquestación de traspasos de existencias entre dos bodegas.
    Valida la invariante anti-traspaso a la misma bodega (`TransferSameWarehouseError`).
    """

    transfer_uuid: UUID | str
    bodega_origen_id: int
    bodega_destino_id: int
    solicitante_user_id: int
    estado: str = "SOLICITADA"
    despachador_user_id: int | None = None
    receptor_user_id: int | None = None
    notas: str | None = None
    id: int | None = None
    tenant_id: str | None = None

    VALID_STATES: frozenset[str] = frozenset({"SOLICITADA", "EN_TRANSITO", "COMPLETADA", "CANCELADA"})

    def __post_init__(self) -> None:
        if self.bodega_origen_id == self.bodega_destino_id:
            raise TransferSameWarehouseError(
                f"Transfer origin warehouse ({self.bodega_origen_id}) and destination warehouse ({self.bodega_destino_id}) cannot be the same",
                context={"origin_id": self.bodega_origen_id, "destination_id": self.bodega_destino_id},
            )
        if self.estado not in self.VALID_STATES:
            raise ValueError(f"Invalid transfer status: {self.estado}. Allowed: {sorted(self.VALID_STATES)}")


__all__ = [
    "KardexMovement",
    "PhysicalCountItem",
    "PhysicalCountSession",
    "StockItem",
    "StockTransfer",
]
