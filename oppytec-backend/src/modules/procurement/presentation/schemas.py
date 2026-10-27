"""
oppytec-backend/src/modules/procurement/presentation/schemas.py
Esquemas Pydantic v2 (precisión Decimal exclusiva, cero floats) para Proveedores,
Catálogo pactado, Órdenes de Compra, Recepción, Incidencias, Dashboard y Analítica de Mermas.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input

# ============================================================================
# ESQUEMAS HISTÓRICOS Y LÍNEAS DE DOCUMENTO
# ============================================================================


class ProcurementDocLinePayload(BaseModel):
    """Línea de documento de compra o recepción en Decimal."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    unit_cost: Decimal = Field(..., ge=Decimal("0"))


class ThreeWayReconcileRequest(BaseModel):
    """Solicitud de conciliación de 3 vías: Orden vs Recepción vs Factura."""

    model_config = ConfigDict(extra="forbid")

    po_number: str = Field(..., min_length=2, max_length=64)
    order_lines: list[ProcurementDocLinePayload] = Field(..., min_length=1)
    receipt_lines: list[ProcurementDocLinePayload] = Field(..., min_length=1)
    invoice_lines: list[ProcurementDocLinePayload] = Field(..., min_length=1)
    tolerance: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))

    @field_validator("po_number")
    @classmethod
    def _sanitize_po_number(cls, val: str) -> str:
        return sanitize_text_input(val, field_name="po_number")


class ThreeWayReconcileResponse(BaseModel):
    """Resultado de la conciliación de 3 vías."""

    model_config = ConfigDict(extra="ignore")

    po_number: str
    status: str
    quantity_diffs: dict[int, Decimal]
    invoice_total_diff: Decimal


class InvoiceOcrUploadRequest(BaseModel):
    """Subida de factura Base64 para extracción OCR con Magic Bytes."""

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(..., min_length=3, max_length=180)
    po_number: str = Field(..., min_length=2, max_length=64)
    content_base64: str = Field(..., min_length=4, max_length=14 * 1024 * 1024)

    @field_validator("filename", "po_number")
    @classmethod
    def _sanitize_ocr_fields(cls, val: str) -> str:
        return sanitize_text_input(val, field_name="invoice_ocr")


class InvoiceOcrResponse(BaseModel):
    """Resultado de validación Magic Bytes y procesamiento OCR."""

    model_config = ConfigDict(extra="ignore")

    po_number: str
    filename: str
    verified_mime_type: str
    extracted_lines: int
    requires_human_review: bool


# ============================================================================
# ESQUEMAS DE PROVEEDORES Y CATÁLOGO PACTADO
# ============================================================================


class SupplierCreateRequest(BaseModel):
    """Alta de nuevo proveedor comercial."""

    model_config = ConfigDict(extra="forbid")

    rut_tax_id: str = Field(..., min_length=3, max_length=64)
    razon_social: str = Field(..., min_length=2, max_length=180)
    nombre_fantasia: str | None = Field(default=None, max_length=180)
    email_contacto: str | None = Field(default=None, max_length=255)
    telefono: str | None = Field(default=None, max_length=50)
    direccion: str | None = Field(default=None, max_length=255)
    lead_time_dias: int = Field(default=1, ge=0)
    estado: str = Field(default="ACTIVO", max_length=32)
    notas: str | None = None

    @field_validator("razon_social", "nombre_fantasia", "email_contacto", "telefono", "direccion", "notas")
    @classmethod
    def _sanitize_names(cls, val: str | None) -> str | None:
        if val is None:
            return None
        return sanitize_text_input(val, field_name="supplier_field")


class SupplierUpdateRequest(BaseModel):
    """Actualización de campos de proveedor."""

    model_config = ConfigDict(extra="forbid")

    razon_social: str | None = None
    nombre_fantasia: str | None = None
    email_contacto: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    lead_time_dias: int | None = Field(default=None, ge=0)
    estado: str | None = None
    notas: str | None = None

    @field_validator("razon_social", "nombre_fantasia", "email_contacto", "telefono", "direccion", "notas")
    @classmethod
    def _sanitize_update_fields(cls, val: str | None) -> str | None:
        if val is None:
            return None
        return sanitize_text_input(val, field_name="supplier_update_field")


class SupplierResponse(BaseModel):
    """Detalle de proveedor con estadísticas de compras acumuladas."""

    model_config = ConfigDict(extra="ignore")

    id: int
    rut_tax_id: str
    razon_social: str
    nombre_fantasia: str | None = None
    email_contacto: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    lead_time_dias: int = 1
    estado: str = "ACTIVO"
    notas: str | None = None
    total_compras_historicas: Decimal = Decimal("0.00")
    ordenes_activas_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SupplierListResponse(BaseModel):
    """Listado paginado de proveedores."""

    model_config = ConfigDict(extra="ignore")

    items: list[SupplierResponse]
    total: int
    skip: int
    limit: int


class SupplierCatalogItemPayload(BaseModel):
    """Ítem para upsert de catálogo y precios pactados."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0)
    precio_pactado: Decimal = Field(..., ge=Decimal("0.00"))
    codigo_producto_proveedor: str | None = Field(default=None, max_length=64)
    tiempo_entrega_dias: int | None = Field(default=None, ge=0)
    es_proveedor_principal: bool = False

    @field_validator("codigo_producto_proveedor")
    @classmethod
    def _sanitize_catalog_code(cls, val: str | None) -> str | None:
        if val is None:
            return None
        return sanitize_text_input(val, field_name="codigo_producto_proveedor")


class SupplierCatalogItemResponse(BaseModel):
    """Ítem del catálogo pactado devuelto por la API."""

    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    producto_id: int
    producto_nombre: str | None = None
    producto_sku: str | None = None
    proveedor_id: int
    precio_pactado: Decimal
    codigo_producto_proveedor: str | None = None
    tiempo_entrega_dias: int | None = None
    es_proveedor_principal: bool = False


class SupplierCatalogBulkUpdateRequest(BaseModel):
    """Carga masiva de catálogo pactado."""

    model_config = ConfigDict(extra="forbid")

    items: list[SupplierCatalogItemPayload]


# ============================================================================
# ESQUEMAS DE ÓRDENES DE COMPRA Y RECEPCIÓN
# ============================================================================


class PurchaseOrderItemPayload(BaseModel):
    """Línea de ítem de orden de compra."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0)
    cantidad_solicitada: Decimal = Field(..., gt=Decimal("0"))
    costo_unitario_neto: Decimal = Field(..., ge=Decimal("0"))
    lote_codigo: str | None = None
    fecha_vencimiento: date | None = None

    @field_validator("lote_codigo")
    @classmethod
    def _sanitize_lote(cls, val: str | None) -> str | None:
        if val is None:
            return None
        return sanitize_text_input(val, field_name="lote_codigo")


class PurchaseOrderItemResponse(BaseModel):
    """Línea de detalle de compra persistida."""

    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    compra_id: int | None = None
    producto_id: int
    producto_nombre: str | None = None
    producto_sku: str | None = None
    cantidad_solicitada: Decimal
    cantidad_recibida: Decimal = Decimal("0.0000")
    costo_unitario_neto: Decimal
    subtotal_linea: Decimal
    lote_codigo: str | None = None
    fecha_vencimiento: date | None = None


class PurchaseIncidenceResponse(BaseModel):
    """Incidencia registrada durante la recepción."""

    model_config = ConfigDict(extra="ignore")

    id: int
    compra_id: int
    compra_item_id: int | None = None
    tipo_incidencia: str
    cantidad_afectada: Decimal
    monto_disputa: Decimal
    resolucion: str
    descripcion: str
    foto_evidencia_url: str | None = None
    registrado_por_user_id: int | None = None
    created_at: datetime | None = None


class PurchaseOrderCreateRequest(BaseModel):
    """
    Creación de orden de compra con soporte de retrocompatibilidad dual:
    - Nuevo modelo enriquecido (items, bodega_destino_id, estado, moneda).
    - Modelo histórico E2E (po_number, supplier_id, supplier_name, lines).
    """

    model_config = ConfigDict(extra="forbid")

    po_number: str | None = None
    numero_orden: str | None = None
    supplier_id: int | None = None
    proveedor_id: int | None = None
    supplier_name: str | None = None
    proveedor_nombre: str | None = None
    bodega_destino_id: int = 1
    estado: str = "BORRADOR"
    moneda: str = "CLP"
    fecha_entrega_estimada: date | None = None
    fecha_entrega_comprometida: datetime | None = None
    notas: str | None = None
    lines: list[ProcurementDocLinePayload] | None = None
    items: list[PurchaseOrderItemPayload] | None = None

    @field_validator("po_number", "numero_orden", "supplier_name", "proveedor_nombre", "notas")
    @classmethod
    def _sanitize_order_text(cls, val: str | None) -> str | None:
        if val is None:
            return None
        return sanitize_text_input(val, field_name="purchase_order_field")


class PurchaseOrderUpdateRequest(BaseModel):
    """Modificación de una orden de compra en estado editable."""

    model_config = ConfigDict(extra="forbid")

    bodega_destino_id: int | None = None
    fecha_entrega_estimada: date | None = None
    fecha_entrega_comprometida: datetime | None = None
    notas: str | None = None
    estado: str | None = None
    items: list[PurchaseOrderItemPayload] | None = None

    @field_validator("notas")
    @classmethod
    def _sanitize_update_notas(cls, val: str | None) -> str | None:
        if val is None:
            return None
        return sanitize_text_input(val, field_name="notas")


class PurchaseOrderResponse(BaseModel):
    """Respuesta consolidada de Orden de Compra compatible con contratos v2 y E2E."""

    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    po_number: str
    numero_orden: str
    supplier_id: int
    proveedor_id: int
    supplier_name: str
    proveedor_nombre: str
    bodega_destino_id: int = 1
    estado: str = "BORRADOR"
    moneda: str = "CLP"
    line_count: int = 0
    items_count: int = 0
    net_total: Decimal = Decimal("0.00")
    monto_neto: Decimal = Decimal("0.00")
    monto_impuestos: Decimal = Decimal("0.00")
    monto_total: Decimal = Decimal("0.00")
    fecha_emision: datetime | None = None
    fecha_entrega_estimada: date | None = None
    fecha_recepcion_real: datetime | None = None
    solicitante_user_id: int | None = None
    receptor_user_id: int | None = None
    notas: str | None = None
    items: list[PurchaseOrderItemResponse] = []
    incidencias: list[PurchaseIncidenceResponse] = []


class PurchaseOrderListResponse(BaseModel):
    """Listado paginado de órdenes de compra."""

    model_config = ConfigDict(extra="ignore")

    items: list[PurchaseOrderResponse]
    total: int
    skip: int
    limit: int


class ReceiveGoodsItemPayload(BaseModel):
    """Ítem recepcionado en bodega."""

    model_config = ConfigDict(extra="forbid")

    compra_item_id: int | None = None
    producto_id: int = Field(..., gt=0)
    cantidad_recibida: Decimal = Field(..., gt=Decimal("0"))
    costo_unitario_neto: Decimal | None = None
    lote_codigo: str | None = None
    fecha_vencimiento: date | None = None

    @field_validator("lote_codigo")
    @classmethod
    def _sanitize_receive_lote(cls, val: str | None) -> str | None:
        if val is None:
            return None
        return sanitize_text_input(val, field_name="lote_codigo")


class ReceiveGoodsRequest(BaseModel):
    """Solicitud de recepción de mercadería física."""

    model_config = ConfigDict(extra="forbid")

    items: list[ReceiveGoodsItemPayload] = Field(..., min_length=1)
    notas: str | None = None

    @field_validator("notas")
    @classmethod
    def _sanitize_receive_notas(cls, val: str | None) -> str | None:
        if val is None:
            return None
        return sanitize_text_input(val, field_name="notas")


class PurchaseIncidenceCreateRequest(BaseModel):
    """Registro de discrepancia o incidencia en la recepción."""

    model_config = ConfigDict(extra="forbid")

    compra_item_id: int | None = None
    tipo_incidencia: str = Field(..., min_length=2, max_length=50)
    cantidad_afectada: Decimal = Field(..., gt=Decimal("0"))
    monto_disputa: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    resolucion: str = Field(default="PENDIENTE", max_length=50)
    descripcion: str = Field(..., min_length=3)
    foto_evidencia_url: str | None = None

    @field_validator("tipo_incidencia", "resolucion", "descripcion")
    @classmethod
    def _sanitize_incidence_fields(cls, val: str) -> str:
        return sanitize_text_input(val, field_name="incidence_field")


class CancelOrderRequest(BaseModel):
    """Cancelación formal de orden de compra."""

    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(..., min_length=3)

    @field_validator("motivo")
    @classmethod
    def _sanitize_motivo(cls, val: str) -> str:
        return sanitize_text_input(val, field_name="motivo")


class ProcurementDashboardResponse(BaseModel):
    """Métricas y KPIs consolidados del tablero de compras."""

    model_config = ConfigDict(extra="ignore")

    total_mes_monto: Decimal
    ordenes_pendientes_recepcion: int
    proveedores_activos: int
    ordenes_recientes: list[PurchaseOrderResponse]
    gastos_por_proveedor: list[dict[str, Any]]


# ============================================================================
# ESQUEMAS DE GESTIÓN ANALÍTICA DE MERMAS
# ============================================================================


class MermaByMotivo(BaseModel):
    """Agregación de pérdidas por motivo."""

    model_config = ConfigDict(extra="ignore")

    motivo: str
    total_costo: Decimal
    cantidad: Decimal
    porcentaje: Decimal


class MermaByCategoria(BaseModel):
    """Agregación de pérdidas por categoría."""

    model_config = ConfigDict(extra="ignore")

    categoria_id: int
    categoria_nombre: str
    total_costo: Decimal
    cantidad: Decimal


class MermaTimelinePoint(BaseModel):
    """Punto en la serie cronológica de mermas."""

    model_config = ConfigDict(extra="ignore")

    fecha: str
    costo: Decimal
    cantidad: Decimal


class MermaAnalyticsResponse(BaseModel):
    """Resumen analítico y financiero de mermas."""

    model_config = ConfigDict(extra="ignore")

    total_perdida_ppp: Decimal
    items_mermados_count: int
    mermas_pendientes_aprobacion: int
    por_motivo: list[MermaByMotivo]
    por_categoria: list[MermaByCategoria]
    timeline: list[MermaTimelinePoint]


class MermaHistoryItemResponse(BaseModel):
    """Entrada individual en el historial de mermas."""

    model_config = ConfigDict(extra="ignore")

    id: int
    producto_id: int
    producto_nombre: str | None = None
    producto_sku: str | None = None
    bodega_id: int
    bodega_nombre: str | None = None
    cantidad: Decimal
    costo_total: Decimal
    motivo: str
    estado_aprobacion: str
    reportado_por_user_id: int
    fecha_merma: datetime | date | None = None
    created_at: datetime | None = None


class MermaHistoryResponse(BaseModel):
    """Historial cronológico paginado de mermas."""

    model_config = ConfigDict(extra="ignore")

    items: list[MermaHistoryItemResponse]
    total: int
    skip: int
    limit: int
