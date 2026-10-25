"""
oppytec-backend/src/modules/inventory/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`, `Decimal` exclusivo) para Kardex, Toma de Inventario,
Mermas, Transferencia Masiva entre Bodegas y Cuadraturas Físicas de Auditoría.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input


class KardexMovementCreateRequest(BaseModel):
    """Registro atómico de movimiento de Kardex por bodega."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0)
    bodega_id: int = Field(..., gt=0)
    movement_type: Literal[
        "ENTRADA",
        "SALIDA",
        "COMPRA",
        "CONSUMO",
        "MERMA",
        "AJUSTE_POSITIVO",
        "AJUSTE_NEGATIVO",
        "AJUSTE_AUDITORIA",
        "TRASPASO_IN",
        "TRASPASO_OUT",
    ]
    quantity: Decimal = Field(..., gt=Decimal("0"))
    unit_cost: Decimal = Field(..., ge=Decimal("0"))
    lote_codigo: str | None = Field(default=None, max_length=64)
    fecha_vencimiento_lote: date | None = None
    documento_referencia: str | None = Field(default=None, max_length=128)


class KardexMovementResponse(BaseModel):
    """Movimiento inmutable registrado en el Kardex con saldo resultante."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int
    bodega_id: int
    movement_type: str
    quantity: Decimal
    resulting_balance: Decimal
    unit_cost: Decimal
    actor_user_id: int
    id: int | None = None
    created_at: datetime | None = None
    lote_codigo: str | None = None
    fecha_vencimiento_lote: date | None = None
    documento_referencia: str | None = None
    transfer_id: str | None = None


# ============================================================================
# ESTADO DE STOCK Y SEMÁFOROS
# ============================================================================


class StockLotStatusResponse(BaseModel):
    """Detalle de lote físico en bodega."""

    model_config = ConfigDict(extra="forbid")

    lote_codigo: str | None = None
    fecha_vencimiento: date | None = None
    cantidad: Decimal = Decimal("0.0000")


class StockStatusItemResponse(BaseModel):
    """Snapshot de existencias consolidado de un producto en bodega con semáforos."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int
    bodega_id: int
    stock_actual: Decimal
    stock_minimo: Decimal
    stock_maximo: Decimal | None = None
    punto_reorden: Decimal | None = None
    pasillo: str | None = None
    estante: str | None = None
    nivel: str | None = None
    is_below_minimum: bool
    is_critical: bool
    needs_reorder: bool
    lots: list[StockLotStatusResponse] = Field(default_factory=list)


# ============================================================================
# UNDO & REDO TRANSACCIONAL
# ============================================================================


class StockUndoRequest(BaseModel):
    """Solicitud de reversión transaccional de un movimiento previo en Kardex."""

    model_config = ConfigDict(extra="forbid")

    movement_id: int = Field(..., gt=0)
    reason: str = Field(default="", max_length=200)

    @field_validator("reason")
    @classmethod
    def _sanitize_reason(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="reason") if value else ""


class StockRedoRequest(BaseModel):
    """Solicitud de reaplicación de un movimiento revertido."""

    model_config = ConfigDict(extra="forbid")

    movement_id: int = Field(..., gt=0)
    reason: str = Field(default="", max_length=200)

    @field_validator("reason")
    @classmethod
    def _sanitize_reason(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="reason") if value else ""


# ============================================================================
# CONTEOS FÍSICOS Y AUDITORÍA
# ============================================================================


class InventoryCountItemRequest(BaseModel):
    """Ítem de conteo físico de inventario en bodega (legacy direct submit)."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0)
    counted_quantity: Decimal = Field(..., ge=Decimal("0"))
    unit_cost: Decimal = Field(..., ge=Decimal("0"))


class InventoryCountSubmitRequest(BaseModel):
    """Envío de toma física de inventario con bloqueo canónico `ORDER BY id ASC`."""

    model_config = ConfigDict(extra="forbid")

    bodega_id: int = Field(..., gt=0)
    items: list[InventoryCountItemRequest] = Field(..., min_length=1)


class InventoryCountResponse(BaseModel):
    """Resultado de conciliar una toma física de inventario en orden canónico de locks."""

    model_config = ConfigDict(extra="forbid")

    bodega_id: int
    locked_product_ids_asc: list[int]
    processed_items: int


class PhysicalCountStartRequest(BaseModel):
    """Apertura de una nueva sesión de recuento físico."""

    model_config = ConfigDict(extra="forbid")

    bodega_id: int = Field(..., gt=0)
    area_operativa_id: int | None = None
    notas: str | None = Field(default=None, max_length=300)

    @field_validator("notas")
    @classmethod
    def _sanitize_notas(cls, value: str | None) -> str | None:
        return sanitize_text_input(value, field_name="notas") if value else None


class PhysicalCountItemInput(BaseModel):
    """Línea contada físicamente en sesión de inventario."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0)
    stock_fisico_contado: Decimal = Field(..., ge=Decimal("0"))
    costo_unitario_ppp: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    lote_codigo: str | None = Field(default=None, max_length=64)
    fecha_vencimiento: date | None = None


class PhysicalCountSaveItemsRequest(BaseModel):
    """Guardado incremental de líneas contadas en sesión."""

    model_config = ConfigDict(extra="forbid")

    items: list[PhysicalCountItemInput] = Field(..., min_length=1)


class PhysicalCountItemDetailResponse(BaseModel):
    """Detalle de línea física comparativa contra stock del sistema."""

    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    producto_id: int
    stock_teorico_sistema: Decimal
    stock_fisico_contado: Decimal
    diferencia_unidades: Decimal
    costo_unitario_ppp: Decimal
    valorizacion_diferencia: Decimal
    lote_codigo: str | None = None
    fecha_vencimiento: date | None = None
    has_discrepancy: bool
    is_surplus: bool
    is_shortage: bool


class PhysicalCountSessionDetailResponse(BaseModel):
    """Detalle completo de sesión de recuento con cuadraturas y discrepancias."""

    model_config = ConfigDict(extra="forbid")

    id: int
    bodega_id: int
    area_operativa_id: int | None = None
    estado: str
    responsable_user_id: int
    aprobador_user_id: int | None = None
    notas: str | None = None
    completed_at: datetime | None = None
    total_discrepancy_units: Decimal = Decimal("0.0000")
    total_discrepancy_value: Decimal = Decimal("0.00")
    items: list[PhysicalCountItemDetailResponse] = Field(default_factory=list)


class PhysicalCountSessionSummaryResponse(BaseModel):
    """Resumen de sesión de recuento para listados históricos."""

    model_config = ConfigDict(extra="forbid")

    id: int
    bodega_id: int
    area_operativa_id: int | None = None
    estado: str
    responsable_user_id: int
    aprobador_user_id: int | None = None
    notas: str | None = None
    completed_at: datetime | None = None
    items_count: int = 0


# ============================================================================
# MERMAS Y PÉRDIDAS
# ============================================================================


class MermaReportRequest(BaseModel):
    """Reporte de merma operativa en bodega o cocina."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0)
    bodega_id: int = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    unit_cost: Decimal = Field(..., ge=Decimal("0"))
    reason: str = Field(..., min_length=4, max_length=300)

    @field_validator("reason")
    @classmethod
    def _sanitize_merma_reason(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="reason")


class MermaApproveRequest(BaseModel):
    """Solicitud de aprobación de una merma pendiente por un supervisor distinto del reportante."""

    model_config = ConfigDict(extra="forbid")

    unit_cost: Decimal = Field(..., ge=Decimal("0"))


class MermaResponse(BaseModel):
    """Estado de un registro de merma (`PENDIENTE`, `APROBADA`, `RECHAZADA`)."""

    model_config = ConfigDict(extra="forbid")

    waste_id: int
    producto_id: int
    bodega_id: int
    quantity: Decimal
    total_cost: Decimal
    reason: str
    reporter_user_id: int
    status: str


# ============================================================================
# TRANSFERENCIAS MASIVAS
# ============================================================================


class BulkTransferItemRequest(BaseModel):
    """Línea de ítem a transferir entre bodegas."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0)
    cantidad: Decimal = Field(..., gt=Decimal("0"))


class BulkTransferRequest(BaseModel):
    """Solicitud de transferencia masiva de stock entre bodegas."""

    model_config = ConfigDict(extra="forbid")

    bodega_origen_id: int = Field(..., gt=0)
    bodega_destino_id: int = Field(..., gt=0)
    fecha_transferencia: str | None = Field(default=None, max_length=64)
    items: list[BulkTransferItemRequest] = Field(..., min_length=1)


class BulkTransferItemResult(BaseModel):
    """Resultado del traspaso atómico para un producto individual."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int
    cantidad: Decimal
    origen_resulting_balance: Decimal
    destino_resulting_balance: Decimal


class BulkTransferResponse(BaseModel):
    """Resultado consolidado de transferencia masiva en Kardex."""

    model_config = ConfigDict(extra="forbid")

    bodega_origen_id: int
    bodega_destino_id: int
    processed_items: int
    items: list[BulkTransferItemResult]


# ============================================================================
# INGESTA DE FACTURAS
# ============================================================================


class InvoiceLineItemParsed(BaseModel):
    """Línea de ítem extraída de una factura con matching heurístico al catálogo."""

    model_config = ConfigDict(extra="forbid")

    line_number: int
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    total_linea: Decimal
    matched_product_id: int | None = None
    matched_product_name: str | None = None
    match_confidence: Decimal = Decimal("0.00")


class InvoiceParseRequest(BaseModel):
    """Solicitud de parseo de factura en Base64."""

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(..., min_length=3, max_length=180)
    content_base64: str = Field(..., min_length=4)


class InvoiceParseResponse(BaseModel):
    """Metadatos y líneas extraídas de documento de factura (PDF, XML DTE, imagen)."""

    model_config = ConfigDict(extra="forbid")

    filename: str
    mime_type: str
    rut_proveedor: str
    razon_social: str
    folio: str
    monto_neto: Decimal
    monto_iva: Decimal
    monto_total: Decimal
    confidence: Decimal
    lines: list[InvoiceLineItemParsed]


class InvoiceItemConfirmPayload(BaseModel):
    """Línea de insumo confirmada para ingresar a bodega."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int | None = None
    descripcion: str = Field(..., min_length=1, max_length=180)
    cantidad: Decimal = Field(..., gt=Decimal("0"))
    costo_unitario: Decimal = Field(..., ge=Decimal("0"))
    create_if_missing: bool = False
    sku: str | None = None


class InvoiceConfirmRequest(BaseModel):
    """Confirmación e ingreso atómico a Kardex de factura parseada."""

    model_config = ConfigDict(extra="forbid")

    supplier: dict[str, str] = Field(default_factory=dict)
    bodega_id: int | str | None = 1
    folio: str | None = None
    items: list[InvoiceItemConfirmPayload] = Field(..., min_length=1)


class InvoiceConfirmResponse(BaseModel):
    """Reporte de factura confirmada e ingresada en Kardex."""

    model_config = ConfigDict(extra="forbid")

    folio: str
    supplier_rut: str
    bodega_id: int
    processed_items: int
    total_registered_cost: Decimal
    kardex_movements: list[KardexMovementResponse]


__all__ = [
    "BulkTransferItemRequest",
    "BulkTransferItemResult",
    "BulkTransferRequest",
    "BulkTransferResponse",
    "InventoryCountItemRequest",
    "InventoryCountResponse",
    "InventoryCountSubmitRequest",
    "InvoiceConfirmRequest",
    "InvoiceConfirmResponse",
    "InvoiceItemConfirmPayload",
    "InvoiceLineItemParsed",
    "InvoiceParseRequest",
    "InvoiceParseResponse",
    "KardexMovementCreateRequest",
    "KardexMovementResponse",
    "MermaApproveRequest",
    "MermaReportRequest",
    "MermaResponse",
    "PhysicalCountItemDetailResponse",
    "PhysicalCountItemInput",
    "PhysicalCountSaveItemsRequest",
    "PhysicalCountSessionDetailResponse",
    "PhysicalCountSessionSummaryResponse",
    "PhysicalCountStartRequest",
    "StockLotStatusResponse",
    "StockRedoRequest",
    "StockStatusItemResponse",
    "StockUndoRequest",
]
