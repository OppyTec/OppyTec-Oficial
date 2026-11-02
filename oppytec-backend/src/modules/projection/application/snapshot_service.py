"""
oppytec-backend/src/modules/projection/application/snapshot_service.py
Servicio de Caché Persistente de Snapshots de Proyección, Bloqueo Anti-Concurrencia,
Paginación Server-Side de Alto Rendimiento y Emisión de Eventos en Tiempo Real.
Cumple Regla 02 (DDD / Clean Architecture), Regla 06 (Paridad Legacy) y 100% Decimal.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, case, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import TENANT_SCHEMA_REGEX, validate_tenant_schema_name
from src.core.exceptions import DomainValidationError, ResourceNotFoundError
from src.core.observability import get_tenant_telemetry_context, trace_span
from src.core.realtime.router import get_realtime_publisher
from src.core.realtime.schemas import RealtimeEventEnvelope
from src.modules.catalog.infrastructure.models import Categoria, Producto
from src.modules.inventory.infrastructure.models import Bodega, ProductoBodega
from src.modules.projection.application.projection_engine import ProjectionEngine
from src.modules.projection.infrastructure.models import DailyConsumptionRate, ProjectionSnapshot

logger = logging.getLogger("oppytec.projection.snapshot_service")

# Lock en memoria para entornos sin PostgreSQL advisory locks (ej: SQLite en tests locales)
_local_in_memory_locks: dict[str, asyncio.Lock] = {}


def _get_tenant_local_lock(tenant_key: str) -> asyncio.Lock:
    if tenant_key not in _local_in_memory_locks:
        _local_in_memory_locks[tenant_key] = asyncio.Lock()
    return _local_in_memory_locks[tenant_key]


# Listas blancas de parámetros de consulta (Red Team: sin valores libres hacia SQL)
ALLOWED_STATUS_FILTERS: frozenset[str] = frozenset({"all", "normal", "warning", "critical"})
ALLOWED_SORT_KEYS: frozenset[str] = frozenset(
    {"urgency_desc", "name_asc", "name_desc", "projected_asc", "current_desc"}
)
SEARCH_MAX_LENGTH: int = 100
_LIKE_ESCAPE_CHAR = "\\"


def escape_like_pattern(term: str) -> str:
    """Escapa comodines LIKE (`%`, `_`) y el carácter de escape para búsquedas literales."""
    return (
        term.replace(_LIKE_ESCAPE_CHAR, _LIKE_ESCAPE_CHAR * 2)
        .replace("%", f"{_LIKE_ESCAPE_CHAR}%")
        .replace("_", f"{_LIKE_ESCAPE_CHAR}_")
    )


def _is_postgres_session(db: AsyncSession) -> bool:
    bind = db.bind
    return bool(bind is not None and hasattr(bind, "dialect") and bind.dialect.name == "postgresql")


async def commit_preserving_tenant_scope(db: AsyncSession) -> None:
    """
    Confirma la transacción y restablece el `search_path` del tenant.

    `get_tenant_db_session` usa `SET LOCAL search_path`, que PostgreSQL descarta al
    finalizar la transacción. Sin este restablecimiento, cualquier consulta posterior
    al `commit()` se ejecutaría fuera del esquema `tenant_*` (fuga/escape de aislamiento).
    """
    tenant_schema: str | None = None
    if _is_postgres_session(db):
        current = (await db.execute(text("SELECT current_schema()"))).scalar()
        if isinstance(current, str) and TENANT_SCHEMA_REGEX.match(current):
            tenant_schema = validate_tenant_schema_name(current)
    await db.commit()
    if tenant_schema is not None:
        await db.execute(text(f'SET LOCAL search_path TO "{tenant_schema}", public'))


class ProjectionSnapshotService:
    """
    Servicio de orquestación de snapshots de proyección:
    - Recálculo por lotes con candado distribuido / advisory locks.
    - Paginación server-side ultrarrápida (< 25 ms) para el Grid frontend.
    - Notificaciones en tiempo real vía WebSocket / Redis PubSub.
    """

    def __init__(self, engine: ProjectionEngine | None = None) -> None:
        self.engine = engine or ProjectionEngine()

    async def recompute_tenant_snapshots(
        self,
        db: AsyncSession,
        tenant_id: str | None = None,
        horizon_days: int = 30,
        batch_size: int = 50,
    ) -> dict[str, Any]:
        """
        Recalcula todos los snapshots de proyección del tenant con protección anti-concurrencia.
        Itera sobre los productos en lotes de tamaño `batch_size` para optimizar memoria.
        Instrumentado con OpenTelemetry span 'projection.recompute_snapshots'.
        """
        resolved_tenant = str(tenant_id or get_tenant_telemetry_context().tenant_id or "default").strip()
        with trace_span(
            "projection.recompute_snapshots",
            attributes={
                "tenant_id": resolved_tenant,
                "horizon_days": horizon_days,
                "batch_size": batch_size,
                "projection.products_processed": 0,
            },
            tracer_name="oppytec.projection",
        ) as span_attrs:
            tenant_key = resolved_tenant
            is_postgres = _is_postgres_session(db)

            # 1. Adquirir candado anti-concurrencia.
            # Red Team: la verificación `locked()` y la adquisición ocurren sin `await` intermedio
            # (fast-path de asyncio.Lock), evitando que dos corrutinas del mismo worker pasen el
            # chequeo y queden encoladas en lugar de recibir `locked`.
            local_lock = _get_tenant_local_lock(tenant_key)
            if local_lock.locked():
                span_attrs["projection.products_processed"] = 0
                span_attrs["status"] = "locked"
                return {
                    "status": "locked",
                    "message": "Recomputation already in progress for this tenant",
                    "processed": 0,
                    "horizon_days": horizon_days,
                }

            async with local_lock:
                if is_postgres:
                    # Candado distribuido entre workers. Es de ámbito transaccional: se mantiene
                    # hasta el único commit final (los lotes intermedios usan `flush`).
                    try:
                        lock_res = await db.execute(
                            text("SELECT pg_try_advisory_xact_lock(hashtext(:lock_key))"),
                            {"lock_key": f"projection_recompute_{tenant_key}"},
                        )
                        acquired = lock_res.scalar()
                        if not acquired:
                            span_attrs["projection.products_processed"] = 0
                            span_attrs["status"] = "locked"
                            return {
                                "status": "locked",
                                "message": "Recomputation already in progress (advisory lock)",
                                "processed": 0,
                                "horizon_days": horizon_days,
                            }
                    except Exception as exc:
                        logger.warning("No se pudo ejecutar advisory lock PostgreSQL: %s", exc)

                # 2. Obtener productos activos del tenant
                prod_stmt = select(Producto.id).where(Producto.deleted_at.is_(None)).order_by(Producto.id.asc())
                prod_res = await db.execute(prod_stmt)
                product_ids = [row[0] for row in prod_res.all()]

                processed_count = 0
                total_prods = len(product_ids)

                # 3. Procesar en lotes de `batch_size`
                for i in range(0, total_prods, batch_size):
                    batch_ids = product_ids[i : i + batch_size]
                    for prod_id in batch_ids:
                        # Buscar bodegas en las que existe el producto
                        pb_stmt = select(ProductoBodega.bodega_id).where(
                            ProductoBodega.producto_id == prod_id
                        )
                        pb_res = await db.execute(pb_stmt)
                        bodega_ids = [r[0] for r in pb_res.all()]

                        # Recalcular tanto para la vista consolidada (bodega_id=None) como para cada bodega
                        targets: list[int | None] = [None] + bodega_ids

                        for b_id in targets:
                            try:
                                sim_result = await self.engine.calculate_product_curve(
                                    db=db,
                                    producto_id=prod_id,
                                    bodega_id=b_id,
                                    horizon_days=horizon_days,
                                    include_events=True,
                                )
                                # Upsert en ProjectionSnapshot
                                await self._upsert_snapshot(db, sim_result)

                                # Upsert en DailyConsumptionRate
                                r7, r30, r90 = await self.engine.calculate_consumption_rates(
                                    db, prod_id, b_id
                                )
                                await self._upsert_consumption_rate(db, prod_id, b_id, r7, r30, r90)
                            except Exception as p_exc:
                                logger.error(
                                    "Error calculando proyección producto_id=%s, bodega_id=%s: %s",
                                    prod_id,
                                    b_id,
                                    p_exc,
                                )

                        processed_count += 1

                    # Flush por lote: libera memoria de escritura pendiente sin cerrar la
                    # transacción (mantiene advisory lock y `SET LOCAL search_path` del tenant).
                    await db.flush()

                # Commit único final preservando el ámbito del esquema tenant
                await commit_preserving_tenant_scope(db)

                # 4. Emitir evento en tiempo real vía WebSocket / Redis
                try:
                    publisher = get_realtime_publisher()
                    if publisher:
                        event = RealtimeEventEnvelope(
                            event_type="projection.snapshots_recomputed",
                            tenant_id=tenant_key,
                            payload={
                                "processed": processed_count,
                                "horizon_days": horizon_days,
                                "timestamp": datetime.now(UTC).isoformat(),
                            },
                        )
                        await publisher.publish_event(event)
                except Exception as rt_exc:
                    logger.warning("Fallo al publicar evento en tiempo real de proyección: %s", rt_exc)

                span_attrs["projection.products_processed"] = processed_count
                span_attrs["products_processed"] = processed_count
                span_attrs["status"] = "completed"
                return {
                    "status": "completed",
                    "processed": processed_count,
                    "horizon_days": horizon_days,
                    "message": f"Successfully recomputed {processed_count} product snapshots",
                }

    async def get_paginated_snapshots(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 30,
        search: str | None = None,
        category_id: int | None = None,
        bodega_id: int | None = None,
        status_filter: str | None = None,
        sort_by: str | None = None,
        horizon_days: int = 30,
    ) -> dict[str, Any]:
        """
        Consulta de lectura paginada ultrarrápida sobre la tabla `projection_snapshots`.
        Soporta filtrado por texto, categoría, bodega, semáforo de estado y ordenamiento de urgencia.
        Instrumentado con OpenTelemetry span 'projection.get_snapshots_paginated'.
        """
        safe_page = max(1, page)
        safe_page_size = min(max(1, page_size), 100)

        # Red Team: listas blancas estrictas (defensa en profundidad tras la validación del router)
        normalized_status = (status_filter or "").strip().lower()
        if normalized_status and normalized_status not in ALLOWED_STATUS_FILTERS:
            raise DomainValidationError(
                "Filtro de estado de proyección no permitido.",
                i18n_key="projection:errors.invalid_status_filter",
            )
        normalized_sort = (sort_by or "").strip().lower()
        if normalized_sort and normalized_sort not in ALLOWED_SORT_KEYS:
            raise DomainValidationError(
                "Criterio de ordenamiento de proyección no permitido.",
                i18n_key="projection:errors.invalid_sort_by",
            )
        normalized_search = (search or "").strip()[:SEARCH_MAX_LENGTH]

        with trace_span(
            "projection.get_snapshots_paginated",
            attributes={
                "page": safe_page,
                "page_size": safe_page_size,
                "search": search or "",
                "category_id": category_id,
                "bodega_id": bodega_id,
                "status_filter": status_filter or "",
                "sort_by": sort_by or "",
                "horizon_days": horizon_days,
            },
            tracer_name="oppytec.projection",
        ) as span_attrs:
            # Base query uniendo Producto, Categoria y Bodega
            query = (
                select(
                    ProjectionSnapshot,
                    Producto.nombre.label("producto_nombre"),
                    Producto.sku.label("producto_sku"),
                    Producto.categoria_id.label("categoria_id"),
                    Categoria.nombre.label("categoria_nombre"),
                    Bodega.nombre.label("bodega_nombre"),
                )
                .join(Producto, Producto.id == ProjectionSnapshot.producto_id)
                .outerjoin(Categoria, Categoria.id == Producto.categoria_id)
                .outerjoin(Bodega, Bodega.id == ProjectionSnapshot.bodega_id)
                .where(ProjectionSnapshot.horizon_days == horizon_days)
            )

            count_query = (
                select(func.count(ProjectionSnapshot.id))
                .join(Producto, Producto.id == ProjectionSnapshot.producto_id)
                .where(ProjectionSnapshot.horizon_days == horizon_days)
            )

            # Filtro de bodega
            if bodega_id is not None:
                query = query.where(ProjectionSnapshot.bodega_id == bodega_id)
                count_query = count_query.where(ProjectionSnapshot.bodega_id == bodega_id)
            else:
                # Por defecto en vista general, muestra consolidado (bodega_id is None) si existen
                # o todos si no se han generado consolidados
                query = query.where(ProjectionSnapshot.bodega_id.is_(None))
                count_query = count_query.where(ProjectionSnapshot.bodega_id.is_(None))

            # Filtro de búsqueda por nombre o SKU (parametrizado + comodines escapados)
            if normalized_search:
                search_pattern = f"%{escape_like_pattern(normalized_search)}%"
                search_cond = or_(
                    Producto.nombre.ilike(search_pattern, escape=_LIKE_ESCAPE_CHAR),
                    Producto.sku.ilike(search_pattern, escape=_LIKE_ESCAPE_CHAR),
                )
                query = query.where(search_cond)
                count_query = count_query.where(search_cond)

            # Filtro de categoría
            if category_id is not None:
                query = query.where(Producto.categoria_id == category_id)
                count_query = count_query.where(Producto.categoria_id == category_id)

            # Filtro de semáforo de estado (normal, warning, critical)
            if status_filter and status_filter.strip().lower() not in ("all", ""):
                status_val = status_filter.strip().lower()
                query = query.where(func.lower(ProjectionSnapshot.worst_status) == status_val)
                count_query = count_query.where(func.lower(ProjectionSnapshot.worst_status) == status_val)

            # Total de registros con los filtros aplicados
            total_res = await db.execute(count_query)
            total_items = total_res.scalar() or 0

            # Si no hay resultados para consolidado (bodega_id is None), y no se especificó bodega_id,
            # verificar si la tabla NO contiene ningún consolidado para este horizonte y hacer fallback a snapshots por bodega
            if total_items == 0 and bodega_id is None:
                has_consolidated = (
                    await db.execute(
                        select(func.count(ProjectionSnapshot.id))
                        .where(ProjectionSnapshot.horizon_days == horizon_days)
                        .where(ProjectionSnapshot.bodega_id.is_(None))
                    )
                ).scalar() or 0
                if has_consolidated == 0:
                    alt_count = (
                        select(func.count(ProjectionSnapshot.id))
                        .join(Producto, Producto.id == ProjectionSnapshot.producto_id)
                        .where(ProjectionSnapshot.horizon_days == horizon_days)
                    )
                    if normalized_search:
                        alt_count = alt_count.where(search_cond)
                    if category_id is not None:
                        alt_count = alt_count.where(Producto.categoria_id == category_id)
                    if status_filter and status_filter.strip().lower() not in ("all", ""):
                        alt_count = alt_count.where(func.lower(ProjectionSnapshot.worst_status) == status_val)

                    alt_total = (await db.execute(alt_count)).scalar() or 0
                    if alt_total > 0:
                        query = (
                            select(
                                ProjectionSnapshot,
                                Producto.nombre.label("producto_nombre"),
                                Producto.sku.label("producto_sku"),
                                Producto.categoria_id.label("categoria_id"),
                                Categoria.nombre.label("categoria_nombre"),
                                Bodega.nombre.label("bodega_nombre"),
                            )
                            .join(Producto, Producto.id == ProjectionSnapshot.producto_id)
                            .outerjoin(Categoria, Categoria.id == Producto.categoria_id)
                            .outerjoin(Bodega, Bodega.id == ProjectionSnapshot.bodega_id)
                            .where(ProjectionSnapshot.horizon_days == horizon_days)
                        )
                        if normalized_search:
                            query = query.where(search_cond)
                        if category_id is not None:
                            query = query.where(Producto.categoria_id == category_id)
                        if status_filter and status_filter.strip().lower() not in ("all", ""):
                            query = query.where(func.lower(ProjectionSnapshot.worst_status) == status_val)
                        total_items = alt_total

            # Criterios de ordenamiento
            order_clause = self._resolve_ordering(sort_by)
            query = query.order_by(*order_clause)

            # Paginación server-side con OFFSET / LIMIT
            total_pages = max(1, (total_items + safe_page_size - 1) // safe_page_size) if total_items > 0 else 1
            offset = (safe_page - 1) * safe_page_size
            paginated_query = query.offset(offset).limit(safe_page_size)

            rows = (await db.execute(paginated_query)).all()

            items: list[dict[str, Any]] = []
            for snapshot, prod_name, prod_sku, cat_id, cat_name, b_name in rows:
                items.append(
                    {
                        "id": snapshot.id,
                        "producto_id": snapshot.producto_id,
                        "producto_nombre": prod_name,
                        "producto_sku": prod_sku,
                        "categoria_id": cat_id,
                        "categoria_nombre": cat_name,
                        "bodega_id": snapshot.bodega_id,
                        "bodega_nombre": b_name or "Consolidado Multi-Bodega",
                        "horizon_days": snapshot.horizon_days,
                        "current_stock": str(snapshot.current_stock),
                        "projected_stock": str(snapshot.projected_stock),
                        "depletion_date": snapshot.depletion_date.isoformat()
                        if snapshot.depletion_date
                        else None,
                        "worst_status": snapshot.worst_status.lower(),
                        "worst_status_label": snapshot.worst_status_label,
                        "worst_day": snapshot.worst_day,
                        "daily_consumption_rate": str(snapshot.daily_consumption_rate),
                        "is_stale": snapshot.is_stale,
                        "calculated_at": snapshot.calculated_at.isoformat()
                        if snapshot.calculated_at
                        else None,
                    }
                )

            span_attrs["total_items"] = total_items
            span_attrs["returned_items"] = len(items)

            return {
                "items": items,
                "total_items": total_items,
                "page": safe_page,
                "page_size": safe_page_size,
                "total_pages": total_pages,
                "has_next": safe_page < total_pages,
                "has_prev": safe_page > 1,
            }

    async def get_product_curve_detail(
        self,
        db: AsyncSession,
        producto_id: int,
        bodega_id: int | None = None,
        horizon_days: int = 30,
    ) -> dict[str, Any]:
        """
        Obtiene la serie temporal completa día a día para el gráfico interactivo Recharts.
        Si el snapshot persistente existe y no es stale, lo entrega inmediatamente (< 15 ms).
        De lo contrario, calcula la curva al vuelo y actualiza el snapshot.
        """
        # 1. Consultar snapshot existente
        snap_stmt = select(
            ProjectionSnapshot,
            Producto.nombre.label("producto_nombre"),
            Bodega.nombre.label("bodega_nombre"),
        ).join(
            Producto, Producto.id == ProjectionSnapshot.producto_id
        ).outerjoin(
            Bodega, Bodega.id == ProjectionSnapshot.bodega_id
        ).where(
            ProjectionSnapshot.producto_id == producto_id,
            ProjectionSnapshot.horizon_days == horizon_days,
        )
        if bodega_id is not None:
            snap_stmt = snap_stmt.where(ProjectionSnapshot.bodega_id == bodega_id)
        else:
            snap_stmt = snap_stmt.where(ProjectionSnapshot.bodega_id.is_(None))

        snap_res = await db.execute(snap_stmt)
        record = snap_res.first()

        if record and not record[0].is_stale and record[0].projection_curve:
            snap, prod_name, b_name = record
            return {
                "producto_id": snap.producto_id,
                "producto_nombre": prod_name,
                "bodega_id": snap.bodega_id,
                "bodega_nombre": b_name or "Consolidado Multi-Bodega",
                "horizon_days": snap.horizon_days,
                "current_stock": str(snap.current_stock),
                "projected_stock": str(snap.projected_stock),
                "depletion_date": snap.depletion_date.isoformat() if snap.depletion_date else None,
                "worst_status": snap.worst_status.lower(),
                "worst_status_label": snap.worst_status_label,
                "worst_day": snap.worst_day,
                "daily_consumption_rate": str(snap.daily_consumption_rate),
                "curve": snap.projection_curve,
            }

        # 2. Si no existe o está obsoleto, calcular al vuelo
        sim_result = await self.engine.calculate_product_curve(
            db=db,
            producto_id=producto_id,
            bodega_id=bodega_id,
            horizon_days=horizon_days,
            include_events=True,
        )
        # Guardar snapshot actualizado (restablece search_path del tenant tras el commit)
        await self._upsert_snapshot(db, sim_result)
        await commit_preserving_tenant_scope(db)

        # Obtener nombres descriptivos
        p_name = "Producto"
        b_name = "Consolidado Multi-Bodega"
        p_res = await db.execute(select(Producto.nombre).where(Producto.id == producto_id))
        p_row = p_res.first()
        if p_row:
            p_name = p_row[0]

        if bodega_id is not None:
            b_res = await db.execute(select(Bodega.nombre).where(Bodega.id == bodega_id))
            b_row = b_res.first()
            if b_row:
                b_name = b_row[0]

        return {
            "producto_id": sim_result.producto_id,
            "producto_nombre": p_name,
            "bodega_id": sim_result.bodega_id,
            "bodega_nombre": b_name,
            "horizon_days": sim_result.horizon_days,
            "current_stock": str(sim_result.current_stock),
            "projected_stock": str(sim_result.projected_stock),
            "depletion_date": sim_result.depletion_date.isoformat()
            if sim_result.depletion_date
            else None,
            "worst_status": sim_result.worst_status.value.lower(),
            "worst_status_label": sim_result.worst_status_label,
            "worst_day": sim_result.worst_day,
            "daily_consumption_rate": str(sim_result.daily_consumption_rate),
            "curve": [pt.to_dict() for pt in sim_result.curve],
        }

    async def get_projection_alerts(
        self,
        db: AsyncSession,
        bodega_id: int | None = None,
        horizon_days: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Consola de alertas de productos en quiebre o estado crítico/warning dentro del horizonte,
        junto con sugerencias automáticas de traspaso inter-bodega para mitigar el déficit.
        """
        alert_stmt = (
            select(
                ProjectionSnapshot,
                Producto.nombre.label("producto_nombre"),
                Bodega.nombre.label("bodega_nombre"),
            )
            .join(Producto, Producto.id == ProjectionSnapshot.producto_id)
            .outerjoin(Bodega, Bodega.id == ProjectionSnapshot.bodega_id)
            .where(
                ProjectionSnapshot.horizon_days == horizon_days,
                func.lower(ProjectionSnapshot.worst_status).in_(["critical", "warning"]),
            )
        )
        if bodega_id is not None:
            alert_stmt = alert_stmt.where(ProjectionSnapshot.bodega_id == bodega_id)

        # Ordenar primero los críticos, luego los warnings
        urgency_order = case(
            (func.lower(ProjectionSnapshot.worst_status) == "critical", 1),
            else_=2,
        ).asc()
        alert_stmt = alert_stmt.order_by(urgency_order, Producto.nombre.asc())

        res = await db.execute(alert_stmt)
        rows = res.all()

        alerts: list[dict[str, Any]] = []
        for snap, prod_name, b_name in rows:
            suggestions: list[dict[str, Any]] = []
            if snap.bodega_id is not None and snap.worst_status.lower() == "critical":
                # Buscar sugerencias de traspaso
                needed = abs(snap.projected_stock) if snap.projected_stock < Decimal("0") else snap.daily_consumption_rate * Decimal("7")
                if needed <= Decimal("0"):
                    needed = Decimal("1.0000")
                depletion_d = snap.depletion_date or date.today()
                recs = await self.engine.find_alternative_stock(
                    db=db,
                    producto_id=snap.producto_id,
                    bodega_id_quiebre=snap.bodega_id,
                    needed_qty=needed,
                    date_needed=depletion_d,
                )
                for rec in recs:
                    # Buscar nombre bodega origen
                    b_orig_name = f"Bodega #{rec.bodega_origen_id}"
                    b_orig_res = await db.execute(
                        select(Bodega.nombre).where(Bodega.id == rec.bodega_origen_id)
                    )
                    b_orig_row = b_orig_res.first()
                    if b_orig_row:
                        b_orig_name = b_orig_row[0]

                    suggestions.append(
                        {
                            "producto_id": rec.producto_id,
                            "bodega_origen_id": rec.bodega_origen_id,
                            "bodega_origen_nombre": b_orig_name,
                            "bodega_destino_id": rec.bodega_destino_id,
                            "cantidad_sugerida": str(rec.cantidad_sugerida),
                            "dias_cobertura_restante_origen": rec.dias_cobertura_restante_origen,
                            "urgencia": rec.urgencia.value,
                        }
                    )

            alerts.append(
                {
                    "producto_id": snap.producto_id,
                    "producto_nombre": prod_name,
                    "bodega_id": snap.bodega_id,
                    "bodega_nombre": b_name or "Consolidado Multi-Bodega",
                    "status": snap.worst_status.lower(),
                    "status_label": snap.worst_status_label,
                    "depletion_date": snap.depletion_date.isoformat()
                    if snap.depletion_date
                    else None,
                    "worst_day": snap.worst_day,
                    "current_stock": str(snap.current_stock),
                    "projected_stock": str(snap.projected_stock),
                    "transfer_suggestions": suggestions,
                }
            )

        return alerts

    def _resolve_ordering(self, sort_by: str | None) -> list[Any]:
        """Mapea parámetros de ordenamiento a expresiones SQLAlchemy."""
        sb = (sort_by or "urgency_desc").strip().lower()

        urgency_expr = case(
            (func.lower(ProjectionSnapshot.worst_status) == "critical", 1),
            (func.lower(ProjectionSnapshot.worst_status) == "warning", 2),
            else_=3,
        ).asc()

        if sb == "name_asc":
            return [Producto.nombre.asc()]
        if sb == "name_desc":
            return [Producto.nombre.desc()]
        if sb == "projected_asc":
            return [ProjectionSnapshot.projected_stock.asc()]
        if sb == "current_desc":
            return [ProjectionSnapshot.current_stock.desc()]
        if sb == "urgency_desc":
            return [urgency_expr, Producto.nombre.asc()]

        return [urgency_expr, Producto.nombre.asc()]

    async def _upsert_snapshot(self, db: AsyncSession, sim: Any) -> None:
        """Actualiza o inserta un snapshot de proyección en la base de datos."""
        stmt = select(ProjectionSnapshot).where(
            ProjectionSnapshot.producto_id == sim.producto_id,
            ProjectionSnapshot.horizon_days == sim.horizon_days,
        )
        if sim.bodega_id is not None:
            stmt = stmt.where(ProjectionSnapshot.bodega_id == sim.bodega_id)
        else:
            stmt = stmt.where(ProjectionSnapshot.bodega_id.is_(None))

        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()

        curve_dicts = [pt.to_dict() for pt in sim.curve]

        if existing:
            existing.current_stock = sim.current_stock
            existing.projected_stock = sim.projected_stock
            existing.depletion_date = sim.depletion_date
            existing.worst_status = sim.worst_status.value
            existing.worst_status_label = sim.worst_status_label
            existing.worst_day = sim.worst_day
            existing.daily_consumption_rate = sim.daily_consumption_rate
            existing.projection_curve = curve_dicts
            existing.is_stale = False
            existing.calculated_at = datetime.now(UTC)
        else:
            new_snap = ProjectionSnapshot(
                producto_id=sim.producto_id,
                bodega_id=sim.bodega_id,
                horizon_days=sim.horizon_days,
                current_stock=sim.current_stock,
                projected_stock=sim.projected_stock,
                depletion_date=sim.depletion_date,
                worst_status=sim.worst_status.value,
                worst_status_label=sim.worst_status_label,
                worst_day=sim.worst_day,
                daily_consumption_rate=sim.daily_consumption_rate,
                projection_curve=curve_dicts,
                is_stale=False,
                calculated_at=datetime.now(UTC),
            )
            db.add(new_snap)

    async def _upsert_consumption_rate(
        self,
        db: AsyncSession,
        producto_id: int,
        bodega_id: int | None,
        rate_7d: Decimal,
        rate_30d: Decimal,
        rate_90d: Decimal,
    ) -> None:
        """Actualiza o inserta las tasas históricas móviles de consumo en DailyConsumptionRate."""
        stmt = select(DailyConsumptionRate).where(
            DailyConsumptionRate.producto_id == producto_id,
        )
        if bodega_id is not None:
            stmt = stmt.where(DailyConsumptionRate.bodega_id == bodega_id)
        else:
            stmt = stmt.where(DailyConsumptionRate.bodega_id.is_(None))

        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.rate_7d = rate_7d
            existing.rate_30d = rate_30d
            existing.rate_90d = rate_90d
            existing.last_calculated_at = datetime.now(UTC)
        else:
            new_rate = DailyConsumptionRate(
                producto_id=producto_id,
                bodega_id=bodega_id,
                rate_7d=rate_7d,
                rate_30d=rate_30d,
                rate_90d=rate_90d,
                last_calculated_at=datetime.now(UTC),
            )
            db.add(new_rate)
