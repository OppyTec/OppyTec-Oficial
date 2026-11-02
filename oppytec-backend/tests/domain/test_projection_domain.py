"""
Pruebas Unitarias de Dominio DDD para el Módulo de Proyección.
Verifica paridad matemática 1:1, anti-float estricto, ordenamiento FEFO y Value Objects inmutables.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import pytest

from src.modules.projection.domain import (
    QTY_QUANT,
    DaySimulationPoint,
    ProjectionHorizon,
    ScheduledEventRequirement,
    SimulatedLot,
    SimulationResult,
    TransferRecommendation,
    UrgencyStatus,
    WarehouseStockCandidate,
    calculate_transfer_recommendations,
    fefo_sort_lots,
    simulate_fefo_projection,
)


def test_urgency_status_enum_and_helpers() -> None:
    assert UrgencyStatus.NORMAL.value == "normal"
    assert UrgencyStatus.WARNING.value == "warning"
    assert UrgencyStatus.CRITICAL.value == "critical"

    assert UrgencyStatus.NORMAL.is_normal
    assert not UrgencyStatus.NORMAL.is_warning
    assert UrgencyStatus.WARNING.is_warning
    assert UrgencyStatus.CRITICAL.is_critical

    assert UrgencyStatus.CRITICAL.severity_rank > UrgencyStatus.WARNING.severity_rank
    assert UrgencyStatus.WARNING.severity_rank > UrgencyStatus.NORMAL.severity_rank


def test_projection_horizon_enum() -> None:
    assert ProjectionHorizon.DAYS_7.value == 7
    assert ProjectionHorizon.DAYS_15.value == 15
    assert ProjectionHorizon.DAYS_30.value == 30
    assert ProjectionHorizon.DAYS_60.value == 60
    assert ProjectionHorizon.DAYS_90.value == 90

    assert ProjectionHorizon.from_int(30) == ProjectionHorizon.DAYS_30
    with pytest.raises(ValueError):
        ProjectionHorizon.from_int(45)


def test_day_simulation_point_immutability_and_quantization() -> None:
    today = date(2026, 11, 1)
    point = DaySimulationPoint(
        date=today,
        day_index=0,
        qty=Decimal("12.5000001"),
        status=UrgencyStatus.NORMAL,
        status_label="Normal",
        expiring_qty=Decimal("0"),
        event_deduction=Decimal("1.25"),
    )

    assert point.qty == Decimal("12.5000")
    assert point.event_deduction == Decimal("1.2500")

    # Inmutabilidad (frozen)
    with pytest.raises(Exception):
        point.qty = Decimal("10.0000")  # type: ignore

    # Serialización
    pdict = point.to_dict()
    assert pdict["date"] == "2026-11-01"
    assert pdict["qty"] == "12.5000"
    assert pdict["status"] == "normal"


def test_day_simulation_point_rejects_floats() -> None:
    today = date(2026, 11, 1)
    with pytest.raises(TypeError, match="Float IEEE-754 is strictly forbidden"):
        DaySimulationPoint(
            date=today,
            day_index=0,
            qty=12.5,  # float prohibido
            status=UrgencyStatus.NORMAL,
            status_label="Normal",
        )


def test_transfer_recommendation_invariants() -> None:
    # Origen y destino no pueden ser iguales
    with pytest.raises(ValueError, match="cannot equal"):
        TransferRecommendation(
            producto_id=1,
            bodega_origen_id=10,
            bodega_destino_id=10,
            cantidad_sugerida=Decimal("5.0000"),
            dias_cobertura_restante_origen=14,
            urgencia=UrgencyStatus.CRITICAL,
        )

    # Cantidad sugerida debe ser positiva
    with pytest.raises(ValueError, match="strictly positive"):
        TransferRecommendation(
            producto_id=1,
            bodega_origen_id=10,
            bodega_destino_id=20,
            cantidad_sugerida=Decimal("0.0000"),
            dias_cobertura_restante_origen=14,
            urgencia=UrgencyStatus.CRITICAL,
        )


def test_fefo_sort_lots() -> None:
    today = date(2026, 11, 1)
    lot_no_date = SimulatedLot(lot_id="L-NO-DATE", quantity=Decimal("10"))
    lot_near = SimulatedLot(lot_id="L-NEAR", quantity=Decimal("10"), fecha_vencimiento=today + timedelta(days=3))
    lot_far = SimulatedLot(lot_id="L-FAR", quantity=Decimal("10"), fecha_vencimiento=today + timedelta(days=10))

    sorted_lots = fefo_sort_lots([lot_no_date, lot_far, lot_near])

    # El más próximo debe ser primero, luego el más lejano, y sin fecha al final
    assert sorted_lots[0].lot_id == "L-NEAR"
    assert sorted_lots[1].lot_id == "L-FAR"
    assert sorted_lots[2].lot_id == "L-NO-DATE"


def test_fefo_engine_expiration_purge_tc_prj_01() -> None:
    """TC-PRJ-01: Lote caducado en día t reduce existencias a 0 en t y marca status = critical con label 'Sin stock (vencimiento)'."""
    today = date(2026, 11, 1)
    expiry_date = today + timedelta(days=5)

    lot = SimulatedLot(lot_id=101, quantity=Decimal("20.0000"), fecha_vencimiento=expiry_date)

    result = simulate_fefo_projection(
        producto_id=1,
        bodega_id=1,
        start_date=today,
        horizon_days=7,
        initial_lots=[lot],
        daily_consumption_rate=Decimal("0"),
        apply_daily_rate=False,
    )

    # Días 0 a 4 tienen stock 20
    for day in range(5):
        assert result.curve[day].qty == Decimal("20.0000")
        assert result.curve[day].status == UrgencyStatus.NORMAL or result.curve[day].status_label == "Próximo a vencer"

    # En el día 5 vence el lote
    day_5 = result.curve[5]
    assert day_5.qty == Decimal("0.0000")
    assert day_5.expiring_qty == Decimal("20.0000")
    assert day_5.status == UrgencyStatus.CRITICAL
    assert day_5.status_label == "Sin stock (vencimiento)"

    # Worst status global debe reflejar el quiebre por vencimiento
    assert result.worst_status == UrgencyStatus.CRITICAL
    assert "Sin stock (vencimiento)" in result.worst_status_label
    assert result.worst_day == 5
    assert result.depletion_date == expiry_date


def test_fefo_engine_scheduled_events_tc_prj_02() -> None:
    """TC-PRJ-02: Un evento programado en fecha f descuenta la cantidad reservada en el gráfico."""
    today = date(2026, 11, 1)
    event_date = today + timedelta(days=3)

    lot1 = SimulatedLot(lot_id=1, quantity=Decimal("15.0000"), fecha_vencimiento=today + timedelta(days=20))
    event = ScheduledEventRequirement(
        event_id="EVT-01",
        event_name="Banquete Matrimonio",
        event_date=event_date,
        quantity=Decimal("10.0000"),
    )

    result = simulate_fefo_projection(
        producto_id=1,
        bodega_id=1,
        start_date=today,
        horizon_days=5,
        initial_lots=[lot1],
        events=[event],
        apply_daily_rate=False,
    )

    # Día 0, 1, 2 tienen 15
    assert result.curve[0].qty == Decimal("15.0000")
    assert result.curve[1].qty == Decimal("15.0000")
    assert result.curve[2].qty == Decimal("15.0000")

    # Día 3 descuenta 10 y queda 5
    day_3 = result.curve[3]
    assert day_3.qty == Decimal("5.0000")
    assert day_3.event_deduction == Decimal("10.0000")
    assert len(day_3.events) == 1
    assert day_3.events[0]["name"] == "Banquete Matrimonio"


def test_fefo_engine_warning_under_stock_minimo() -> None:
    today = date(2026, 11, 1)
    lot = SimulatedLot(lot_id=1, quantity=Decimal("8.0000"))

    result = simulate_fefo_projection(
        producto_id=1,
        bodega_id=1,
        start_date=today,
        horizon_days=5,
        initial_lots=[lot],
        stock_minimo=Decimal("10.0000"),
        apply_daily_rate=False,
    )

    # Con stock 8 <= stock_minimo 10, debe marcar WARNING con "Bajo stock"
    assert result.curve[0].status == UrgencyStatus.WARNING
    assert result.curve[0].status_label == "Bajo stock"
    assert result.worst_status == UrgencyStatus.WARNING


def test_transfer_recommendations_calculation() -> None:
    candidates = [
        WarehouseStockCandidate(
            bodega_id=2,
            bodega_nombre="Bodega Central",
            available_stock=Decimal("50.0000"),
            stock_minimo=Decimal("10.0000"),
            daily_consumption_rate=Decimal("2.0000"),
        ),
        WarehouseStockCandidate(
            bodega_id=3,
            bodega_nombre="Bodega Bar",
            available_stock=Decimal("5.0000"),
            stock_minimo=Decimal("10.0000"),  # No tiene excedente
            daily_consumption_rate=Decimal("1.0000"),
        ),
    ]

    recommendations = calculate_transfer_recommendations(
        producto_id=1,
        bodega_destino_id=1,  # Cocina
        deficit_qty=Decimal("15.0000"),
        candidate_bodegas=candidates,
        urgency=UrgencyStatus.CRITICAL,
    )

    assert len(recommendations) == 1
    rec = recommendations[0]
    assert rec.bodega_origen_id == 2
    assert rec.bodega_destino_id == 1
    assert rec.cantidad_sugerida == Decimal("15.0000")
    # Bodega 2 tenía 50 - 15 = 35 remanente. Con consumo 2.0/día: 35 / 2 = 18 días de cobertura
    assert rec.dias_cobertura_restante_origen == 18
    assert rec.urgencia == UrgencyStatus.CRITICAL
