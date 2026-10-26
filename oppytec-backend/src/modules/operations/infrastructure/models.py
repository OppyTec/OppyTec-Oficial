"""
oppytec-backend/src/modules/operations/infrastructure/models.py
Modelos SQLAlchemy 2.0 de Operaciones Gastronómicas, Hoteleras y Consumo (`TenantBase`):
- `Venta`, `VentaReceta`
- `Salon`, `Evento`
- `BuffetTemplate`, `BuffetSession`, `BuffetStation`, `BuffetSessionItem`
- `TurnoHorario`, `NotaPersonal`, `NotaEquipo`, `Tarea`
- `ConsumptionRecord`, `ConsumptionRecordItem`, `ConsumptionTemplate`
- `VoiceStation`, `VoiceOrderLog`.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models_base import (
    AuditTimestampsMixin,
    JSONDictType,
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
    descripcion: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)
    comensales_estimados: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    estaciones_json: Mapped[Any] = mapped_column(JSONDictType, default=list, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


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
    area_operativa_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("areas_operativas.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
        index=True,
    )
    bodega_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
        index=True,
    )
    usuario_creador_id: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
        index=True,
    )
    tipo_servicio: Mapped[str] = mapped_column(
        String(64),
        default="DESAYUNO",
        nullable=False,
    )
    estado: Mapped[str] = mapped_column(String(32), default="ACTIVA", nullable=False)
    comensales_reales: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pax_comensales: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    costo_total_sesion: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    costo_total_montaje: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    valor_sobrante_reutilizable: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    costo_neto_pax: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    stations: Mapped[list[BuffetStation]] = relationship(
        "BuffetStation",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    items: Mapped[list[BuffetSessionItem]] = relationship(
        "BuffetSessionItem",
        back_populates="session",
        cascade="all, delete-orphan",
    )


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
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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

    session: Mapped[BuffetSession] = relationship("BuffetSession", back_populates="stations")
    items: Mapped[list[BuffetSessionItem]] = relationship(
        "BuffetSessionItem",
        back_populates="station",
        cascade="all, delete-orphan",
    )

    @property
    def nombre_estacion(self) -> str:
        return self.nombre


class BuffetSessionItem(TenantBase, AuditTimestampsMixin):
    """Detalle de consumo, merma y sobrante de ítems por estación en una sesión de Buffet."""

    __tablename__ = "buffet_session_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("buffet_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    station_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("buffet_stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_item: Mapped[str] = mapped_column(
        String(20),
        default="PRODUCTO",
        nullable=False,
        index=True,
    )  # PRODUCTO | RECETA
    item_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cantidad_montada: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    cantidad_sobrante: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    cantidad_merma: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    cantidad_neta_consumida: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    costo_unitario_ppp: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    costo_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    session: Mapped[BuffetSession] = relationship("BuffetSession", back_populates="items")
    station: Mapped[BuffetStation] = relationship("BuffetStation", back_populates="items")


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


# ==============================================================================
# Módulo de Consumo, Plantillas y Manos Libres (Fase 1 - PLAN_MAESTRO_CONSUMO)
# ==============================================================================


class ConsumptionRecord(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """
    Cabecera de transacción de consumo directo, personal o mermas (`consumption_records`).
    Permite registrar salidas sin venta comercial directa con trazabilidad biyectiva a Kardex.
    """

    __tablename__ = "consumption_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    codigo_folio: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    folio_ticket: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, index=True)
    area_operativa_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("areas_operativas.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
        index=True,
    )
    bodega_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
        index=True,
    )
    usuario_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tipo_origen: Mapped[str] = mapped_column(
        String(32),
        default="MANUAL_TERMINAL",
        nullable=False,
        index=True,
    )  # MANUAL_TERMINAL | MANOS_LIBRES_VOZ | BUFFET_LIQUIDACION | VENTA_POS
    costo_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    notas: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)

    items: Mapped[list[ConsumptionRecordItem]] = relationship(
        "ConsumptionRecordItem",
        back_populates="consumption_record",
        cascade="all, delete-orphan",
    )


class ConsumptionRecordItem(TenantBase, AuditTimestampsMixin):
    """
    Detalle de ítems descontados por transacción de consumo (`consumption_record_items`).
    Soporta desglose de productos individuales, recetas compuestas y combos.
    """

    __tablename__ = "consumption_record_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    consumption_record_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("consumption_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_item: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )  # PRODUCTO | RECETA | COMBO
    item_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unidad_medida: Mapped[str] = mapped_column(String(20), default="UN", nullable=False)
    costo_unitario_ppp: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    costo_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    lote_codigo: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True)
    fecha_vencimiento_lote: Mapped[date | None] = mapped_column(Date, default=None, nullable=True)
    kardex_movement_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("registro_stock.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
        index=True,
    )
    opciones_seleccionadas: Mapped[Any] = mapped_column(JSONDictType, default=None, nullable=True)

    consumption_record: Mapped[ConsumptionRecord] = relationship(
        "ConsumptionRecord",
        back_populates="items",
    )


class ConsumptionTemplate(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """
    Plantillas de consumo rápido para agilizar el despacho y turnos de cocina/barra (`consumption_templates`).
    Permite configuración de orden visual de ítems, visibilidad pública/privada y número de columnas.
    """

    __tablename__ = "consumption_templates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)
    usuario_creador_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    columnas_count: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    sort_mode: Mapped[str] = mapped_column(String(32), default="alpha_asc", nullable=False)
    product_ids: Mapped[Any] = mapped_column(JSONDictType, default=list, nullable=False)
    custom_product_order: Mapped[Any] = mapped_column(JSONDictType, default=None, nullable=True)


class VoiceStation(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """
    Estación de captura de voz (cocina, barra, pastelería) para órdenes manos libres (`voice_stations`).
    """

    __tablename__ = "voice_stations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    area_operativa_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("areas_operativas.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
        index=True,
    )
    nombre_estacion: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    voice_command: Mapped[str] = mapped_column(String(64), nullable=False)
    usuario_asignado_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    order_logs: Mapped[list[VoiceOrderLog]] = relationship(
        "VoiceOrderLog",
        back_populates="station",
        cascade="all, delete-orphan",
    )


class VoiceOrderLog(TenantBase, AuditTimestampsMixin):
    """
    Bitácora de transcripción fonética y procesamiento de intenciones por voz (`voice_order_logs`).
    """

    __tablename__ = "voice_order_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    station_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("voice_stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    texto_transcrito: Mapped[str] = mapped_column(Text, nullable=False)
    accion_detectada: Mapped[str] = mapped_column(
        String(32),
        default="CONSUMO",
        nullable=False,
        index=True,
    )  # CONSUMO | MERMA
    confianza_ia: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    items_interpretados_json: Mapped[Any] = mapped_column(JSONDictType, default=list, nullable=True)
    estado: Mapped[str] = mapped_column(
        String(32),
        default="PENDIENTE",
        nullable=False,
        index=True,
    )  # PENDIENTE | CONFIRMADO | RECHAZADO | EJECUTADO
    consumption_record_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("consumption_records.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
        index=True,
    )

    station: Mapped[VoiceStation] = relationship("VoiceStation", back_populates="order_logs")
    consumption_record: Mapped[ConsumptionRecord | None] = relationship("ConsumptionRecord")
