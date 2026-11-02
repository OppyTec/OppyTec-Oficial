"""
oppytec-backend/src/modules/events/presentation/schemas.py
Esquemas Pydantic V2 para el Módulo de Eventos, Salones y Consumo de Inventario.
Cumple estrictamente con la Regla de Oro Inviolable:
- Cero floats, precisión monetaria y cantidades con `Decimal`.
- Serialización compatible con Pydantic V2 (`ConfigDict(from_attributes=True)`).
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# SALONES SCHEMAS
# ============================================================================


class SalonCreate(BaseModel):
    """Payload para dar de alta un nuevo Salón o Espacio Físico."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=1, max_length=200, description="Nombre del salón")
    capacidad_personas: int | None = Field(default=50, ge=1, description="Aforo máximo de personas")
    precio_neto: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), description="Arancel neto")
    iva_porcentaje: Decimal = Field(
        default=Decimal("19.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Porcentaje de IVA aplicable",
    )
    precio_bruto: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        description="Precio bruto con IVA (se calcula automáticamente si se omite)",
    )
    notas: str | None = Field(default=None, description="Observaciones o descripción técnica")
    estado: str = Field(
        default="limpio",
        pattern=r"^(limpio|en_uso|mantenimiento|sucio|activo)$",
        description="Estado operativo/higiénico del salón",
    )
    color: str = Field(default="#ec4899", max_length=20, description="Color identificador hexadecimal")
    areas_operativas_ids: list[int] = Field(
        default_factory=list,
        description="IDs de áreas operativas vinculadas de soporte",
    )


class SalonUpdate(BaseModel):
    """Payload para actualizar un Salón existente."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    capacidad_personas: int | None = Field(default=None, ge=1)
    precio_neto: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    iva_porcentaje: Decimal | None = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    precio_bruto: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    notas: str | None = None
    estado: str | None = Field(default=None, pattern=r"^(limpio|en_uso|mantenimiento|sucio|activo)$")
    color: str | None = Field(default=None, max_length=20)
    areas_operativas_ids: list[int] | None = None


class SalonOut(BaseModel):
    """Representación pública y normalizada de un Salón."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nombre: str
    capacidad_personas: int | None = 50
    precio_neto: Decimal = Decimal("0.00")
    iva_porcentaje: Decimal = Decimal("19.00")
    precio_bruto: Decimal = Decimal("0.00")
    notas: str | None = None
    estado: str = "limpio"
    color: str = "#ec4899"
    areas_operativas_ids: list[int] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


SalonResponse = SalonOut


# ============================================================================
# EVENTO SUB-ENTIDADES SCHEMAS (Items, Recetas, Combos, Trabajadores)
# ============================================================================


class EventoItemIn(BaseModel):
    """Insumo o materia prima directa asignada a un evento desde una bodega."""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    producto_id: int = Field(..., ge=1, description="ID del producto de catálogo")
    bodega_id: int = Field(..., ge=1, description="ID de la bodega origen de despacho")
    cantidad: Decimal = Field(..., gt=Decimal("0.0000"), description="Cantidad solicitada")
    costo_unitario_estimado: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Costo unitario referencial",
    )
    notas: str | None = None


class EventoItemOut(BaseModel):
    """Insumo directo asignado reflejado en respuestas."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    evento_id: UUID
    producto_id: int
    bodega_id: int
    cantidad: Decimal
    costo_unitario_estimado: Decimal = Decimal("0.00")
    notas: str | None = None


class EventoRecetaIn(BaseModel):
    """Ficha técnica gastronómica o preparación asignada al evento."""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    receta_id: int = Field(..., ge=1, description="ID de la receta gastronómica")
    bodega_id: int | None = Field(default=None, description="Bodega opcional para imputación de insumos")
    porciones: int = Field(default=1, ge=1, description="Número de porciones o raciones")
    notas: str | None = None


class EventoRecetaOut(BaseModel):
    """Receta asignada reflejada en respuestas."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    evento_id: UUID
    receta_id: int
    bodega_id: int | None = None
    porciones: int = 1
    notas: str | None = None


class EventoComboIn(BaseModel):
    """Combo o pack comercial asignado al evento."""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    combo_id: int = Field(..., ge=1, description="ID del combo comercial")
    bodega_id: int | None = Field(default=None, description="Bodega opcional de despacho")
    cantidad: int = Field(default=1, ge=1, description="Cantidad de combos")
    notas: str | None = None


class EventoComboOut(BaseModel):
    """Combo asignado reflejado en respuestas."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    evento_id: UUID
    combo_id: int
    bodega_id: int | None = None
    cantidad: int = 1
    notas: str | None = None


class EventoTrabajadorIn(BaseModel):
    """Personal operativo / brigada asignada al evento."""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    usuario_id: int = Field(..., ge=1, description="ID del usuario / trabajador")
    rol_evento: str | None = Field(default=None, max_length=100, description="Rol o función en el evento")
    horas_asignadas: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Horas de trabajo programadas",
    )


class EventoTrabajadorOut(BaseModel):
    """Trabajador asignado reflejado en respuestas."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    evento_id: UUID
    usuario_id: int
    rol_evento: str | None = None
    horas_asignadas: Decimal = Decimal("0.00")


class EventoConsumoKardexOut(BaseModel):
    """Asiento de trazabilidad inmutable de consumo en Kardex."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    evento_id: UUID
    kardex_movement_id: int
    producto_id: int
    bodega_id: int
    cantidad_consumida: Decimal
    costo_unitario_ppp: Decimal = Decimal("0.00")
    origen_tipo: str = "DIRECTO"
    origen_id: int | None = None


# ============================================================================
# EVENTOS PRINCIPALES SCHEMAS
# ============================================================================


class EventoCreate(BaseModel):
    """Payload para agendar un nuevo Evento o Banquete."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=1, max_length=255, description="Nombre o descripción del evento")
    titular: str | None = Field(default=None, max_length=200, description="Nombre del cliente o titular")
    tipo_evento: str = Field(default="GENERAL", max_length=64, description="Categoría del evento")
    salon_id: UUID | None = Field(default=None, description="Salón reservado")
    lugar: str | None = Field(default=None, max_length=300, description="Ubicación o dirección externa")
    fecha: date = Field(..., description="Fecha de realización")
    hora_inicio: time | None = Field(default=None, description="Hora de inicio")
    hora_fin: time | None = Field(default=None, description="Hora de finalización")
    cantidad_personas: int = Field(default=0, ge=0, description="Cantidad estimada de comensales / invitados")
    estado: str = Field(
        default="AGENDADO",
        pattern=r"^(AGENDADO|CONFIRMADO|EN_CURSO|EJECUTADO|CANCELADO)$",
        description="Estado del ciclo de vida",
    )
    color: str = Field(default="#ec4899", max_length=20, description="Color identificador")
    encargado_id: int | None = Field(default=None, description="ID del trabajador responsable")
    valor_publico: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Presupuesto o valor cobrado",
    )
    notas: str | None = None
    nota_personal: str | None = None
    nota_equipo: str | None = None
    nota_visible: str | None = None

    items: list[EventoItemIn] = Field(default_factory=list)
    recetas: list[EventoRecetaIn] = Field(default_factory=list)
    combos: list[EventoComboIn] = Field(default_factory=list)
    trabajadores: list[EventoTrabajadorIn] = Field(default_factory=list)


class EventoUpdate(BaseModel):
    """Payload para actualizar un Evento en estado no finalizado."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    titular: str | None = Field(default=None, max_length=200)
    tipo_evento: str | None = Field(default=None, max_length=64)
    salon_id: UUID | None = None
    lugar: str | None = Field(default=None, max_length=300)
    fecha: date | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    cantidad_personas: int | None = Field(default=None, ge=0)
    estado: str | None = Field(
        default=None,
        pattern=r"^(AGENDADO|CONFIRMADO|EN_CURSO|EJECUTADO|CANCELADO)$",
    )
    color: str | None = Field(default=None, max_length=20)
    encargado_id: int | None = None
    valor_publico: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    notas: str | None = None
    nota_personal: str | None = None
    nota_equipo: str | None = None
    nota_visible: str | None = None

    items: list[EventoItemIn] | None = None
    recetas: list[EventoRecetaIn] | None = None
    combos: list[EventoComboIn] | None = None
    trabajadores: list[EventoTrabajadorIn] | None = None


class EventoCancelRequest(BaseModel):
    """Payload opcional para cancelar un evento."""

    model_config = ConfigDict(extra="forbid")

    motivo: str | None = Field(default=None, description="Motivo descriptivo de la cancelación")


class EventoListItemOut(BaseModel):
    """Resumen compacto de un Evento para listados, calendario y filtros."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nombre: str
    titular: str | None = None
    tipo_evento: str = "GENERAL"
    salon_id: UUID | None = None
    salon_nombre: str | None = None
    lugar: str | None = None
    fecha: date
    hora_inicio: time | None = None
    hora_fin: time | None = None
    cantidad_personas: int = 0
    estado: str = "AGENDADO"
    color: str = "#ec4899"
    ejecutado: bool = False
    cancelado: bool = False
    encargado_id: int | None = None
    valor_publico: Decimal = Decimal("0.00")
    items_count: int = 0
    recetas_count: int = 0
    combos_count: int = 0
    trabajadores_count: int = 0


class EventoOut(BaseModel):
    """Detalle completo del Agregado Raíz de Evento."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nombre: str
    titular: str | None = None
    tipo_evento: str = "GENERAL"
    salon_id: UUID | None = None
    salon_nombre: str | None = None
    lugar: str | None = None
    fecha: date
    hora_inicio: time | None = None
    hora_fin: time | None = None
    cantidad_personas: int = 0
    estado: str = "AGENDADO"
    color: str = "#ec4899"

    ejecutado: bool = False
    cancelado: bool = False
    ejecutado_at: datetime | None = None
    cancelado_at: datetime | None = None
    motivo_cancelacion: str | None = None

    encargado_id: int | None = None
    created_by_user_id: int | None = None
    valor_publico: Decimal = Decimal("0.00")

    notas: str | None = None
    nota_personal: str | None = None
    nota_equipo: str | None = None
    nota_visible: str | None = None

    items: list[EventoItemOut] = Field(default_factory=list)
    recetas: list[EventoRecetaOut] = Field(default_factory=list)
    combos: list[EventoComboOut] = Field(default_factory=list)
    trabajadores: list[EventoTrabajadorOut] = Field(default_factory=list)
    consumos_kardex: list[EventoConsumoKardexOut] = Field(default_factory=list)

    created_at: datetime | None = None
    updated_at: datetime | None = None


EventoResponse = EventoOut
EventoDetailResponse = EventoOut


# ============================================================================
# SHORTAGE / ANALYTICS FALTANTES SCHEMAS
# ============================================================================


class EventFaltanteItemOut(BaseModel):
    """Ítem con déficit de stock consolidado para eventos futuros agendados."""

    model_config = ConfigDict(from_attributes=True)

    producto_id: int
    producto_nombre: str | None = None
    bodega_id: int
    bodega_nombre: str | None = None
    cantidad_requerida: Decimal
    stock_actual: Decimal
    deficit: Decimal
    unidad_medida: str | None = "UN"


class EventFaltantesResponse(BaseModel):
    """Resumen estructurado de faltantes para banner analítico y órdenes sugeridas."""

    model_config = ConfigDict(from_attributes=True)

    total_faltantes: int = 0
    items: list[EventFaltanteItemOut] = Field(default_factory=list)
    eventos_afectados_count: int = 0
    generado_at: datetime


class EventExecutionResultSchema(BaseModel):
    """Resultado devuelto tras ejecutar un evento en Kardex."""

    model_config = ConfigDict(from_attributes=True)

    evento_id: UUID
    ejecutado: bool = True
    ejecutado_at: datetime
    total_movimientos_kardex: int
    costo_total_consumido: Decimal = Decimal("0.00")
    consumos: list[EventoConsumoKardexOut] = Field(default_factory=list)


class EventoReverseRequest(BaseModel):
    """Payload obligatorio para revertir compensatoriamente un evento ejecutado."""

    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Motivo detallado de la anulación y reversión compensatoria",
    )


class EventoReverseResultSchema(BaseModel):
    """Resultado de la reversión compensatoria de un evento en Kardex."""

    model_config = ConfigDict(from_attributes=True)

    evento_id: UUID
    revertido: bool = True
    revertido_at: datetime
    motivo: str
    total_movimientos_compensatorios: int
    total_unidades_reingresadas: Decimal = Decimal("0.0000")
    costo_total_revertido: Decimal = Decimal("0.00")
    evento: EventoOut


class EventoExportMinutaRequest(BaseModel):
    """Payload para solicitud de exportación de minutas de producción."""

    model_config = ConfigDict(extra="forbid")

    event_ids: list[UUID] | None = Field(
        default=None,
        description="Lista opcional de IDs de eventos específicos para exportar",
    )
    event_id: UUID | None = Field(
        default=None,
        description="ID opcional de un único evento",
    )


# ============================================================================
# COMMITTED STOCK & EVENT ALERTS SCHEMAS (FASE 7)
# ============================================================================


class CommittedStockEventRef(BaseModel):
    """Referencia al evento programado que compromete existencias del insumo."""

    model_config = ConfigDict(from_attributes=True)

    evento_id: UUID = Field(..., description="Identificador único del evento")
    evento_nombre: str = Field(..., description="Nombre comercial del evento")
    fecha: date = Field(..., description="Fecha de ejecución del evento")
    hora_inicio: time | None = Field(default=None, description="Horario de inicio programado")
    cantidad: Decimal = Field(..., description="Volumen comprometido para este evento")


class CommittedStockItemOut(BaseModel):
    """Desglose de existencias y demanda futura reservada por insumo y bodega."""

    model_config = ConfigDict(from_attributes=True)

    producto_id: int = Field(..., gt=0, description="Identificador del insumo")
    producto_nombre: str | None = Field(default=None, description="Nombre comercial del producto")
    bodega_id: int = Field(..., gt=0, description="Identificador de la bodega de almacenamiento")
    bodega_nombre: str | None = Field(default=None, description="Nombre de la bodega")
    stock_actual: Decimal = Field(..., description="Stock físico actual en bodega")
    stock_comprometido: Decimal = Field(..., description="Demanda futura reservada sumada de eventos agendados")
    stock_disponible_real: Decimal = Field(
        ...,
        description="Saldo libre para operación diaria: max(0, stock_actual - stock_comprometido)",
    )
    unidad_medida: str | None = Field(default="UN", description="Unidad de medida")
    eventos: list[CommittedStockEventRef] = Field(
        default_factory=list,
        description="Eventos asociados que comprometen este insumo",
    )


class CommittedStockSummaryResponse(BaseModel):
    """Resumen consolidado de stock comprometido para analítica predictiva de inventario."""

    model_config = ConfigDict(from_attributes=True)

    total_items: int = Field(default=0, description="Total de ítems con demanda reservada")
    items: list[CommittedStockItemOut] = Field(default_factory=list, description="Lista de insumos comprometidos")
    generado_at: datetime = Field(..., description="Fecha y hora de cálculo del resumen")


class EventAlertInsumoDeficit(BaseModel):
    """Detalle del insumo en situación de quiebre o déficit para un evento."""

    model_config = ConfigDict(from_attributes=True)

    producto_id: int = Field(..., gt=0, description="Identificador del producto")
    producto_nombre: str | None = Field(default=None, description="Nombre comercial del producto")
    bodega_id: int = Field(..., gt=0, description="Identificador de la bodega")
    bodega_nombre: str | None = Field(default=None, description="Nombre de la bodega")
    cantidad_requerida: Decimal = Field(..., description="Cantidad total requerida para el evento")
    stock_actual: Decimal = Field(..., description="Saldo físico disponible en bodega")
    deficit: Decimal = Field(..., description="Volumen faltante por abastecer")
    unidad_medida: str | None = Field(default="UN", description="Unidad de medida")


class EventAlertOut(BaseModel):
    """Alerta operativa de evento con riesgo de desabastecimiento de insumos."""

    model_config = ConfigDict(from_attributes=True)

    alerta_id: str = Field(..., description="Identificador único de la alerta (ej: ALERT-EVT-{id})")
    evento_id: UUID = Field(..., description="Identificador único del evento agendado")
    evento_nombre: str = Field(..., description="Nombre del banquete o evento")
    fecha_evento: date = Field(..., description="Fecha de realización")
    hora_inicio: time = Field(..., description="Hora de inicio")
    severidad: str = Field(
        ...,
        description="Clasificación de severidad: 'CRITICAL' (< 48h con déficit) o 'WARNING' (<= 14 días)",
    )
    horas_restantes: Decimal = Field(..., description="Horas restantes hasta el inicio del evento")
    dias_restantes: int = Field(..., description="Días enteros restantes")
    total_insumos_deficit: int = Field(default=0, description="Total de insumos en situación de quiebre")
    insumos_deficit: list[EventAlertInsumoDeficit] = Field(
        default_factory=list,
        description="Desglose de insumos en déficit",
    )
    mensaje: str = Field(..., description="Mensaje explicativo para el operador")
    generado_at: datetime = Field(..., description="Timestamp de emisión de la alerta")


class EventAlertsResponse(BaseModel):
    """Contenedor estructurado de alertas operativas de eventos."""

    model_config = ConfigDict(from_attributes=True)

    total_alertas: int = Field(default=0, description="Total de alertas generadas")
    critical_count: int = Field(default=0, description="Cantidad de alertas críticas (<48h)")
    warning_count: int = Field(default=0, description="Cantidad de alertas preventivas (<=14d)")
    items: list[EventAlertOut] = Field(default_factory=list, description="Lista de alertas de eventos")
    generado_at: datetime = Field(..., description="Timestamp de consolidación")


__all__ = [
    "CommittedStockEventRef",
    "CommittedStockItemOut",
    "CommittedStockSummaryResponse",
    "EventAlertInsumoDeficit",
    "EventAlertOut",
    "EventAlertsResponse",
    "EventExecutionResultSchema",
    "EventFaltanteItemOut",
    "EventFaltantesResponse",
    "EventoCancelRequest",
    "EventoComboIn",
    "EventoComboOut",
    "EventoConsumoKardexOut",
    "EventoCreate",
    "EventoDetailResponse",
    "EventoExportMinutaRequest",
    "EventoItemIn",
    "EventoItemOut",
    "EventoListItemOut",
    "EventoOut",
    "EventoRecetaIn",
    "EventoRecetaOut",
    "EventoResponse",
    "EventoReverseRequest",
    "EventoReverseResultSchema",
    "EventoTrabajadorIn",
    "EventoTrabajadorOut",
    "EventoUpdate",
    "SalonCreate",
    "SalonOut",
    "SalonResponse",
    "SalonUpdate",
]
