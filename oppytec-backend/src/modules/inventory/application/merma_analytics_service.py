"""
oppytec-backend/src/modules/inventory/application/merma_analytics_service.py
Servicio de Analítica y Agregación Financiera de Mermas (/gestion?tab=mermas):
- Agregación temporal, por categoría y por motivo con valoración PPP estricta Decimal(14, 2).
- Historial cronológico paginado con filtros avanzados.
- Modo híbrido (SQLAlchemy 2.0 Async + In-Memory Fallback).
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import contextlib
import logging
from collections import defaultdict
from datetime import UTC, date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.observability import (
    get_tenant_telemetry_context,
    trace_span,
)
from src.modules.catalog.infrastructure.models import Categoria, Producto
from src.modules.inventory.infrastructure.models import Bodega, Merma

logger = logging.getLogger("oppytec.inventory.merma_analytics")


class MermaAnalyticsService:
    """Servicio de agregación y análisis financiero de mermas e inventario dañado."""

    def __init__(self, use_in_memory: bool = False) -> None:
        self._use_in_memory = use_in_memory
        self._memory_mermas: list[dict[str, Any]] = []

    def enable_in_memory_mode(self) -> None:
        self._use_in_memory = True

    def reset_in_memory_store(self) -> None:
        self._memory_mermas.clear()

    def reset(self) -> None:
        self.reset_in_memory_store()

    def register_in_memory_merma(self, merma_data: dict[str, Any]) -> None:
        self._memory_mermas.append(merma_data)

    async def get_analytics(
        self,
        session: AsyncSession | None,
        date_from: date | datetime | None = None,
        date_to: date | datetime | None = None,
        bodega_id: int | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Obtiene KPIs agregados de mermas, desglose por motivo, por categoría y serie temporal."""
        resolved_tenant = str(
            tenant_id
            or get_tenant_telemetry_context().tenant_id
            or "tenant_default"
        )
        with trace_span(
            "inventory.waste.analytics_query",
            attributes={
                "tenant_id": resolved_tenant,
                "bodega_id": bodega_id if bodega_id is not None else "all",
                "date_from": str(date_from) if date_from is not None else None,
                "date_to": str(date_to) if date_to is not None else None,
            },
            tracer_name="oppytec.inventory.merma_analytics",
        ) as span_attrs:
            if not self._use_in_memory and session is not None:
                try:
                    # Totales
                    totals_stmt = select(
                        func.coalesce(func.sum(Merma.costo_total), Decimal("0.00")),
                        func.count(Merma.id),
                    ).where(Merma.is_deleted.is_(False))
                    if bodega_id:
                        totals_stmt = totals_stmt.where(Merma.bodega_id == bodega_id)
                    if date_from:
                        dt_from = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc) if isinstance(date_from, date) and not isinstance(date_from, datetime) else date_from
                        totals_stmt = totals_stmt.where(Merma.created_at >= dt_from)
                    if date_to:
                        dt_to = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc) if isinstance(date_to, date) and not isinstance(date_to, datetime) else date_to
                        totals_stmt = totals_stmt.where(Merma.created_at <= dt_to)

                    tot_res = (await session.execute(totals_stmt)).first()
                    total_perdida = tot_res[0] if tot_res else Decimal("0.00")
                    total_items = tot_res[1] if tot_res else 0

                    # Pendientes
                    pending_stmt = select(func.count(Merma.id)).where(
                        Merma.is_deleted.is_(False),
                        Merma.estado_aprobacion == "PENDIENTE",
                    )
                    if bodega_id:
                        pending_stmt = pending_stmt.where(Merma.bodega_id == bodega_id)
                    pending_count = (await session.execute(pending_stmt)).scalar() or 0

                    # Agrupado por motivo
                    motivo_stmt = (
                        select(
                            Merma.motivo,
                            func.sum(Merma.costo_total).label("total_costo"),
                            func.sum(Merma.cantidad).label("total_cantidad"),
                        )
                        .where(Merma.is_deleted.is_(False))
                        .group_by(Merma.motivo)
                    )
                    if bodega_id:
                        motivo_stmt = motivo_stmt.where(Merma.bodega_id == bodega_id)
                    motivo_rows = (await session.execute(motivo_stmt)).all()
                    por_motivo = [
                        {
                            "motivo": r[0],
                            "total_costo": r[1] or Decimal("0.00"),
                            "cantidad": r[2] or Decimal("0.0000"),
                            "porcentaje": ((r[1] / total_perdida) * Decimal("100.00")).quantize(Decimal("0.01")) if total_perdida > Decimal("0.00") and r[1] else Decimal("0.00"),
                        }
                        for r in motivo_rows
                    ]

                    # Agrupado por categoría
                    cat_stmt = (
                        select(
                            Categoria.id,
                            Categoria.nombre,
                            func.coalesce(func.sum(Merma.costo_total), Decimal("0.00")),
                            func.coalesce(func.sum(Merma.cantidad), Decimal("0.0000")),
                        )
                        .join(Producto, Merma.producto_id == Producto.id)
                        .join(Categoria, Producto.categoria_id == Categoria.id)
                        .where(Merma.is_deleted.is_(False))
                        .group_by(Categoria.id, Categoria.nombre)
                    )
                    if bodega_id:
                        cat_stmt = cat_stmt.where(Merma.bodega_id == bodega_id)
                    cat_rows = (await session.execute(cat_stmt)).all()
                    por_categoria = [
                        {
                            "categoria_id": r[0],
                            "categoria_nombre": r[1],
                            "total_costo": r[2],
                            "cantidad": r[3],
                        }
                        for r in cat_rows
                    ]

                    # Timeline (agrupado por fecha)
                    time_stmt = (
                        select(
                            func.date(Merma.created_at).label("fecha"),
                            func.coalesce(func.sum(Merma.costo_total), Decimal("0.00")),
                            func.coalesce(func.sum(Merma.cantidad), Decimal("0.0000")),
                        )
                        .where(Merma.is_deleted.is_(False))
                        .group_by(func.date(Merma.created_at))
                        .order_by(func.date(Merma.created_at).asc())
                    )
                    if bodega_id:
                        time_stmt = time_stmt.where(Merma.bodega_id == bodega_id)
                    time_rows = (await session.execute(time_stmt)).all()
                    timeline = [
                        {
                            "fecha": str(r[0]),
                            "costo": r[1],
                            "cantidad": r[2],
                        }
                        for r in time_rows
                    ]

                    span_attrs["total_perdida_ppp"] = str(total_perdida)
                    span_attrs["items_mermados_count"] = total_items
                    span_attrs["mermas_pendientes_aprobacion"] = pending_count

                    return {
                        "total_perdida_ppp": total_perdida,
                        "items_mermados_count": total_items,
                        "mermas_pendientes_aprobacion": pending_count,
                        "por_motivo": por_motivo,
                        "por_categoria": por_categoria,
                        "timeline": timeline,
                    }
                except Exception as exc:
                    logger.debug("get_analytics fallback to in-memory: %s", exc)
                    with contextlib.suppress(Exception):
                        await session.rollback()

            # In-memory execution
            filtered = [
                m for m in self._memory_mermas
                if tenant_id is None or m.get("tenant_id") in (None, tenant_id)
            ]
            if bodega_id:
                filtered = [m for m in filtered if m.get("bodega_id") == bodega_id]

            total_costo = sum((m.get("costo_total", Decimal("0.00")) for m in filtered), Decimal("0.00"))
            items_count = len(filtered)
            pending_count = len([m for m in filtered if m.get("estado_aprobacion") == "PENDIENTE"])

            motivo_dict: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"costo": Decimal("0.00"), "cantidad": Decimal("0.0000")})
            categoria_dict: dict[int, dict[str, Any]] = defaultdict(lambda: {"nombre": "General", "costo": Decimal("0.00"), "cantidad": Decimal("0.0000")})
            timeline_dict: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"costo": Decimal("0.00"), "cantidad": Decimal("0.0000")})

            for m in filtered:
                motivo = str(m.get("motivo", "OTRO"))
                costo = m.get("costo_total", Decimal("0.00"))
                qty = m.get("cantidad", Decimal("0.0000"))
                cat_id = m.get("categoria_id", 1)
                cat_nombre = m.get("categoria_nombre", "General")
                fecha_str = str(m.get("fecha_merma") or date.today().isoformat())

                motivo_dict[motivo]["costo"] += costo
                motivo_dict[motivo]["cantidad"] += qty

                categoria_dict[cat_id]["nombre"] = cat_nombre
                categoria_dict[cat_id]["costo"] += costo
                categoria_dict[cat_id]["cantidad"] += qty

                timeline_dict[fecha_str]["costo"] += costo
                timeline_dict[fecha_str]["cantidad"] += qty

            por_motivo = [
                {
                    "motivo": k,
                    "total_costo": v["costo"],
                    "cantidad": v["cantidad"],
                    "porcentaje": ((v["costo"] / total_costo) * Decimal("100.00")).quantize(Decimal("0.01")) if total_costo > 0 else Decimal("0.00"),
                }
                for k, v in motivo_dict.items()
            ]

            por_categoria = [
                {
                    "categoria_id": k,
                    "categoria_nombre": v["nombre"],
                    "total_costo": v["costo"],
                    "cantidad": v["cantidad"],
                }
                for k, v in categoria_dict.items()
            ]

            timeline = [
                {"fecha": k, "costo": v["costo"], "cantidad": v["cantidad"]}
                for k, v in sorted(timeline_dict.items())
            ]

            span_attrs["total_perdida_ppp"] = str(total_costo)
            span_attrs["items_mermados_count"] = items_count
            span_attrs["mermas_pendientes_aprobacion"] = pending_count

            return {
                "total_perdida_ppp": total_costo,
                "items_mermados_count": items_count,
                "mermas_pendientes_aprobacion": pending_count,
                "por_motivo": por_motivo,
                "por_categoria": por_categoria,
                "timeline": timeline,
            }

    async def get_history(
        self,
        session: AsyncSession | None,
        date_from: date | None = None,
        date_to: date | None = None,
        bodega_id: int | None = None,
        estado: str | None = None,
        motivo: str | None = None,
        skip: int = 0,
        limit: int = 50,
        tenant_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Consulta paginada del historial cronológico de mermas."""
        if not self._use_in_memory and session is not None:
            try:
                stmt = (
                    select(
                        Merma,
                        Producto.nombre.label("producto_nombre"),
                        Producto.sku.label("producto_sku"),
                        Bodega.nombre.label("bodega_nombre"),
                    )
                    .outerjoin(Producto, Merma.producto_id == Producto.id)
                    .outerjoin(Bodega, Merma.bodega_id == Bodega.id)
                    .where(Merma.is_deleted.is_(False))
                )
                if bodega_id:
                    stmt = stmt.where(Merma.bodega_id == bodega_id)
                if estado:
                    stmt = stmt.where(Merma.estado_aprobacion == estado)
                if motivo:
                    stmt = stmt.where(Merma.motivo == motivo)
                if date_from:
                    dt_from = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
                    stmt = stmt.where(Merma.created_at >= dt_from)
                if date_to:
                    dt_to = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)
                    stmt = stmt.where(Merma.created_at <= dt_to)

                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar() or 0

                stmt = stmt.order_by(Merma.id.desc()).offset(skip).limit(limit)
                results = (await session.execute(stmt)).all()

                items: list[dict[str, Any]] = []
                for m, prod_nombre, prod_sku, bodega_nombre in results:
                    items.append({
                        "id": m.id,
                        "producto_id": m.producto_id,
                        "producto_nombre": prod_nombre,
                        "producto_sku": prod_sku,
                        "bodega_id": m.bodega_id,
                        "bodega_nombre": bodega_nombre,
                        "cantidad": m.cantidad,
                        "costo_total": m.costo_total,
                        "motivo": m.motivo,
                        "estado_aprobacion": m.estado_aprobacion,
                        "reportado_por_user_id": m.reportado_por_user_id,
                        "fecha_merma": m.created_at,
                        "created_at": m.created_at,
                    })

                return items, total
            except Exception as exc:
                logger.debug("get_history fallback to in-memory: %s", exc)
                with contextlib.suppress(Exception):
                    await session.rollback()

        # In-memory execution
        filtered = [
            m for m in self._memory_mermas
            if tenant_id is None or m.get("tenant_id") in (None, tenant_id)
        ]
        if bodega_id:
            filtered = [m for m in filtered if m.get("bodega_id") == bodega_id]
        if estado:
            filtered = [m for m in filtered if m.get("estado_aprobacion") == estado]
        if motivo:
            filtered = [m for m in filtered if m.get("motivo") == motivo]
        total = len(filtered)
        paginated = filtered[skip : skip + limit]
        return paginated, total
