"""
oppytec-backend/src/modules/catalog/presentation/router.py
Endpoints REST de Catálogo Maestro, Categorías, Marcas, Tipos de Envase,
Conversión de 3 Capas, Importación Excel JEV y Subida R2:
- CRUD de Productos (`GET`, `POST`, `PUT`, `DELETE /api/v1/catalog/products`)
- CRUD de Categorías (`GET`, `POST`, `PUT`, `DELETE /api/v1/catalog/categories`)
- CRUD de Marcas (`GET`, `POST`, `PUT`, `DELETE /api/v1/catalog/brands`)
- CRUD de Tipos de Envase (`GET`, `POST`, `PUT`, `DELETE /api/v1/catalog/container-types`)
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

from fastapi import APIRouter, Depends, Query, status

from src.core.config import get_settings
from src.core.exceptions import (
    DomainValidationError,
    ResourceNotFoundError,
    SecurityValidationError,
)
from src.core.guards.file_magic_guard import (
    sanitize_spreadsheet_cell,
    validate_file_magic_bytes,
)
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
    BodegaConfigSchema,
    BrandCreateRequest,
    BrandResponse,
    BrandUpdateRequest,
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
    ContainerTypeCreateRequest,
    ContainerTypeResponse,
    ContainerTypeUpdateRequest,
    DeleteResponse,
    ExcelAnalyzeRequest,
    ExcelAnalyzeResponse,
    ExcelBatchCreateRequest,
    ExcelBatchCreateResponse,
    ExcelImportRequest,
    ExcelImportResponse,
    MediaUploadBase64Request,
    MediaUploadResponse,
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
    UnitConversionRequest,
    UnitConversionResponse,
)

router = APIRouter(tags=["catalog"])

# Stores en memoria con persistencia de ciclo de vida de aplicación
_products_store: dict[int, ProductResponse] = {}
_product_seq: int = 0

_categories_store: dict[int, CategoryResponse] = {
    1: CategoryResponse(id=1, nombre="Carnes y Aves", icono="Beef", color="#EF4444"),
    2: CategoryResponse(id=2, nombre="Verduras y Frutas", icono="Carrot", color="#10B981"),
    3: CategoryResponse(id=3, nombre="Lácteos y Quesos", icono="Milk", color="#3B82F6"),
}
_category_seq: int = 3

_brands_store: dict[int, BrandResponse] = {
    1: BrandResponse(id=1, nombre="Pollo King", logo_url=None),
    2: BrandResponse(id=2, nombre="Savory", logo_url=None),
    3: BrandResponse(id=3, nombre="Colun", logo_url=None),
}
_brand_seq: int = 3

_container_types_store: dict[int, ContainerTypeResponse] = {
    1: ContainerTypeResponse(id=1, nombre="Caja", icono="Box", es_predeterminado=True),
    2: ContainerTypeResponse(id=2, nombre="Botella", icono="Wine", es_predeterminado=False),
    3: ContainerTypeResponse(id=3, nombre="Bolsa", icono="ShoppingBag", es_predeterminado=False),
}
_container_type_seq: int = 3


class _StaticJevMapper:
    def __init__(self, confidence: Decimal) -> None:
        self._confidence = confidence

    def map_columns(self, headers: Sequence[str]) -> JevColumnMapping:
        canonical = {h.strip(): h.strip() for h in headers}
        return JevColumnMapping(mapping=canonical, confidence=self._confidence)


# ============================================================================
# CRUD DE PRODUCTOS
# ============================================================================


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

    costo_neto = (
        payload.costo_compra_neto
        if payload.costo_compra_neto is not None
        else (payload.costo_unitario if payload.costo_unitario is not None else Decimal("0.00"))
    )
    costo_unit = (
        payload.costo_unitario
        if payload.costo_unitario is not None
        else costo_neto
    )

    layers = UnitLayers(
        factor_compra_a_almacen=payload.factor_compra_a_almacen,
        factor_almacen_a_receta=payload.factor_almacen_a_receta,
    )
    cost_alm = storage_cost_from_purchase(costo_neto, layers)
    cost_rec = recipe_unit_cost(cost_alm, layers)

    # Marca comercial
    marca_comercial = payload.marca_comercial
    if not marca_comercial and payload.marca_id and payload.marca_id in _brands_store:
        marca_comercial = _brands_store[payload.marca_id].nombre

    stock_act = (
        sum((b.stock_actual for b in payload.bodegas_config), start=Decimal("0.0000"))
        if payload.bodegas_config
        else Decimal("0.0000")
    )

    record = ProductResponse(
        id=_product_seq,
        product_id=_product_seq,
        sku=payload.sku,
        nombre=payload.nombre,
        marca_id=payload.marca_id,
        marca_comercial=marca_comercial,
        categoria_id=payload.categoria_id,
        codigo_barra=payload.codigo_barra,
        unidad_base=payload.unidad_base or payload.unidad_compra,
        tipo_envase_id=payload.tipo_envase_id,
        contenido_envase=payload.contenido_envase,
        unidad_envase=payload.unidad_envase,
        costo_unitario=costo_unit,
        costo_compra_neto=costo_neto,
        costo_unitario_almacen=cost_alm,
        costo_unitario_receta=cost_rec,
        precio_venta=payload.precio_venta,
        iva_porcentaje=payload.iva_porcentaje,
        presentaciones_compra=payload.presentaciones_compra,
        bodegas_config=payload.bodegas_config,
        unidad_compra=payload.unidad_compra,
        unidad_almacen=payload.unidad_almacen,
        unidad_receta=payload.unidad_receta,
        factor_compra_a_almacen=payload.factor_compra_a_almacen,
        factor_almacen_a_receta=payload.factor_almacen_a_receta,
        stock_minimo=payload.stock_minimo,
        stock_actual=stock_act,
        is_active=payload.is_active,
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
    categoria_id: int | None = Query(default=None),
    marca_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    bodega_id: int | None = Query(default=None),
) -> list[ProductResponse]:
    """Lista los productos activos del catálogo con filtros opcionales de categoría, marca, search y bodega."""
    results: list[ProductResponse] = []
    search_term = search.strip().lower() if search and search.strip() else None

    for p in _products_store.values():
        if not p.is_active:
            continue
        if categoria_id is not None and p.categoria_id != categoria_id:
            continue
        if marca_id is not None and p.marca_id != marca_id:
            continue
        if search_term is not None:
            matches_name = search_term in p.nombre.lower()
            matches_sku = search_term in p.sku.lower()
            matches_code = bool(p.codigo_barra and search_term in p.codigo_barra.lower())
            matches_brand = bool(p.marca_comercial and search_term in p.marca_comercial.lower())
            if not (matches_name or matches_sku or matches_code or matches_brand):
                continue
        if bodega_id is not None and p.bodegas_config:
            matching_b = next((b for b in p.bodegas_config if b.bodega_id == bodega_id), None)
            if matching_b is None:
                continue
            # Reflejar stock_actual de la bodega específica solicitada
            p = p.model_copy(update={"stock_actual": matching_b.stock_actual})

        results.append(p)

    return results


@router.get(
    "/api/v1/catalog/products/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
)
async def get_product_endpoint(
    product_id: int,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.products.read")),
    ],
) -> ProductResponse:
    """Obtiene un producto específico por su identificador primario."""
    product = _products_store.get(product_id)
    if product is None:
        raise ResourceNotFoundError(
            f"Product {product_id} not found.",
            i18n_key="catalog:errors.product_not_found",
        )
    return product


@router.put(
    "/api/v1/catalog/products/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
)
async def update_product_endpoint(
    product_id: int,
    payload: ProductUpdateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.products.update")),
    ],
) -> ProductResponse:
    """Actualiza completa o parcialmente los datos y costos de un producto."""
    existing = _products_store.get(product_id)
    if existing is None:
        raise ResourceNotFoundError(
            f"Product {product_id} not found.",
            i18n_key="catalog:errors.product_not_found",
        )

    # Actualizar campos no nulos
    nombre = payload.nombre if payload.nombre is not None else existing.nombre
    sku = payload.sku if payload.sku is not None else existing.sku
    marca_id = payload.marca_id if payload.marca_id is not None else existing.marca_id
    marca_comercial = payload.marca_comercial if payload.marca_comercial is not None else existing.marca_comercial
    if not marca_comercial and marca_id and marca_id in _brands_store:
        marca_comercial = _brands_store[marca_id].nombre

    categoria_id = payload.categoria_id if payload.categoria_id is not None else existing.categoria_id
    codigo_barra = payload.codigo_barra if payload.codigo_barra is not None else existing.codigo_barra
    unidad_base = payload.unidad_base if payload.unidad_base is not None else existing.unidad_base
    tipo_envase_id = payload.tipo_envase_id if payload.tipo_envase_id is not None else existing.tipo_envase_id
    contenido_envase = payload.contenido_envase if payload.contenido_envase is not None else existing.contenido_envase
    unidad_envase = payload.unidad_envase if payload.unidad_envase is not None else existing.unidad_envase

    costo_neto = payload.costo_compra_neto if payload.costo_compra_neto is not None else existing.costo_compra_neto
    costo_unit = payload.costo_unitario if payload.costo_unitario is not None else (
        costo_neto if payload.costo_compra_neto is not None else existing.costo_unitario
    )
    precio_venta = payload.precio_venta if payload.precio_venta is not None else existing.precio_venta
    iva_porcentaje = payload.iva_porcentaje if payload.iva_porcentaje is not None else existing.iva_porcentaje

    presentaciones = payload.presentaciones_compra if payload.presentaciones_compra is not None else existing.presentaciones_compra
    bodegas = payload.bodegas_config if payload.bodegas_config is not None else existing.bodegas_config

    unidad_compra = payload.unidad_compra if payload.unidad_compra is not None else existing.unidad_compra
    unidad_almacen = payload.unidad_almacen if payload.unidad_almacen is not None else existing.unidad_almacen
    unidad_receta = payload.unidad_receta if payload.unidad_receta is not None else existing.unidad_receta
    factor_c_a = payload.factor_compra_a_almacen if payload.factor_compra_a_almacen is not None else existing.factor_compra_a_almacen
    factor_a_r = payload.factor_almacen_a_receta if payload.factor_almacen_a_receta is not None else existing.factor_almacen_a_receta
    stock_min = payload.stock_minimo if payload.stock_minimo is not None else existing.stock_minimo
    is_active = payload.is_active if payload.is_active is not None else existing.is_active

    layers = UnitLayers(
        factor_compra_a_almacen=factor_c_a,
        factor_almacen_a_receta=factor_a_r,
    )
    cost_alm = storage_cost_from_purchase(costo_neto, layers)
    cost_rec = recipe_unit_cost(cost_alm, layers)

    stock_act = (
        sum((b.stock_actual for b in bodegas), start=Decimal("0.0000"))
        if bodegas
        else existing.stock_actual
    )

    updated = ProductResponse(
        id=product_id,
        product_id=product_id,
        sku=sku,
        nombre=nombre,
        marca_id=marca_id,
        marca_comercial=marca_comercial,
        categoria_id=categoria_id,
        codigo_barra=codigo_barra,
        unidad_base=unidad_base,
        tipo_envase_id=tipo_envase_id,
        contenido_envase=contenido_envase,
        unidad_envase=unidad_envase,
        costo_unitario=costo_unit,
        costo_compra_neto=costo_neto,
        costo_unitario_almacen=cost_alm,
        costo_unitario_receta=cost_rec,
        precio_venta=precio_venta,
        iva_porcentaje=iva_porcentaje,
        presentaciones_compra=presentaciones,
        bodegas_config=bodegas,
        unidad_compra=unidad_compra,
        unidad_almacen=unidad_almacen,
        unidad_receta=unidad_receta,
        factor_compra_a_almacen=factor_c_a,
        factor_almacen_a_receta=factor_a_r,
        stock_minimo=stock_min,
        stock_actual=stock_act,
        is_active=is_active,
    )
    _products_store[product_id] = updated
    return updated


@router.delete(
    "/api/v1/catalog/products/{product_id}",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_product_endpoint(
    product_id: int,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.products.delete")),
    ],
    permanent: bool = Query(default=False),
) -> DeleteResponse:
    """Eliminación lógica o física de un producto."""
    if product_id not in _products_store:
        raise ResourceNotFoundError(
            f"Product {product_id} not found.",
            i18n_key="catalog:errors.product_not_found",
        )

    if permanent:
        _products_store.pop(product_id)
        msg = f"Product {product_id} permanently deleted."
    else:
        existing = _products_store[product_id]
        _products_store[product_id] = existing.model_copy(update={"is_active": False})
        msg = f"Product {product_id} logically soft-deleted."

    return DeleteResponse(success=True, message=msg, id=product_id)


# ============================================================================
# CRUD DE CATEGORÍAS
# ============================================================================


@router.get(
    "/api/v1/catalog/categories",
    response_model=list[CategoryResponse],
    status_code=status.HTTP_200_OK,
)
async def list_categories_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.categories.read")),
    ],
) -> list[CategoryResponse]:
    """Lista las categorías activas del catálogo."""
    return [c for c in _categories_store.values() if c.is_active]


@router.post(
    "/api/v1/catalog/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category_endpoint(
    payload: CategoryCreateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.categories.create")),
    ],
) -> CategoryResponse:
    """Crea una nueva categoría de catálogo."""
    global _category_seq
    _category_seq += 1
    record = CategoryResponse(
        id=_category_seq,
        nombre=payload.nombre,
        icono=payload.icono,
        color=payload.color,
        is_active=True,
    )
    _categories_store[_category_seq] = record
    return record


@router.put(
    "/api/v1/catalog/categories/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
)
async def update_category_endpoint(
    category_id: int,
    payload: CategoryUpdateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.categories.update")),
    ],
) -> CategoryResponse:
    """Actualiza una categoría existente."""
    existing = _categories_store.get(category_id)
    if existing is None:
        raise ResourceNotFoundError(
            f"Category {category_id} not found.",
            i18n_key="catalog:errors.category_not_found",
        )
    updated = CategoryResponse(
        id=category_id,
        nombre=payload.nombre if payload.nombre is not None else existing.nombre,
        icono=payload.icono if payload.icono is not None else existing.icono,
        color=payload.color if payload.color is not None else existing.color,
        is_active=payload.is_active if payload.is_active is not None else existing.is_active,
    )
    _categories_store[category_id] = updated
    return updated


@router.delete(
    "/api/v1/catalog/categories/{category_id}",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_category_endpoint(
    category_id: int,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.categories.delete")),
    ],
    permanent: bool = Query(default=False),
) -> DeleteResponse:
    """Elimina lógica o físicamente una categoría."""
    if category_id not in _categories_store:
        raise ResourceNotFoundError(
            f"Category {category_id} not found.",
            i18n_key="catalog:errors.category_not_found",
        )
    if permanent:
        _categories_store.pop(category_id)
        msg = f"Category {category_id} permanently deleted."
    else:
        existing = _categories_store[category_id]
        _categories_store[category_id] = existing.model_copy(update={"is_active": False})
        msg = f"Category {category_id} logically soft-deleted."

    return DeleteResponse(success=True, message=msg, id=category_id)


# ============================================================================
# CRUD DE MARCAS
# ============================================================================


@router.get(
    "/api/v1/catalog/brands",
    response_model=list[BrandResponse],
    status_code=status.HTTP_200_OK,
)
async def list_brands_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.brands.read")),
    ],
) -> list[BrandResponse]:
    """Lista las marcas comerciales activas del catálogo."""
    return [b for b in _brands_store.values() if b.is_active]


@router.post(
    "/api/v1/catalog/brands",
    response_model=BrandResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_brand_endpoint(
    payload: BrandCreateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.brands.create")),
    ],
) -> BrandResponse:
    """Crea una nueva marca comercial inmutable."""
    global _brand_seq
    _brand_seq += 1
    record = BrandResponse(
        id=_brand_seq,
        nombre=payload.nombre,
        logo_url=payload.logo_url,
        is_active=True,
    )
    _brands_store[_brand_seq] = record
    return record


@router.put(
    "/api/v1/catalog/brands/{brand_id}",
    response_model=BrandResponse,
    status_code=status.HTTP_200_OK,
)
async def update_brand_endpoint(
    brand_id: int,
    payload: BrandUpdateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.brands.update")),
    ],
) -> BrandResponse:
    """Actualiza una marca comercial."""
    existing = _brands_store.get(brand_id)
    if existing is None:
        raise ResourceNotFoundError(
            f"Brand {brand_id} not found.",
            i18n_key="catalog:errors.brand_not_found",
        )
    updated = BrandResponse(
        id=brand_id,
        nombre=payload.nombre if payload.nombre is not None else existing.nombre,
        logo_url=payload.logo_url if payload.logo_url is not None else existing.logo_url,
        is_active=payload.is_active if payload.is_active is not None else existing.is_active,
    )
    _brands_store[brand_id] = updated
    return updated


@router.delete(
    "/api/v1/catalog/brands/{brand_id}",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_brand_endpoint(
    brand_id: int,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.brands.delete")),
    ],
    permanent: bool = Query(default=False),
) -> DeleteResponse:
    """Elimina lógica o físicamente una marca comercial."""
    if brand_id not in _brands_store:
        raise ResourceNotFoundError(
            f"Brand {brand_id} not found.",
            i18n_key="catalog:errors.brand_not_found",
        )
    if permanent:
        _brands_store.pop(brand_id)
        msg = f"Brand {brand_id} permanently deleted."
    else:
        existing = _brands_store[brand_id]
        _brands_store[brand_id] = existing.model_copy(update={"is_active": False})
        msg = f"Brand {brand_id} logically soft-deleted."

    return DeleteResponse(success=True, message=msg, id=brand_id)


# ============================================================================
# CRUD DE TIPOS DE ENVASE
# ============================================================================


@router.get(
    "/api/v1/catalog/container-types",
    response_model=list[ContainerTypeResponse],
    status_code=status.HTTP_200_OK,
)
async def list_container_types_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.container_types.read")),
    ],
) -> list[ContainerTypeResponse]:
    """Lista los tipos de envase o empaque registrados."""
    return [c for c in _container_types_store.values() if c.is_active]


@router.post(
    "/api/v1/catalog/container-types",
    response_model=ContainerTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_container_type_endpoint(
    payload: ContainerTypeCreateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.container_types.create")),
    ],
) -> ContainerTypeResponse:
    """Crea un nuevo tipo de envase."""
    global _container_type_seq
    _container_type_seq += 1
    record = ContainerTypeResponse(
        id=_container_type_seq,
        nombre=payload.nombre,
        icono=payload.icono,
        es_predeterminado=payload.es_predeterminado,
        is_active=True,
    )
    _container_types_store[_container_type_seq] = record
    return record


@router.put(
    "/api/v1/catalog/container-types/{container_type_id}",
    response_model=ContainerTypeResponse,
    status_code=status.HTTP_200_OK,
)
async def update_container_type_endpoint(
    container_type_id: int,
    payload: ContainerTypeUpdateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.container_types.update")),
    ],
) -> ContainerTypeResponse:
    """Actualiza un tipo de envase."""
    existing = _container_types_store.get(container_type_id)
    if existing is None:
        raise ResourceNotFoundError(
            f"Container type {container_type_id} not found.",
            i18n_key="catalog:errors.container_type_not_found",
        )
    updated = ContainerTypeResponse(
        id=container_type_id,
        nombre=payload.nombre if payload.nombre is not None else existing.nombre,
        icono=payload.icono if payload.icono is not None else existing.icono,
        es_predeterminado=(
            payload.es_predeterminado if payload.es_predeterminado is not None else existing.es_predeterminado
        ),
        is_active=payload.is_active if payload.is_active is not None else existing.is_active,
    )
    _container_types_store[container_type_id] = updated
    return updated


@router.delete(
    "/api/v1/catalog/container-types/{container_type_id}",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_container_type_endpoint(
    container_type_id: int,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.container_types.delete")),
    ],
    permanent: bool = Query(default=False),
) -> DeleteResponse:
    """Elimina lógica o físicamente un tipo de envase."""
    if container_type_id not in _container_types_store:
        raise ResourceNotFoundError(
            f"Container type {container_type_id} not found.",
            i18n_key="catalog:errors.container_type_not_found",
        )
    if permanent:
        _container_types_store.pop(container_type_id)
        msg = f"Container type {container_type_id} permanently deleted."
    else:
        existing = _container_types_store[container_type_id]
        _container_types_store[container_type_id] = existing.model_copy(update={"is_active": False})
        msg = f"Container type {container_type_id} logically soft-deleted."

    return DeleteResponse(success=True, message=msg, id=container_type_id)


# ============================================================================
# CONVERSIÓN DE 3 CAPAS, IMPORTACIÓN EXCEL Y SUBIDA R2
# ============================================================================


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


def find_product_by_id(product_id: int) -> ProductResponse | None:
    """Retorna un producto por ID primario."""
    return _products_store.get(product_id)


def create_product_record(product: ProductResponse) -> int:
    """Registra un producto en el store asignando ID autoincremental."""
    global _product_seq
    _product_seq += 1
    p = product.model_copy(update={"id": _product_seq, "product_id": _product_seq})
    _products_store[_product_seq] = p
    return _product_seq


# ============================================================================
# INGESTA INTELIGENTE: EXCEL IA
# ============================================================================

_CANONICAL_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("sku", ("sku", "codigo", "cod_barra", "barcode", "cod", "referencia")),
    ("costo_neto", ("costo_neto", "costo_compra", "precio_compra", "costo_unitario", "valor_neto", "costo")),
    ("costo_bruto", ("costo_bruto", "costo_con_iva", "costo_total")),
    ("precio_venta", ("precio_venta", "pvp", "precio_bruto", "precio_unitario", "precio")),
    ("stock_inicial", ("stock_inicial", "cantidad", "saldo", "existencia", "inventario", "stock", "cant")),
    ("categoria", ("categoria", "rubro", "familia", "linea", "grupo", "cat")),
    ("marca", ("marca", "fabricante", "brand", "laboratorio")),
    ("unidad_envase", ("envase", "embalaje", "empaque", "formato", "unidad_medida", "unidad", "um")),
    ("nombre", ("descripcion", "descrip", "producto", "item", "detalle", "nombre", "articulo")),
]


@router.post(
    "/api/v1/catalog/import/analyze-excel",
    response_model=ExcelAnalyzeResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_excel_endpoint(
    payload: ExcelAnalyzeRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.import.analyze")),
    ],
) -> ExcelAnalyzeResponse:
    """
    Analiza heurísticamente encabezados y datos de planilla Excel, detectando columnas canónicas,
    entidades sugeridas y neutralizando vectores de Formula Injection (CWE-1236).
    """
    # 1. Detección heurística de columnas
    detected_cols: dict[str, str] = {}
    assigned_canonicals: set[str] = set()

    for raw_h in payload.raw_headers:
        norm_h = raw_h.strip().lower().replace("-", "_").replace(" ", "_")
        if payload.column_mapping and raw_h in payload.column_mapping:
            canon = payload.column_mapping[raw_h]
            detected_cols[raw_h] = canon
            assigned_canonicals.add(canon)
            continue

        h_tokens = set(norm_h.split("_"))
        for canon, keywords in _CANONICAL_KEYWORDS:
            if canon in assigned_canonicals:
                continue
            if any(kw == norm_h or kw in h_tokens for kw in keywords):
                detected_cols[raw_h] = canon
                assigned_canonicals.add(canon)
                break


    # 2. Sanitización estricta anti-Formula Injection (CWE-1236)
    sanitized_rows: list[dict[str, object]] = []
    warnings: list[str] = []

    for r_idx, row in enumerate(payload.rows_data, start=1):
        clean_row: dict[str, object] = {}
        for col, val in row.items():
            if isinstance(val, str):
                cleaned_val = sanitize_spreadsheet_cell(val, reject_dde_payloads=True)
                if cleaned_val != val:
                    warnings.append(f"Fila {r_idx} columna '{col}': vector de inyección de fórmula neutralizado.")
                clean_row[col] = cleaned_val
            else:
                clean_row[col] = val
        sanitized_rows.append(clean_row)

    # 3. Detección de entidades sugeridas (categorías y marcas)
    cat_header = next((h for h, c in detected_cols.items() if c == "categoria"), None)
    marca_header = next((h for h, c in detected_cols.items() if c == "marca"), None)

    existing_cats_map = {c.nombre.lower(): c.nombre for c in _categories_store.values() if c.is_active}
    existing_brands_map = {b.nombre.lower(): b.nombre for b in _brands_store.values() if b.is_active}

    found_cats: set[str] = set()
    found_brands: set[str] = set()

    for r in sanitized_rows:
        if cat_header and cat_header in r and r[cat_header]:
            val_c = str(r[cat_header]).strip()
            if val_c:
                found_cats.add(val_c)
        if marca_header and marca_header in r and r[marca_header]:
            val_m = str(r[marca_header]).strip()
            if val_m:
                found_brands.add(val_m)

    suggested_cats: list[str] = []
    matched_cats: list[str] = []
    for c_val in sorted(found_cats):
        if c_val.lower() in existing_cats_map:
            matched_cats.append(existing_cats_map[c_val.lower()])
        else:
            suggested_cats.append(c_val)

    suggested_brands: list[str] = []
    matched_brands: list[str] = []
    for b_val in sorted(found_brands):
        if b_val.lower() in existing_brands_map:
            matched_brands.append(existing_brands_map[b_val.lower()])
        else:
            suggested_brands.append(b_val)

    confidence = Decimal("0.95") if len(detected_cols) >= 3 else Decimal("0.70")

    return ExcelAnalyzeResponse(
        sheet_name=payload.sheet_name,
        detected_columns=detected_cols,
        confidence=confidence,
        total_rows=len(sanitized_rows),
        suggested_categories_to_create=suggested_cats,
        existing_categories=matched_cats,
        suggested_brands_to_create=suggested_brands,
        existing_brands=matched_brands,
        sample_rows=sanitized_rows[:5],
        warnings=warnings,
    )


@router.post(
    "/api/v1/catalog/import/batch-create",
    response_model=ExcelBatchCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def batch_create_catalog_endpoint(
    payload: ExcelBatchCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("catalog.import.batch_create")),
    ],
) -> ExcelBatchCreateResponse:
    """
    Carga masiva transaccional de productos y creación automática de categorías y marcas sugeridas.
    Límite máximo estricto: 1.500 productos por lote (HTTP 400 si excede).
    """
    if len(payload.items) > 1500:
        raise DomainValidationError(
            f"Batch limit exceeded: maximum 1,500 products per upload (received {len(payload.items)}).",
            i18n_key="catalog:errors.batch_limit_exceeded",
        )

    # 1. Crear categorías sugeridas
    created_cats: list[str] = []
    global _category_seq
    for cat_name in payload.entities_to_create.get("categories", []):
        cat_clean = sanitize_spreadsheet_cell(cat_name.strip(), reject_dde_payloads=True)
        if cat_clean and not any(c.nombre.lower() == cat_clean.lower() for c in _categories_store.values()):
            _category_seq += 1
            _categories_store[_category_seq] = CategoryResponse(
                id=_category_seq,
                nombre=cat_clean,
                icono="Package",
                color="#007BFF",
                is_active=True,
            )
            created_cats.append(cat_clean)

    # 2. Crear marcas sugeridas
    created_brands: list[str] = []
    global _brand_seq
    for brand_name in payload.entities_to_create.get("brands", []):
        brand_clean = sanitize_spreadsheet_cell(brand_name.strip(), reject_dde_payloads=True)
        if brand_clean and not any(b.nombre.lower() == brand_clean.lower() for b in _brands_store.values()):
            _brand_seq += 1
            _brands_store[_brand_seq] = BrandResponse(
                id=_brand_seq,
                nombre=brand_clean,
                logo_url=None,
                is_active=True,
            )
            created_brands.append(brand_clean)

    # 3. Crear productos e inicializar stock en Kardex si corresponde
    global _product_seq
    created_count = 0
    kardex_movements = 0
    errors: list[str] = []

    for idx, raw_item in enumerate(payload.items, start=1):
        try:
            nombre = str(raw_item.get("nombre") or raw_item.get("descripcion") or f"Producto {idx}").strip()
            nombre = sanitize_spreadsheet_cell(nombre, reject_dde_payloads=True)
            sku = str(raw_item.get("sku") or raw_item.get("codigo") or f"SKU-{_product_seq + 1:04d}").strip()
            sku = sanitize_spreadsheet_cell(sku, reject_dde_payloads=True)

            costo_raw = raw_item.get("costo_unitario") or raw_item.get("costo_neto") or raw_item.get("costo") or "0.00"
            costo_dec = Decimal(str(costo_raw))
            precio_raw = raw_item.get("precio_venta") or raw_item.get("precio") or "0.00"
            precio_dec = Decimal(str(precio_raw))

            # Resuelve categoría
            cat_id: int | None = None
            raw_cat = raw_item.get("categoria") or raw_item.get("categoria_id")
            if raw_cat:
                if isinstance(raw_cat, int):
                    cat_id = raw_cat
                else:
                    found_c = next((c for c in _categories_store.values() if c.nombre.lower() == str(raw_cat).lower()), None)
                    if found_c:
                        cat_id = found_c.id

            # Resuelve marca
            marca_id: int | None = None
            raw_marca = raw_item.get("marca") or raw_item.get("marca_id")
            if raw_marca:
                if isinstance(raw_marca, int):
                    marca_id = raw_marca
                else:
                    found_b = next((b for b in _brands_store.values() if b.nombre.lower() == str(raw_marca).lower()), None)
                    if found_b:
                        marca_id = found_b.id

            _product_seq += 1
            prod_id = _product_seq
            layers = UnitLayers(Decimal("1.0000"), Decimal("1000.0000"))
            cost_alm = storage_cost_from_purchase(costo_dec, layers)
            cost_rec = recipe_unit_cost(cost_alm, layers)

            bodega_id_int = int(payload.default_bodega_id) if payload.default_bodega_id else None
            stock_ini_raw = raw_item.get("stock_inicial") or raw_item.get("stock") or "0.0000"
            stock_ini = Decimal(str(stock_ini_raw))

            bodegas_cfg: list[BodegaConfigSchema] = []
            if bodega_id_int:
                bodegas_cfg.append(
                    BodegaConfigSchema(
                        bodega_id=bodega_id_int,
                        stock_minimo=Decimal("0.0000"),
                        stock_actual=stock_ini,
                    )
                )

            new_prod = ProductResponse(
                id=prod_id,
                product_id=prod_id,
                sku=sku,
                nombre=nombre,
                marca_id=marca_id,
                marca_comercial=str(raw_marca) if raw_marca else None,
                categoria_id=cat_id,
                codigo_barra=str(raw_item.get("codigo_barra")) if raw_item.get("codigo_barra") else None,
                costo_unitario=costo_dec,
                costo_compra_neto=costo_dec,
                costo_unitario_almacen=cost_alm,
                costo_unitario_receta=cost_rec,
                precio_venta=precio_dec,
                bodegas_config=bodegas_cfg,
                stock_actual=stock_ini,
                is_active=True,
            )
            _products_store[prod_id] = new_prod
            created_count += 1

            if payload.register_initial_stock and bodega_id_int and stock_ini > Decimal("0.0000"):
                from src.modules.inventory.presentation.router import _inventory_service
                _inventory_service.register_movement(
                    producto_id=prod_id,
                    bodega_id=bodega_id_int,
                    movement_type="ENTRADA",
                    quantity=stock_ini,
                    unit_cost=costo_dec,
                    actor_user_id=principal.user_id,
                )
                kardex_movements += 1

        except Exception as ex:
            errors.append(f"Row {idx}: {ex}")

    return ExcelBatchCreateResponse(
        created_products_count=created_count,
        created_categories=created_cats,
        created_brands=created_brands,
        kardex_movements_count=kardex_movements,
        errors=errors,
    )

