"""
oppytec-backend/src/modules/projection/application/projection_engine.py
Motor de Aplicación de Proyección de Demandas, Cálculo de Consumo y Sugerencias de Traspaso.
Orquesta datos de persistencia (Kardex, Bodegas, Productos, Eventos) y ejecuta el dominio FEFO puro.
Cumple Regla 02 (Clean Architecture / DDD), Regla 06 (Paridad Legacy) y 100% Decimal Anti-Float.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ResourceNotFoundError
from src.modules.catalog.infrastructure.models import Producto
from src.modules.events.infrastructure.models import Evento, EventoItem, EventoReceta
from src.modules.inventory.infrastructure.models import Bodega, ProductoBodega, RegistroStock
from src.modules.projection.domain.entities import (
    QTY_QUANT,
    ScheduledEventRequirement,
    SimulatedLot,
    SimulationResult,
    TransferRecommendation,
    UrgencyStatus,
    WarehouseStockCandidate,
)
from src.modules.projection.domain.fefo_engine import (
    calculate_transfer_recommendations,
    simulate_fefo_projection,
)
from src.modules.projection.infrastructure.models import DailyConsumptionRate
from src.modules.recipes.infrastructure.models import RecetaIngrediente

logger = logging.getLogger("oppytec.projection.engine")

ZERO_DEC = Decimal("0.0000")


class ProjectionEngine:
    """
    Servicio de aplicación transaccional para calcular la curva proyectada de un producto
    y recomendar traspasos preventivos entre bodegas ante quiebres futuros.
    """

    async def calculate_product_curve(
        self,
        db: AsyncSession,
        producto_id: int,
        bodega_id: int | None = None,
        horizon_days: int = 30,
        include_events: bool = True,
        start_date: date | None = None,
    ) -> SimulationResult:
        """
        Calcula la curva de stock día a día para un producto en una bodega (o consolidado multi-bodega).
        1. Consulta existencias actuales y stock mínimo.
        2. Reconstruye lotes y vigencias desde Kardex / RegistroStock.
        3. Obtiene o calcula la tasa diaria de consumo de los últimos 30 días.
        4. Cruza eventos agendados y recetas gastronómicas (con fallback tolerante a fallos).
        5. Ejecuta la simulación matemática FEFO en la capa de dominio.
        """
        ref_date = start_date or date.today()

        # 1. Obtener producto y validar existencia
        prod_stmt = select(Producto).where(Producto.id == producto_id)
        prod_res = await db.execute(prod_stmt)
        producto = prod_res.scalar_one_or_none()
        if not producto:
            raise ResourceNotFoundError(
                f"Producto con id {producto_id} no encontrado en el tenant.",
                i18n_key="catalog:errors.product_not_found",
            )

        # 2. Obtener existencias actuales y stock mínimo
        stock_minimo = producto.stock_minimo or ZERO_DEC
        if bodega_id is not None:
            pb_stmt = select(ProductoBodega).where(
                ProductoBodega.producto_id == producto_id,
                ProductoBodega.bodega_id == bodega_id,
            )
            pb_res = await db.execute(pb_stmt)
            pb = pb_res.scalar_one_or_none()
            current_stock = pb.stock_actual if pb else ZERO_DEC
            if pb and pb.stock_minimo > ZERO_DEC:
                stock_minimo = pb.stock_minimo
        else:
            sum_stmt = select(
                func.coalesce(func.sum(ProductoBodega.stock_actual), ZERO_DEC)
            ).where(ProductoBodega.producto_id == producto_id)
            sum_res = await db.execute(sum_stmt)
            current_stock = Decimal(str(sum_res.scalar() or ZERO_DEC))

        current_stock = current_stock.quantize(QTY_QUANT, ROUND_HALF_UP)
        stock_minimo = stock_minimo.quantize(QTY_QUANT, ROUND_HALF_UP)

        # 3. Reconstruir lotes y vigencias desde RegistroStock (Kardex)
        initial_lots = await self._fetch_active_lots(
            db=db,
            producto_id=producto_id,
            bodega_id=bodega_id,
            current_stock=current_stock,
        )

        # 4. Obtener o calcular tasa de consumo promedio diario
        daily_rate = await self._get_or_calculate_daily_rate(
            db=db,
            producto_id=producto_id,
            bodega_id=bodega_id,
            ref_date=ref_date,
        )

        # 5. Obtener consumo por eventos agendados y recetas
        event_reqs: list[ScheduledEventRequirement] = []
        if include_events:
            event_reqs = await self._fetch_scheduled_events(
                db=db,
                producto_id=producto_id,
                bodega_id=bodega_id,
                start_date=ref_date,
                horizon_days=horizon_days,
            )

        # 6. Ejecutar simulación FEFO pura en dominio
        return simulate_fefo_projection(
            producto_id=producto_id,
            bodega_id=bodega_id,
            start_date=ref_date,
            horizon_days=horizon_days,
            initial_lots=initial_lots,
            daily_consumption_rate=daily_rate,
            events=event_reqs,
            stock_minimo=stock_minimo,
        )

    async def find_alternative_stock(
        self,
        db: AsyncSession,
        producto_id: int,
        bodega_id_quiebre: int,
        needed_qty: Decimal,
        date_needed: date,
    ) -> list[TransferRecommendation]:
        """
        Busca otras bodegas dentro del tenant que tengan existencias excedentes sobre su stock mínimo
        para recomendar un traspaso preventivo hacia la bodega en riesgo de quiebre.
        """
        stmt = (
            select(ProductoBodega, Bodega.nombre)
            .join(Bodega, Bodega.id == ProductoBodega.bodega_id)
            .where(
                ProductoBodega.producto_id == producto_id,
                ProductoBodega.bodega_id != bodega_id_quiebre,
                Bodega.deleted_at.is_(None),
            )
        )
        res = await db.execute(stmt)
        rows = res.all()

        candidates: list[WarehouseStockCandidate] = []
        for pb, bodega_nombre in rows:
            rate = await self._get_or_calculate_daily_rate(
                db=db,
                producto_id=producto_id,
                bodega_id=pb.bodega_id,
                ref_date=date.today(),
            )
            candidates.append(
                WarehouseStockCandidate(
                    bodega_id=pb.bodega_id,
                    bodega_nombre=bodega_nombre,
                    available_stock=pb.stock_actual,
                    stock_minimo=pb.stock_minimo,
                    daily_consumption_rate=rate,
                )
            )

        return calculate_transfer_recommendations(
            producto_id=producto_id,
            bodega_destino_id=bodega_id_quiebre,
            deficit_qty=needed_qty,
            candidate_bodegas=candidates,
            urgency=UrgencyStatus.CRITICAL,
        )

    async def calculate_consumption_rates(
        self,
        db: AsyncSession,
        producto_id: int,
        bodega_id: int | None = None,
        ref_date: date | None = None,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Analiza los movimientos de Kardex para calcular las tasas móviles a 7, 30 y 90 días.
        Retorna (rate_7d, rate_30d, rate_90d) con 4 decimales en Decimal.
        """
        return await _calculate_consumption_rates_impl(db, producto_id, bodega_id, ref_date)

    async def _fetch_active_lots(
        self,
        db: AsyncSession,
        producto_id: int,
        bodega_id: int | None,
        current_stock: Decimal,
    ) -> list[SimulatedLot]:
        """
        Reconstruye la distribución de lotes físicos desde los registros de Kardex.
        Si no hay lotes individuales registrados pero sí hay stock actual, se asigna como lote único sin caducidad.
        """
        if current_stock <= ZERO_DEC:
            return []

        lots_query = select(
            RegistroStock.lote_codigo,
            RegistroStock.fecha_vencimiento_lote,
            func.sum(RegistroStock.cantidad).label("total_qty"),
        ).where(
            RegistroStock.producto_id == producto_id,
            RegistroStock.fecha_vencimiento_lote.is_not(None),
        )
        if bodega_id is not None:
            lots_query = lots_query.where(RegistroStock.bodega_id == bodega_id)

        lots_query = lots_query.group_by(
            RegistroStock.lote_codigo,
            RegistroStock.fecha_vencimiento_lote,
        )

        res = await db.execute(lots_query)
        rows = res.all()

        active_lots: list[SimulatedLot] = []
        allocated_qty = ZERO_DEC

        for idx, row in enumerate(rows):
            lot_qty = Decimal(str(row.total_qty or ZERO_DEC)).quantize(QTY_QUANT, ROUND_HALF_UP)
            if lot_qty > ZERO_DEC:
                # Cap lot quantity to current_stock to avoid phantom overstock
                usable_qty = min(lot_qty, current_stock - allocated_qty)
                if usable_qty > ZERO_DEC:
                    allocated_qty += usable_qty
                    active_lots.append(
                        SimulatedLot(
                            lot_id=row.lote_codigo or f"lote_{idx + 1}",
                            quantity=usable_qty,
                            fecha_vencimiento=row.fecha_vencimiento_lote,
                        )
                    )

        # Si el stock actual supera los lotes individualizados con fecha, el remanente se asigna sin caducidad
        remanente = current_stock - allocated_qty
        if remanente > ZERO_DEC:
            active_lots.append(
                SimulatedLot(
                    lot_id="unassigned_stock",
                    quantity=remanente,
                    fecha_vencimiento=None,
                )
            )

        return active_lots

    async def _get_or_calculate_daily_rate(
        self,
        db: AsyncSession,
        producto_id: int,
        bodega_id: int | None,
        ref_date: date,
    ) -> Decimal:
        """Obtiene la tasa de consumo de DailyConsumptionRate o la calcula desde Kardex."""
        rate_stmt = select(DailyConsumptionRate).where(
            DailyConsumptionRate.producto_id == producto_id,
        )
        if bodega_id is not None:
            rate_stmt = rate_stmt.where(DailyConsumptionRate.bodega_id == bodega_id)
        else:
            rate_stmt = rate_stmt.where(DailyConsumptionRate.bodega_id.is_(None))

        rate_res = await db.execute(rate_stmt)
        record = rate_res.scalar_one_or_none()
        if record and record.rate_30d > ZERO_DEC:
            return record.rate_30d.quantize(QTY_QUANT, ROUND_HALF_UP)

        # Calcular dinámicamente desde Kardex para 30 días
        rate_7d, rate_30d, rate_90d = await _calculate_consumption_rates_impl(
            db, producto_id, bodega_id, ref_date
        )
        return rate_30d

    async def _fetch_scheduled_events(
        self,
        db: AsyncSession,
        producto_id: int,
        bodega_id: int | None,
        start_date: date,
        horizon_days: int,
    ) -> list[ScheduledEventRequirement]:
        """
        Busca eventos programados y recetas que consuman el producto dentro de la ventana de proyección.
        Diseñado con fallback tolerante para no romper la proyección si el módulo de eventos está vacío o deshabilitado.
        """
        end_date = start_date + timedelta(days=horizon_days)
        requirements: dict[tuple[str, str, date], Decimal] = {}

        try:
            # 1. Insumos directos de EventoItem
            item_stmt = (
                select(
                    Evento.id,
                    Evento.nombre,
                    Evento.fecha,
                    EventoItem.cantidad,
                )
                .join(EventoItem, EventoItem.evento_id == Evento.id)
                .where(
                    Evento.cancelado.is_(False),
                    Evento.ejecutado.is_(False),
                    Evento.fecha >= start_date,
                    Evento.fecha <= end_date,
                    EventoItem.producto_id == producto_id,
                )
            )
            if bodega_id is not None:
                item_stmt = item_stmt.where(EventoItem.bodega_id == bodega_id)

            item_res = await db.execute(item_stmt)
            for ev_id, ev_nombre, ev_fecha, ev_cantidad in item_res.all():
                key = (str(ev_id), ev_nombre, ev_fecha)
                qty = Decimal(str(ev_cantidad or ZERO_DEC)).quantize(QTY_QUANT, ROUND_HALF_UP)
                requirements[key] = requirements.get(key, ZERO_DEC) + qty

            # 2. Insumos derivados de Recetas gastronómicas (EventoReceta -> RecetaIngrediente)
            receta_stmt = (
                select(
                    Evento.id,
                    Evento.nombre,
                    Evento.fecha,
                    EventoReceta.porciones,
                    RecetaIngrediente.cantidad_receta,
                    RecetaIngrediente.porcentaje_merma,
                )
                .join(EventoReceta, EventoReceta.evento_id == Evento.id)
                .join(RecetaIngrediente, RecetaIngrediente.receta_id == EventoReceta.receta_id)
                .where(
                    Evento.cancelado.is_(False),
                    Evento.ejecutado.is_(False),
                    Evento.fecha >= start_date,
                    Evento.fecha <= end_date,
                    RecetaIngrediente.producto_id == producto_id,
                )
            )
            if bodega_id is not None:
                receta_stmt = receta_stmt.where(
                    (EventoReceta.bodega_id == bodega_id) | (EventoReceta.bodega_id.is_(None))
                )

            receta_res = await db.execute(receta_stmt)
            for ev_id, ev_nombre, ev_fecha, porciones, cant_receta, pct_merma in receta_res.all():
                key = (str(ev_id), ev_nombre, ev_fecha)
                p = Decimal(str(porciones or 1))
                c = Decimal(str(cant_receta or ZERO_DEC))
                m = Decimal(str(pct_merma or ZERO_DEC))
                # Factor de merma: cantidad_bruta = porciones * cantidad_neta * (1 + merma / 100)
                factor_merma = Decimal("1.0000") + (m / Decimal("100.0000"))
                total_receta_qty = (p * c * factor_merma).quantize(QTY_QUANT, ROUND_HALF_UP)
                requirements[key] = requirements.get(key, ZERO_DEC) + total_receta_qty

        except Exception as exc:
            logger.warning(
                "Fallback tolerante en consulta de eventos para producto_id=%s: %s",
                producto_id,
                exc,
            )

        return [
            ScheduledEventRequirement(
                event_id=ev_id,
                event_name=ev_nombre,
                event_date=ev_fecha,
                quantity=total_qty,
            )
            for (ev_id, ev_nombre, ev_fecha), total_qty in requirements.items()
            if total_qty > ZERO_DEC
        ]


async def _calculate_consumption_rates_impl(
    db: AsyncSession,
    producto_id: int,
    bodega_id: int | None = None,
    ref_date: date | None = None,
) -> tuple[Decimal, Decimal, Decimal]:
    """Cálculo auxiliar de tasas de consumo en ventanas de 7, 30 y 90 días desde Kardex."""
    today = ref_date or date.today()
    consumption_types = ["CONSUMO", "SALIDA", "VENTA", "MERMA", "PRODUCCION"]

    async def _rate_for_days(days: int) -> Decimal:
        start_w = today - timedelta(days=days)
        stmt = select(
            func.coalesce(func.sum(func.abs(RegistroStock.cantidad)), ZERO_DEC)
        ).where(
            RegistroStock.producto_id == producto_id,
            RegistroStock.fecha_recuento >= start_w,
            RegistroStock.fecha_recuento <= today,
            RegistroStock.tipo_movimiento.in_(consumption_types),
        )
        if bodega_id is not None:
            stmt = stmt.where(RegistroStock.bodega_id == bodega_id)

        res = await db.execute(stmt)
        total_consumed = Decimal(str(res.scalar() or ZERO_DEC))
        if total_consumed <= ZERO_DEC or days <= 0:
            return ZERO_DEC
        return (total_consumed / Decimal(str(days))).quantize(QTY_QUANT, ROUND_HALF_UP)

    rate_7d = await _rate_for_days(7)
    rate_30d = await _rate_for_days(30)
    rate_90d = await _rate_for_days(90)

    return rate_7d, rate_30d, rate_90d
