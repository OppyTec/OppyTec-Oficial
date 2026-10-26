"""
oppytec-backend/src/modules/inventory/presentation/schemas_alerts.py
Contratos Pydantic v2 estrictos (extra="forbid") para el módulo de Alertas (/alertas):
- `CriticalStockAlertResponse`
- `ExpiredLotAlertResponse`
- `UpcomingExpiryAlertResponse`
- `AlertsSummaryResponse`
- `AlertsBadgeResponse`
Cumple con Regla 02 (Decimal estricto sin float IEEE 754) y Regla 04 (Validación de Esquemas).
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class StockHealthRatioResponse(BaseModel):
    """Proyección de salud porcentual y clasificación cromática para barra de progreso."""

    model_config = ConfigDict(extra="forbid")

    stock_actual: Decimal = Field(..., description="Saldo físico actual en bodega")
    stock_minimo: Decimal = Field(..., description="Nivel mínimo de seguridad configurado")
    raw_ratio: Decimal = Field(..., description="Ratio matemático porcentual no acotado")
    clamped_ratio: Decimal = Field(..., description="Ratio acotado entre 0.00% y 100.00% para renderizado de barra")
    status: str = Field(..., description="Estado cromático: 'depleted', 'critical', 'warning', 'healthy'")


class CriticalStockAlertResponse(BaseModel):
    """Contrato REST para insumos bajo stock mínimo o agotados."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0, description="Identificador único del producto")
    bodega_id: int = Field(..., gt=0, description="Identificador único de la bodega")
    bodega_nombre: str = Field(..., min_length=1, description="Nombre de la bodega")
    producto_nombre: str = Field(..., min_length=1, description="Nombre comercial del insumo")
    stock_actual: Decimal = Field(..., description="Saldo físico disponible en bodega")
    stock_minimo: Decimal = Field(..., description="Umbral mínimo configurado")
    unidad_medida: str = Field(..., min_length=1, description="Unidad de medida de almacén")
    ratio: StockHealthRatioResponse = Field(..., description="Detalle del ratio de salud cromática")
    is_depleted: bool = Field(..., description="True si las existencias son <= 0")
    bodega_color: str = Field(default="#3B82F6", description="Color representativo de la bodega")
    bodega_icono: str = Field(default="warehouse", description="Ícono representativo de la bodega")
    costo_promedio: Decimal = Field(default=Decimal("0.00"), description="Costo unitario PPP")


class ExpiredLotAlertResponse(BaseModel):
    """Contrato REST para lotes caducados que conservan saldo físico."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0, description="Identificador único del producto")
    bodega_id: int = Field(..., gt=0, description="Identificador único de la bodega")
    bodega_nombre: str = Field(..., min_length=1, description="Nombre de la bodega")
    producto_nombre: str = Field(..., min_length=1, description="Nombre comercial del producto")
    lote_codigo: str | None = Field(default=None, description="Código de identificación del lote físico")
    fecha_vencimiento: date = Field(..., description="Fecha límite de caducidad del lote")
    cantidad_vencida: Decimal = Field(..., gt=Decimal("0.0000"), description="Saldo físico caducado")
    dias_vencido: int = Field(..., ge=0, description="Días transcurridos desde el vencimiento")
    costo_ppp: Decimal = Field(..., ge=Decimal("0.00"), description="Costo promedio ponderado unitario")
    valor_total_riesgo: Decimal = Field(..., ge=Decimal("0.00"), description="Valor monetario total en pérdida")
    unidad_medida: str = Field(..., min_length=1, description="Unidad de medida")
    bodega_color: str = Field(default="#3B82F6", description="Color de la bodega")
    bodega_icono: str = Field(default="warehouse", description="Ícono de la bodega")


class UpcomingExpiryAlertResponse(BaseModel):
    """Contrato REST para lotes próximos a caducar dentro de la ventana FEFO."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0, description="Identificador único del producto")
    bodega_id: int = Field(..., gt=0, description="Identificador único de la bodega")
    bodega_nombre: str = Field(..., min_length=1, description="Nombre de la bodega")
    producto_nombre: str = Field(..., min_length=1, description="Nombre comercial del producto")
    lote_codigo: str | None = Field(default=None, description="Código de identificación del lote físico")
    fecha_vencimiento: date = Field(..., description="Fecha límite de caducidad del lote")
    cantidad_en_riesgo: Decimal = Field(..., gt=Decimal("0.0000"), description="Saldo físico próximo a expirar")
    dias_restantes: int = Field(..., ge=0, description="Días restantes para caducar")
    costo_ppp: Decimal = Field(..., ge=Decimal("0.00"), description="Costo promedio ponderado unitario")
    valor_total_riesgo: Decimal = Field(..., ge=Decimal("0.00"), description="Valor monetario total en riesgo")
    unidad_medida: str = Field(..., min_length=1, description="Unidad de medida")
    bodega_color: str = Field(default="#3B82F6", description="Color de la bodega")
    bodega_icono: str = Field(default="warehouse", description="Ícono de la bodega")


class AlertsSummaryResponse(BaseModel):
    """Contrato REST consolidado para la vista principal /alertas."""

    model_config = ConfigDict(extra="forbid")

    total_count: int = Field(..., ge=0, description="Conteo total de alertas operativas")
    critical_count: int = Field(..., ge=0, description="Conteo de alertas de stock crítico / agotado")
    expired_count: int = Field(..., ge=0, description="Conteo de lotes vencidos")
    upcoming_count: int = Field(..., ge=0, description="Conteo de lotes próximos a vencer")
    has_critical: bool = Field(..., description="True si existen quiebres de stock o lotes caducados")
    total_financial_risk: Decimal = Field(
        default=Decimal("0.00"),
        description="Valorización monetaria consolidada del riesgo en lotes caducados y próximos",
    )
    critical_stock: list[CriticalStockAlertResponse] = Field(
        default_factory=list,
        description="Lista de insumos en stock crítico o agotado",
    )
    expired_lots: list[ExpiredLotAlertResponse] = Field(
        default_factory=list,
        description="Lista de lotes caducados con existencias",
    )
    upcoming_expiries: list[UpcomingExpiryAlertResponse] = Field(
        default_factory=list,
        description="Lista de lotes próximos a caducar dentro de la ventana FEFO",
    )


class AlertsBadgeResponse(BaseModel):
    """Contrato ultraliviano para el Sidebar institucional y barra de cabecera (< 5ms)."""

    model_config = ConfigDict(extra="forbid")

    total_count: int = Field(..., ge=0, description="Conteo total de alertas activas")
    has_critical: bool = Field(..., description="True si requiere pulsación destructiva roja")
    critical_stock_count: int = Field(..., ge=0, description="Conteo de productos críticos")
    expired_count: int = Field(..., ge=0, description="Conteo de lotes vencidos")
    upcoming_count: int = Field(..., ge=0, description="Conteo de lotes próximos a vencer")
