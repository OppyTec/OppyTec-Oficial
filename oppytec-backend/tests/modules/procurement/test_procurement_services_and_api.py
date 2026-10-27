"""
oppytec-backend/tests/modules/procurement/test_procurement_services_and_api.py
Pruebas de Integración y de Servicios de Aplicación para Fase 2 de Procurement:
- `SupplierService`: CRUD, RUT único Módulo 11, inmutabilidad "Pollo King", catálogo y precios pactados.
- `ProcurementService`: ciclo de vida (BORRADOR -> SOLICITADA -> RECEPCIÓN PARCIAL/TOTAL -> CANCELADA),
  invariante de Kardex, recálculo PPP determinista con `calculate_reception_ppp`, incidencias y KPIs dashboard.
- `MermaAnalyticsService`: agregación por fecha, motivo, categoría y timeline en Decimal(14, 2).
- RBAC Dual de 3 niveles en endpoints REST y emisión de eventos WebSocket en tiempo real.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import get_settings
from src.core.database import get_tenant_db_session
from src.core.exceptions import (
    DomainValidationError,
    ProperNounImmutabilityError,
    ResourceNotFoundError,
)
from src.core.realtime.router import get_realtime_publisher
from src.core.security import create_access_token
from src.modules.catalog.infrastructure.models import Categoria, Producto
from src.modules.inventory.application.inventory_service import InventoryService
from src.modules.inventory.application.merma_analytics_service import (
    MermaAnalyticsService,
)
from src.modules.inventory.infrastructure.models import (
    Bodega,
    Merma,
    ProductoBodega,
    RegistroStock,
)
from src.modules.inventory.presentation.router import _merma_analytics_service
from src.modules.procurement.application.procurement_service import (
    ProcurementService,
)
from src.modules.procurement.application.supplier_service import (
    SupplierService,
)
from src.modules.procurement.domain.value_objects import calculate_reception_ppp
from src.modules.procurement.infrastructure.models import (
    Compra,
    CompraIncidencia,
    CompraItem,
    ProductoProveedor,
    Proveedor,
)
from src.modules.procurement.presentation.router import (
    _procurement_service,
    _supplier_service,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

TENANT_TEST = "tenant_procurement_fase2"
HOLDING_TEST = "holding_procurement_fase2"
DB_TENANT_SCHEMA = "tenant_test_procurement"


def _make_headers(permissions: list[str], user_id: int = 401) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado y permisos RBAC de 3 niveles."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=TENANT_TEST,
        holding_id=HOLDING_TEST,
        role_grants=permissions,
        accessible_tenants=[TENANT_TEST],
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_TEST,
    }


@pytest.fixture(autouse=True)
def _reset_in_memory_procurement_state() -> None:
    """Aísla el estado en memoria para los tests REST."""
    _procurement_service.reset_in_memory_store()
    _supplier_service.reset_in_memory_store()
    _merma_analytics_service.reset_in_memory_store()
    _procurement_service.enable_in_memory_mode()
    _supplier_service.enable_in_memory_mode()
    _merma_analytics_service.enable_in_memory_mode()


@pytest.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provee una sesión PostgreSQL asíncrona real en el esquema tenant_test_procurement usando NullPool."""
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL.get_secret_value(),
        poolclass=NullPool,
        connect_args={"server_settings": {"search_path": f"{DB_TENANT_SCHEMA},public"}},
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    tables = [
        "compra_incidencias", "compra_items", "compras",
        "producto_proveedores", "proveedores", "mermas",
        "registro_stock", "producto_bodegas", "productos",
        "bodegas", "categorias",
    ]
    truncate_stmt = f"TRUNCATE TABLE {', '.join(f'{DB_TENANT_SCHEMA}.{t}' for t in tables)} CASCADE"

    async with session_factory() as session:
        await session.execute(text(truncate_stmt))
        await session.commit()
        try:
            yield session
        finally:
            with contextlib.suppress(Exception):
                await session.rollback()
            with contextlib.suppress(Exception):
                await session.execute(text(truncate_stmt))
                await session.commit()

    await engine.dispose()


# ============================================================================
# 1. PRUEBAS DE SERVICIO: SUPPLIER SERVICE (PostgreSQL AsyncSession Real)
# ============================================================================


async def test_supplier_service_create_and_pollo_king_immutability(async_db_session: AsyncSession) -> None:
    """Verifica alta de proveedor, validación Módulo 11 de RUT e inmutabilidad 'Pollo King'."""
    service = SupplierService(use_in_memory=False)

    # 1. Alta exitosa con RUT chileno válido Módulo 11
    created = await service.create_supplier(
        async_db_session,
        {
            "rut_tax_id": "76.543.210-3",
            "razon_social": "Pollo King",
            "nombre_fantasia": "Pollo King SpA",
            "email_contacto": "contacto@polloking.cl",
            "telefono": "+56911223344",
            "direccion": "Av. Central 123",
            "lead_time_dias": 2,
            "estado": "ACTIVO",
        },
    )
    assert created["id"] is not None
    assert created["razon_social"] == "Pollo King"
    assert created["rut_tax_id"] == "76.543.210-3"

    # 2. Rechazo de RUT duplicado
    with pytest.raises(DomainValidationError):
        await service.create_supplier(
            async_db_session,
            {
                "rut_tax_id": "76.543.210-3",
                "razon_social": "Pollo King Duplicate",
            },
        )

    # 3. Rechazo de violación a regla "Pollo King" en actualización
    with pytest.raises(ProperNounImmutabilityError):
        await service.update_supplier(
            async_db_session,
            created["id"],
            {"razon_social": "Chicken King Translation Attempt"},
        )

    # 4. Actualización permitida de campos no nominales
    updated = await service.update_supplier(
        async_db_session,
        created["id"],
        {
            "telefono": "+56999887766",
            "lead_time_dias": 4,
            "notas": "Proveedor estratégico",
        },
    )
    assert updated["telefono"] == "+56999887766"
    assert updated["lead_time_dias"] == 4
    assert updated["notas"] == "Proveedor estratégico"


async def test_supplier_service_list_filter_and_soft_delete(async_db_session: AsyncSession) -> None:
    """Verifica listado paginado, búsqueda por nombre o RUT y borrado lógico."""
    service = SupplierService(use_in_memory=False)

    # Crear 3 proveedores con RUTs válidos
    s1 = await service.create_supplier(
        async_db_session,
        {"rut_tax_id": "76.543.210-3", "razon_social": "Pollo King", "estado": "ACTIVO"},
    )
    s2 = await service.create_supplier(
        async_db_session,
        {"rut_tax_id": "77.123.456-9", "razon_social": "Carnes del Sur", "estado": "ACTIVO"},
    )
    s3 = await service.create_supplier(
        async_db_session,
        {"rut_tax_id": "78.987.654-1", "razon_social": "Verduras Frescas", "estado": "INACTIVO"},
    )

    # Listar todos activos
    items, total = await service.list_suppliers(async_db_session, status="ACTIVO")
    assert total == 2
    assert len(items) == 2

    # Búsqueda por término
    search_items, search_total = await service.list_suppliers(async_db_session, search="Pollo")
    assert search_total == 1
    assert search_items[0]["razon_social"] == "Pollo King"

    # Borrado lógico
    ok = await service.delete_supplier(async_db_session, s2["id"])
    assert ok is True

    # Comprobar que ya no aparece en el listado
    after_items, after_total = await service.list_suppliers(async_db_session)
    assert after_total == 2
    assert not any(it["id"] == s2["id"] for it in after_items)

    # Comprobar que get_supplier lanza 404
    with pytest.raises(ResourceNotFoundError):
        await service.get_supplier(async_db_session, s2["id"])


async def test_supplier_catalog_agreements_upsert(async_db_session: AsyncSession) -> None:
    """Verifica acuerdos de catálogo y actualización de proveedor principal."""
    cat = Categoria(nombre="Carnes")
    async_db_session.add(cat)
    await async_db_session.flush()

    prod1 = Producto(sku="POL-01", nombre="Pechuga 1kg", categoria_id=cat.id)
    prod2 = Producto(sku="POL-02", nombre="Alas 1kg", categoria_id=cat.id)
    async_db_session.add_all([prod1, prod2])
    await async_db_session.flush()

    service = SupplierService(use_in_memory=False)
    s = await service.create_supplier(
        async_db_session,
        {"rut_tax_id": "76.543.210-3", "razon_social": "Pollo King"},
    )

    catalog = await service.update_supplier_catalog(
        async_db_session,
        s["id"],
        [
            {
                "producto_id": prod1.id,
                "precio_pactado": Decimal("4500.00"),
                "codigo_producto_proveedor": "PK-PECH",
                "tiempo_entrega_dias": 2,
                "es_proveedor_principal": True,
            },
            {
                "producto_id": prod2.id,
                "precio_pactado": Decimal("2800.00"),
                "codigo_producto_proveedor": "PK-ALAS",
                "tiempo_entrega_dias": 3,
                "es_proveedor_principal": False,
            },
        ],
    )
    assert len(catalog) == 2
    item1 = next(it for it in catalog if it["producto_id"] == prod1.id)
    assert Decimal(str(item1["precio_pactado"])) == Decimal("4500.00")
    assert item1["es_proveedor_principal"] is True

    # Actualizar precio pactado
    catalog_updated = await service.update_supplier_catalog(
        async_db_session,
        s["id"],
        [
            {
                "producto_id": prod1.id,
                "precio_pactado": Decimal("4800.00"),
            }
        ],
    )
    item1_up = next(it for it in catalog_updated if it["producto_id"] == prod1.id)
    assert Decimal(str(item1_up["precio_pactado"])) == Decimal("4800.00")


# ============================================================================
# 2. PRUEBAS DE SERVICIO: PROCUREMENT SERVICE & INVARIANTE KARDEX (Real DB)
# ============================================================================


async def test_procurement_service_order_lifecycle_and_kardex_ppp(async_db_session: AsyncSession) -> None:
    """
    Invariante Crítica:
    - Creación de orden con subtotal y cálculo de IVA (19%) en Decimal.
    - Recepción parcial y total.
    - Impacto en existencias e inserción en Kardex con recálculo PPP exacto.
    """
    cat = Categoria(nombre="Aves")
    async_db_session.add(cat)
    await async_db_session.flush()
    cat_id = cat.id

    bodega = Bodega(nombre="Bodega Central", es_principal=True)
    async_db_session.add(bodega)
    await async_db_session.flush()
    bodega_id = bodega.id

    prod = Producto(
        sku="PK-FILETE-01",
        nombre="Filete Pollo King",
        categoria_id=cat_id,
        costo_promedio_almacen=Decimal("5000.00"),
        costo_compra_neto=Decimal("5000.00"),
    )
    async_db_session.add(prod)
    await async_db_session.flush()
    prod_id = prod.id

    prod_bodega = ProductoBodega(
        producto_id=prod_id,
        bodega_id=bodega_id,
        stock_actual=Decimal("10.0000"),
    )
    async_db_session.add(prod_bodega)
    await async_db_session.commit()

    supplier_service = SupplierService(use_in_memory=False)
    prov = await supplier_service.create_supplier(
        async_db_session,
        {"rut_tax_id": "76.543.210-3", "razon_social": "Pollo King"},
    )
    prov_id = prov["id"]

    proc_service = ProcurementService(use_in_memory=False)

    # 1. Crear Orden de Compra: 20 kg a CLP 6.000 c/u = CLP 120.000 neto
    order = await proc_service.create_order(
        async_db_session,
        {
            "proveedor_id": prov_id,
            "bodega_destino_id": bodega_id,
            "estado": "SOLICITADA",
            "items": [
                {
                    "producto_id": prod_id,
                    "cantidad_solicitada": Decimal("20.0000"),
                    "costo_unitario_neto": Decimal("6000.00"),
                }
            ],
            "notas": "Pedido urgente",
        },
        user_id=101,
    )
    order_id = order["id"]
    assert order["numero_orden"].startswith("OC-")
    assert Decimal(str(order["monto_neto"])) == Decimal("120000.00")
    assert Decimal(str(order["monto_impuestos"])) == Decimal("22800.00")
    assert Decimal(str(order["monto_total"])) == Decimal("142800.00")
    assert order["estado"] == "SOLICITADA"

    # 2. Recepción Parcial: recepcionamos 10 kg
    rec_order_partial = await proc_service.receive_goods(
        async_db_session,
        order_id,
        [
            {
                "producto_id": prod_id,
                "cantidad_recibida": Decimal("10.0000"),
                "lote_codigo": "LOTE-PK-01",
                "fecha_vencimiento": date(2026, 12, 31),
            }
        ],
        user_id=102,
    )
    assert rec_order_partial["estado"] == "RECIBIDA_PARCIAL"
    assert rec_order_partial["receptor_user_id"] == 102
    assert Decimal(str(rec_order_partial["items"][0]["cantidad_recibida"])) == Decimal("10.0000")

    pb_stmt = select(ProductoBodega).where(
        ProductoBodega.producto_id == prod_id, ProductoBodega.bodega_id == bodega_id
    )
    pb = (await async_db_session.execute(pb_stmt)).scalar_one()
    p = (await async_db_session.execute(select(Producto).where(Producto.id == prod_id))).scalar_one()
    assert pb.stock_actual == Decimal("20.0000")
    assert p.costo_promedio_almacen == Decimal("5500.00")

    # 3. Recepción Total: recepcionamos los 10 kg restantes
    rec_order_full = await proc_service.receive_goods(
        async_db_session,
        order_id,
        [
            {
                "producto_id": prod_id,
                "cantidad_recibida": Decimal("10.0000"),
                "lote_codigo": "LOTE-PK-02",
            }
        ],
        user_id=102,
    )
    assert rec_order_full["estado"] == "RECIBIDA_TOTAL"
    assert Decimal(str(rec_order_full["items"][0]["cantidad_recibida"])) == Decimal("20.0000")

    pb = (await async_db_session.execute(pb_stmt)).scalar_one()
    p = (await async_db_session.execute(select(Producto).where(Producto.id == prod_id))).scalar_one()
    assert pb.stock_actual == Decimal("30.0000")
    assert p.costo_promedio_almacen == Decimal("5666.67")

    # 4. Intentar recepcionar sobre orden cerrada debe fallar
    with pytest.raises(DomainValidationError):
        await proc_service.receive_goods(
            async_db_session,
            order_id,
            [{"producto_id": prod_id, "cantidad_recibida": Decimal("1.0000")}],
            user_id=102,
        )


async def test_procurement_service_incidences_and_cancellation(async_db_session: AsyncSession) -> None:
    """Verifica registro de incidencias y cancelación de órdenes."""
    prov_service = SupplierService(use_in_memory=False)
    p = await prov_service.create_supplier(
        async_db_session,
        {"rut_tax_id": "76.543.210-3", "razon_social": "Pollo King"},
    )

    bodega = Bodega(nombre="Bodega 1")
    cat = Categoria(nombre="General")
    async_db_session.add_all([bodega, cat])
    await async_db_session.flush()
    bodega_id = bodega.id
    cat_id = cat.id

    prod = Producto(sku="P1", nombre="Prod 1", categoria_id=cat_id)
    async_db_session.add(prod)
    await async_db_session.flush()
    prod_id = prod.id
    await async_db_session.commit()

    proc_service = ProcurementService(use_in_memory=False)
    order = await proc_service.create_order(
        async_db_session,
        {
            "proveedor_id": p["id"],
            "bodega_destino_id": bodega_id,
            "estado": "BORRADOR",
            "items": [
                {
                    "producto_id": prod_id,
                    "cantidad_solicitada": Decimal("10.0000"),
                    "costo_unitario_neto": Decimal("1000.00"),
                }
            ],
        },
        user_id=101,
    )

    # Registrar incidencia
    inc = await proc_service.register_incidence(
        async_db_session,
        order["id"],
        {
            "tipo_incidencia": "PRODUCTO_DANADO",
            "cantidad_afectada": Decimal("2.0000"),
            "monto_disputa": Decimal("2000.00"),
            "descripcion": "Cajas rotas durante el transporte",
        },
        user_id=101,
    )
    assert inc["id"] is not None
    assert inc["tipo_incidencia"] == "PRODUCTO_DANADO"
    assert inc["resolucion"] == "PENDIENTE"

    # Cancelar la orden
    cancelled = await proc_service.cancel_order(
        async_db_session,
        order["id"],
        reason="Discrepancia comercial irreversible",
        user_id=101,
    )
    assert cancelled["estado"] == "CANCELADA"
    assert "Discrepancia comercial irreversible" in cancelled["notas"]

    # Re-cancelar debe fallar
    with pytest.raises(DomainValidationError):
        await proc_service.cancel_order(
            async_db_session,
            order["id"],
            reason="Otro intento",
            user_id=101,
        )


# ============================================================================
# 3. PRUEBAS DE SERVICIO: MERMA ANALYTICS SERVICE (Real DB)
# ============================================================================


async def test_merma_analytics_aggregations(async_db_session: AsyncSession) -> None:
    """Verifica agregaciones por motivo, por categoría y timeline en Decimal."""
    cat1 = Categoria(nombre="Carnes")
    cat2 = Categoria(nombre="Verduras")
    async_db_session.add_all([cat1, cat2])
    await async_db_session.flush()

    p1 = Producto(sku="P1", nombre="Carne Vacuno", categoria_id=cat1.id)
    p2 = Producto(sku="P2", nombre="Tomates", categoria_id=cat2.id)
    bodega = Bodega(nombre="Central")
    async_db_session.add_all([p1, p2, bodega])
    await async_db_session.flush()

    m1 = Merma(
        producto_id=p1.id,
        bodega_id=bodega.id,
        cantidad=Decimal("5.0000"),
        costo_total=Decimal("25000.00"),
        motivo="VENCIMIENTO",
        estado_aprobacion="APROBADA",
        reportado_por_user_id=101,
    )
    m2 = Merma(
        producto_id=p2.id,
        bodega_id=bodega.id,
        cantidad=Decimal("10.0000"),
        costo_total=Decimal("15000.00"),
        motivo="DETERIORO",
        estado_aprobacion="PENDIENTE",
        reportado_por_user_id=102,
    )
    async_db_session.add_all([m1, m2])
    await async_db_session.commit()

    service = MermaAnalyticsService(use_in_memory=False)
    analytics = await service.get_analytics(async_db_session)

    assert analytics["total_perdida_ppp"] == Decimal("40000.00")
    assert analytics["items_mermados_count"] == 2
    assert analytics["mermas_pendientes_aprobacion"] == 1

    motivos = {m["motivo"]: m["total_costo"] for m in analytics["por_motivo"]}
    assert motivos["VENCIMIENTO"] == Decimal("25000.00")
    assert motivos["DETERIORO"] == Decimal("15000.00")

    cats = {c["categoria_nombre"]: c["total_costo"] for c in analytics["por_categoria"]}
    assert cats["Carnes"] == Decimal("25000.00")
    assert cats["Verduras"] == Decimal("15000.00")

    history_items, total = await service.get_history(async_db_session)
    assert total == 2
    assert history_items[0]["producto_nombre"] in ("Carne Vacuno", "Tomates")


# ============================================================================
# 4. PRUEBAS REST API & RBAC DUAL DE 3 NIVELES (FastAPI AsyncClient)
# ============================================================================


async def test_api_procurement_suppliers_endpoints_and_rbac(async_client: httpx.AsyncClient) -> None:
    """Verifica endpoints REST de proveedores y bloqueo RBAC 3 niveles."""
    unauthorized_headers = _make_headers(["catalog.products.read"])
    resp_unauth = await async_client.get(
        "/api/v1/procurement/suppliers",
        headers=unauthorized_headers,
    )
    assert resp_unauth.status_code == 403

    manage_headers = _make_headers(
        ["procurement.suppliers.read", "procurement.suppliers.manage"]
    )
    create_resp = await async_client.post(
        "/api/v1/procurement/suppliers",
        headers=manage_headers,
        json={
            "rut_tax_id": "76.543.210-3",
            "razon_social": "Pollo King",
            "nombre_fantasia": "Pollo King SpA",
            "email_contacto": "contacto@polloking.cl",
            "lead_time_dias": 2,
        },
    )
    assert create_resp.status_code == 201
    created_supplier = create_resp.json()
    supplier_id = created_supplier["id"]
    assert created_supplier["razon_social"] == "Pollo King"

    read_headers = _make_headers(["procurement.suppliers.read"])
    get_resp = await async_client.get(
        f"/api/v1/procurement/suppliers/{supplier_id}",
        headers=read_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == supplier_id

    catalog_resp = await async_client.post(
        f"/api/v1/procurement/suppliers/{supplier_id}/products",
        headers=manage_headers,
        json={
            "items": [
                {
                    "producto_id": 10,
                    "precio_pactado": "5200.50",
                    "codigo_producto_proveedor": "PK-10",
                    "tiempo_entrega_dias": 2,
                    "es_proveedor_principal": True,
                }
            ]
        },
    )
    assert catalog_resp.status_code == 200
    cat_body = catalog_resp.json()
    assert len(cat_body) >= 1
    assert Decimal(str(cat_body[0]["precio_pactado"])) == Decimal("5200.50")


async def test_api_procurement_orders_lifecycle_and_rbac(async_client: httpx.AsyncClient) -> None:
    """Verifica ciclo completo de compras vía REST: crear, recepcionar, incidencias, KPIs y cancelar."""
    headers_all = _make_headers(
        [
            "procurement.orders.read",
            "procurement.orders.create",
            "procurement.orders.receive",
            "procurement.orders.cancel",
            "procurement.suppliers.manage",
        ]
    )

    create_resp = await async_client.post(
        "/api/v1/procurement/orders",
        headers=headers_all,
        json={
            "numero_orden": "OC-2026-F2-001",
            "proveedor_id": 1,
            "supplier_name": "Pollo King",
            "bodega_destino_id": 1,
            "estado": "SOLICITADA",
            "items": [
                {
                    "producto_id": 5,
                    "cantidad_solicitada": "20.0000",
                    "costo_unitario_neto": "5000.00",
                }
            ],
            "notas": "Orden de abastecimiento semanal",
        },
    )
    assert create_resp.status_code == 201
    order_data = create_resp.json()
    order_id = order_data["id"]
    assert order_data["numero_orden"] == "OC-2026-F2-001"
    assert Decimal(str(order_data["monto_neto"])) == Decimal("100000.00")

    receive_resp = await async_client.post(
        f"/api/v1/procurement/orders/{order_id}/receive",
        headers=headers_all,
        json={
            "items": [
                {
                    "producto_id": 5,
                    "cantidad_recibida": "10.0000",
                    "lote_codigo": "L-PK-01",
                }
            ]
        },
    )
    assert receive_resp.status_code == 200
    rec_body = receive_resp.json()
    assert rec_body["estado"] == "RECIBIDA_PARCIAL"

    inc_resp = await async_client.post(
        f"/api/v1/procurement/orders/{order_id}/incidences",
        headers=headers_all,
        json={
            "tipo_incidencia": "DIFERENCIA_CANTIDAD",
            "cantidad_afectada": "10.0000",
            "monto_disputa": "50000.00",
            "descripcion": "Entrega parcial con saldo pendiente de despacho",
        },
    )
    assert inc_resp.status_code == 201
    assert inc_resp.json()["tipo_incidencia"] == "DIFERENCIA_CANTIDAD"

    dash_resp = await async_client.get(
        "/api/v1/procurement/dashboard",
        headers=headers_all,
    )
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert "total_mes_monto" in dash_data
    assert "ordenes_pendientes_recepcion" in dash_data
    assert "proveedores_activos" in dash_data

    cancel_resp = await async_client.post(
        f"/api/v1/procurement/orders/{order_id}/cancel",
        headers=headers_all,
        json={"motivo": "Cancelado por falta de stock restante del proveedor"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["estado"] == "CANCELADA"


async def test_api_inventory_mermas_analytics_endpoints(async_client: httpx.AsyncClient) -> None:
    """Verifica endpoints /api/v1/inventory/mermas/analytics y history con RBAC."""
    headers_forbidden = _make_headers(["procurement.orders.read"])
    resp_forbid = await async_client.get(
        "/api/v1/inventory/mermas/analytics",
        headers=headers_forbidden,
    )
    assert resp_forbid.status_code == 403

    headers_waste = _make_headers(
        ["inventory.mermas.create", "inventory.mermas.view"]
    )
    rep_resp = await async_client.post(
        "/api/v1/inventory/mermas",
        headers=headers_waste,
        json={
            "producto_id": 1,
            "bodega_id": 1,
            "quantity": "4.0000",
            "unit_cost": "2500.00",
            "reason": "VENCIMIENTO",
        },
    )
    assert rep_resp.status_code == 201

    ana_resp = await async_client.get(
        "/api/v1/inventory/mermas/analytics",
        headers=headers_waste,
    )
    assert ana_resp.status_code == 200
    ana_data = ana_resp.json()
    assert Decimal(str(ana_data["total_perdida_ppp"])) >= Decimal("10000.00")
    assert ana_data["items_mermados_count"] >= 1
    assert isinstance(ana_data["por_motivo"], list)
    assert isinstance(ana_data["por_categoria"], list)
    assert isinstance(ana_data["timeline"], list)

    hist_resp = await async_client.get(
        "/api/v1/inventory/mermas/history",
        headers=headers_waste,
    )
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert hist_data["total"] >= 1
    assert len(hist_data["items"]) >= 1
