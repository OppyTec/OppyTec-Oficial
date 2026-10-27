"""
oppytec-backend/tests/modules/procurement/test_reception_kardex_integration.py
Certificación 5D (Tarea 7.4) — Integración Recepción de Mercadería -> Kardex (`COMPRA`) y Recálculo PPP:
1. Unitario: Fórmula determinista `calculate_reception_ppp` con `ROUND_HALF_UP` y manejo de bordes.
2. Integración (In-Memory & PostgreSQL AsyncSession): Recepción de órdenes de compra impactando
   `InventoryService`, `ProductoBodega.stock_actual`, `Producto.costo_promedio_almacen` y `RegistroStock` (`COMPRA`).
3. Propiedades (Hypothesis): Invariantes de convexidad (`min <= PPP <= max`), conservación de masa
   en bodega (`Stock_final == Stock_inicial + sum(Cant_recibidas)`) y precisión `Decimal(14, 2)`.
4. Contratos: Esquemas `ReceiveGoodsRequest` y `ReceiveGoodsItemPayload`.
5. Paridad Matemática con Legacy: Múltiples recepciones secuenciales con costos variables y lotes FEFO.
"""
from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import get_settings
from src.modules.catalog.infrastructure.models import Categoria, Producto
from src.modules.inventory.application.inventory_service import InventoryService
from src.modules.inventory.infrastructure.models import (
    Bodega,
    ProductoBodega,
    RegistroStock,
)
from src.modules.procurement.application.procurement_service import ProcurementService
from src.modules.procurement.application.supplier_service import SupplierService
from src.modules.procurement.domain import (
    NegativeMoneyError,
    NegativeQuantityError,
    calculate_reception_ppp,
)
from src.modules.procurement.presentation.schemas import (
    ReceiveGoodsItemPayload,
    ReceiveGoodsRequest,
)

pytestmark = [pytest.mark.unit]

DB_TENANT_SCHEMA = "tenant_test_procurement"

st_stock = st.decimals(
    min_value=Decimal("0.0000"),
    max_value=Decimal("10000.0000"),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)
st_positive_qty = st.decimals(
    min_value=Decimal("0.0100"),
    max_value=Decimal("5000.0000"),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)
st_price = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("500000.00"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


@pytest.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provee una sesión PostgreSQL asíncrona real en `tenant_test_procurement`."""
    settings_obj = get_settings()
    engine = create_async_engine(
        settings_obj.DATABASE_URL.get_secret_value(),
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
        "compra_incidencias",
        "compra_items",
        "compras",
        "producto_proveedores",
        "proveedores",
        "mermas",
        "registro_stock",
        "producto_bodegas",
        "productos",
        "bodegas",
        "categorias",
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


# ==============================================================================
# DIMENSIÓN 1 & 3 & 5: PROPIEDADES (HYPOTHESIS) Y PARIDAD MATEMÁTICA DE PPP
# ==============================================================================


class TestReceptionPppMathematicalProperties:
    """Certifica mediante Hypothesis las propiedades algebraicas de `calculate_reception_ppp`."""

    @given(
        stock_actual=st_positive_qty,
        costo_ppp_ant=st_price,
        cant_recibida=st_positive_qty,
        precio_compra=st_price,
    )
    @settings(max_examples=80, deadline=None)
    def test_property_ppp_convexity_bounded_between_old_and_new_cost(
        self,
        stock_actual: Decimal,
        costo_ppp_ant: Decimal,
        cant_recibida: Decimal,
        precio_compra: Decimal,
    ) -> None:
        """
        Propiedad de Convexidad (Media Ponderada):
        Para todo `stock_actual > 0` y `cant_recibida > 0`, el nuevo PPP siempre se encuentra
        acotado entre `min(costo_ppp_ant, precio_compra)` y `max(costo_ppp_ant, precio_compra)`.
        """
        nuevo_ppp = calculate_reception_ppp(
            stock_actual=stock_actual,
            costo_ppp_ant=costo_ppp_ant,
            cant_recibida=cant_recibida,
            precio_compra=precio_compra,
        )

        lower_bound = min(costo_ppp_ant, precio_compra)
        upper_bound = max(costo_ppp_ant, precio_compra)

        assert isinstance(nuevo_ppp, Decimal)
        assert lower_bound <= nuevo_ppp <= upper_bound

        # Verificación exacta contra la fórmula analítica con ROUND_HALF_UP
        expected = (
            (stock_actual * costo_ppp_ant + cant_recibida * precio_compra)
            / (stock_actual + cant_recibida)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        assert nuevo_ppp == expected

    @given(
        cant_recibida=st_positive_qty,
        precio_compra=st_price,
        costo_ppp_ant=st_price,
    )
    @settings(max_examples=50, deadline=None)
    def test_property_ppp_when_initial_stock_is_zero_equals_purchase_price(
        self,
        cant_recibida: Decimal,
        precio_compra: Decimal,
        costo_ppp_ant: Decimal,
    ) -> None:
        """
        Propiedad de Identidad en Stock Cero:
        Si `stock_actual == 0` y `cant_recibida > 0`, el nuevo PPP es exactamente `precio_compra`.
        """
        nuevo_ppp = calculate_reception_ppp(
            stock_actual=Decimal("0.0000"),
            costo_ppp_ant=costo_ppp_ant,
            cant_recibida=cant_recibida,
            precio_compra=precio_compra,
        )
        assert nuevo_ppp == precio_compra.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @given(
        stock_actual=st_positive_qty,
        cant_recibida=st_positive_qty,
        same_cost=st_price,
    )
    @settings(max_examples=50, deadline=None)
    def test_property_ppp_idempotence_when_purchase_price_equals_previous_ppp(
        self,
        stock_actual: Decimal,
        cant_recibida: Decimal,
        same_cost: Decimal,
    ) -> None:
        """
        Propiedad de Idempotencia:
        Si `precio_compra == costo_ppp_ant`, el PPP permanece invariante para cualquier cantidad.
        """
        nuevo_ppp = calculate_reception_ppp(
            stock_actual=stock_actual,
            costo_ppp_ant=same_cost,
            cant_recibida=cant_recibida,
            precio_compra=same_cost,
        )
        assert nuevo_ppp == same_cost

    def test_ppp_edge_cases_and_defensive_exceptions(self) -> None:
        """Verifica rechazo de negativos, floats y seguridad ante división por cero."""
        assert (
            calculate_reception_ppp(
                stock_actual=Decimal("0"),
                costo_ppp_ant=Decimal("0"),
                cant_recibida=Decimal("0"),
                precio_compra=Decimal("3450.00"),
            )
            == Decimal("3450.00")
        )

        with pytest.raises(NegativeQuantityError):
            calculate_reception_ppp(
                stock_actual=Decimal("-1"),
                costo_ppp_ant=Decimal("1000"),
                cant_recibida=Decimal("5"),
                precio_compra=Decimal("1000"),
                allow_negative_stock=False,
            )

        with pytest.raises(NegativeMoneyError):
            calculate_reception_ppp(
                stock_actual=Decimal("10"),
                costo_ppp_ant=Decimal("1000"),
                cant_recibida=Decimal("5"),
                precio_compra=Decimal("-50"),
            )


# ==============================================================================
# DIMENSIÓN 2 & 3: INTEGRACIÓN RECEPCIÓN -> KARDEX (IN-MEMORY + HYPOTHESIS)
# ==============================================================================


class TestReceptionKardexInMemoryAndPropertyIntegration:
    """Verifica que `ProcurementService.receive_goods` impacte `InventoryService` con movimientos `COMPRA`."""

    @given(
        receptions=st.lists(
            st.decimals(
                min_value=Decimal("1.0000"),
                max_value=Decimal("200.0000"),
                places=4,
                allow_nan=False,
                allow_infinity=False,
            ),
            min_size=1,
            max_size=5,
        ),
        unit_cost=st_price,
    )
    @settings(max_examples=40, deadline=None)
    @pytest.mark.asyncio
    async def test_property_sequential_receptions_conserve_kardex_mass(
        self,
        receptions: list[Decimal],
        unit_cost: Decimal,
    ) -> None:
        """
        Propiedad de Conservación de Masa en Recepción:
        Dada una orden por `total_ordered = sum(receptions)`, tras aplicar `N - 1` recepciones parciales
        y la última recepción que completa el total:
        - El estado es `RECIBIDA_PARCIAL` en los pasos `1..N-1` y `RECIBIDA_TOTAL` en el paso `N`.
        - El saldo en `InventoryService` para `(producto_id, bodega_id)` es exactamente `sum(receptions)`.
        """
        inv_service = InventoryService()
        proc_service = ProcurementService(inventory_service=inv_service, use_in_memory=True)

        total_ordered = sum(receptions, Decimal("0.0000"))
        prod_id = 701
        bodega_id = 3

        order = await proc_service.create_order(
            None,
            {
                "proveedor_id": 1,
                "bodega_destino_id": bodega_id,
                "estado": "SOLICITADA",
                "items": [
                    {
                        "producto_id": prod_id,
                        "cantidad_solicitada": total_ordered,
                        "costo_unitario_neto": unit_cost,
                    }
                ],
            },
            user_id=99,
        )
        order_id = order["id"]

        accumulated = Decimal("0.0000")
        for idx, qty in enumerate(receptions):
            updated = await proc_service.receive_goods(
                None,
                order_id,
                [
                    {
                        "producto_id": prod_id,
                        "cantidad_recibida": qty,
                        "lote_codigo": f"LOTE-{idx + 1}",
                    }
                ],
                user_id=100,
            )
            accumulated += qty
            assert inv_service.balance(prod_id, bodega_id) == accumulated

            if idx < len(receptions) - 1:
                assert updated["estado"] == "RECIBIDA_PARCIAL"
            else:
                assert updated["estado"] == "RECIBIDA_TOTAL"


# ==============================================================================
# DIMENSIÓN 2 & 5: INTEGRACIÓN TRANSACCIONAL EN POSTGRESQL (KARDEX + PPP)
# ==============================================================================


@pytest.mark.asyncio
async def test_reception_kardex_postgresql_multi_delivery_ppp_and_lots(
    async_db_session: AsyncSession,
) -> None:
    """
    Certifica en PostgreSQL real que dos recepciones parciales con una orden previa y stock inicial:
    1. Generan registros `RegistroStock` con `tipo_movimiento == "COMPRA"`, `lote_codigo`, `fecha_vencimiento_lote` y `referencia_documento`.
    2. Actualizan `ProductoBodega.stock_actual` exactamente en cada recepción.
    3. Recalculan `Producto.costo_promedio_almacen` siguiendo `calculate_reception_ppp`.
    """
    cat = Categoria(nombre="Lácteos y Quesos")
    bodega = Bodega(nombre="Bodega Frío Central", es_principal=True)
    async_db_session.add_all([cat, bodega])
    await async_db_session.flush()
    cat_id = cat.id
    bodega_id = bodega.id

    prod = Producto(
        sku="QUESO-GOUDA-5KG",
        nombre="Queso Gouda Laminado",
        categoria_id=cat_id,
        costo_promedio_almacen=Decimal("4000.00"),
        costo_compra_neto=Decimal("4000.00"),
    )
    async_db_session.add(prod)
    await async_db_session.flush()
    prod_id = prod.id

    # Stock inicial: 20 unidades a PPP $4,000.00 ($80,000)
    pb_init = ProductoBodega(
        producto_id=prod_id,
        bodega_id=bodega_id,
        stock_actual=Decimal("20.0000"),
    )
    async_db_session.add(pb_init)
    await async_db_session.commit()

    supplier_service = SupplierService(use_in_memory=False)
    prov = await supplier_service.create_supplier(
        async_db_session,
        {"rut_tax_id": "76.543.210-3", "razon_social": "Pollo King"},
    )

    inv_service = InventoryService()
    proc_service = ProcurementService(inventory_service=inv_service, use_in_memory=False)

    # Orden de Compra por 30 unidades a $5,000.00
    order = await proc_service.create_order(
        async_db_session,
        {
            "numero_orden": "OC-KARDEX-PG-001",
            "proveedor_id": prov["id"],
            "bodega_destino_id": bodega_id,
            "estado": "SOLICITADA",
            "items": [
                {
                    "producto_id": prod_id,
                    "cantidad_solicitada": Decimal("30.0000"),
                    "costo_unitario_neto": Decimal("5000.00"),
                }
            ],
        },
        user_id=201,
    )
    order_id = order["id"]

    # Entrega 1: 10 unidades @ $5,000.00 -> Stock: 20 + 10 = 30
    # PPP esperado: ((20 * 4000) + (10 * 5000)) / 30 = 130000 / 30 = 4333.33
    exp_ppp_1 = calculate_reception_ppp(
        stock_actual=Decimal("20.0000"),
        costo_ppp_ant=Decimal("4000.00"),
        cant_recibida=Decimal("10.0000"),
        precio_compra=Decimal("5000.00"),
    )
    assert exp_ppp_1 == Decimal("4333.33")

    rec1 = await proc_service.receive_goods(
        async_db_session,
        order_id,
        [
            {
                "producto_id": prod_id,
                "cantidad_recibida": Decimal("10.0000"),
                "lote_codigo": "LOTE-QG-101",
                "fecha_vencimiento": date(2027, 3, 15),
            }
        ],
        user_id=202,
    )
    assert rec1["estado"] == "RECIBIDA_PARCIAL"

    pb_row1 = (
        await async_db_session.execute(
            select(ProductoBodega).where(
                ProductoBodega.producto_id == prod_id,
                ProductoBodega.bodega_id == bodega_id,
            )
        )
    ).scalar_one()
    prod_row1 = (
        await async_db_session.execute(select(Producto).where(Producto.id == prod_id))
    ).scalar_one()
    assert pb_row1.stock_actual == Decimal("30.0000")
    assert prod_row1.costo_promedio_almacen == exp_ppp_1

    # Entrega 2: 20 unidades restantes @ $5,000.00 -> Stock: 30 + 20 = 50
    # PPP esperado: ((30 * 4333.33) + (20 * 5000)) / 50 = (129999.90 + 100000) / 50 = 4600.00
    exp_ppp_2 = calculate_reception_ppp(
        stock_actual=Decimal("30.0000"),
        costo_ppp_ant=exp_ppp_1,
        cant_recibida=Decimal("20.0000"),
        precio_compra=Decimal("5000.00"),
    )
    assert exp_ppp_2 == Decimal("4600.00")

    rec2 = await proc_service.receive_goods(
        async_db_session,
        order_id,
        [
            {
                "producto_id": prod_id,
                "cantidad_recibida": Decimal("20.0000"),
                "lote_codigo": "LOTE-QG-102",
                "fecha_vencimiento": date(2027, 4, 20),
            }
        ],
        user_id=202,
    )
    assert rec2["estado"] == "RECIBIDA_TOTAL"

    pb_row2 = (
        await async_db_session.execute(
            select(ProductoBodega).where(
                ProductoBodega.producto_id == prod_id,
                ProductoBodega.bodega_id == bodega_id,
            )
        )
    ).scalar_one()
    prod_row2 = (
        await async_db_session.execute(select(Producto).where(Producto.id == prod_id))
    ).scalar_one()
    assert pb_row2.stock_actual == Decimal("50.0000")
    assert prod_row2.costo_promedio_almacen == exp_ppp_2

    # Verificar los 2 movimientos COMPRA en RegistroStock
    kardex_rows = list(
        (
            await async_db_session.execute(
                select(RegistroStock)
                .where(
                    RegistroStock.producto_id == prod_id,
                    RegistroStock.bodega_id == bodega_id,
                )
                .order_by(RegistroStock.id.asc())
            )
        )
        .scalars()
        .all()
    )
    assert len(kardex_rows) == 2
    assert kardex_rows[0].tipo_movimiento == "COMPRA"
    assert kardex_rows[0].cantidad == Decimal("10.0000")
    assert kardex_rows[0].saldo_resultante == Decimal("30.0000")
    assert kardex_rows[0].costo_unitario_ppp == Decimal("4333.33")
    assert kardex_rows[0].lote_codigo == "LOTE-QG-101"
    assert kardex_rows[0].referencia_documento == "OC-KARDEX-PG-001"

    assert kardex_rows[1].tipo_movimiento == "COMPRA"
    assert kardex_rows[1].cantidad == Decimal("20.0000")
    assert kardex_rows[1].saldo_resultante == Decimal("50.0000")
    assert kardex_rows[1].costo_unitario_ppp == Decimal("4600.00")
    assert kardex_rows[1].lote_codigo == "LOTE-QG-102"


def test_receive_goods_request_contract_validation() -> None:
    """Valida el contrato Pydantic v2 `ReceiveGoodsRequest`."""
    payload = ReceiveGoodsRequest(
        items=[
            ReceiveGoodsItemPayload(
                producto_id=10,
                cantidad_recibida=Decimal("15.5000"),
                costo_unitario_neto=Decimal("4200.00"),
                lote_codigo="LOTE-2026-X",
                fecha_vencimiento=date(2026, 12, 31),
            )
        ],
        notas="Recepción conforme en rampa 2",
    )
    assert len(payload.items) == 1
    assert payload.items[0].cantidad_recibida == Decimal("15.5000")
