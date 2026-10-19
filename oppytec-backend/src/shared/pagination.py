"""
oppytec-backend/src/shared/pagination.py
Esquemas genéricos tipados de paginación en Pydantic v2 (`extra="forbid"`).
"""
from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field


class PaginationParams(BaseModel):  # type: ignore[explicit-any]
    """Parámetros de entrada validados para consultas paginadas."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    page: int = Field(default=1, ge=1, le=100_000)
    page_size: int = Field(default=20, ge=1, le=200)

    @property
    def offset(self) -> int:
        """Calcula el desplazamiento SQL (`OFFSET`) a partir de `page` y `page_size`."""
        return (self.page - 1) * self.page_size


class PaginatedResponse[ItemT](BaseModel):  # type: ignore[explicit-any]
    """Sobre de respuesta paginada tipada genéricamente (`PaginatedResponse[T]`)."""

    model_config = ConfigDict(extra="forbid")

    items: list[ItemT]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)
    total_pages: int = Field(ge=0)

    @classmethod
    def create(
        cls,
        items: list[ItemT],
        total: int,
        params: PaginationParams,
    ) -> PaginatedResponse[ItemT]:
        """Construye un `PaginatedResponse[T]` calculando `total_pages` de forma determinista."""
        safe_total = max(0, total)
        pages = math.ceil(safe_total / params.page_size) if safe_total > 0 else 0
        return cls(
            items=items,
            total=safe_total,
            page=params.page,
            page_size=params.page_size,
            total_pages=pages,
        )
