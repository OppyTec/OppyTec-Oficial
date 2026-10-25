"""
oppytec-backend/src/modules/catalog/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`, `Decimal` exclusivo) para Catálogo, Categorías, Marcas,
Tipos de Envase, Conversión de 3 Capas, Importación Excel y Subida Segura de Imágenes WebP a R2.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.file_magic_guard import MAX_BATCH_ROWS, sanitize_spreadsheet_cell
from src.core.guards.xss_sanitizer import sanitize_text_input


class BodegaConfigSchema(BaseModel):
    """Configuración de stock y ubicación de un producto por bodega."""

    model_config = ConfigDict(extra="forbid")

    bodega_id: int = Field(..., gt=0)
    stock_minimo: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"))
    stock_actual: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"))
    coordenada_letra: str | None = None
    coordenada_numero: str | None = None
    bodega_nombre: str | None = None

    @field_validator("coordenada_letra", "coordenada_numero", "bodega_nombre")
    @classmethod
    def _sanitize_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="bodega_config_field")


class PresentacionCompraSchema(BaseModel):
    """Presentación de compra de un producto (caja, bolsa, pack) con equivalencia en unidades base."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=1, max_length=120)
    equivalencia: Decimal = Field(default=Decimal("1.0000"), gt=Decimal("0"))
    proveedor_id: str | int | None = None
    ultimo_costo: Decimal | None = None
    penultimo_costo: Decimal | None = None
    costo_bruto: Decimal | None = None
    iva_porcentaje: Decimal | None = None
    tipo_embalaje: str | None = None
    tipo_envase_id: int | str | None = None
    contenido_envase: Decimal | None = None
    cantidad: Decimal | None = None
    unidad_medida: str | None = None
    sku: str | None = None
    codigo_barra: str | None = None

    @field_validator(
        "nombre",
        "tipo_embalaje",
        "unidad_medida",
        "sku",
        "codigo_barra",
        check_fields=False,
    )
    @classmethod
    def _sanitize_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="presentacion_field")


class ProductCreateRequest(BaseModel):
    """Alta de producto en el catálogo con soporte multi-bodega, presentaciones y 3 capas."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=2, max_length=180)
    sku: str = Field(..., min_length=1, max_length=64)
    marca_id: int | None = None
    marca_comercial: str | None = Field(default=None, max_length=120)
    categoria_id: int | None = None
    codigo_barra: str | None = Field(default=None, max_length=64)
    unidad_base: str = Field(default="UNIDAD", min_length=1, max_length=32)
    tipo_envase_id: int | None = None
    contenido_envase: Decimal | None = Field(default=None, ge=Decimal("0"))
    unidad_envase: str | None = Field(default=None, max_length=32)
    costo_unitario: Decimal | None = Field(default=None, ge=Decimal("0"))
    costo_compra_neto: Decimal | None = Field(default=None, ge=Decimal("0"))
    precio_venta: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    iva_porcentaje: Decimal = Field(default=Decimal("19.00"), ge=Decimal("0"))
    presentaciones_compra: list[PresentacionCompraSchema] = Field(default_factory=list)
    bodegas_config: list[BodegaConfigSchema] = Field(default_factory=list)

    # 3 Capas de unidades (compatibilidad)
    unidad_compra: str = Field(default="UNIDAD", min_length=1, max_length=32)
    unidad_almacen: str = Field(default="kg", min_length=1, max_length=32)
    unidad_receta: str = Field(default="g", min_length=1, max_length=32)
    factor_compra_a_almacen: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    factor_almacen_a_receta: Decimal = Field(default=Decimal("1000"), gt=Decimal("0"))
    stock_minimo: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"))
    is_active: bool = True

    @field_validator(
        "sku",
        "nombre",
        "marca_comercial",
        "codigo_barra",
        "unidad_base",
        "unidad_envase",
        "unidad_compra",
        "unidad_almacen",
        "unidad_receta",
    )
    @classmethod
    def _sanitize_product_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="product_field")


class ProductUpdateRequest(BaseModel):
    """Actualización completa o parcial de producto en el catálogo."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=2, max_length=180)
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    marca_id: int | None = None
    marca_comercial: str | None = Field(default=None, max_length=120)
    categoria_id: int | None = None
    codigo_barra: str | None = Field(default=None, max_length=64)
    unidad_base: str | None = Field(default=None, max_length=32)
    tipo_envase_id: int | None = None
    contenido_envase: Decimal | None = Field(default=None, ge=Decimal("0"))
    unidad_envase: str | None = Field(default=None, max_length=32)
    costo_unitario: Decimal | None = Field(default=None, ge=Decimal("0"))
    costo_compra_neto: Decimal | None = Field(default=None, ge=Decimal("0"))
    precio_venta: Decimal | None = Field(default=None, ge=Decimal("0"))
    iva_porcentaje: Decimal | None = Field(default=None, ge=Decimal("0"))
    presentaciones_compra: list[PresentacionCompraSchema] | None = None
    bodegas_config: list[BodegaConfigSchema] | None = None

    unidad_compra: str | None = Field(default=None, min_length=1, max_length=32)
    unidad_almacen: str | None = Field(default=None, min_length=1, max_length=32)
    unidad_receta: str | None = Field(default=None, min_length=1, max_length=32)
    factor_compra_a_almacen: Decimal | None = Field(default=None, gt=Decimal("0"))
    factor_almacen_a_receta: Decimal | None = Field(default=None, gt=Decimal("0"))
    stock_minimo: Decimal | None = Field(default=None, ge=Decimal("0"))
    is_active: bool | None = None

    @field_validator(
        "sku",
        "nombre",
        "marca_comercial",
        "codigo_barra",
        "unidad_base",
        "unidad_envase",
        "unidad_compra",
        "unidad_almacen",
        "unidad_receta",
    )
    @classmethod
    def _sanitize_product_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="product_field")


class ProductResponse(BaseModel):
    """Respuesta completa de producto con costos calculados en las 3 capas de unidades."""

    model_config = ConfigDict(extra="forbid")

    id: int
    product_id: int
    sku: str
    nombre: str
    marca_id: int | None = None
    marca_comercial: str | None = None
    categoria_id: int | None = None
    codigo_barra: str | None = None
    unidad_base: str = "UNIDAD"
    tipo_envase_id: int | None = None
    contenido_envase: Decimal | None = None
    unidad_envase: str | None = None
    costo_unitario: Decimal = Decimal("0.00")
    costo_compra_neto: Decimal = Decimal("0.00")
    costo_unitario_almacen: Decimal = Decimal("0.00")
    costo_unitario_receta: Decimal = Decimal("0.00")
    precio_venta: Decimal = Decimal("0.00")
    iva_porcentaje: Decimal = Decimal("19.00")
    presentaciones_compra: list[PresentacionCompraSchema] = Field(default_factory=list)
    bodegas_config: list[BodegaConfigSchema] = Field(default_factory=list)
    unidad_compra: str = "UNIDAD"
    unidad_almacen: str = "kg"
    unidad_receta: str = "g"
    factor_compra_a_almacen: Decimal = Decimal("1.0000")
    factor_almacen_a_receta: Decimal = Decimal("1000.0000")
    stock_minimo: Decimal = Decimal("0.0000")
    stock_actual: Decimal = Decimal("0.0000")
    is_active: bool = True


class CategoryCreateRequest(BaseModel):
    """Creación de categoría con nombre e iconografía."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=1, max_length=120)
    icono: str = Field(default="Package", max_length=64)
    color: str = Field(default="#007BFF", max_length=32)

    @field_validator("nombre", "icono", "color")
    @classmethod
    def _sanitize(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="category_field")


class CategoryUpdateRequest(BaseModel):
    """Actualización de categoría."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    icono: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None

    @field_validator("nombre", "icono", "color")
    @classmethod
    def _sanitize(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="category_field")


class CategoryResponse(BaseModel):
    """Representación de categoría."""

    model_config = ConfigDict(extra="forbid")

    id: int
    nombre: str
    icono: str
    color: str
    is_active: bool = True


class BrandCreateRequest(BaseModel):
    """Creación de marca comercial inmutable (`translatable = False`)."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=1, max_length=120)
    logo_url: str | None = Field(default=None, max_length=255)

    @field_validator("nombre", "logo_url")
    @classmethod
    def _sanitize(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="brand_field")


class BrandUpdateRequest(BaseModel):
    """Actualización de marca comercial."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    logo_url: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None

    @field_validator("nombre", "logo_url")
    @classmethod
    def _sanitize(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="brand_field")


class BrandResponse(BaseModel):
    """Representación de marca comercial."""

    model_config = ConfigDict(extra="forbid")

    id: int
    nombre: str
    logo_url: str | None = None
    is_active: bool = True


class ContainerTypeCreateRequest(BaseModel):
    """Creación de tipo de envase o empaque."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=1, max_length=120)
    icono: str | None = Field(default=None, max_length=64)
    es_predeterminado: bool = False

    @field_validator("nombre", "icono")
    @classmethod
    def _sanitize(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="container_type_field")


class ContainerTypeUpdateRequest(BaseModel):
    """Actualización de tipo de envase."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    icono: str | None = Field(default=None, max_length=64)
    es_predeterminado: bool | None = None
    is_active: bool | None = None

    @field_validator("nombre", "icono")
    @classmethod
    def _sanitize(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="container_type_field")


class ContainerTypeResponse(BaseModel):
    """Representación de tipo de envase."""

    model_config = ConfigDict(extra="forbid")

    id: int
    nombre: str
    icono: str | None = None
    es_predeterminado: bool = False
    is_active: bool = True


class DeleteResponse(BaseModel):
    """Respuesta estándar de eliminación lógica o física."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    message: str
    id: int


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
    """Lote de filas Excel a validar e importar con umbral de confianza JEV (máx 1.500 filas)."""

    model_config = ConfigDict(extra="forbid")

    headers: list[str] = Field(
        default_factory=lambda: ["sku", "nombre", "unidad_compra", "costo_compra_neto"],
        max_length=100,
    )
    rows: list[ExcelImportRowPayload] = Field(..., min_length=1, max_length=MAX_BATCH_ROWS)
    jev_confidence: Decimal = Field(default=Decimal("0.92"), ge=Decimal("0"), le=Decimal("1"))

    @field_validator("headers")
    @classmethod
    def _sanitize_headers(cls, headers: list[str]) -> list[str]:
        return [
            sanitize_text_input(
                sanitize_spreadsheet_cell(h, reject_dde_payloads=True),
                field_name="excel_header",
            )
            for h in headers
        ]


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
    content_base64: str = Field(..., min_length=4, max_length=14 * 1024 * 1024)


class MediaUploadResponse(BaseModel):
    """Claves R2 aisladas por `{env}/{holding}/{tenant}/` y metadatos del archivo validado."""

    model_config = ConfigDict(extra="forbid")

    filename: str
    verified_mime_type: str
    size_bytes: int
    thumb_object_key: str
    display_object_key: str


class ExcelAnalyzeRequest(BaseModel):
    """Solicitud de análisis heurístico de planilla Excel."""

    model_config = ConfigDict(extra="forbid")

    sheet_name: str = Field(default="Sheet1", max_length=120)
    raw_headers: list[str] = Field(..., min_length=1)
    rows_data: list[dict[str, object]] = Field(default_factory=list)
    column_mapping: dict[str, str] | None = None


class ExcelAnalyzeResponse(BaseModel):
    """Resultado del análisis heurístico de columnas y entidades del Excel."""

    model_config = ConfigDict(extra="forbid")

    sheet_name: str
    detected_columns: dict[str, str]
    confidence: Decimal
    total_rows: int
    suggested_categories_to_create: list[str]
    existing_categories: list[str]
    suggested_brands_to_create: list[str]
    existing_brands: list[str]
    sample_rows: list[dict[str, object]]
    warnings: list[str]


class ExcelBatchCreateRequest(BaseModel):
    """Solicitud de creación masiva de productos y entidades detectadas."""

    model_config = ConfigDict(extra="forbid")

    items: list[dict[str, object]] = Field(..., min_length=1)
    entities_to_create: dict[str, list[str]] = Field(default_factory=dict)
    register_initial_stock: bool = False
    default_bodega_id: int | str | None = None


class ExcelBatchCreateResponse(BaseModel):
    """Reporte de creación masiva desde planilla Excel."""

    model_config = ConfigDict(extra="forbid")

    created_products_count: int
    created_categories: list[str]
    created_brands: list[str]
    kardex_movements_count: int
    errors: list[str]

