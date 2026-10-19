"""
oppytec-backend/src/modules/operations/infrastructure/models.py
Modelos SQLAlchemy 2.0 de Operaciones Gastronómicas y Hoteleras (`TenantBase`):
- `Venta`, `VentaReceta`
- `Salon`, `Evento`
- `BuffetTemplate`, `BuffetSession`, `BuffetStation`
- `TurnoHorario`, `NotaPersonal`, `NotaEquipo`, `Tarea`.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models_base import (
    AuditTimestampsMixin,
    TenantBase,
    TranslatableI18nMixin,
)
from src.shared.soft_delete_mixin import SoftDeleteMixin


class Venta(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """Registro de venta / consumo operativo con montos en `Decimal(14, 2)`."""

    __tablename__ = "ventas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    folio_ticket: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    cajero_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    moneda: Mapped[str] = mapped_column(String(10), default="CLP", nullable=False)
    monto_total_bruto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    costo_total_insumos: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    canal_venta: Mapped[str] = mapped_column(String(32), default="SALON", nullable=False)


class VentaReceta(TenantBase, AuditTimestampsMixin):
    """Detalle de recetas o combos vendidos dentro de una `Venta` (`Decimal`)."""

    __tablename__ = "venta_recetas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    venta_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ventas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receta_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("recetas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    precio_unitario_bruto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)


class Salon(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Salón o espacio físico del restaurante/hotel para eventos y servicio."""

    __tablename__ = "salones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    capacidad_personas: Mapped[int] = mapped_column(Integer, default=50, nullable=False)


class Evento(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Banquete, matrimonio o evento corporativo programado en un `Salon`."""

    __tablename__ = "eventos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    salon_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("salones.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nombre_evento: Mapped[str] = mapped_column(String(180), nullable=False)
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    asistentes_confirmados: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    presupuesto_acordado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )


class BuffetTemplate(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Plantilla reutilizable de montaje de estaciones de Buffet."""

    __tablename__ = "buffet_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(140), nullable=False)
    comensales_estimados: Mapped[int] = mapped_column(Integer, default=100, nullable=False)


class BuffetSession(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """Sesión activa o cerrada de servicio de Buffet."""

    __tablename__ = "buffet_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("buffet_templates.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
    )
    comensales_reales: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    costo_total_sesion: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    estado: Mapped[str] = mapped_column(String(32), default="ACTIVA", nullable=False)


class BuffetStation(TenantBase, AuditTimestampsMixin, TranslatableI18nMixin):
    """Estación de reposición dentro de una `BuffetSession`."""

    __tablename__ = "buffet_stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("buffet_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    peso_inicial_kg: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    peso_sobrante_kg: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )


class TurnoHorario(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """Turno horario asignado a un colaborador del local."""

    __tablename__ = "turnos_horarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    inicio_turno: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fin_turno: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NotaPersonal(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """Nota privada del colaborador en su espacio de trabajo."""

    __tablename__ = "notas_personales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)


class NotaEquipo(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Bitácora de novedades compartida entre el equipo del turno."""

    __tablename__ = "notas_equipo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    autor_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)


class Tarea(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Tarea operativa o checklist de apertura/cierre de turno."""

    __tablename__ = "tareas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(180), nullable=False)
    asignado_a_user_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    completada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
