"""
oppytec-backend/src/modules/projection/infrastructure/models.py
Modelos SQLAlchemy 2.0 Async de Proyección (`TenantBase`, `AuditTimestampsMixin`):
- `ProjectionSnapshot`: Snapshot persistente de la simulación de stock por producto, bodega y horizonte.
- `DailyConsumptionRate`: Tasa histórica móvil de consumo diario (7, 30, 90 días) para simulación FEFO.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.modules.catalog.infrastructure.models import Producto
from src.modules.inventory.infrastructure.models import Bodega
from src.shared.models_base import (
    AuditTimestampsMixin,
    JSONDictType,
    TenantBase,
)


class ProjectionSnapshot(TenantBase, AuditTimestampsMixin):
    """
    Snapshot persistente del estado de proyección de demanda y simulación FEFO por producto y bodega.
    Almacena la curva día a día en JSONB para lecturas ultrarrápidas (< 25ms) en el frontend.
    """

    __tablename__ = "projection_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "producto_id",
            "bodega_id",
            "horizon_days",
            name="uq_proj_snapshots_prod_bod_horiz",
        ),
        Index("idx_proj_snapshots_lookup", "bodega_id", "horizon_days", "worst_status"),
        Index("idx_proj_snapshots_prod", "producto_id", "horizon_days"),
        Index("idx_proj_snapshots_calc", "calculated_at", "is_stale"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("productos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bodega_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("bodegas.id", ondelete="CASCADE"),
        default=None,
        nullable=True,
        index=True,
    )
    horizon_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False,
    )
    current_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    projected_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    depletion_date: Mapped[date | None] = mapped_column(
        Date,
        default=None,
        nullable=True,
    )
    worst_status: Mapped[str] = mapped_column(
        String(20),
        default="NORMAL",
        nullable=False,
    )
    worst_status_label: Mapped[str] = mapped_column(
        String(64),
        default="Normal",
        nullable=False,
    )
    worst_day: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )
    daily_consumption_rate: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    projection_curve: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONDictType,
        default=list,
        nullable=False,
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    is_stale: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    metadata_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONDictType,
        default=None,
        nullable=True,
    )

    # Relaciones ORM
    producto: Mapped[Producto] = relationship("Producto", foreign_keys=[producto_id])
    bodega: Mapped[Bodega | None] = relationship("Bodega", foreign_keys=[bodega_id])


class DailyConsumptionRate(TenantBase, AuditTimestampsMixin):
    """
    Tasa histórica promedio de consumo diario móvil calculada a partir de los movimientos
    de Kardex (`registro_stock`) para diferentes ventanas temporales (7, 30 y 90 días).
    """

    __tablename__ = "daily_consumption_rates"
    __table_args__ = (
        UniqueConstraint(
            "producto_id",
            "bodega_id",
            name="uq_daily_consumption_rates_prod_bod",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("productos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bodega_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("bodegas.id", ondelete="CASCADE"),
        default=None,
        nullable=True,
        index=True,
    )
    rate_7d: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    rate_30d: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    rate_90d: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    last_calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    # Relaciones ORM
    producto: Mapped[Producto] = relationship("Producto", foreign_keys=[producto_id])
    bodega: Mapped[Bodega | None] = relationship("Bodega", foreign_keys=[bodega_id])
