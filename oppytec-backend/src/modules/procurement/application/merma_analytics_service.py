"""
oppytec-backend/src/modules/procurement/application/merma_analytics_service.py
Re-exportación canónica de `MermaAnalyticsService` para compatibilidad de importación transversal.
"""
from src.modules.inventory.application.merma_analytics_service import (
    MermaAnalyticsService,
)

__all__ = ["MermaAnalyticsService"]
