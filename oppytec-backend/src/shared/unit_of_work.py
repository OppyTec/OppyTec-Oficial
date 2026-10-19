"""
oppytec-backend/src/shared/unit_of_work.py
Patrón Unit of Work asíncrono con soporte para transacciones atómicas y `SAVEPOINT` anidados.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction


class AbstractUnitOfWork(ABC):
    """Puerto abstracto de Unit of Work para coordinar transacciones de dominio."""

    async def __aenter__(self) -> AbstractUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    @abstractmethod
    async def commit(self) -> None:
        """Confirma los cambios pendientes de la unidad de trabajo."""

    @abstractmethod
    async def rollback(self) -> None:
        """Revierte todos los cambios no confirmados de la unidad de trabajo."""


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """Implementación SQLAlchemy 2.0 Async del patrón Unit of Work con soporte de `SAVEPOINT`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session: AsyncSession = session
        self.committed: bool = False
        self.rolled_back: bool = False

    async def commit(self) -> None:
        """Ejecuta `session.commit()` y marca el estado como confirmado."""
        await self.session.commit()
        self.committed = True

    async def rollback(self) -> None:
        """Ejecuta `session.rollback()` y marca el estado como revertido."""
        await self.session.rollback()
        self.rolled_back = True

    @asynccontextmanager
    async def savepoint(self) -> AsyncIterator[AsyncSessionTransaction]:
        """Crea un `SAVEPOINT` (`begin_nested()`) para aislar sub-operaciones recuperables."""
        async with self.session.begin_nested() as nested_tx:
            yield nested_tx
