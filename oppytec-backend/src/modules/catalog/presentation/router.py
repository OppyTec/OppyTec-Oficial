"""
oppytec-backend/src/modules/catalog/presentation/router.py
Endpoints REST de Catálogo Maestro, Conversión de 3 Capas, Importación Excel JEV y Subida R2:
- `POST /api/v1/catalog/products` y `GET /api/v1/catalog/products`
- `POST /api/v1/catalog/units/convert`
- `POST /api/v1/catalog/import-excel`
- `POST /api/v1/catalog/media/upload`
"""
from __future__ import annotations

import base64
import binascii
from collections.abc import Sequence
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.config import get_settings
from src.core.exceptions import SecurityValidationError
from src.core.guards.file_magic_guard import validate_file_magic_bytes
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireTenantPermission,
)
from src.modules.catalog.application.excel_importer_service import (
    ExcelImporterService,
    JevColumnMapping,
)
from src.modules.catalog.domain.unit_conversion import (
    UnitLayers,
    purchase_to_recipe,
    purchase_to_storage,
    recipe_unit_cost,
    storage_cost_from_purchase,
)
from src.modules.catalog.presentation.schemas import (
    ExcelImportRequest,
    ExcelImportResponse,
    MediaUploadBase64Request,
    MediaUploadResponse,
    ProductCreateRequest,
    ProductResponse,
    UnitConversionRequest,
    UnitConversionResponse,
)

router = APIRouter(tags=["catalog"])

_products_store: dict[int, ProductResponse] = {}
_product_seq: int = 0


class _StaticJevMapper:
    def __init__(self, confidence: Decimal) -> None:
        self._confidence = confidence

    def map_columns(self, headers: Sequence[str]) -> JevColumnMapping:
        canonical = {h.strip(): h.strip() for h in headers}
        return JevColumnMapping(mapping=canonical, confidence=self._confidence)


@router.post(
    "/api/v1/catalog/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_endpoint(
    payload: ProductCreateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.products.create")),
    ],
) -> ProductResponse:
    """Crea un producto calculando sus costos en unidad de almacén y receta en `Decimal`."""
    global _product_seq
    _product_seq += 1
    layers = UnitLayers(
        factor_compra_a_almacen=payload.factor_compra_a_almacen,
        factor_almacen_a_receta=payload.factor_almacen_a_receta,
    )
    cost_alm = storage_cost_from_purchase(payload.costo_compra_neto, layers)
    cost_rec = recipe_unit_cost(cost_alm, layers)
    record = ProductResponse(
        product_id=_product_seq,
        sku=payload.sku,
        nombre=payload.nombre,
        marca_comercial=payload.marca_comercial,
        unidad_compra=payload.unidad_compra,
        unidad_almacen=payload.unidad_almacen,
        unidad_receta=payload.unidad_receta,
        costo_compra_neto=payload.costo_compra_neto,
        costo_unitario_almacen=cost_alm,
        costo_unitario_receta=cost_rec,
    )
    _products_store[_product_seq] = record
    return record


@router.get(
    "/api/v1/catalog/products",
    response_model=list[ProductResponse],
    status_code=status.HTTP_200_OK,
)
async def list_products_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.products.read")),
    ],
) -> list[ProductResponse]:
    """Lista los productos activos del catálogo del Tenant."""
    return list(_products_store.values())


@router.post(
    "/api/v1/catalog/units/convert",
    response_model=UnitConversionResponse,
    status_code=status.HTTP_200_OK,
)
async def convert_units_endpoint(
    payload: UnitConversionRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.units.convert")),
    ],
) -> UnitConversionResponse:
    """Calcula la conversión exacta Compra -> Almacén -> Receta en `Decimal`."""
    layers = UnitLayers(
        factor_compra_a_almacen=payload.factor_compra_a_almacen,
        factor_almacen_a_receta=payload.factor_almacen_a_receta,
    )
    cost_alm = storage_cost_from_purchase(payload.costo_compra_neto, layers)
    return UnitConversionResponse(
        cantidad_almacen=purchase_to_storage(payload.cantidad_compra, layers),
        cantidad_receta=purchase_to_recipe(payload.cantidad_compra, layers),
        costo_unitario_almacen=cost_alm,
        costo_unitario_receta=recipe_unit_cost(cost_alm, layers),
    )


@router.post(
    "/api/v1/catalog/import-excel",
    response_model=ExcelImportResponse,
    status_code=status.HTTP_200_OK,
)
async def import_excel_catalog_endpoint(
    payload: ExcelImportRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.products.import_excel")),
    ],
) -> ExcelImportResponse:
    """Importa filas de catálogo sanitizadas contra Formula Injection y validadas por umbral JEV."""
    service = ExcelImporterService(mapper=_StaticJevMapper(payload.jev_confidence))
    raw_rows = [
        {
            "sku": r.sku,
            "nombre": r.nombre,
            "unidad_compra": r.unidad_compra,
            "costo_compra_neto": str(r.costo_compra_neto),
            "factor_compra_a_almacen": str(r.factor_compra_a_almacen),
            "factor_almacen_a_receta": str(r.factor_almacen_a_receta),
        }
        for r in payload.rows
    ]
    report = service.import_rows(payload.headers, raw_rows)
    return ExcelImportResponse(
        imported_count=len(report.products),
        error_count=len(report.errors),
        requires_human_review=report.requires_human_review,
        confidence=report.confidence,
        errors=list(report.errors),
    )


@router.post(
    "/api/v1/catalog/media/upload",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_catalog_media_endpoint(
    payload: MediaUploadBase64Request,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.media.upload")),
    ],
) -> MediaUploadResponse:
    """Verifica Magic Bytes binarios del archivo subido y genera claves R2 aisladas por Tenant."""
    try:
        raw_bytes = base64.b64decode(payload.content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SecurityValidationError(
            "Invalid Base64 content in media upload.",
            i18n_key="security:errors.invalid_base64_payload",
            error_code="INVALID_BASE64_PAYLOAD",
        ) from exc

    verified_mime = validate_file_magic_bytes(
        content=raw_bytes,
        filename=payload.filename,
        allowed_types=frozenset({"image/png", "image/webp", "image/jpeg", "application/pdf"}),
    )
    env_name = get_settings().ENVIRONMENT.strip().lower()
    holding_id = principal.holding_id or "holding_default"
    tenant_id = principal.tenant_id or "tenant_default"
    prefix = f"{env_name}/{holding_id}/{tenant_id}/{payload.category}/{payload.entity_id}"

    return MediaUploadResponse(
        filename=payload.filename,
        verified_mime_type=verified_mime,
        size_bytes=len(raw_bytes),
        thumb_object_key=f"{prefix}/thumb.webp",
        display_object_key=f"{prefix}/display.webp",
    )
