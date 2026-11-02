"""
oppytec-backend/src/modules/projection/infrastructure/__init__.py
Capa de infraestructura del Módulo de Proyección.
"""
from __future__ import annotations

from src.modules.projection.infrastructure.models import (
    DailyConsumptionRate,
    ProjectionSnapshot,
)

__all__ = [
    "DailyConsumptionRate",
    "ProjectionSnapshot",
]
