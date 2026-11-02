"""
oppytec-backend/src/modules/events/presentation/__init__.py
Capa de Presentación del Módulo de Eventos (FastAPI Routers y Schemas Pydantic v2).
"""
from __future__ import annotations

from src.modules.events.presentation.schemas import (
    EventFaltanteItemOut,
    EventFaltantesResponse,
    EventoCancelRequest,
    EventoComboIn,
    EventoComboOut,
    EventoConsumoKardexOut,
    EventoCreate,
    EventoDetailResponse,
    EventoItemIn,
    EventoItemOut,
    EventoListItemOut,
    EventoOut,
    EventoRecetaIn,
    EventoRecetaOut,
    EventoResponse,
    EventoTrabajadorIn,
    EventoTrabajadorOut,
    EventoUpdate,
    SalonCreate,
    SalonOut,
    SalonResponse,
    SalonUpdate,
)

__all__ = [
    "EventFaltanteItemOut",
    "EventFaltantesResponse",
    "EventoCancelRequest",
    "EventoComboIn",
    "EventoComboOut",
    "EventoConsumoKardexOut",
    "EventoCreate",
    "EventoDetailResponse",
    "EventoItemIn",
    "EventoItemOut",
    "EventoListItemOut",
    "EventoOut",
    "EventoRecetaIn",
    "EventoRecetaOut",
    "EventoResponse",
    "EventoTrabajadorIn",
    "EventoTrabajadorOut",
    "EventoUpdate",
    "SalonCreate",
    "SalonOut",
    "SalonResponse",
    "SalonUpdate",
]
