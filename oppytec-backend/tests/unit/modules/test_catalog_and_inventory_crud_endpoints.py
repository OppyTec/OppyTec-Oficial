"""
oppytec-backend/tests/unit/modules/test_catalog_and_inventory_crud_endpoints.py
Pruebas unitarias 1:1 para los endpoints de CRUD de Catálogo e Inventario:
- CRUD de Productos (filtros categoria_id, marca_id, search, bodega_id)
- CRUD de Categorías
- CRUD de Marcas
- CRUD de Tipos de Envase
- Transferencia Masiva de Stock en Kardex (validación origen vs destino, control de saldos)
- Verificación estricta de RBAC de 3 niveles y contratos RFC 7807 (cero float).
"""
from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from src.core.security import create_access_token

pytestmark = pytest.mark.unit

TENANT_A = "tenant_catalog_test"


def _make_headers(permissions: list[str], tenant_id: str = TENANT_A, user_id: int = 101) -> dict[str, str]:
    """Genera token JWT con permisos RBAC y cabecera de aislamiento multi-tenant."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        holding_id="holding_catalog",
        role_grants=permissions,
        accessible_tenants=[tenant_id],
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }


@pytest.mark.asyncio
async def test_products_crud_and_filters(async_client: httpx.AsyncClient) -> None:
    """Verifica el ciclo CRUD completo de productos y filtrado por categoría, marca, search y bodega."""
    headers_all = _make_headers(
        [
            "catalog.products.create",
            "catalog.products.read",
            "catalog.products.update",
            "catalog.products.delete",
        ]
    )

    # 1. Crear producto con payload enriquecido (v2)
    create_payload = {
        "nombre": "Leche Entera 1L",
        "sku": "LEC-ENT-001",
        "marca_id": 3,
        "categoria_id": 3,
        "codigo_barra": "7801234567890",
        "unidad_base": "LITRO",
        "tipo_envase_id": 2,
        "contenido_envase": "1.0000",
        "unidad_envase": "L",
        "costo_unitario": "850.00",
        "precio_venta": "1290.00",
        "iva_porcentaje": "19.00",
        "presentaciones_compra": [
            {
                "nombre": "Caja 12 Unidades",
                "equivalencia": "12.0000",
                "sku": "CAJA-LEC-12",
                "ultimo_costo": "10200.00",
            }
        ],
        "bodegas_config": [
            {
                "bodega_id": 1,
                "stock_minimo": "10.0000",
                "stock_actual": "48.0000",
                "coordenada_letra": "A",
                "coordenada_numero": "3",
                "bodega_nombre": "Bodega Principal",
            },
            {
                "bodega_id": 2,
                "stock_minimo": "5.0000",
                "stock_actual": "12.0000",
                "coordenada_letra": "B",
                "coordenada_numero": "1",
                "bodega_nombre": "Bodega Bar",
            },
        ],
    }

    create_resp = await async_client.post(
        "/api/v1/catalog/products",
        headers=headers_all,
        json=create_payload,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    product_id = created_data["id"]
    assert created_data["nombre"] == "Leche Entera 1L"
    assert created_data["sku"] == "LEC-ENT-001"
    assert created_data["marca_comercial"] == "Colun"
    assert Decimal(created_data["costo_unitario"]) == Decimal("850.00")
    assert Decimal(created_data["precio_venta"]) == Decimal("1290.00")
    assert Decimal(created_data["stock_actual"]) == Decimal("60.0000")
    assert len(created_data["presentaciones_compra"]) == 1
    assert len(created_data["bodegas_config"]) == 2

    # 2. Obtener producto por ID
    get_resp = await async_client.get(
        f"/api/v1/catalog/products/{product_id}",
        headers=headers_all,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == product_id

    # 3. Filtrar por categoría existente
    cat_filter_resp = await async_client.get(
        "/api/v1/catalog/products?categoria_id=3",
        headers=headers_all,
    )
    assert cat_filter_resp.status_code == 200
    assert any(p["id"] == product_id for p in cat_filter_resp.json())

    # Filtrar por categoría inexistente
    cat_empty_resp = await async_client.get(
        "/api/v1/catalog/products?categoria_id=9999",
        headers=headers_all,
    )
    assert cat_empty_resp.status_code == 200
    assert not any(p["id"] == product_id for p in cat_empty_resp.json())

    # 4. Filtrar por search (nombre / sku / código de barra)
    search_resp = await async_client.get(
        "/api/v1/catalog/products?search=LEC-ENT",
        headers=headers_all,
    )
    assert search_resp.status_code == 200
    assert any(p["id"] == product_id for p in search_resp.json())

    # 5. Filtrar por bodega_id (y reflejar stock_actual de esa bodega)
    bodega_resp = await async_client.get(
        "/api/v1/catalog/products?bodega_id=2",
        headers=headers_all,
    )
    assert bodega_resp.status_code == 200
    matched = next((p for p in bodega_resp.json() if p["id"] == product_id), None)
    assert matched is not None
    assert Decimal(matched["stock_actual"]) == Decimal("12.0000")

    # 6. Actualizar producto (PUT)
    update_payload = {
        "precio_venta": "1350.00",
        "nombre": "Leche Entera 1L Premium",
    }
    update_resp = await async_client.put(
        f"/api/v1/catalog/products/{product_id}",
        headers=headers_all,
        json=update_payload,
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["nombre"] == "Leche Entera 1L Premium"
    assert Decimal(updated_data["precio_venta"]) == Decimal("1350.00")
    # SKU y otros campos deben permanecer inalterados
    assert updated_data["sku"] == "LEC-ENT-001"

    # 7. Eliminación lógica (soft-delete)
    del_soft_resp = await async_client.delete(
        f"/api/v1/catalog/products/{product_id}?permanent=false",
        headers=headers_all,
    )
    assert del_soft_resp.status_code == 200
    assert del_soft_resp.json()["success"] is True

    # Comprobar que ya no aparece en el listado activo
    list_after_del = await async_client.get(
        "/api/v1/catalog/products",
        headers=headers_all,
    )
    assert not any(p["id"] == product_id for p in list_after_del.json())

    # 8. Eliminación física (permanent=true)
    del_perm_resp = await async_client.delete(
        f"/api/v1/catalog/products/{product_id}?permanent=true",
        headers=headers_all,
    )
    assert del_perm_resp.status_code == 200

    # 404 en intento posterior
    get_404 = await async_client.get(
        f"/api/v1/catalog/products/{product_id}",
        headers=headers_all,
    )
    assert get_404.status_code == 404
    assert get_404.json()["error_code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_categories_crud(async_client: httpx.AsyncClient) -> None:
    """Verifica el ciclo completo de CRUD para Categorías con permisos RBAC."""
    headers = _make_headers(
        [
            "catalog.categories.read",
            "catalog.categories.create",
            "catalog.categories.update",
            "catalog.categories.delete",
        ]
    )

    # Listar iniciales
    list_resp = await async_client.get("/api/v1/catalog/categories", headers=headers)
    assert list_resp.status_code == 200
    initial_count = len(list_resp.json())
    assert initial_count >= 1

    # Crear categoría
    create_resp = await async_client.post(
        "/api/v1/catalog/categories",
        headers=headers,
        json={"nombre": "Bebidas y Licores", "icono": "Wine", "color": "#8B5CF6"},
    )
    assert create_resp.status_code == 201
    cat_id = create_resp.json()["id"]
    assert create_resp.json()["nombre"] == "Bebidas y Licores"

    # Actualizar categoría
    update_resp = await async_client.put(
        f"/api/v1/catalog/categories/{cat_id}",
        headers=headers,
        json={"nombre": "Bebidas, Vinos y Licores", "color": "#7C3AED"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["nombre"] == "Bebidas, Vinos y Licores"
    assert update_resp.json()["color"] == "#7C3AED"

    # Eliminar categoría
    del_resp = await async_client.delete(
        f"/api/v1/catalog/categories/{cat_id}?permanent=true",
        headers=headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # 404 al intentar actualizar inexistente
    bad_update = await async_client.put(
        f"/api/v1/catalog/categories/{cat_id}",
        headers=headers,
        json={"nombre": "Fallo"},
    )
    assert bad_update.status_code == 404


@pytest.mark.asyncio
async def test_brands_crud(async_client: httpx.AsyncClient) -> None:
    """Verifica el CRUD de Marcas comerciales inmutables."""
    headers = _make_headers(
        [
            "catalog.brands.read",
            "catalog.brands.create",
            "catalog.brands.update",
            "catalog.brands.delete",
        ]
    )

    # Crear marca
    create_resp = await async_client.post(
        "/api/v1/catalog/brands",
        headers=headers,
        json={"nombre": "Nestlé", "logo_url": "https://r2.oppytec.com/brands/nestle.webp"},
    )
    assert create_resp.status_code == 201
    brand_id = create_resp.json()["id"]
    assert create_resp.json()["nombre"] == "Nestlé"

    # Listar marcas
    list_resp = await async_client.get("/api/v1/catalog/brands", headers=headers)
    assert list_resp.status_code == 200
    assert any(b["id"] == brand_id for b in list_resp.json())

    # Actualizar marca
    update_resp = await async_client.put(
        f"/api/v1/catalog/brands/{brand_id}",
        headers=headers,
        json={"logo_url": "https://r2.oppytec.com/brands/nestle_v2.webp"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["logo_url"] == "https://r2.oppytec.com/brands/nestle_v2.webp"

    # Eliminar marca
    del_resp = await async_client.delete(
        f"/api/v1/catalog/brands/{brand_id}?permanent=true",
        headers=headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True


@pytest.mark.asyncio
async def test_container_types_crud(async_client: httpx.AsyncClient) -> None:
    """Verifica el CRUD de Tipos de Envase o Empaque."""
    headers = _make_headers(
        [
            "catalog.container_types.read",
            "catalog.container_types.create",
            "catalog.container_types.update",
            "catalog.container_types.delete",
        ]
    )

    # Crear tipo de envase
    create_resp = await async_client.post(
        "/api/v1/catalog/container-types",
        headers=headers,
        json={"nombre": "Bidón 5L", "icono": "Container", "es_predeterminado": False},
    )
    assert create_resp.status_code == 201
    cont_id = create_resp.json()["id"]

    # Listar
    list_resp = await async_client.get("/api/v1/catalog/container-types", headers=headers)
    assert list_resp.status_code == 200
    assert any(c["id"] == cont_id for c in list_resp.json())

    # Actualizar
    update_resp = await async_client.put(
        f"/api/v1/catalog/container-types/{cont_id}",
        headers=headers,
        json={"es_predeterminado": True},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["es_predeterminado"] is True

    # Eliminar
    del_resp = await async_client.delete(
        f"/api/v1/catalog/container-types/{cont_id}?permanent=true",
        headers=headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True


@pytest.mark.asyncio
async def test_inventory_bulk_transfer_stock(async_client: httpx.AsyncClient) -> None:
    """
    Verifica la transferencia masiva de existencias entre bodegas en `src/modules/inventory/`:
    - Inicialización de stock previo en bodega origen.
    - Validación: rechazo de misma bodega origen y destino (HTTP 400).
    - Validación: saldo insuficiente en bodega origen (HTTP 409).
    - Ejecución exitosa con descuentos en origen y aumentos en destino reflejados en Kardex.
    """
    headers = _make_headers(
        [
            "inventory.kardex.write",
            "inventory.stock.transfer",
        ]
    )

    # 1. Alimentar stock inicial en bodega origen 1 para productos 101 y 102
    await async_client.post(
        "/api/v1/inventory/kardex/movements",
        headers=headers,
        json={
            "producto_id": 101,
            "bodega_id": 1,
            "movement_type": "ENTRADA",
            "quantity": "50.0000",
            "unit_cost": "1000.00",
        },
    )
    await async_client.post(
        "/api/v1/inventory/kardex/movements",
        headers=headers,
        json={
            "producto_id": 102,
            "bodega_id": 1,
            "movement_type": "ENTRADA",
            "quantity": "30.0000",
            "unit_cost": "2500.00",
        },
    )

    # 2. Validación de misma bodega origen y destino -> HTTP 400
    same_warehouse_resp = await async_client.post(
        "/api/v1/inventory/stock/bulk-transfer",
        headers=headers,
        json={
            "bodega_origen_id": 1,
            "bodega_destino_id": 1,
            "items": [{"producto_id": 101, "cantidad": "10.0000"}],
        },
    )
    assert same_warehouse_resp.status_code == 400
    assert same_warehouse_resp.json()["error_code"] == "DOMAIN_VALIDATION_ERROR"

    # 3. Validación de saldo insuficiente -> HTTP 409
    insufficient_resp = await async_client.post(
        "/api/v1/inventory/stock/bulk-transfer",
        headers=headers,
        json={
            "bodega_origen_id": 1,
            "bodega_destino_id": 2,
            "items": [{"producto_id": 101, "cantidad": "9999.0000"}],
        },
    )
    assert insufficient_resp.status_code == 409
    assert insufficient_resp.json()["error_code"] == "INSUFFICIENT_STOCK"

    # 4. Traspaso masivo exitoso entre bodega 1 y bodega 2
    transfer_payload = {
        "bodega_origen_id": 1,
        "bodega_destino_id": 2,
        "items": [
            {"producto_id": 101, "cantidad": "20.0000"},
            {"producto_id": 102, "cantidad": "10.0000"},
        ],
    }
    transfer_resp = await async_client.post(
        "/api/v1/inventory/stock/bulk-transfer",
        headers=headers,
        json=transfer_payload,
    )
    assert transfer_resp.status_code == 200
    res = transfer_resp.json()
    assert res["bodega_origen_id"] == 1
    assert res["bodega_destino_id"] == 2
    assert res["processed_items"] == 2

    item_101 = next(i for i in res["items"] if i["producto_id"] == 101)
    # 50 iniciales - 20 = 30 en origen; 0 + 20 = 20 en destino
    assert Decimal(item_101["origen_resulting_balance"]) == Decimal("30.0000")
    assert Decimal(item_101["destino_resulting_balance"]) == Decimal("20.0000")

    item_102 = next(i for i in res["items"] if i["producto_id"] == 102)
    # 30 iniciales - 10 = 20 en origen; 0 + 10 = 10 en destino
    assert Decimal(item_102["origen_resulting_balance"]) == Decimal("20.0000")
    assert Decimal(item_102["destino_resulting_balance"]) == Decimal("10.0000")


@pytest.mark.asyncio
async def test_rbac_denial_on_unauthorized_endpoints(async_client: httpx.AsyncClient) -> None:
    """Verifica que un usuario sin los permisos específicos reciba HTTP 403 con RFC 7807."""
    unauthorized_headers = _make_headers(["catalog.products.read"])

    # Intento de creación de producto sin permiso 'catalog.products.create'
    create_resp = await async_client.post(
        "/api/v1/catalog/products",
        headers=unauthorized_headers,
        json={
            "sku": "FORBIDDEN-01",
            "nombre": "Producto No Autorizado",
            "unidad_compra": "UNIDAD",
            "costo_compra_neto": "100.00",
        },
    )
    assert create_resp.status_code == 403
    assert create_resp.json()["error_code"] in {
        "MISSING_PERMISSION",
        "RBAC_PERMISSION_DENIED",
        "MODULE_NOT_ENABLED_IN_PLAN",
    }

    # Intento de transferencia sin permiso 'inventory.stock.transfer'
    transfer_resp = await async_client.post(
        "/api/v1/inventory/stock/bulk-transfer",
        headers=unauthorized_headers,
        json={
            "bodega_origen_id": 1,
            "bodega_destino_id": 2,
            "items": [{"producto_id": 1, "cantidad": "1.0000"}],
        },
    )
    assert transfer_resp.status_code == 403
    assert transfer_resp.json()["error_code"] in {
        "MISSING_PERMISSION",
        "RBAC_PERMISSION_DENIED",
        "MODULE_NOT_ENABLED_IN_PLAN",
    }
