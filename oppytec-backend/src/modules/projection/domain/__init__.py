"""
oppytec-backend/src/modules/projection/domain
Capa de Dominio Pura del Módulo de Proyección (Clean Architecture / DDD).
Sin dependencias de infraestructura ni base de datos.
"""
from __future__ import annotations

from src.modules.projection.domain.entities import (
    QTY_QUANT,
    ZERO_QTY,
    DaySimulationPoint,
    ProjectionHorizon,
    ScheduledEventRequirement,
    SimulatedLot,
    SimulationResult,
    TransferRecommendation,
    UrgencyStatus,
    WarehouseStockCandidate,
)
from src.modules.projection.domain.fefo_engine import (
    calculate_transfer_recommendations,
    fefo_sort_lots,
    simulate_fefo_projection,
)

__all__ = [
    "QTY_QUANT",
    "ZERO_QTY",
    "DaySimulationPoint",
    "ProjectionHorizon",
    "ScheduledEventRequirement",
    "SimulatedLot",
    "SimulationResult",
    "TransferRecommendation",
    "UrgencyStatus",
    "WarehouseStockCandidate",
    "calculate_transfer_recommendations",
    "fefo_sort_lots",
    "simulate_fefo_projection",
]
