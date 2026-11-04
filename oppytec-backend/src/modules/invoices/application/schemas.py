"""
oppytec-backend/src/modules/invoices/application/schemas.py
DTOs y esquemas de validación Pydantic v2 para el Módulo de Facturas y Contabilidad.
Cumple estrictamente la regla de cero floats: todos los montos, cantidades, factores y tasas son Decimal.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards import sanitize_text_input, validate_safe_webhook_url
from src.modules.invoices.domain.value_objects import (
    AuditRuleCode,
    AuditSeverity,
    DTEType,
    InvoiceStatus,
    MatchStatus,
    TaxId,
)


class InvoiceAuditFlagDTO(BaseModel):
    """DTO para flags y alertas de auditoría contable/tributaria."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    invoice_id: Optional[UUID] = None
    severity: AuditSeverity | str
    rule_code: AuditRuleCode | str
    message: str
    created_at: Optional[datetime] = None


class InvoiceLineItemBaseDTO(BaseModel):
    """DTO base para líneas de detalle de factura."""

    model_config = ConfigDict(from_attributes=True)

    raw_description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(default=Decimal("1.0000"), ge=Decimal("0.0001"))
    unit: str = Field(default="un", max_length=30)
    unit_price: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0.0000"))
    line_total: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0.0000"))
    vat_rate: Decimal = Field(default=Decimal("19.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    matched_catalog_item_id: Optional[UUID] = None
    match_status: MatchStatus | str = MatchStatus.UNMATCHED
    suggested_catalog_item_id: Optional[UUID] = None
    match_confidence: Optional[Decimal] = None
    packaging_description: Optional[str] = None
    packaging_factor: Decimal = Field(default=Decimal("1.0000"), ge=Decimal("0.0001"))
    calculated_stock_qty: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0.0000"))
    inventory_unit: str = Field(default="un", max_length=30)
    inventory_unit_cost: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0.0000"))
    target_bodega_id: Optional[int] = None

    @field_validator("raw_description", mode="before")
    @classmethod
    def sanitize_raw_desc(cls, v: str) -> str:
        if isinstance(v, str):
            return sanitize_text_input(v, field_name="raw_description")
        return v


class InvoiceLineItemCreateDTO(InvoiceLineItemBaseDTO):
    """DTO para crear una línea de factura."""

    line_number: int = Field(default=1, ge=1)


class InvoiceLineItemUpdateDTO(BaseModel):
    """DTO para actualización parcial de una línea de factura."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    line_number: Optional[int] = Field(default=None, ge=1)
    raw_description: Optional[str] = None
    quantity: Optional[Decimal] = Field(default=None, ge=Decimal("0.0001"))
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = Field(default=None, ge=Decimal("0.0000"))
    line_total: Optional[Decimal] = Field(default=None, ge=Decimal("0.0000"))
    vat_rate: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    matched_catalog_item_id: Optional[UUID] = None
    match_status: Optional[MatchStatus | str] = None
    suggested_catalog_item_id: Optional[UUID] = None
    match_confidence: Optional[Decimal] = None
    packaging_description: Optional[str] = None
    packaging_factor: Optional[Decimal] = Field(default=None, ge=Decimal("0.0001"))
    inventory_unit: Optional[str] = None
    target_bodega_id: Optional[int] = None

    @field_validator("raw_description", mode="before")
    @classmethod
    def sanitize_raw_desc(cls, v: str) -> str:
        if isinstance(v, str):
            return sanitize_text_input(v, field_name="raw_description")
        return v


class InvoiceLineItemResponseDTO(InvoiceLineItemBaseDTO):
    """DTO de respuesta para una línea de factura con ID."""

    id: UUID
    invoice_id: Optional[UUID] = None
    line_number: int = 1
    created_at: Optional[datetime] = None


class InvoiceCreateDTO(BaseModel):
    """DTO para creación manual o programática de una factura."""

    vendor_name: str = Field(..., min_length=1, max_length=255)
    vendor_tax_id: str = Field(..., min_length=3, max_length=30)
    invoice_number: str = Field(..., min_length=1, max_length=50)
    file_path: Optional[str] = None
    file_name: str = Field(default="invoice.pdf", max_length=255)
    file_type: str = Field(default="pdf", max_length=10)
    vendor_address: Optional[str] = None
    invoice_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    currency: str = Field(default="CLP", max_length=3)
    exchange_rate: Decimal = Field(default=Decimal("1.0000"), ge=Decimal("0.0001"))
    net_amount: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0.0000"))
    tax_amount: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0.0000"))
    total_amount: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0.0000"))
    dte_type: int = Field(default=33)
    status: InvoiceStatus | str = InvoiceStatus.PENDING
    confidence_score: Optional[Decimal] = None
    lines: List[InvoiceLineItemCreateDTO] = Field(default_factory=list)

    @field_validator("vendor_name", "invoice_number", "vendor_address", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v: Optional[str]) -> Optional[str]:
        if v and isinstance(v, str):
            return sanitize_text_input(v, field_name="invoice_field")
        return v

    @field_validator("vendor_tax_id")
    @classmethod
    def validate_tax_id(cls, v: str) -> str:
        # Intenta validar via TaxId (si es rut chileno aplicará modulo 11)
        tax = TaxId(v)
        return tax.clean_tax_id


class InvoiceUpdateDTO(BaseModel):
    """DTO para actualizar datos de cabecera y líneas de una factura en revisión."""

    model_config = ConfigDict(from_attributes=True)

    vendor_name: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    invoice_number: Optional[str] = None
    vendor_address: Optional[str] = None
    invoice_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    currency: Optional[str] = None
    exchange_rate: Optional[Decimal] = Field(default=None, ge=Decimal("0.0001"))
    net_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.0000"))
    tax_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.0000"))
    total_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.0000"))
    dte_type: Optional[int] = None
    status: Optional[InvoiceStatus | str] = None
    lines: Optional[List[InvoiceLineItemUpdateDTO]] = None

    @field_validator("vendor_name", "invoice_number", "vendor_address", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v: Optional[str]) -> Optional[str]:
        if v and isinstance(v, str):
            return sanitize_text_input(v, field_name="invoice_field")
        return v

    @field_validator("vendor_tax_id")
    @classmethod
    def validate_tax_id(cls, v: Optional[str]) -> Optional[str]:
        if v:
            tax = TaxId(v)
            return tax.clean_tax_id
        return v


class InvoiceResponseDTO(BaseModel):
    """DTO de respuesta integral para factura."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    file_path: Optional[str] = None
    file_name: str
    file_type: str
    vendor_name: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    vendor_address: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    currency: str = "CLP"
    exchange_rate: Decimal = Decimal("1.0000")
    net_amount: Decimal = Decimal("0.0000")
    tax_amount: Decimal = Decimal("0.0000")
    total_amount: Decimal = Decimal("0.0000")
    dte_type: int = 33
    status: str = "PENDING"
    confidence_score: Optional[Decimal] = None
    gemini_tokens_used: int = 0
    gemini_cost_usd: Decimal = Decimal("0.000000")
    is_stock_ingested: bool = False
    created_at: datetime
    updated_at: datetime
    lines: List[InvoiceLineItemResponseDTO] = Field(default_factory=list)
    audit_flags: List[InvoiceAuditFlagDTO] = Field(default_factory=list)


class InvoiceListResponseDTO(BaseModel):
    """DTO paginado para listado de facturas."""

    items: List[InvoiceResponseDTO]
    total: int
    skip: int
    limit: int


class SupplierAliasDTO(BaseModel):
    """DTO para mapeo de alias proveedor-catálogo."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    raw_vendor_product_name: str = Field(..., min_length=1)
    catalog_item_id: UUID
    default_packaging_factor: Decimal = Field(default=Decimal("1.0000"), ge=Decimal("0.0001"))
    default_inventory_unit: str = Field(default="un", max_length=30)
    is_verified: bool = True
    times_used: int = 1
    last_matched_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("raw_vendor_product_name", mode="before")
    @classmethod
    def sanitize_alias_name(cls, v: str) -> str:
        if isinstance(v, str):
            return sanitize_text_input(v, field_name="raw_vendor_product_name")
        return v


class SupplierAliasCreateDTO(BaseModel):
    """DTO para crear o aprender un nuevo alias."""

    supplier_id: Optional[UUID] = None
    raw_vendor_product_name: str = Field(..., min_length=1)
    catalog_item_id: UUID
    default_packaging_factor: Decimal = Field(default=Decimal("1.0000"), ge=Decimal("0.0001"))
    default_inventory_unit: str = Field(default="un", max_length=30)

    @field_validator("raw_vendor_product_name", mode="before")
    @classmethod
    def sanitize_alias_name(cls, v: str) -> str:
        if isinstance(v, str):
            return sanitize_text_input(v, field_name="raw_vendor_product_name")
        return v


class DashboardStatsDTO(BaseModel):
    """DTO para KPIs consolidados del panel de Facturas y FinOps tokens."""

    total_invoices_count: int = 0
    pending_review_count: int = 0
    confirmed_stock_count: int = 0
    rejected_count: int = 0
    total_net_amount: Decimal = Decimal("0.0000")
    total_tax_amount: Decimal = Decimal("0.0000")
    total_invoiced_amount: Decimal = Decimal("0.0000")
    total_gemini_tokens: int = 0
    total_gemini_cost_usd: Decimal = Decimal("0.000000")
    currency: str = "CLP"


class ExportFormatDTO(BaseModel):
    """Parámetros para solicitar exportación contable."""

    export_format: str = Field(default="SII_CSV", description="SII_CSV, QUICKBOOKS, XERO, ODOO, EXCEL_CSV")
    invoice_ids: Optional[List[UUID]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class IngestToStockDTO(BaseModel):
    """DTO para confirmar el ingreso físico a bodega de los insumos de una factura."""

    bodega_id: int | UUID = Field(..., description="ID de la bodega destino para el ingreso al kardex")
    lote_codigo: Optional[str] = Field(default=None, max_length=64)
    fecha_vencimiento_lote: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class BulkProcessDTO(BaseModel):
    """DTO para procesamiento masivo de facturas."""

    invoice_ids: List[UUID] = Field(..., min_length=1)
    action: str = Field(..., description="'APPROVE', 'RECALCULATE', 'REJECT'")


class BulkDeleteDTO(BaseModel):
    """DTO para eliminación masiva de facturas."""

    invoice_ids: List[UUID] = Field(..., min_length=1)


class InvoiceWebhookDTO(BaseModel):
    """DTO para suscripción o envío de webhooks de facturas con validación anti-SSRF."""

    webhook_url: str = Field(..., description="URL destino del webhook saliente")
    description: Optional[str] = Field(default=None, max_length=255)

    @field_validator("webhook_url", mode="before")
    @classmethod
    def validate_url_anti_ssrf(cls, v: str) -> str:
        if isinstance(v, str):
            return validate_safe_webhook_url(v, field_name="webhook_url")
        return v

