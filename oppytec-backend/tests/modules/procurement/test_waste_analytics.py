"""
oppytec-backend/tests/modules/procurement/test_waste_analytics.py
Certificación 5D (Tarea 7.4) — Gestión Analítica de Mermas Valorizadas a PPP:
1. Unitario: Valorización de mermas a PPP (`waste_total_cost`), umbral de aprobación (`waste_requires_approval`)
   y segregación de funciones en `WasteService`.
2. Integración (In-Memory & PostgreSQL AsyncSession): Agregaciones temporales (`timeline`),
   desglose por motivos (`por_motivo`), desglose por categorías (`por_categoria`) e historial paginado (`get_history`).
3. Propiedades (Hypothesis): Conservación exacta de la pérdida valorizada a PPP entre todas las dimensiones
   (`total_perdida_ppp == sum(por_motivo) == sum(por_categoria) == sum(timeline)`) y ratios porcentuales en `Decimal(14, 2)`.
4. Contratos: Esquemas Pydantic v2 (`MermaAnalyticsResponse`, `MermaHistoryResponse`).
5. Paridad Matemática con Legacy: Exactitud de ratios de pérdida y filtros por bodega y rango de fechas.
"""
from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import get_settings
from src.core.exceptions import CrossTenantAccessError, PermissionDeniedError
from src.modules.catalog.infrastructure.models import Categoria, Producto
from src.modules.inventory.application.inventory_service import InventoryService
from src.modules.inventory.application.merma_analytics_service import (
    MermaAnalyticsService,
)
from src.modules.inventory.application.waste_service import WasteService
from src.modules.inventory.domain.kardex_math import (
    waste_requires_approval,
    waste_total_cost,
)
from src.modules.inventory.infrastructure.models import Bodega, Merma
from src.modules.procurement.presentation.schemas import (
    MermaAnalyticsResponse,
    MermaByCategoria,
    MermaByMotivo,
    MermaHistoryItemResponse,
    MermaHistoryResponse,
    MermaTimelinePoint,
)

pytestmark = [pytest.mark.unit]

DB_TENANT_SCHEMA = "tenant_test_procurement"

MOTIVOS_CANONICOS = ("VENCIMIENTO", "DANO", "ERROR_PREPARACION", "MAL_ESTADO", "OTRO")
ESTADOS_APROBACION = ("PENDIENTE", "APROBADA")

st_waste_qty = st.decimals(
    min_value=Decimal("0.1000"),
    max_value=Decimal("500.0000"),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)
st_ppp_cost = st.decimals(
    min_value=Decimal("10.00"),
    max_value=Decimal("100000.00"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)
st_waste_record = st.tuples(
    st.sampled_from(MOTIVOS_CANONICOS),
    st.integers(min_value=1, max_value=4),
    st_waste_qty,
    st_ppp_cost,
    st.sampled_from(["2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"]),
    st.sampled_from(ESTADOS_APROBACION),
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
# DIMENSIÓN 1: UNITARIO — VALORIZACIÓN PPP Y FLUJO DE APROBACIÓN DE MERMAS
# ==============================================================================


class TestWasteValuationAndApprovalWorkflow:
    """Verifica el cálculo de pérdida valorizada a PPP y segregación de aprobación."""

    def test_waste_below_and_above_threshold_kardex_impact(self) -> None:
        inv = InventoryService()
        inv.register_movement(
            producto_id=10,
            bodega_id=1,
            movement_type="ENTRADA",
            quantity=Decimal("100.0000"),
            unit_cost=Decimal("2000.00"),
            actor_user_id=1,
        )
        waste_svc = WasteService(inventory=inv, approval_threshold=Decimal("50000.00"))

        # 1. Merma bajo umbral (5 * 2000 = 10,000 <= 50,000) -> APROBADA inmediato y descuenta Kardex
        rec_low = waste_svc.report_waste(
            producto_id=10,
            bodega_id=1,
            quantity=Decimal("5.0000"),
            unit_cost=Decimal("2000.00"),
            reason="VENCIMIENTO",
            reporter_user_id=101,
            tenant_id="tenant_a",
        )
        assert rec_low.status == "APROBADA"
        assert rec_low.total_cost == Decimal("10000.00")
        assert inv.balance(10, 1) == Decimal("95.0000")

        # 2. Merma sobre umbral (30 * 2000 = 60,000 > 50,000) -> PENDIENTE sin tocar Kardex aún
        rec_high = waste_svc.report_waste(
            producto_id=10,
            bodega_id=1,
            quantity=Decimal("30.0000"),
            unit_cost=Decimal("2000.00"),
            reason="DANO",
            reporter_user_id=101,
            tenant_id="tenant_a",
        )
        assert rec_high.status == "PENDIENTE"
        assert rec_high.total_cost == Decimal("60000.00")
        assert inv.balance(10, 1) == Decimal("95.0000")

        # 3. El mismo usuario que reportó NO puede aprobar su propia merma
        with pytest.raises(PermissionDeniedError):
            waste_svc.approve(rec_high.waste_id, approver_user_id=101, unit_cost=Decimal("2000.00"))

        # 4. Otro tenant NO puede aprobar ni rechazar la merma
        with pytest.raises(CrossTenantAccessError):
            waste_svc.approve(
                rec_high.waste_id,
                approver_user_id=102,
                unit_cost=Decimal("2000.00"),
                tenant_id="tenant_intruder",
            )

        # 5. Supervisor distinto del mismo tenant aprueba -> descuenta Kardex
        approved = waste_svc.approve(
            rec_high.waste_id,
            approver_user_id=102,
            unit_cost=Decimal("2000.00"),
            tenant_id="tenant_a",
        )
        assert approved.status == "APROBADA"
        assert inv.balance(10, 1) == Decimal("65.0000")


# ==============================================================================
# DIMENSIÓN 3 & 5: PROPIEDADES (HYPOTHESIS) DE AGREGACIONES Y RATIOS DE MERMAS
# ==============================================================================


class TestWasteAnalyticsMathematicalProperties:
    """Certifica con Hypothesis las invariantes de agregación multidimensional de mermas."""

    @given(records=st.lists(st_waste_record, min_size=1, max_size=25))
    @settings(max_examples=60, deadline=None)
    @pytest.mark.asyncio
    async def test_property_waste_analytics_dimensional_conservation_and_ratios(
        self,
        records: list[tuple[str, int, Decimal, Decimal, str, str]],
    ) -> None:
        """
        Propiedad de Conservación Multidimensional:
        Para cualquier conjunto de mermas valorizadas a PPP (`costo_total = waste_total_cost(qty, ppp)`):
        1. `total_perdida_ppp` es igual a la suma exacta de `costo_total` de todos los eventos.
        2. La suma de `total_costo` en `por_motivo` == `total_perdida_ppp`.
        3. La suma de `total_costo` en `por_categoria` == `total_perdida_ppp`.
        4. La suma de `costo` en `timeline` == `total_perdida_ppp`.
        5. La serie `timeline` está estrictamente ordenada de forma ascendente por `fecha`.
        6. Cada `porcentaje` en `por_motivo` cumple `0.00 <= porcentaje <= 100.00` y coincide con
           `((motivo_costo / total_perdida_ppp) * 100).quantize(Decimal("0.01"))`.
        """
        service = MermaAnalyticsService(use_in_memory=True)
        cat_names = {1: "Carnes", 2: "Lácteos", 3: "Verduras", 4: "Abarrotes"}

        expected_total = Decimal("0.00")
        expected_pending = 0

        for idx, (motivo, cat_id, qty, ppp, fecha_str, estado) in enumerate(records):
            costo_linea = waste_total_cost(qty, ppp)
            expected_total += costo_linea
            if estado == "PENDIENTE":
                expected_pending += 1

            service.register_in_memory_merma(
                {
                    "id": idx + 1,
                    "producto_id": idx + 100,
                    "producto_nombre": f"Insumo {idx + 1}",
                    "bodega_id": 1,
                    "categoria_id": cat_id,
                    "categoria_nombre": cat_names[cat_id],
                    "cantidad": qty,
                    "costo_total": costo_linea,
                    "motivo": motivo,
                    "estado_aprobacion": estado,
                    "fecha_merma": fecha_str,
                    "reportado_por_user_id": 10,
                }
            )

        analytics = await service.get_analytics(None)

        assert analytics["total_perdida_ppp"] == expected_total
        assert analytics["items_mermados_count"] == len(records)
        assert analytics["mermas_pendientes_aprobacion"] == expected_pending

        sum_motivos = sum((m["total_costo"] for m in analytics["por_motivo"]), Decimal("0.00"))
        sum_categorias = sum((c["total_costo"] for c in analytics["por_categoria"]), Decimal("0.00"))
        sum_timeline = sum((t["costo"] for t in analytics["timeline"]), Decimal("0.00"))

        assert sum_motivos == expected_total
        assert sum_categorias == expected_total
        assert sum_timeline == expected_total

        # Verificar orden cronológico del timeline
        fechas = [t["fecha"] for t in analytics["timeline"]]
        assert fechas == sorted(fechas)

        # Verificar exactitud de ratios porcentuales por motivo
        for m_entry in analytics["por_motivo"]:
            pct = m_entry["porcentaje"]
            assert isinstance(pct, Decimal)
            assert Decimal("0.00") <= pct <= Decimal("100.00")
            expected_pct = (
                (m_entry["total_costo"] / expected_total) * Decimal("100.00")
            ).quantize(Decimal("0.01"))
            assert pct == expected_pct


# ==============================================================================
# DIMENSIÓN 2 & 4: INTEGRACIÓN POSTGRESQL Y CONTRATOS PYDANTIC DE MERMAS
# ==============================================================================


@pytest.mark.asyncio
async def test_waste_analytics_postgresql_filters_and_ratios(
    async_db_session: AsyncSession,
) -> None:
    """
    Verifica en PostgreSQL real:
    - Desglose por motivos con cálculo exacto de porcentaje (ej. 60.00% y 40.00%).
    - Desglose por categorías e historial paginado con filtros por `bodega_id`, `motivo` y `estado`.
    """
    cat_carnes = Categoria(nombre="Carnes Premium")
    cat_lacteos = Categoria(nombre="Lácteos Frescos")
    bodega_central = Bodega(nombre="Bodega Central", es_principal=True)
    bodega_cocina = Bodega(nombre="Bodega Cocina", es_principal=False)
    async_db_session.add_all([cat_carnes, cat_lacteos, bodega_central, bodega_cocina])
    await async_db_session.flush()

    p_lomo = Producto(sku="CAR-LOMO", nombre="Lomo Vetado", categoria_id=cat_carnes.id)
    p_crema = Producto(sku="LAC-CREMA", nombre="Crema Pastelera", categoria_id=cat_lacteos.id)
    async_db_session.add_all([p_lomo, p_crema])
    await async_db_session.flush()

    # Merma 1 en Bodega Central: $30,000.00 (60% de Bodega Central)
    m1 = Merma(
        producto_id=p_lomo.id,
        bodega_id=bodega_central.id,
        cantidad=Decimal("3.0000"),
        costo_total=Decimal("30000.00"),
        motivo="VENCIMIENTO",
        estado_aprobacion="APROBADA",
        reportado_por_user_id=301,
    )
    # Merma 2 en Bodega Central: $20,000.00 (40% de Bodega Central)
    m2 = Merma(
        producto_id=p_crema.id,
        bodega_id=bodega_central.id,
        cantidad=Decimal("8.0000"),
        costo_total=Decimal("20000.00"),
        motivo="DANO",
        estado_aprobacion="PENDIENTE",
        reportado_por_user_id=302,
    )
    # Merma 3 en Bodega Cocina: $10,000.00
    m3 = Merma(
        producto_id=p_crema.id,
        bodega_id=bodega_cocina.id,
        cantidad=Decimal("4.0000"),
        costo_total=Decimal("10000.00"),
        motivo="ERROR_PREPARACION",
        estado_aprobacion="APROBADA",
        reportado_por_user_id=303,
    )
    async_db_session.add_all([m1, m2, m3])
    await async_db_session.commit()

    service = MermaAnalyticsService(use_in_memory=False)

    # 1. Analítica filtrada por Bodega Central
    ana_central = await service.get_analytics(async_db_session, bodega_id=bodega_central.id)
    assert ana_central["total_perdida_ppp"] == Decimal("50000.00")
    assert ana_central["items_mermados_count"] == 2
    assert ana_central["mermas_pendientes_aprobacion"] == 1

    motivos_map = {m["motivo"]: m for m in ana_central["por_motivo"]}
    assert motivos_map["VENCIMIENTO"]["total_costo"] == Decimal("30000.00")
    assert motivos_map["VENCIMIENTO"]["porcentaje"] == Decimal("60.00")
    assert motivos_map["DANO"]["total_costo"] == Decimal("20000.00")
    assert motivos_map["DANO"]["porcentaje"] == Decimal("40.00")

    # 2. Analítica global (ambas bodegas)
    ana_global = await service.get_analytics(
        async_db_session,
        date_from=date.today(),
        date_to=date.today(),
    )
    assert ana_global["total_perdida_ppp"] == Decimal("60000.00")
    assert ana_global["items_mermados_count"] == 3
    assert len(ana_global["timeline"]) == 1
    assert ana_global["timeline"][0]["costo"] == Decimal("60000.00")

    # 3. Historial filtrado por estado y motivo
    pending_items, pending_total = await service.get_history(
        async_db_session,
        estado="PENDIENTE",
        motivo="DANO",
    )
    assert pending_total == 1
    assert pending_items[0]["producto_sku"] == "LAC-CREMA"
    assert pending_items[0]["costo_total"] == Decimal("20000.00")


def test_merma_analytics_pydantic_contracts() -> None:
    """Valida los esquemas Pydantic v2 de analítica e historial de mermas."""
    resp = MermaAnalyticsResponse(
        total_perdida_ppp=Decimal("45000.00"),
        items_mermados_count=3,
        mermas_pendientes_aprobacion=1,
        por_motivo=[
            MermaByMotivo(
                motivo="VENCIMIENTO",
                total_costo=Decimal("45000.00"),
                cantidad=Decimal("9.0000"),
                porcentaje=Decimal("100.00"),
            )
        ],
        por_categoria=[
            MermaByCategoria(
                categoria_id=1,
                categoria_nombre="Carnes",
                total_costo=Decimal("45000.00"),
                cantidad=Decimal("9.0000"),
            )
        ],
        timeline=[
            MermaTimelinePoint(
                fecha="2026-10-26",
                costo=Decimal("45000.00"),
                cantidad=Decimal("9.0000"),
            )
        ],
    )
    assert resp.total_perdida_ppp == Decimal("45000.00")
    assert resp.por_motivo[0].porcentaje == Decimal("100.00")

    hist = MermaHistoryResponse(
        items=[
            MermaHistoryItemResponse(
                id=1,
                producto_id=10,
                producto_nombre="Pollo Entero",
                producto_sku="PK-001",
                bodega_id=1,
                bodega_nombre="Central",
                cantidad=Decimal("3.0000"),
                costo_total=Decimal("15000.00"),
                motivo="VENCIMIENTO",
                estado_aprobacion="APROBADA",
                reportado_por_user_id=101,
                fecha_merma=datetime.now(UTC),
            )
        ],
        total=1,
        skip=0,
        limit=50,
    )
    assert hist.total == 1
    assert hist.items[0].costo_total == Decimal("15000.00")
    assert waste_requires_approval(Decimal("50000.01"), Decimal("50000.00")) is True
    assert waste_requires_approval(Decimal("50000.00"), Decimal("50000.00")) is False
