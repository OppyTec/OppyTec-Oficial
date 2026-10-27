"""
oppytec-backend/src/modules/procurement/domain/entities.py
Entidades puras del dominio de adquisiciones y compras (Clean Architecture).
Aisladas al 100% de SQLAlchemy, Pydantic y FastAPI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import ClassVar

from src.core.exceptions import ProperNounImmutabilityError
from src.modules.procurement.domain.exceptions import (
    NegativeQuantityError,
)
from src.modules.procurement.domain.value_objects import (
    IncidenceResolution,
    IncidenceType,
    MoneyAmount,
    PurchaseStatus,
    RutTaxId,
)

ZERO_QTY = Decimal("0.0000")


@dataclass
class Supplier:
    """
    Entidad pura que representa un proveedor comercial.
    Invariante inmutable ("Pollo King"): `translatable: ClassVar[bool] = False`.
    Su razón social o nombre de fantasía jamás debe ser modificado por traducción automática.
    """

    rut_tax_id: RutTaxId
    razon_social: str
    nombre_fantasia: str | None = None
    email_contacto: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    lead_time_dias: int = 1
    estado: str = "ACTIVO"
    notas: str | None = None
    id: int | None = None

    translatable: ClassVar[bool] = False

    def assert_proper_noun_immutable(self, proposed_name: str) -> None:
        """Verifica que el nombre comercial permanezca inmutable ante intentos de traducción."""
        if proposed_name != self.razon_social and proposed_name != (self.nombre_fantasia or self.razon_social):
            raise ProperNounImmutabilityError(
                f"Supplier name '{self.razon_social}' is an immutable proper noun and cannot be translated or altered.",
                context={"table": "proveedores", "supplier_id": self.id or 0},
            )


@dataclass
class PurchaseItem:
    """Línea de detalle individual de una orden de compra."""

    producto_id: int
    cantidad_solicitada: Decimal
    precio_unitario: MoneyAmount
    cantidad_recibida: Decimal = field(default_factory=lambda: ZERO_QTY)
    subtotal_linea: MoneyAmount | None = None
    lote_codigo: str | None = None
    fecha_vencimiento: date | None = None
    id: int | None = None
    compra_id: int | None = None

    def __post_init__(self) -> None:
        if self.cantidad_solicitada <= ZERO_QTY:
            raise NegativeQuantityError("cantidad_solicitada must be strictly positive")
        if self.cantidad_recibida < ZERO_QTY:
            raise NegativeQuantityError("cantidad_recibida cannot be negative")
        if self.subtotal_linea is None:
            self.subtotal_linea = self.precio_unitario * self.cantidad_solicitada

    def is_fully_received(self) -> bool:
        """Determina si la cantidad recibida cubre o supera lo solicitado."""
        return self.cantidad_recibida >= self.cantidad_solicitada

    def pending_quantity(self) -> Decimal:
        """Cantidad pendiente por recepcionar."""
        diff = self.cantidad_solicitada - self.cantidad_recibida
        return diff if diff > ZERO_QTY else ZERO_QTY


@dataclass
class PurchaseIncidence:
    """Registro de incidencia, merma u objeción en la recepción de mercadería."""

    compra_id: int
    tipo_incidencia: IncidenceType
    cantidad_afectada: Decimal
    descripcion: str
    monto_disputa: MoneyAmount | None = None
    resolucion: IncidenceResolution = IncidenceResolution.PENDIENTE
    compra_item_id: int | None = None
    foto_evidencia_url: str | None = None
    registrado_por_user_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.cantidad_afectada <= ZERO_QTY:
            raise NegativeQuantityError("cantidad_afectada must be strictly positive")

    def resolve(self, resolution: IncidenceResolution) -> None:
        """Aplica una resolución formal a la incidencia."""
        self.resolucion = resolution


@dataclass
class PurchaseOrder:
    """
    Agregado Raíz del Dominio de Compras (DDD Aggregate Root).
    Controla el ciclo de vida transaccional, líneas de pedido e incidencias.
    """

    numero_orden: str
    proveedor_id: int
    bodega_destino_id: int
    monto_neto: MoneyAmount
    monto_impuestos: MoneyAmount
    monto_total: MoneyAmount
    estado: PurchaseStatus = PurchaseStatus.BORRADOR
    moneda_codigo: str = "CLP"
    fecha_emision: datetime | None = None
    fecha_entrega_estimada: date | None = None
    fecha_recepcion_real: datetime | None = None
    solicitante_user_id: int | None = None
    receptor_user_id: int | None = None
    notas: str | None = None
    id: int | None = None
    items: list[PurchaseItem] = field(default_factory=list)
    incidencias: list[PurchaseIncidence] = field(default_factory=list)

    def submit(self) -> None:
        """Envía la orden formalmente al proveedor (BORRADOR -> SOLICITADA)."""
        self.estado.validate_transition(PurchaseStatus.SOLICITADA)
        self.estado = PurchaseStatus.SOLICITADA

    def mark_in_transit(self) -> None:
        """Registra el despacho en tránsito (SOLICITADA -> EN_CAMINO)."""
        self.estado.validate_transition(PurchaseStatus.EN_CAMINO)
        self.estado = PurchaseStatus.EN_CAMINO

    def receive_delivery(self, fully_received: bool = False) -> None:
        """
        Recepciona mercadería en bodega.
        Transiciona a RECIBIDA_TOTAL si se cubrió el 100% o RECIBIDA_PARCIAL si quedan pendientes.
        """
        target = PurchaseStatus.RECIBIDA_TOTAL if fully_received else PurchaseStatus.RECIBIDA_PARCIAL
        self.estado.validate_transition(target)
        self.estado = target

    def cancel(self) -> None:
        """Cancela la orden de compra si no se encuentra en estado terminal."""
        self.estado.validate_transition(PurchaseStatus.CANCELADA)
        self.estado = PurchaseStatus.CANCELADA

    def add_incidence(self, incidence: PurchaseIncidence) -> None:
        """Registra una incidencia de recepción vinculada a la orden."""
        self.incidencias.append(incidence)


__all__ = [
    "PurchaseIncidence",
    "PurchaseItem",
    "PurchaseOrder",
    "Supplier",
]
