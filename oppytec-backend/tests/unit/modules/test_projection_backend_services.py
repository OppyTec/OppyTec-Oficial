"""
oppytec-backend/tests/unit/modules/test_projection_backend_services.py
Pruebas Unitarias 1:1 de los Servicios de Aplicación del Módulo de Proyección:
- `ProjectionEngine`: Cálculo de curvas día a día, deducción FEFO, cruce de eventos/recetas y traspasos preventivos.
- `ProjectionSnapshotService`: Bloqueo anti-concurrencia, paginación server-side y consola de alertas.
Cumple Regla 02 (Clean Architecture), Regla 06 (Paridad Legacy) y 100% Decimal Anti-Float.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import get_settings
from src.core.exceptions import ResourceNotFoundError
from src.modules.catalog.infrastructure.models import Categoria, Producto
from src.modules.events.infrastructure.models import Evento, EventoItem, EventoReceta
from src.modules.inventory.infrastructure.models import Bodega, ProductoBodega, RegistroStock
from src.modules.projection.application.projection_engine import ProjectionEngine
from src.modules.projection.application.snapshot_service import (
    ProjectionSnapshotService,
    _get_tenant_local_lock,
    commit_preserving_tenant_scope,
    escape_like_pattern,
)
from src.modules.projection.domain.entities import UrgencyStatus
from src.modules.projection.infrastructure.models import DailyConsumptionRate, ProjectionSnapshot
from src.modules.recipes.infrastructure.models import CategoriaReceta, Receta, RecetaIngrediente

pytestmark = pytest.mark.unit

TEST_SCHEMA = "tenant_test_procurement"


@pytest.fixture
async def db_session() -> AsyncSession:
    """Provee una sesión PostgreSQL asíncrona real en el esquema tenant_test_procurement."""
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL.get_secret_value(),
        poolclass=NullPool,
        connect_args={"server_settings": {"search_path": f"{TEST_SCHEMA},public"}},
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    clean_tables = [
        "projection_snapshots",
        "daily_consumption_rates",
        "evento_items",
        "evento_recetas",
        "eventos",
        "receta_ingredientes",
        "recetas",
        "categorias_recetas",
        "registro_stock",
        "producto_bodegas",
        "productos",
        "categorias",
        "bodegas",
    ]
    truncate_sql = f"TRUNCATE TABLE {', '.join(f'{TEST_SCHEMA}.{t}' for t in clean_tables)} CASCADE"

    async with session_factory() as session:
        await session.execute(text(truncate_sql))
        await session.commit()
        try:
            yield session
        finally:
            await session.rollback()
            await session.execute(text(truncate_sql))
            await session.commit()

    await engine.dispose()


@pytest.mark.asyncio
async def test_projection_engine_product_not_found(db_session: AsyncSession) -> None:
    """Verifica que ProjectionEngine lance ResourceNotFoundError si el producto no existe."""
    engine = ProjectionEngine()
    with pytest.raises(ResourceNotFoundError):
        await engine.calculate_product_curve(db=db_session, producto_id=999999)


@pytest.mark.asyncio
async def test_projection_engine_calculate_curve_basic(db_session: AsyncSession) -> None:
    """Verifica el cálculo de la curva proyectada básica sin eventos ni lotes caducados."""
    # 1. Crear categoría y producto
    categoria = Categoria(nombre="Abarrotes", icono="Box", color="#10b981")
    db_session.add(categoria)
    await db_session.flush()

    producto = Producto(
        sku="ARR-001",
        nombre="Arroz Extra Grano Largo",
        categoria_id=categoria.id,
        stock_minimo=Decimal("10.0000"),
    )
    db_session.add(producto)
    await db_session.flush()

    bodega = Bodega(nombre="Bodega Central", es_principal=True)
    db_session.add(bodega)
    await db_session.flush()

    pb = ProductoBodega(
        producto_id=producto.id,
        bodega_id=bodega.id,
        stock_actual=Decimal("100.0000"),
        stock_minimo=Decimal("15.0000"),
    )
    db_session.add(pb)

    # 2. Registrar tasa de consumo base de 2.0 por día
    rate = DailyConsumptionRate(
        producto_id=producto.id,
        bodega_id=bodega.id,
        rate_7d=Decimal("2.0000"),
        rate_30d=Decimal("2.0000"),
        rate_90d=Decimal("2.0000"),
    )
    db_session.add(rate)
    await db_session.commit()

    engine = ProjectionEngine()
    result = await engine.calculate_product_curve(
        db=db_session,
        producto_id=producto.id,
        bodega_id=bodega.id,
        horizon_days=30,
        include_events=False,
    )

    assert result.producto_id == producto.id
    assert result.bodega_id == bodega.id
    assert result.horizon_days == 30
    assert result.current_stock == Decimal("100.0000")
    # Al final de 30 días consumiendo 2.0 por día: 100 - (30 * 2) = 40.0000
    assert result.projected_stock == Decimal("40.0000")
    assert result.worst_status == UrgencyStatus.NORMAL
    assert len(result.curve) == 31  # días 0..30


@pytest.mark.asyncio
async def test_projection_engine_fefo_expiry_deduction(db_session: AsyncSession) -> None:
    """Verifica que los lotes con caducidad se purguen en el día exacto de vencimiento."""
    cat = Categoria(nombre="Lácteos", icono="Milk", color="#3b82f6")
    db_session.add(cat)
    await db_session.flush()

    prod = Producto(
        sku="YOG-001",
        nombre="Yogurt Natural 1L",
        categoria_id=cat.id,
        stock_minimo=Decimal("5.0000"),
    )
    db_session.add(prod)
    await db_session.flush()

    bodega = Bodega(nombre="Cámara Fría", es_principal=True)
    db_session.add(bodega)
    await db_session.flush()

    pb = ProductoBodega(
        producto_id=prod.id,
        bodega_id=bodega.id,
        stock_actual=Decimal("20.0000"),
        stock_minimo=Decimal("5.0000"),
    )
    db_session.add(pb)

    today = date.today()
    expiry_date = today + timedelta(days=5)

    # Registrar lote en Kardex con vencimiento en día 5
    kardex = RegistroStock(
        producto_id=prod.id,
        bodega_id=bodega.id,
        tipo_movimiento="ENTRADA",
        cantidad=Decimal("20.0000"),
        saldo_resultante=Decimal("20.0000"),
        lote_codigo="LOT-YOG-2026",
        fecha_vencimiento_lote=expiry_date,
        actor_user_id=1,
    )
    db_session.add(kardex)
    await db_session.commit()

    engine = ProjectionEngine()
    result = await engine.calculate_product_curve(
        db=db_session,
        producto_id=prod.id,
        bodega_id=bodega.id,
        horizon_days=10,
        include_events=False,
    )

    assert result.current_stock == Decimal("20.0000")
    # En el día 5 el lote caduca, por lo que el stock cae a 0.0000 y entra en CRITICAL
    assert result.projected_stock == Decimal("0.0000")
    assert result.worst_status == UrgencyStatus.CRITICAL
    assert result.worst_day == 5
    assert result.depletion_date == expiry_date
    assert "vencimiento" in result.worst_status_label.lower()


@pytest.mark.asyncio
async def test_projection_engine_scheduled_events_and_recipes(db_session: AsyncSession) -> None:
    """Verifica que los eventos agendados y las recetas deduzcan existencias en el día previsto."""
    cat = Categoria(nombre="Carnes", icono="Beef", color="#ef4444")
    db_session.add(cat)
    await db_session.flush()

    prod = Producto(
        sku="CAR-001",
        nombre="Lomo Liso Vacuno",
        categoria_id=cat.id,
        stock_minimo=Decimal("10.0000"),
    )
    db_session.add(prod)
    await db_session.flush()

    bodega = Bodega(nombre="Bodega Carnes", es_principal=True)
    db_session.add(bodega)
    await db_session.flush()

    pb = ProductoBodega(
        producto_id=prod.id,
        bodega_id=bodega.id,
        stock_actual=Decimal("50.0000"),
        stock_minimo=Decimal("10.0000"),
    )
    db_session.add(pb)

    today = date.today()
    event_date = today + timedelta(days=3)

    # 1. Crear Evento agendado
    evento = Evento(
        nombre="Banquete Matrimonio VIP",
        tipo_evento="BANQUETE",
        fecha=event_date,
        hora_inicio=time(12, 0),
        hora_fin=time(18, 0),
        cantidad_personas=100,
        estado="CONFIRMADO",
    )
    db_session.add(evento)
    await db_session.flush()

    # Insumo directo: 15.0000 kg
    item_directo = EventoItem(
        evento_id=evento.id,
        producto_id=prod.id,
        bodega_id=bodega.id,
        cantidad=Decimal("15.0000"),
    )
    db_session.add(item_directo)

    # Insumo por receta: 10 porciones * 0.5 kg con 10% merma = 5.5 kg
    cat_receta = CategoriaReceta(nombre="Platos Principales")
    db_session.add(cat_receta)
    await db_session.flush()

    receta = Receta(
        codigo="REC-LOMO",
        nombre="Lomo a la Parrilla",
        categoria_receta_id=cat_receta.id,
    )
    db_session.add(receta)
    await db_session.flush()

    rec_ing = RecetaIngrediente(
        receta_id=receta.id,
        producto_id=prod.id,
        cantidad_receta=Decimal("0.5000"),
        porcentaje_merma=Decimal("10.00"),
    )
    db_session.add(rec_ing)

    ev_receta = EventoReceta(
        evento_id=evento.id,
        receta_id=receta.id,
        bodega_id=bodega.id,
        porciones=10,
    )
    db_session.add(ev_receta)
    await db_session.commit()

    engine = ProjectionEngine()
    result = await engine.calculate_product_curve(
        db=db_session,
        producto_id=prod.id,
        bodega_id=bodega.id,
        horizon_days=7,
        include_events=True,
    )

    # Total deducido en día 3: 15.0000 (directo) + 5.5000 (receta) = 20.5000
    # Stock resultante en día 3: 50.0000 - 20.5000 = 29.5000
    pt_day3 = result.curve[3]
    assert pt_day3.qty == Decimal("29.5000")
    assert pt_day3.event_deduction == Decimal("20.5000")
    assert len(pt_day3.events) >= 1


@pytest.mark.asyncio
async def test_find_alternative_stock_and_transfer_recommendations(db_session: AsyncSession) -> None:
    """Verifica que find_alternative_stock encuentre excedentes en otras bodegas respetando su stock mínimo."""
    cat = Categoria(nombre="Bebidas", icono="Glass", color="#06b6d4")
    db_session.add(cat)
    await db_session.flush()

    prod = Producto(sku="BEB-001", nombre="Vino Tinto Reserva", categoria_id=cat.id)
    db_session.add(prod)
    await db_session.flush()

    b_quiebre = Bodega(nombre="Bar Terraza", es_principal=False)
    b_origen = Bodega(nombre="Bodega Central Vinos", es_principal=True)
    db_session.add_all([b_quiebre, b_origen])
    await db_session.flush()

    # Bodega en quiebre tiene 0
    pb_q = ProductoBodega(producto_id=prod.id, bodega_id=b_quiebre.id, stock_actual=Decimal("0.0000"))
    # Bodega origen tiene 50 disponible y stock mínimo 20 -> superávit de 30
    pb_orig = ProductoBodega(
        producto_id=prod.id,
        bodega_id=b_origen.id,
        stock_actual=Decimal("50.0000"),
        stock_minimo=Decimal("20.0000"),
    )
    db_session.add_all([pb_q, pb_orig])
    await db_session.commit()

    engine = ProjectionEngine()
    recs = await engine.find_alternative_stock(
        db=db_session,
        producto_id=prod.id,
        bodega_id_quiebre=b_quiebre.id,
        needed_qty=Decimal("15.0000"),
        date_needed=date.today() + timedelta(days=5),
    )

    assert len(recs) == 1
    rec = recs[0]
    assert rec.producto_id == prod.id
    assert rec.bodega_origen_id == b_origen.id
    assert rec.bodega_destino_id == b_quiebre.id
    assert rec.cantidad_sugerida == Decimal("15.0000")


@pytest.mark.asyncio
async def test_calculate_consumption_rates_from_kardex(db_session: AsyncSession) -> None:
    """Verifica el cálculo de tasas promedio de consumo en ventanas de 7, 30 y 90 días."""
    cat = Categoria(nombre="Verduras", icono="Carrot", color="#10b981")
    db_session.add(cat)
    await db_session.flush()

    prod = Producto(sku="TOM-001", nombre="Tomate Larga Vida", categoria_id=cat.id)
    db_session.add(prod)
    await db_session.flush()

    bodega = Bodega(nombre="Bodega Frutería")
    db_session.add(bodega)
    await db_session.flush()

    today = date.today()

    # Registrar movimientos de consumo:
    # 14 kg consumidos en los últimos 7 días -> tasa 7d = 14 / 7 = 2.0000
    # 60 kg consumidos en total en los últimos 30 días -> tasa 30d = 60 / 30 = 2.0000
    for day_back in [1, 3]:
        db_session.add(
            RegistroStock(
                producto_id=prod.id,
                bodega_id=bodega.id,
                tipo_movimiento="CONSUMO",
                cantidad=Decimal("7.0000"),
                saldo_resultante=Decimal("100.0000"),
                fecha_recuento=today - timedelta(days=day_back),
                actor_user_id=1,
            )
        )
    for day_back in [10, 20]:
        db_session.add(
            RegistroStock(
                producto_id=prod.id,
                bodega_id=bodega.id,
                tipo_movimiento="SALIDA",
                cantidad=Decimal("23.0000"),
                saldo_resultante=Decimal("80.0000"),
                fecha_recuento=today - timedelta(days=day_back),
                actor_user_id=1,
            )
        )
    await db_session.commit()

    engine = ProjectionEngine()
    r7, r30, r90 = await engine.calculate_consumption_rates(db_session, prod.id, bodega.id, ref_date=today)

    assert r7 == Decimal("2.0000")  # 14 / 7 = 2.0000
    assert r30 == Decimal("2.0000")  # 60 / 30 = 2.0000
    assert r90 == Decimal("0.6667")  # 60 / 90 = 0.6667


@pytest.mark.asyncio
async def test_snapshot_service_recompute_and_pagination(db_session: AsyncSession) -> None:
    """Verifica el recálculo integral de snapshots y la paginación server-side."""
    cat = Categoria(nombre="Pastas", icono="Utensils", color="#f59e0b")
    db_session.add(cat)
    await db_session.flush()

    prod = Producto(
        sku="PAS-001",
        nombre="Fideos Spaghetti N5",
        categoria_id=cat.id,
        stock_minimo=Decimal("10.0000"),
    )
    db_session.add(prod)
    await db_session.flush()

    bodega = Bodega(nombre="Bodega Abarrotes")
    db_session.add(bodega)
    await db_session.flush()

    pb = ProductoBodega(
        producto_id=prod.id,
        bodega_id=bodega.id,
        stock_actual=Decimal("50.0000"),
        stock_minimo=Decimal("10.0000"),
    )
    db_session.add(pb)
    await db_session.commit()

    service = ProjectionSnapshotService()

    # 1. Ejecutar recálculo
    recompute_res = await service.recompute_tenant_snapshots(
        db=db_session,
        tenant_id="tenant_test_procurement",
        horizon_days=30,
    )
    assert recompute_res["status"] == "completed"
    assert recompute_res["processed"] >= 1

    # 2. Consultar paginación server-side
    page_data = await service.get_paginated_snapshots(
        db=db_session,
        page=1,
        page_size=10,
        search="Spaghetti",
        horizon_days=30,
    )

    assert page_data["total_items"] >= 1
    assert page_data["page"] == 1
    assert len(page_data["items"]) >= 1
    item = page_data["items"][0]
    assert item["producto_id"] == prod.id
    assert item["producto_nombre"] == "Fideos Spaghetti N5"
    assert Decimal(item["current_stock"]) == Decimal("50.0000")

    # 3. Detalle de curva
    curve_data = await service.get_product_curve_detail(
        db=db_session,
        producto_id=prod.id,
        bodega_id=bodega.id,
        horizon_days=30,
    )
    assert curve_data["producto_id"] == prod.id
    assert len(curve_data["curve"]) == 31


@pytest.mark.asyncio
async def test_snapshot_service_concurrency_lock_protection(db_session: AsyncSession) -> None:
    """Verifica que dos llamadas concurrentes a recompute respeten el candado anti-concurrencia."""
    service = ProjectionSnapshotService()
    lock = _get_tenant_local_lock("test_concurrency_tenant")

    # Adquirir el lock manualmente simulando un proceso en vuelo
    await lock.acquire()
    try:
        res = await service.recompute_tenant_snapshots(
            db=db_session,
            tenant_id="test_concurrency_tenant",
            horizon_days=30,
        )
        assert res["status"] == "locked"
        assert "already in progress" in res["message"]
    finally:
        lock.release()


# ---------------------------------------------------------------------------
# Red Team (Agente 10) — Regresiones de seguridad del Módulo de Proyección
# ---------------------------------------------------------------------------


def test_escape_like_pattern_neutralizes_wildcards() -> None:
    """Los comodines LIKE del usuario se tratan como literales."""
    assert escape_like_pattern("100%") == "100\\%"
    assert escape_like_pattern("a_b") == "a\\_b"
    assert escape_like_pattern("c:\\x") == "c:\\\\x"
    assert escape_like_pattern("Pollo King") == "Pollo King"


@pytest.mark.asyncio
async def test_paginated_snapshots_rejects_non_whitelisted_status_and_sort(
    db_session: AsyncSession,
) -> None:
    """`status` y `sort_by` fuera de lista blanca generan DomainValidationError (RFC 7807)."""
    from src.core.exceptions import DomainValidationError

    service = ProjectionSnapshotService()
    with pytest.raises(DomainValidationError):
        await service.get_paginated_snapshots(db=db_session, status_filter="critical' OR '1'='1")
    with pytest.raises(DomainValidationError):
        await service.get_paginated_snapshots(db=db_session, sort_by="id; DROP TABLE productos")


@pytest.mark.asyncio
async def test_paginated_snapshots_search_wildcards_are_literal(db_session: AsyncSession) -> None:
    """Buscar `%` o `_` no debe devolver todo el catálogo (sin enumeración por comodines)."""
    cat = Categoria(nombre="Condimentos", icono="Utensils", color="#f59e0b")
    db_session.add(cat)
    await db_session.flush()

    prod_literal = Producto(sku="SAL-100", nombre="Sal 100% Marina", categoria_id=cat.id, stock_minimo=Decimal("1.0000"))
    prod_other = Producto(sku="ACE001", nombre="Aceite Oliva", categoria_id=cat.id, stock_minimo=Decimal("1.0000"))
    db_session.add_all([prod_literal, prod_other])
    await db_session.flush()
    for prod in (prod_literal, prod_other):
        db_session.add(
            ProjectionSnapshot(
                producto_id=prod.id,
                bodega_id=None,
                horizon_days=30,
                current_stock=Decimal("5.0000"),
                projected_stock=Decimal("1.0000"),
                worst_status="normal",
                worst_status_label="Normal",
                daily_consumption_rate=Decimal("0.1000"),
                projection_curve=[],
                is_stale=False,
                calculated_at=datetime.now(UTC),
            )
        )
    await db_session.commit()

    service = ProjectionSnapshotService()
    pct = await service.get_paginated_snapshots(db=db_session, search="%", horizon_days=30)
    assert [it["producto_id"] for it in pct["items"]] == [prod_literal.id]

    underscore = await service.get_paginated_snapshots(db=db_session, search="_", horizon_days=30)
    assert underscore["total_items"] == 0

    injection = await service.get_paginated_snapshots(
        db=db_session, search="' OR 1=1 --", horizon_days=30
    )
    assert injection["total_items"] == 0


@pytest.mark.asyncio
async def test_commit_preserving_tenant_scope_restores_search_path() -> None:
    """Tras commit, `SET LOCAL search_path` se pierde; el helper debe restaurar el esquema tenant."""
    from src.core.database import get_tenant_db_session

    session_gen = get_tenant_db_session(TEST_SCHEMA)
    session = await anext(session_gen)
    try:
        await commit_preserving_tenant_scope(session)
        restored = (await session.execute(text("SELECT current_schema()"))).scalar()
        assert restored == TEST_SCHEMA

        # Control: un commit plano escapa del esquema tenant (vulnerabilidad corregida)
        await session.commit()
        escaped = (await session.execute(text("SELECT current_schema()"))).scalar()
        assert escaped != TEST_SCHEMA
    finally:
        await session_gen.aclose()
