"""
oppytec-backend/src/modules/events/domain/repositories.py
Interfaces y contratos de persistencia para el Módulo de Eventos (Domain Driven Design).
Define las abstracciones desacopladas de SQLAlchemy para pruebas y servicios de aplicación.
"""
from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from src.modules.events.domain.entities import Evento, Salon


class SalonRepositoryProtocol(Protocol):
    """Contrato del repositorio para la gestión de Salones y Espacios Físicos."""

    async def get_by_id(self, salon_id: UUID) -> Salon | None: ...

    async def list_all(self, *, include_deleted: bool = False) -> list[Salon]: ...

    async def save(self, salon: Salon) -> Salon: ...

    async def delete(self, salon_id: UUID, soft: bool = True) -> bool: ...


class EventRepositoryProtocol(Protocol):
    """Contrato del repositorio para el Agregado Raíz Evento."""

    async def get_by_id(self, evento_id: UUID) -> Evento | None: ...

    async def list_by_date_range(
        self,
        fecha_desde: date,
        fecha_hasta: date,
        salon_id: UUID | None = None,
    ) -> list[Evento]: ...

    async def find_active_by_salon_and_date(
        self,
        salon_id: UUID,
        fecha: date,
    ) -> list[Evento]: ...

    async def save(self, evento: Evento) -> Evento: ...

    async def delete(self, evento_id: UUID, soft: bool = True) -> bool: ...


__all__ = [
    "EventRepositoryProtocol",
    "SalonRepositoryProtocol",
]
