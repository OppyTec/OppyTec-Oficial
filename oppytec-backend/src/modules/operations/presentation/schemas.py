"""
oppytec-backend/src/modules/operations/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`, `Decimal` exclusivo) para:
- Ventas POS, Buffet por Pax y Eventos gastronómicos.
- Registro de Consumo Batch (productos, recetas y combos), Kardex y plantillas.
- Buffet Inteligente (apertura, actualización de estaciones y liquidación Pax).
- Cocina por Voz / Manos Libres (estaciones y pedidos verbales).
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input


# ============================================================================
# 1. ESQUEMAS PREVIOS DE OPERACIONES (VENTAS POS, BUFFET COST, EVENTOS)
# ============================================================================


class PosSaleItemPayload(BaseModel):
    """Ítem vendido en el punto de venta (receta y cantidad de porciones en `Decimal`)."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: int = Field(..., gt=0)
    portions: Decimal = Field(..., gt=Decimal("0"))


class PosSaleProcessRequest(BaseModel):
    """Solicitud de registro de venta POS con explosión de insumos en orden canónico de locks."""

    model_config = ConfigDict(extra="forbid")

    bodega_id: int = Field(..., gt=0)
    items: list[PosSaleItemPayload] = Field(..., min_length=1)
    recipe_ingredients: dict[int, dict[int, Decimal]] = Field(..., min_length=1)
    ingredient_costs: dict[int, Decimal] = Field(default_factory=dict)


class PosSaleProcessResponse(BaseModel):
    """Resultado de procesar una venta POS y descargar el Kardex."""

    model_config = ConfigDict(extra="forbid")

    bodega_id: int
    movements_registered: int
    consumed_by_ingredient: dict[int, Decimal]


class BuffetCostRequest(BaseModel):
    """Cálculo de costo por comensal (`pax`) de un servicio de Buffet."""

    model_config = ConfigDict(extra="forbid")

    service_name: str = Field(..., min_length=2, max_length=150)
    total_buffet_cost: Decimal = Field(..., ge=Decimal("0"))
    pax: int = Field(..., gt=0)
    leftover_value: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))

    @field_validator("service_name")
    @classmethod
    def _sanitize_service_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="service_name")


class BuffetCostResponse(BaseModel):
    """Costo neto por comensal (`pax`) calculado en `Decimal`."""

    model_config = ConfigDict(extra="forbid")

    service_name: str
    pax: int
    total_buffet_cost: Decimal
    leftover_value: Decimal
    cost_per_pax: Decimal


class CateringEventRequest(BaseModel):
    """Cotización y registro de un evento gastronómico / banquetería."""

    model_config = ConfigDict(extra="forbid")

    event_name: str = Field(..., min_length=2, max_length=160)
    attendees_pax: int = Field(..., gt=0)
    food_cost_per_pax: Decimal = Field(..., ge=Decimal("0"))
    net_price_per_pax: Decimal = Field(..., gt=Decimal("0"))

    @field_validator("event_name")
    @classmethod
    def _sanitize_event_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="event_name")


class CateringEventResponse(BaseModel):
    """Resumen económico de un evento gastronómico en `Decimal`."""

    model_config = ConfigDict(extra="forbid")

    event_name: str
    attendees_pax: int
    total_food_cost: Decimal
    total_net_revenue: Decimal
    gross_margin: Decimal


# ============================================================================
# 2. ESQUEMAS DE REGISTRO DE CONSUMO (FASE 2)
# ============================================================================


class BatchConsumptionItemInput(BaseModel):
    """Línea de consumo batch (producto directo, receta o combo)."""

    model_config = ConfigDict(extra="forbid")

    tipo_item: Literal["PRODUCTO", "RECETA", "COMBO"] = "PRODUCTO"
    item_id: int = Field(..., gt=0)
    cantidad: Decimal = Field(..., gt=Decimal("0"))
    unidad_medida: str = Field(default="UN", max_length=20)
    costo_unitario_ppp: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    lote_codigo: str | None = Field(default=None, max_length=64)
    fecha_vencimiento_lote: date | None = None
    opciones_seleccionadas: dict[str, Any] | None = None


class ConsumptionRegisterRequest(BaseModel):
    """Solicitud batch para registrar consumo directo."""

    model_config = ConfigDict(extra="forbid")

    bodega_id: int = Field(..., gt=0)
    items: list[BatchConsumptionItemInput] = Field(..., min_length=1)
    tipo_origen: str = Field(default="MANUAL_TERMINAL", max_length=32)
    area_operativa_id: int | None = Field(default=None, gt=0)
    folio_ticket: str | None = Field(default=None, max_length=64)
    notas: str | None = Field(default=None, max_length=1000)
    allow_expired: bool = False

    @field_validator("notas")
    @classmethod
    def _sanitize_notas(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="notas")


class ConsumptionRecordItemResponse(BaseModel):
    """Detalle de ítem descontado en el registro de consumo."""

    model_config = ConfigDict(extra="forbid")

    id: int
    consumption_record_id: int
    tipo_item: str
    item_id: int
    cantidad: Decimal
    unidad_medida: str
    costo_unitario_ppp: Decimal
    costo_total: Decimal
    lote_codigo: str | None = None
    fecha_vencimiento_lote: date | None = None
    kardex_movement_id: int | None = None
    opciones_seleccionadas: dict[str, Any] | None = None


class ConsumptionRecordResponse(BaseModel):
    """Respuesta con cabecera y detalle de un consumo registrado."""

    model_config = ConfigDict(extra="forbid")

    id: int
    codigo_folio: str
    bodega_id: int
    usuario_id: int
    tipo_origen: str
    costo_total: Decimal
    items: list[ConsumptionRecordItemResponse]
    folio_ticket: str | None = None
    area_operativa_id: int | None = None
    notas: str | None = None
    created_at: datetime
    is_undone: bool = False


class ConsumptionHistoryResponse(BaseModel):
    """Listado paginado de historial de consumo."""

    model_config = ConfigDict(extra="forbid")

    items: list[ConsumptionRecordResponse]
    total: int
    page: int
    page_size: int


class ConsumptionUpdateRequest(BaseModel):
    """Corrección o actualización de notas de un registro de consumo."""

    model_config = ConfigDict(extra="forbid")

    notas: str | None = Field(default=None, max_length=1000)

    @field_validator("notas")
    @classmethod
    def _sanitize_notas(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="notas")


class MermaExpiredStockRequest(BaseModel):
    """Solicitud de merma directa de lote vencido desde contingencia."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0)
    bodega_id: int = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    lote_codigo: str = Field(..., min_length=1, max_length=64)
    fecha_vencimiento: date | None = None
    motivo: str = Field(default="LOTE_VENCIDO", max_length=64)
    unit_cost: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    descripcion: str | None = Field(default=None, max_length=500)

    @field_validator("descripcion")
    @classmethod
    def _sanitize_desc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name="descripcion")


class MermaExpiredStockResponse(BaseModel):
    """Resultado de la merma directa del lote vencido."""

    model_config = ConfigDict(extra="forbid")

    kardex_entry_id: int
    producto_id: int
    bodega_id: int
    quantity: Decimal
    movement_type: str
    resulting_balance: Decimal
    lote_codigo: str | None


class ConsumptionTemplateCreateRequest(BaseModel):
    """Creación de plantilla de catálogo de consumo."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(..., min_length=2, max_length=64)
    nombre: str = Field(..., min_length=2, max_length=128)
    descripcion: str | None = Field(default=None, max_length=500)
    is_public: bool = False
    columnas_count: int = Field(default=8, ge=5, le=10)
    sort_mode: str = Field(default="alpha_asc", max_length=32)
    product_ids: list[int] = Field(default_factory=list)
    custom_product_order: list[int] | None = None

    @field_validator("nombre", "descripcion", "slug")
    @classmethod
    def _sanitize_strings(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name=info.field_name)


class ConsumptionTemplateResponse(BaseModel):
    """Detalle de una plantilla de consumo rápido."""

    model_config = ConfigDict(extra="forbid")

    id: int
    slug: str
    nombre: str
    descripcion: str | None = None
    usuario_creador_id: int
    is_public: bool
    columnas_count: int
    sort_mode: str
    product_ids: list[int]
    custom_product_order: list[int] | None = None


# ============================================================================
# 3. ESQUEMAS DE BUFFET INTELIGENTE (FASE 2)
# ============================================================================


class BuffetSessionItemInput(BaseModel):
    """Ítem asignado a una estación en sesión de buffet."""

    model_config = ConfigDict(extra="forbid")

    tipo_item: Literal["PRODUCTO", "RECETA"] = "PRODUCTO"
    item_id: int = Field(..., gt=0)
    cantidad_montada: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"))
    cantidad_sobrante: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"))
    cantidad_merma: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"))
    costo_unitario_ppp: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))


class BuffetStationInput(BaseModel):
    """Estación creada al abrir sesión de buffet."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=2, max_length=120)
    orden: int = Field(default=0, ge=0)
    peso_inicial_kg: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"))
    items: list[BuffetSessionItemInput] = Field(default_factory=list)

    @field_validator("nombre")
    @classmethod
    def _sanitize_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="nombre")


class BuffetSessionStartRequest(BaseModel):
    """Apertura de una nueva sesión de buffet."""

    model_config = ConfigDict(extra="forbid")

    bodega_id: int = Field(..., gt=0)
    tipo_servicio: str = Field(default="DESAYUNO", max_length=64)
    area_operativa_id: int | None = Field(default=None, gt=0)
    template_id: int | None = Field(default=None, gt=0)
    estaciones: list[BuffetStationInput] = Field(default_factory=list)


class BuffetSessionItemResponse(BaseModel):
    """Resumen de ítem por estación."""

    model_config = ConfigDict(extra="forbid")

    id: int
    station_id: int
    session_id: int
    tipo_item: str
    item_id: int
    cantidad_montada: Decimal
    cantidad_sobrante: Decimal
    cantidad_merma: Decimal
    cantidad_neta_consumida: Decimal
    costo_unitario_ppp: Decimal
    costo_total: Decimal


class BuffetStationResponse(BaseModel):
    """Detalle de estación de buffet."""

    model_config = ConfigDict(extra="forbid")

    id: int
    session_id: int
    nombre: str
    orden: int
    peso_inicial_kg: Decimal
    peso_sobrante_kg: Decimal
    items: list[BuffetSessionItemResponse]


class BuffetSessionResponse(BaseModel):
    """Detalle completo de sesión de buffet."""

    model_config = ConfigDict(extra="forbid")

    id: int
    bodega_id: int
    usuario_creador_id: int
    tipo_servicio: str
    estado: str
    costo_total_montaje: Decimal
    valor_sobrante_reutilizable: Decimal
    costo_neto_pax: Decimal
    pax_comensales: int
    area_operativa_id: int | None = None
    template_id: int | None = None
    stations: list[BuffetStationResponse]
    created_at: datetime
    closed_at: datetime | None = None


class BuffetItemUpdateInput(BaseModel):
    """Actualización de conteo de ítem en estación."""

    model_config = ConfigDict(extra="forbid")

    item_id: int = Field(..., gt=0)
    tipo_item: Literal["PRODUCTO", "RECETA"] = "PRODUCTO"
    cantidad_montada: Decimal = Field(..., ge=Decimal("0"))
    cantidad_sobrante: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"))
    cantidad_merma: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"))
    costo_unitario_ppp: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))


class BuffetStationUpdateInput(BaseModel):
    """Actualización de estación de buffet."""

    model_config = ConfigDict(extra="forbid")

    station_id: int = Field(..., gt=0)
    peso_sobrante_kg: Decimal | None = Field(default=None, ge=Decimal("0"))
    items: list[BuffetItemUpdateInput] = Field(default_factory=list)


class BuffetItemsUpdateRequest(BaseModel):
    """Lote de actualización de estaciones e ítems de buffet."""

    model_config = ConfigDict(extra="forbid")

    stations: list[BuffetStationUpdateInput] = Field(..., min_length=1)


class BuffetFinalizeRequest(BaseModel):
    """Liquidación y costeo por Pax de buffet."""

    model_config = ConfigDict(extra="forbid")

    pax: int = Field(..., gt=0)
    leftover_reusable_value: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))


class BuffetTemplateCreateRequest(BaseModel):
    """Creación de plantilla de montaje de estaciones."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=2, max_length=120)
    descripcion: str | None = Field(default=None, max_length=500)
    comensales_estimados: int = Field(default=100, gt=0)
    estaciones_json: list[dict[str, Any]] = Field(default_factory=list)
    is_system: bool = False
    is_public: bool = True

    @field_validator("nombre", "descripcion")
    @classmethod
    def _sanitize_name_desc(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name=info.field_name)


class BuffetTemplateResponse(BaseModel):
    """Plantilla de estaciones de buffet."""

    model_config = ConfigDict(extra="forbid")

    id: int
    nombre: str
    descripcion: str | None = None
    comensales_estimados: int
    estaciones_json: list[dict[str, Any]]
    is_system: bool
    is_public: bool


# ============================================================================
# 4. ESQUEMAS DE COCINA POR VOZ / MANOS LIBRES (FASE 2)
# ============================================================================


class VoiceStationCreateRequest(BaseModel):
    """Creación o registro de estación de voz."""

    model_config = ConfigDict(extra="forbid")

    nombre_estacion: str = Field(..., min_length=2, max_length=64)
    voice_command: str = Field(..., min_length=2, max_length=64)
    area_operativa_id: int | None = Field(default=None, gt=0)
    usuario_asignado_id: int | None = Field(default=None, gt=0)

    @field_validator("nombre_estacion", "voice_command")
    @classmethod
    def _sanitize_station_strings(cls, value: str, info: Any) -> str:
        return sanitize_text_input(value, field_name=info.field_name)


class VoiceStationResponse(BaseModel):
    """Estación de voz registrada."""

    model_config = ConfigDict(extra="forbid")

    id: int
    nombre_estacion: str
    voice_command: str
    area_operativa_id: int | None = None
    usuario_asignado_id: int | None = None
    is_active: bool


class VoiceOrderRegisterRequest(BaseModel):
    """Captura y transcripción de un pedido verbal en cocina."""

    model_config = ConfigDict(extra="forbid")

    station_id: int = Field(..., gt=0)
    texto_transcrito: str = Field(..., min_length=2, max_length=1000)
    accion_detectada: Literal["CONSUMO", "MERMA"] = "CONSUMO"
    confianza_ia: Decimal = Field(default=Decimal("0.9500"), ge=Decimal("0"), le=Decimal("1"))
    items_interpretados: list[BatchConsumptionItemInput] = Field(default_factory=list)

    @field_validator("texto_transcrito")
    @classmethod
    def _sanitize_transcription(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="texto_transcrito")


class VoiceOrderConfirmRequest(BaseModel):
    """Confirmación y ejecución del pedido verbal hacia inventario."""

    model_config = ConfigDict(extra="forbid")

    bodega_id: int = Field(..., gt=0)


class VoiceOrderResponse(BaseModel):
    """Detalle de log de orden de voz."""

    model_config = ConfigDict(extra="forbid")

    id: int
    station_id: int
    texto_transcrito: str
    accion_detectada: str
    confianza_ia: Decimal
    items_interpretados_json: list[dict[str, Any]]
    estado: str
    consumption_record_id: int | None = None
    created_at: datetime
