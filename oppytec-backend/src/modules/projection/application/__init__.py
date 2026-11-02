"""
oppytec-backend/src/modules/projection/application
Capa de Aplicación del Módulo de Proyección:
- `ProjectionEngine`: Cálculo de consumo histórico, cruce de eventos/recetas y simulación FEFO.
- `ProjectionSnapshotService`: Cache persistente de snapshots con bloqueo anti-concurrencia y paginación server-side.
"""
from __future__ import annotations

from src.modules.projection.application.projection_engine import ProjectionEngine
from src.modules.projection.application.snapshot_service import ProjectionSnapshotService

__all__ = [
    "ProjectionEngine",
    "ProjectionSnapshotService",
]
