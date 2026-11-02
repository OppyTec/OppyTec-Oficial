"""
oppytec-backend/src/modules/projection/presentation/schemas.py
Esquemas Pydantic V2 de Proyección de Demandas, Agotamiento FEFO y Traspasos Preventivos.
Cumple Regla 02 (Clean Architecture), validación estricta y ejemplos OpenAPI.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DaySimulationPointResponse(BaseModel):
    """Punto de simulación temporal para el gráfico interactivo Recharts."""

    model_config = ConfigDict(from_attributes=True)

    date: str = Field(..., description="Fecha del punto de simulación en formato YYYY-MM-DD", examples=["2026-11-15"])
    day_index: int = Field(..., description="Día relativo t (0..N)", examples=[14])
    qty: str = Field(..., description="Saldo físico de stock proyectado en Decimal string", examples=["15.5000"])
    status: str = Field(..., description="Estado de urgencia: normal, warning, critical", examples=["warning"])
    status_label: str = Field(..., description="Etiqueta legible del estado", examples=["Bajo stock"])
    expiring_qty: str = Field(default="0.0000", description="Cantidad caducada en el día", examples=["0.0000"])
    event_deduction: str = Field(default="0.0000", description="Deducción de eventos agendados", examples=["5.0000"])
    events: list[dict[str, Any]] = Field(default_factory=list, description="Eventos agendados para este día")
    expiring_lots: list[dict[str, Any]] = Field(default_factory=list, description="Lotes caducados este día")


class TransferRecommendationResponse(BaseModel):
    """Sugerencia estructurada de traspaso preventivo entre bodegas."""

    model_config = ConfigDict(from_attributes=True)

    producto_id: int = Field(..., description="ID del producto a transferir", examples=[10])
    bodega_origen_id: int = Field(..., description="ID de la bodega origen con excedente", examples=[2])
    bodega_origen_nombre: str | None = Field(default=None, description="Nombre de la bodega origen", examples=["Bodega Bar"])
    bodega_destino_id: int = Field(..., description="ID de la bodega destino en quiebre", examples=[1])
    cantidad_sugerida: str = Field(..., description="Cantidad sugerida a transferir en Decimal string", examples=["10.0000"])
    dias_cobertura_restante_origen: int = Field(..., description="Días de stock residual en bodega origen", examples=[15])
    urgencia: str = Field(default="critical", description="Nivel de urgencia del traspaso", examples=["critical"])


class ProjectionCardItemResponse(BaseModel):
    """Tarjeta resumen para el Grid principal paginado de proyección."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID del snapshot de proyección", examples=[1])
    producto_id: int = Field(..., description="ID del producto", examples=[10])
    producto_nombre: str = Field(..., description="Nombre del producto", examples=["Pechuga de Pollo"])
    producto_sku: str = Field(..., description="Código SKU del producto", examples=["POL-001"])
    categoria_id: int | None = Field(default=None, description="ID de la categoría", examples=[2])
    categoria_nombre: str | None = Field(default=None, description="Nombre de la categoría", examples=["Carnes"])
    bodega_id: int | None = Field(default=None, description="ID de la bodega (None si consolidado)", examples=[1])
    bodega_nombre: str | None = Field(default=None, description="Nombre de la bodega", examples=["Bodega Principal"])
    horizon_days: int = Field(default=30, description="Horizonte de días proyectado", examples=[30])
    current_stock: str = Field(..., description="Stock físico actual en Decimal string", examples=["25.0000"])
    projected_stock: str = Field(..., description="Stock proyectado final en Decimal string", examples=["0.0000"])
    depletion_date: str | None = Field(default=None, description="Fecha de quiebre de stock si aplica", examples=["2026-11-15"])
    worst_status: str = Field(..., description="Peor estado dentro del horizonte: normal, warning, critical", examples=["critical"])
    worst_status_label: str = Field(..., description="Etiqueta descriptiva del peor estado", examples=["Sin stock (día 14)"])
    worst_day: int | None = Field(default=None, description="Día en que ocurre el peor estado", examples=[14])
    daily_consumption_rate: str = Field(default="0.0000", description="Tasa de consumo diario en Decimal string", examples=["1.7500"])
    is_stale: bool = Field(default=False, description="Indica si el snapshot necesita recálculo", examples=[False])
    calculated_at: str | None = Field(default=None, description="Timestamp UTC del cálculo", examples=["2026-11-01T12:00:00Z"])


class PaginatedProjectionSnapshotsResponse(BaseModel):
    """Sobre de paginación server-side de alto rendimiento para proyección."""

    model_config = ConfigDict(from_attributes=True)

    items: list[ProjectionCardItemResponse] = Field(..., description="Listado de tarjetas paginadas")
    total_items: int = Field(..., description="Total de registros que coinciden con los filtros", examples=[154])
    page: int = Field(..., description="Página actual (1..N)", examples=[1])
    page_size: int = Field(..., description="Tamaño de página (10, 30, 50, 100)", examples=[30])
    total_pages: int = Field(..., description="Cantidad total de páginas", examples=[6])
    has_next: bool = Field(..., description="Existe página siguiente", examples=[True])
    has_prev: bool = Field(..., description="Existe página anterior", examples=[False])


class ProductCurveDetailResponse(BaseModel):
    """Detalle completo de la curva de un producto para el modal interactivo con Recharts."""

    model_config = ConfigDict(from_attributes=True)

    producto_id: int = Field(..., description="ID del producto", examples=[10])
    producto_nombre: str = Field(..., description="Nombre del producto", examples=["Pechuga de Pollo"])
    bodega_id: int | None = Field(default=None, description="ID de bodega si aplica", examples=[1])
    bodega_nombre: str | None = Field(default=None, description="Nombre de la bodega", examples=["Bodega Principal"])
    horizon_days: int = Field(default=30, description="Horizonte de simulación en días", examples=[30])
    current_stock: str = Field(..., description="Stock actual", examples=["25.0000"])
    projected_stock: str = Field(..., description="Stock residual al final del horizonte", examples=["0.0000"])
    depletion_date: str | None = Field(default=None, description="Fecha de agotamiento si ocurre", examples=["2026-11-15"])
    worst_status: str = Field(..., description="Peor estado en la serie", examples=["critical"])
    worst_status_label: str = Field(..., description="Etiqueta del peor estado", examples=["Sin stock (día 14)"])
    worst_day: int | None = Field(default=None, description="Día relativo del peor estado", examples=[14])
    daily_consumption_rate: str = Field(default="0.0000", description="Consumo diario base", examples=["1.7500"])
    curve: list[DaySimulationPointResponse] = Field(..., description="Serie temporal día a día (0..horizon_days)")


class ProjectionAlertResponse(BaseModel):
    """Alerta de quiebre o riesgo de abastecimiento para la consola de alertas preventivas."""

    model_config = ConfigDict(from_attributes=True)

    producto_id: int = Field(..., description="ID del producto", examples=[10])
    producto_nombre: str = Field(..., description="Nombre del producto", examples=["Pechuga de Pollo"])
    bodega_id: int | None = Field(default=None, description="ID de la bodega", examples=[1])
    bodega_nombre: str | None = Field(default=None, description="Nombre de la bodega", examples=["Bodega Principal"])
    status: str = Field(..., description="Estado de alerta: critical o warning", examples=["critical"])
    status_label: str = Field(..., description="Etiqueta explicativa del quiebre", examples=["Sin stock (día 14)"])
    depletion_date: str | None = Field(default=None, description="Fecha de agotamiento prevista", examples=["2026-11-15"])
    worst_day: int | None = Field(default=None, description="Día en que ocurre el quiebre", examples=[14])
    current_stock: str = Field(..., description="Stock físico actual", examples=["25.0000"])
    projected_stock: str = Field(..., description="Stock proyectado al final del horizonte", examples=["0.0000"])
    transfer_suggestions: list[TransferRecommendationResponse] = Field(
        default_factory=list,
        description="Sugerencias de traspaso desde otras bodegas con superávit",
    )


class RecomputeRequest(BaseModel):
    """Payload opcional para solicitar el recálculo masivo de snapshots."""

    horizon_days: int = Field(default=30, ge=7, le=90, description="Horizonte a recalcular", examples=[30])


class RecomputeResponse(BaseModel):
    """Respuesta del recálculo de snapshots con estado y métricas de procesamiento."""

    status: str = Field(..., description="Estado de la operación: completed o locked", examples=["completed"])
    processed: int = Field(..., description="Cantidad de productos procesados", examples=[45])
    horizon_days: int = Field(..., description="Horizonte recalculado", examples=[30])
    message: str = Field(..., description="Mensaje explicativo del resultado", examples=["Successfully recomputed 45 product snapshots"])
