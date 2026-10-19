"""
oppytec-backend/src/modules/analytics/infrastructure/models.py
Modelos SQLAlchemy 2.0 de Analítica Ejecutiva y Financiera (`TenantBase`):
- `KpiSnapshot`, `FinancialProjection` (100% precisión `Decimal`, prohibido `float`).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models_base import AuditTimestampsMixin, TenantBase


class KpiSnapshot(TenantBase, AuditTimestampsMixin):
    """Instantánea diaria/mensual de indicadores operativos y food cost (`Decimal`)."""

    __tablename__ = "kpi_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    periodo_codigo: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    fecha_corte: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ventas_totales: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    costo_ventas: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    mermas_totales: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    food_cost_porcentaje: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        default=Decimal("0.00"),
        nullable=False,
    )


class FinancialProjection(TenantBase, AuditTimestampsMixin):
    """Proyección financiera de ingresos, costos y flujo de caja en `Decimal(14, 2)`."""

    __tablename__ = "financial_projections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    horizonte_meses: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    moneda: Mapped[str] = mapped_column(String(10), default="CLP", nullable=False)
    ingresos_proyectados: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    egresos_proyectados: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    margen_neto_proyectado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
