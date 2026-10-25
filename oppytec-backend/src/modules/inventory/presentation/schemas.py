"""
oppytec-backend/src/modules/inventory/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`, `Decimal` exclusivo) para Kardex, Toma de Inventario,
Mermas y Transferencia Masiva entre Bodegas.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input


class KardexMovementCreateRequest(BaseModel):
    """Registro atómico de movimiento de Kardex por bodega."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0)
    bodega_id: int = Field(..., gt=0)
    movement_type: Literal["ENTRADA", "SALIDA", "MERMA", "CONSUMO", "AJUSTE_POSITIVO", "TRASPASO_IN", "TRASPASO_OUT"]
    quantity: Decimal = Field(..., gt=Decimal("0"))
    unit_cost: Decimal = Field(..., ge=Decimal("0"))


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


class InventoryCountItemRequest(BaseModel):
    """Ítem de conteo físico de inventario en bodega."""

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

