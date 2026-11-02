"""
oppytec-backend/src/modules/projection/domain/fefo_engine.py
Motor Algorítmico Puro de Simulación FEFO (First-Expired-First-Out) y Proyección Temporal.
100% Matemática Decimal sin dependencias de infraestructura ni efectos secundarios.
Cumple Regla 02 (DDD / Clean Architecture), Regla 06 (Paridad 1:1 con Legacy) y Anti-Float.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from src.modules.projection.domain.entities import (
    QTY_QUANT,
    DaySimulationPoint,
    ProjectionHorizon,
    ScheduledEventRequirement,
    SimulatedLot,
    SimulationResult,
    TransferRecommendation,
    UrgencyStatus,
    WarehouseStockCandidate,
)

ZERO = Decimal("0.0000")


@dataclass
class _WorkingLot:
    """Estructura interna mutable de trabajo para el rastreo del lote en la simulación."""

    lot_id: int | str
    qty: Decimal
    fecha_vencimiento: date | None


def fefo_sort_lots(lots: Iterable[SimulatedLot]) -> list[SimulatedLot]:
    """
    Ordena lotes bajo la política FEFO canónica:
    1. Lotes con fecha de caducidad más próxima primero.
    2. Lotes sin caducidad (fecha_vencimiento is None) al final.
    3. Desempate determinista por `lot_id` convertido a string.
    """
    return sorted(
        lots,
        key=lambda lot: (
            lot.fecha_vencimiento is None,
            lot.fecha_vencimiento or date.max,
            str(lot.lot_id),
        ),
    )


def simulate_fefo_projection(
    producto_id: int,
    bodega_id: int | None,
    start_date: date,
    horizon_days: int | ProjectionHorizon = ProjectionHorizon.DAYS_30,
    initial_lots: Sequence[SimulatedLot] = (),
    daily_consumption_rate: Decimal | str | int = Decimal("0"),
    events: Sequence[ScheduledEventRequirement] = (),
    stock_minimo: Decimal | str | int = Decimal("0"),
    expiry_alert_days: int = 7,
    apply_daily_rate: bool = True,
    apply_rate_on_day_zero: bool = False,
) -> SimulationResult:
    """
    Ejecuta la simulación temporal pura día a día desde `start_date` hasta `start_date + horizon_days`.

    Reglas de cálculo en cada día t (t = 0..horizon_days):
    1. Vencimiento FEFO: Todo lote con `fecha_vencimiento <= current_date` se da por mermado
       inmediatamente (`qty = 0`) y se registra en `expiring_lots`.
    2. Deducción de Consumo y Eventos:
       - Se identifican eventos agendados para la fecha exacta `current_date`.
       - Se suma la tasa promedio diaria si corresponde (`apply_daily_rate`).
       - Se deduce de los lotes remanentes consumiendo en orden FEFO estricto.
    3. Evaluación de Estados de Urgencia:
       - Saldo <= 0: `CRITICAL`. Si se agotó por caducidad: "Sin stock (vencimiento)", sino: "Sin stock".
       - Saldo <= stock_minimo: `WARNING` ("Bajo stock").
       - Saldo > stock_minimo pero lotes vencen dentro de `expiry_alert_days`: `WARNING` ("Próximo a vencer").
       - Saldo > stock_minimo y sin vencimientos cercanos: `NORMAL` ("Normal").
    """
    # Validaciones anti-float y conversión a Decimal
    if isinstance(horizon_days, ProjectionHorizon):
        effective_horizon = horizon_days.value
    else:
        effective_horizon = int(horizon_days)

    if effective_horizon <= 0:
        raise ValueError(f"horizon_days must be strictly positive, got {effective_horizon}")

    if type(daily_consumption_rate).__name__ == "float" or type(stock_minimo).__name__ == "float":
        raise TypeError("Float precision IEEE-754 is strictly forbidden; use Decimal, int or str")

    dec_daily_rate = Decimal(str(daily_consumption_rate)).quantize(QTY_QUANT, ROUND_HALF_UP)
    dec_stock_min = Decimal(str(stock_minimo)).quantize(QTY_QUANT, ROUND_HALF_UP)

    # Clonar estado de lotes a estructura mutable de trabajo
    working_lots: list[_WorkingLot] = [
        _WorkingLot(
            lot_id=lot.lot_id,
            qty=lot.quantity.quantize(QTY_QUANT, ROUND_HALF_UP),
            fecha_vencimiento=lot.fecha_vencimiento,
        )
        for lot in initial_lots
    ]

    curve: list[DaySimulationPoint] = []
    total_expired_cumulative = Decimal("0")

    worst_status = UrgencyStatus.NORMAL
    worst_label = "Normal"
    worst_day: int | None = None
    depletion_date: date | None = None

    for day_index in range(effective_horizon + 1):
        current_date = start_date + timedelta(days=day_index)

        # -------------------------------------------------------------
        # 1. Purgar lotes caducados a la fecha
        # -------------------------------------------------------------
        day_expiring_qty = Decimal("0")
        expiring_lots_today: list[dict[str, Any]] = []

        for lot in working_lots:
            if (
                lot.fecha_vencimiento is not None
                and lot.fecha_vencimiento <= current_date
                and lot.qty > Decimal("0")
            ):
                lost_qty = lot.qty
                day_expiring_qty += lost_qty
                total_expired_cumulative += lost_qty
                expiring_lots_today.append(
                    {
                        "lot_id": lot.lot_id,
                        "fecha_vencimiento": lot.fecha_vencimiento.isoformat(),
                        "cantidad": str(lost_qty),
                    }
                )
                lot.qty = Decimal("0")

        # -------------------------------------------------------------
        # 2. Descontar eventos y consumo promedio programado
        # -------------------------------------------------------------
        day_events: list[dict[str, Any]] = []
        event_deduction_today = Decimal("0")

        for ev in events:
            if ev.event_date == current_date:
                ev_qty = ev.quantity.quantize(QTY_QUANT, ROUND_HALF_UP)
                event_deduction_today += ev_qty
                day_events.append(
                    {
                        "event_id": ev.event_id,
                        "name": ev.event_name,
                        "qty": str(ev_qty),
                    }
                )

        rate_deduction_today = Decimal("0")
        if apply_daily_rate and (day_index > 0 or apply_rate_on_day_zero):
            rate_deduction_today = dec_daily_rate

        total_demand_today = event_deduction_today + rate_deduction_today

        # Deducción de lotes en orden FEFO
        if total_demand_today > Decimal("0"):
            rem_demand = total_demand_today
            active_lots = [l for l in working_lots if l.qty > Decimal("0")]
            # Orden FEFO canónico
            active_lots.sort(
                key=lambda l: (
                    l.fecha_vencimiento is None,
                    l.fecha_vencimiento or date.max,
                    str(l.lot_id),
                )
            )
            for lot in active_lots:
                if rem_demand <= Decimal("0"):
                    break
                take = min(lot.qty, rem_demand)
                lot.qty -= take
                rem_demand -= take

        # Saldo remanente físico del día
        current_balance = sum(
            (max(Decimal("0"), l.qty) for l in working_lots), Decimal("0")
        ).quantize(QTY_QUANT, ROUND_HALF_UP)

        # -------------------------------------------------------------
        # 3. Evaluar estado de urgencia del día t
        # -------------------------------------------------------------
        if current_balance <= Decimal("0"):
            status = UrgencyStatus.CRITICAL
            all_zero = all(l.qty <= Decimal("0") for l in working_lots)
            had_expiry = any(
                l.fecha_vencimiento and l.fecha_vencimiento <= current_date
                for l in initial_lots
                if l.quantity > Decimal("0")
            )
            if all_zero and had_expiry and total_expired_cumulative > Decimal("0"):
                status_label = "Sin stock (vencimiento)"
            else:
                status_label = "Sin stock"
        elif current_balance <= dec_stock_min:
            status = UrgencyStatus.WARNING
            status_label = "Bajo stock"
        else:
            # Revisar si hay lotes próximos a vencer dentro de la ventana de alerta
            has_expiring_soon = any(
                l.qty > Decimal("0")
                and l.fecha_vencimiento is not None
                and 0 <= (l.fecha_vencimiento - current_date).days <= expiry_alert_days
                for l in working_lots
            )
            if has_expiring_soon:
                status = UrgencyStatus.WARNING
                status_label = "Próximo a vencer"
            else:
                status = UrgencyStatus.NORMAL
                status_label = "Normal"

        point = DaySimulationPoint(
            date=current_date,
            day_index=day_index,
            qty=current_balance,
            status=status,
            status_label=status_label,
            expiring_qty=day_expiring_qty.quantize(QTY_QUANT, ROUND_HALF_UP),
            event_deduction=event_deduction_today.quantize(QTY_QUANT, ROUND_HALF_UP),
            events=day_events,
            expiring_lots=expiring_lots_today,
        )
        curve.append(point)

        # Actualizar peor estado de la serie
        if status == UrgencyStatus.CRITICAL and worst_status != UrgencyStatus.CRITICAL:
            worst_status = UrgencyStatus.CRITICAL
            worst_label = status_label
            worst_day = day_index
            if depletion_date is None:
                depletion_date = current_date
        elif status == UrgencyStatus.WARNING and worst_status == UrgencyStatus.NORMAL:
            worst_status = UrgencyStatus.WARNING
            worst_label = status_label
            worst_day = day_index

    # Enriquecer peor label con el día relativo si no ocurrió en t=0 (paridad Legacy)
    final_worst_label = worst_label
    if worst_status != UrgencyStatus.NORMAL and worst_day is not None and worst_day > 0:
        final_worst_label = f"{worst_label} (día {worst_day})"

    current_stock = curve[0].qty if curve else Decimal("0")
    projected_stock = curve[-1].qty if curve else Decimal("0")

    return SimulationResult(
        producto_id=producto_id,
        bodega_id=bodega_id,
        horizon_days=effective_horizon,
        current_stock=current_stock,
        projected_stock=projected_stock,
        depletion_date=depletion_date,
        worst_status=worst_status,
        worst_status_label=final_worst_label,
        worst_day=worst_day,
        daily_consumption_rate=dec_daily_rate,
        curve=curve,
    )


def calculate_transfer_recommendations(
    producto_id: int,
    bodega_destino_id: int,
    deficit_qty: Decimal | str | int,
    candidate_bodegas: Sequence[WarehouseStockCandidate],
    urgency: UrgencyStatus = UrgencyStatus.CRITICAL,
) -> list[TransferRecommendation]:
    """
    Calcula recomendaciones estructuradas de traspaso preventivo desde bodegas con excedente.
    Respeta el stock mínimo de la bodega de origen y proyecta la cobertura restante.
    """
    if type(deficit_qty).__name__ == "float":
        raise TypeError("Float precision IEEE-754 is forbidden for deficit_qty; use Decimal, int or str")

    dec_deficit = Decimal(str(deficit_qty)).quantize(QTY_QUANT, ROUND_HALF_UP)
    if dec_deficit <= Decimal("0"):
        return []

    recommendations: list[TransferRecommendation] = []
    rem_to_cover = dec_deficit

    for candidate in candidate_bodegas:
        if candidate.bodega_id == bodega_destino_id:
            continue
        if rem_to_cover <= Decimal("0"):
            break

        # Excedente transferible respetando el stock mínimo de origen
        surplus = candidate.available_stock - candidate.stock_minimo
        if surplus <= Decimal("0"):
            continue

        transfer_qty = min(surplus, rem_to_cover).quantize(QTY_QUANT, ROUND_HALF_UP)
        rem_to_cover -= transfer_qty

        # Días de cobertura remanente en la bodega origen tras el traspaso
        remaining_origin_stock = candidate.available_stock - transfer_qty
        if candidate.daily_consumption_rate > Decimal("0"):
            coverage_days = int(
                (remaining_origin_stock / candidate.daily_consumption_rate).to_integral_value(
                    ROUND_HALF_UP
                )
            )
        else:
            coverage_days = 999 if remaining_origin_stock > Decimal("0") else 0

        recommendations.append(
            TransferRecommendation(
                producto_id=producto_id,
                bodega_origen_id=candidate.bodega_id,
                bodega_destino_id=bodega_destino_id,
                cantidad_sugerida=transfer_qty,
                dias_cobertura_restante_origen=coverage_days,
                urgencia=urgency,
            )
        )

    return recommendations
