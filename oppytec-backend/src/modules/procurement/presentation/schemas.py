"""
oppytec-backend/src/modules/procurement/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`, `Decimal` exclusivo) para Órdenes de Compra,
Conciliación de 3 Vías (OC vs Recepción vs Factura) y OCR de Facturas.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input


class ProcurementDocLinePayload(BaseModel):
    """Línea de Orden de Compra, Recepción o Factura con cantidad y costo en `Decimal`."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    unit_cost: Decimal = Field(..., ge=Decimal("0"))


class PurchaseOrderCreateRequest(BaseModel):
    """Creación de Orden de Compra con proveedor cuyo nombre propio comercial es inmutable."""

    model_config = ConfigDict(extra="forbid")

    po_number: str = Field(..., min_length=2, max_length=64)
    supplier_id: int = Field(..., gt=0)
    supplier_name: str = Field(..., min_length=2, max_length=150)
    lines: list[ProcurementDocLinePayload] = Field(..., min_length=1)

    @field_validator("po_number", "supplier_name")
    @classmethod
    def _sanitize_po_strings(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="po_field")


class PurchaseOrderResponse(BaseModel):
    """Orden de compra registrada con total neto calculado en `Decimal`."""

    model_config = ConfigDict(extra="forbid")

    po_number: str
    supplier_id: int
    supplier_name: str
    line_count: int
    net_total: Decimal


class ThreeWayReconcileRequest(BaseModel):
    """Solicitud de conciliación de 3 vías: Orden de Compra vs Recepción vs Factura."""

    model_config = ConfigDict(extra="forbid")

    po_number: str = Field(..., min_length=2, max_length=64)
    order_lines: list[ProcurementDocLinePayload] = Field(..., min_length=1)
    receipt_lines: list[ProcurementDocLinePayload] = Field(..., min_length=1)
    invoice_lines: list[ProcurementDocLinePayload] = Field(..., min_length=1)
    tolerance: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


class ThreeWayReconcileResponse(BaseModel):
    """Resultado de la conciliación de 3 vías (`MATCHED`, `PARTIAL_RECEIPT`, `PRICE_MISMATCH`, etc.)."""

    model_config = ConfigDict(extra="forbid")

    po_number: str
    status: str
    quantity_diffs: dict[int, Decimal]
    invoice_total_diff: Decimal


class InvoiceOcrUploadRequest(BaseModel):
    """Subida de factura PDF/XML/Imagen en Base64 para extracción OCR con validación de Magic Bytes."""

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(..., min_length=3, max_length=180)
    po_number: str = Field(..., min_length=2, max_length=64)
    content_base64: str = Field(..., min_length=4, max_length=14 * 1024 * 1024)


class InvoiceOcrResponse(BaseModel):
    """Resultado de validar Magic Bytes y procesar la factura para conciliación."""

    model_config = ConfigDict(extra="forbid")

    po_number: str
    filename: str
    verified_mime_type: str
    extracted_lines: int
    requires_human_review: bool
