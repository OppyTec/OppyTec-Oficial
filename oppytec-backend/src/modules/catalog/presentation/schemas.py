"""
oppytec-backend/src/modules/catalog/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`, `Decimal` exclusivo) para Catálogo, Conversión de 3 Capas,
Importación Excel y Subida Segura de Imágenes WebP a R2.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.file_magic_guard import sanitize_spreadsheet_cell
from src.core.guards.xss_sanitizer import sanitize_text_input


class ProductCreateRequest(BaseModel):
    """Alta de producto en el catálogo con conversión de unidades de 3 capas en `Decimal`."""

    model_config = ConfigDict(extra="forbid")

    sku: str = Field(..., min_length=1, max_length=64)
    nombre: str = Field(..., min_length=2, max_length=180)
    marca_comercial: str | None = Field(default=None, max_length=120)
    unidad_compra: str = Field(..., min_length=1, max_length=32)
    unidad_almacen: str = Field(default="kg", min_length=1, max_length=32)
    unidad_receta: str = Field(default="g", min_length=1, max_length=32)
    factor_compra_a_almacen: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    factor_almacen_a_receta: Decimal = Field(default=Decimal("1000"), gt=Decimal("0"))
    costo_compra_neto: Decimal = Field(..., ge=Decimal("0"))

    @field_validator("sku", "nombre", "unidad_compra", "unidad_almacen", "unidad_receta")
    @classmethod
    def _sanitize_product_strings(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="product_field")


class ProductResponse(BaseModel):
    """Respuesta de producto con costos calculados en las 3 capas de unidades."""

    model_config = ConfigDict(extra="forbid")

    product_id: int
    sku: str
    nombre: str
    marca_comercial: str | None
    unidad_compra: str
    unidad_almacen: str
    unidad_receta: str
    costo_compra_neto: Decimal
    costo_unitario_almacen: Decimal
    costo_unitario_receta: Decimal


class UnitConversionRequest(BaseModel):
    """Solicitud de conversión exacta entre unidades de Compra -> Almacén -> Receta."""

    model_config = ConfigDict(extra="forbid")

    cantidad_compra: Decimal = Field(..., gt=Decimal("0"))
    costo_compra_neto: Decimal = Field(..., ge=Decimal("0"))
    factor_compra_a_almacen: Decimal = Field(..., gt=Decimal("0"))
    factor_almacen_a_receta: Decimal = Field(..., gt=Decimal("0"))


class UnitConversionResponse(BaseModel):
    """Resultado de conversión de 3 capas cuantizado en `Decimal`."""

    model_config = ConfigDict(extra="forbid")

    cantidad_almacen: Decimal
    cantidad_receta: Decimal
    costo_unitario_almacen: Decimal
    costo_unitario_receta: Decimal


class ExcelImportRowPayload(BaseModel):
    """Fila de planilla Excel para importar productos (con sanitización anti-Formula Injection)."""

    model_config = ConfigDict(extra="forbid")

    sku: str
    nombre: str
    unidad_compra: str
    costo_compra_neto: Decimal
    factor_compra_a_almacen: Decimal = Decimal("1")
    factor_almacen_a_receta: Decimal = Decimal("1")

    @field_validator("sku", "nombre", "unidad_compra")
    @classmethod
    def _sanitize_cells(cls, value: str) -> str:
        cleaned = sanitize_spreadsheet_cell(value, reject_dde_payloads=True)
        return sanitize_text_input(cleaned, field_name="excel_cell")


class ExcelImportRequest(BaseModel):
    """Lote de filas Excel a validar e importar con umbral de confianza JEV."""

    model_config = ConfigDict(extra="forbid")

    headers: list[str] = Field(
        default_factory=lambda: ["sku", "nombre", "unidad_compra", "costo_compra_neto"]
    )
    rows: list[ExcelImportRowPayload] = Field(..., min_length=1)
    jev_confidence: Decimal = Field(default=Decimal("0.92"), ge=Decimal("0"), le=Decimal("1"))


class ExcelImportResponse(BaseModel):
    """Reporte del importador Excel del catálogo."""

    model_config = ConfigDict(extra="forbid")

    imported_count: int
    error_count: int
    requires_human_review: bool
    confidence: Decimal
    errors: list[str]


class MediaUploadBase64Request(BaseModel):
    """Subida verificada de imagen o documento codificado en Base64 con chequeo de Magic Bytes."""

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(..., min_length=3, max_length=180)
    category: str = Field(default="products", pattern=r"^[a-z_]+$")
    entity_id: str = Field(..., min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    content_base64: str = Field(..., min_length=4)


class MediaUploadResponse(BaseModel):
    """Claves R2 aisladas por `{env}/{holding}/{tenant}/` y metadatos del archivo validado."""

    model_config = ConfigDict(extra="forbid")

    filename: str
    verified_mime_type: str
    size_bytes: int
    thumb_object_key: str
    display_object_key: str
