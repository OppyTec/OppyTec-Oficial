"""
oppytec-backend/src/modules/events/infrastructure/models.py
Modelos SQLAlchemy 2.0 Multi-Tenant para el Módulo de Eventos, Salones y Consumo de Inventario (`TenantBase`):
- `Salon`, `SalonAreaOperativa`
- `Evento`
- `EventoItem` (Insumos directos de bodega)
- `EventoReceta` (Escandallos gastronómicos)
- `EventoCombo` (Combos y packs comerciales)
- `EventoTrabajador` (Brigada y personal de servicio)
- `EventoConsumoKardex` (Trazabilidad estricta de consumo en registro_stock)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from src.shared.models_base import (
    AuditTimestampsMixin,
    JSONDictType,
    TenantBase,
    TranslatableI18nMixin,
)
from src.shared.soft_delete_mixin import SoftDeleteMixin


class Salon(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """
    Espacio físico o salón de eventos disponible para reservas y banquetes.
    Almacena aranceles con precisión monetaria (`Decimal(14, 2)`) e IVA parametrizable.
    """

    __tablename__ = "salones"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('limpio', 'en_uso', 'mantenimiento', 'sucio', 'activo')",
            name="ck_salones_estado_valido",
        ),
        Index("ix_salones_nombre", "nombre"),
        Index("ix_salones_estado", "estado"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    capacidad_personas: Mapped[int | None] = mapped_column(Integer, default=50, nullable=True)
    precio_neto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    iva_porcentaje: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("19.00"),
        nullable=False,
    )
    precio_bruto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    notas: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)
    estado: Mapped[str] = mapped_column(String(32), default="limpio", nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#ec4899", nullable=False)
    areas_operativas_ids: Mapped[list[int] | None] = mapped_column(
        JSONDictType,
        default=list,
        nullable=True,
    )

    # Relaciones
    eventos: Mapped[list[Evento]] = relationship(
        "Evento",
        back_populates="salon",
        cascade="all, delete-orphan",
    )
    areas_vinculadas: Mapped[list[SalonAreaOperativa]] = relationship(
        "SalonAreaOperativa",
        back_populates="salon",
        cascade="all, delete-orphan",
    )


class SalonAreaOperativa(TenantBase):
    """
    Tabla asociativa física para vincular Salones con Áreas Operativas de soporte (Cocina, Bar, etc.).
    """

    __tablename__ = "salon_areas_operativas"

    salon_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("salones.id", ondelete="CASCADE"),
        primary_key=True,
    )
    area_operativa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("areas_operativas.id", ondelete="CASCADE"),
        primary_key=True,
    )

    salon: Mapped[Salon] = relationship("Salon", back_populates="areas_vinculadas")


class Evento(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """
    Agregado Raíz de Eventos y Banquetes.
    Coordina asignación de insumos, recetas, combos, brigada de personal
    y auditoría de ejecución en Kardex.
    """

    __tablename__ = "eventos"
    __table_args__ = (
        Index("ix_eventos_fecha_salon", "fecha", "salon_id"),
        Index("ix_eventos_estado_ejec_canc", "estado", "ejecutado", "cancelado"),
        CheckConstraint(
            "estado IN ('AGENDADO', 'CONFIRMADO', 'EN_CURSO', 'EJECUTADO', 'CANCELADO')",
            name="ck_eventos_estado_valido",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    titular: Mapped[str | None] = mapped_column(String(200), default=None, nullable=True)
    tipo_evento: Mapped[str] = mapped_column(String(64), default="GENERAL", nullable=False)
    salon_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("salones.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
        index=True,
    )
    lugar: Mapped[str | None] = mapped_column(String(300), default=None, nullable=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hora_inicio: Mapped[time | None] = mapped_column(Time, default=None, nullable=True)
    hora_fin: Mapped[time | None] = mapped_column(Time, default=None, nullable=True)
    cantidad_personas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estado: Mapped[str] = mapped_column(String(32), default="AGENDADO", nullable=False, index=True)
    color: Mapped[str] = mapped_column(String(20), default="#ec4899", nullable=False)

    ejecutado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    cancelado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    ejecutado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )
    cancelado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )
    motivo_cancelacion: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)

    encargado_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    valor_publico: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    notas: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)
    nota_personal: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)
    nota_equipo: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)
    nota_visible: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)

    # Synonyms y propiedades para retrocompatibilidad total
    nombre_evento = synonym("nombre")
    cantidad_invitados = synonym("cantidad_personas")
    asistentes_confirmados = synonym("cantidad_personas")
    presupuesto_acordado = synonym("valor_publico")

    def __init__(self, **kwargs: Any) -> None:
        # Soporte para inicialización mediante fecha_inicio y fecha_fin (datetimes)
        if "fecha_inicio" in kwargs:
            fi = kwargs.pop("fecha_inicio")
            if isinstance(fi, datetime):
                kwargs.setdefault("fecha", fi.date())
                kwargs.setdefault("hora_inicio", fi.time())
        if "fecha_fin" in kwargs:
            ff = kwargs.pop("fecha_fin")
            if isinstance(ff, datetime):
                kwargs.setdefault("hora_fin", ff.time())
        super().__init__(**kwargs)

    @property
    def fecha_inicio(self) -> datetime | None:
        """Propiedad virtual que combina fecha y hora_inicio."""
        if self.fecha is None:
            return None
        t = self.hora_inicio or time.min
        return datetime.combine(self.fecha, t)

    @property
    def fecha_fin(self) -> datetime | None:
        """Propiedad virtual que combina fecha y hora_fin."""
        if self.fecha is None:
            return None
        t = self.hora_fin or time.max
        return datetime.combine(self.fecha, t)

    # Relaciones del Agregado Raíz
    salon: Mapped[Salon | None] = relationship("Salon", back_populates="eventos")
    items: Mapped[list[EventoItem]] = relationship(
        "EventoItem",
        back_populates="evento",
        cascade="all, delete-orphan",
    )
    recetas: Mapped[list[EventoReceta]] = relationship(
        "EventoReceta",
        back_populates="evento",
        cascade="all, delete-orphan",
    )
    combos: Mapped[list[EventoCombo]] = relationship(
        "EventoCombo",
        back_populates="evento",
        cascade="all, delete-orphan",
    )
    trabajadores: Mapped[list[EventoTrabajador]] = relationship(
        "EventoTrabajador",
        back_populates="evento",
        cascade="all, delete-orphan",
    )
    consumos_kardex: Mapped[list[EventoConsumoKardex]] = relationship(
        "EventoConsumoKardex",
        back_populates="evento",
        cascade="all, delete-orphan",
    )


class EventoItem(TenantBase, AuditTimestampsMixin):
    """
    Insumo o materia prima directa asignada desde una bodega específica para el evento.
    """

    __tablename__ = "evento_items"
    __table_args__ = (
        UniqueConstraint("evento_id", "producto_id", "bodega_id", name="uq_evento_items_prod_bodega"),
        CheckConstraint("cantidad > 0", name="ck_evento_items_cantidad_positiva"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    evento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("eventos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("productos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bodega_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )
    costo_unitario_estimado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    notas: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)

    evento: Mapped[Evento] = relationship("Evento", back_populates="items")


class EventoReceta(TenantBase, AuditTimestampsMixin):
    """
    Ficha técnica gastronómica o receta asignada al evento (menú, cóctel, postre).
    """

    __tablename__ = "evento_recetas"
    __table_args__ = (
        CheckConstraint("porciones > 0", name="ck_evento_recetas_porciones_positivas"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    evento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("eventos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receta_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("recetas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bodega_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        default=None,
        nullable=True,
        index=True,
    )
    porciones: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    notas: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)

    evento: Mapped[Evento] = relationship("Evento", back_populates="recetas")


class EventoCombo(TenantBase, AuditTimestampsMixin):
    """
    Combo gastronómico o pack comercial asignado al evento.
    """

    __tablename__ = "evento_combos"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_evento_combos_cantidad_positiva"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    evento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("eventos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    combo_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("combos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bodega_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        default=None,
        nullable=True,
        index=True,
    )
    cantidad: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    notas: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)

    evento: Mapped[Evento] = relationship("Evento", back_populates="combos")


class EventoTrabajador(TenantBase, AuditTimestampsMixin):
    """
    Asignación de personal operativo / brigada de sala y cocina para el evento.
    """

    __tablename__ = "evento_trabajadores"
    __table_args__ = (
        UniqueConstraint("evento_id", "usuario_id", name="uq_evento_trabajadores_evento_usuario"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    evento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("eventos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    rol_evento: Mapped[str | None] = mapped_column(
        String(100),
        default=None,
        nullable=True,
    )
    horas_asignadas: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    evento: Mapped[Evento] = relationship("Evento", back_populates="trabajadores")


class EventoConsumoKardex(TenantBase, AuditTimestampsMixin):
    """
    Trazabilidad inmutable de consumo en Kardex (`registro_stock`) generado tras ejecutar el evento.
    """

    __tablename__ = "evento_consumos_kardex"
    __table_args__ = (
        Index("ix_evento_consumos_evento", "evento_id"),
        Index("ix_evento_consumos_kardex_mov", "kardex_movement_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    evento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("eventos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kardex_movement_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("registro_stock.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("productos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bodega_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cantidad_consumida: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )
    costo_unitario_ppp: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    origen_tipo: Mapped[str] = mapped_column(
        String(32),
        default="DIRECTO",
        nullable=False,
    )
    origen_id: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )

    evento: Mapped[Evento] = relationship("Evento", back_populates="consumos_kardex")


__all__ = [
    "Evento",
    "EventoCombo",
    "EventoConsumoKardex",
    "EventoItem",
    "EventoReceta",
    "EventoTrabajador",
    "Salon",
    "SalonAreaOperativa",
]
