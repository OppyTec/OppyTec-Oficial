"""
oppytec-backend/src/modules/tenancy/presentation/schemas_holding_hub.py
Esquemas Pydantic V2 (`extra="forbid"`, `Decimal` estricto y cero floats) para:
- Holding Hub Enterprise Dashboard (`HoldingHubSummaryResponse`).
- Tarjetas de Sucursales / Tenants (`HoldingTenantCardResponse`).
- Consumo Diario de Créditos IA (`HoldingDailyCreditUsageItem`).
- Distribución de Créditos entre Sucursales (`HoldingCreditDistributionRequest`/`Response`).
- Compra de Paquetes de Créditos IA (`HoldingPurchaseCreditsRequest`/`Response`).
- Cambio y Upgrade de Plan SaaS (`HoldingPlanChangeRequest`/`Response`).
- Benchmarking y Analítica Cross-Tenant (`HoldingBenchmarkingResponse`).
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input
from src.modules.tenancy.domain.holding_hub import (
    CreditDistributionMode,
    HoldingMetricsVO,
    TenantCardVO,
)

# ============================================================================
# 1. ESQUEMAS BASE Y COMPONENTES
# ============================================================================


class HoldingDailyCreditUsageItem(BaseModel):
    """Punto diario de consumo de créditos IA y tokens para gráficas temporales."""

    model_config = ConfigDict(extra="forbid")

    date: str = Field(..., description="Fecha del registro en formato ISO (YYYY-MM-DD)")
    credits: int = Field(..., ge=0, description="Créditos IA consumidos en el día")
    tokens: int = Field(..., ge=0, description="Tokens brutos procesados por LLM")
    requests: int = Field(..., ge=0, description="Cantidad de peticiones procesadas")


class HoldingMetricsSchema(BaseModel):
    """Métricas operativas y financieras consolidadas del Holding gastronómico."""

    model_config = ConfigDict(extra="forbid")

    total_sales: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Ventas totales acumuladas en moneda base del holding",
    )
    inventory_value: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Valorización total del inventario en almacenes",
    )
    waste_pct: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Porcentaje de merma operativa consolidada",
    )

    @classmethod
    def from_domain(cls, vo: HoldingMetricsVO) -> HoldingMetricsSchema:
        """Fabrica un esquema Pydantic a partir del Value Object de dominio puro."""
        return cls(
            total_sales=vo.total_sales,
            inventory_value=vo.inventory_value,
            waste_pct=vo.waste_pct,
        )


class HoldingTenantCardResponse(BaseModel):
    """Ficha informativa de cada sucursal/restaurante asociada al Holding."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Identificador único UUID de la sucursal (Tenant)")
    name: str = Field(..., description="Nombre comercial del restaurante/sucursal")
    schema_name: str = Field(..., description="Nombre del esquema físico PostgreSQL aislado")
    operational_status: str = Field(
        default="active",
        description="Estado operativo (active, suspended, maintenance)",
    )
    used_credits: int = Field(
        default=0,
        ge=0,
        description="Créditos IA consumidos por esta sucursal",
    )
    allocated_credits: int = Field(
        default=0,
        ge=0,
        description="Créditos IA asignados (en modo ALLOCATED) o 0 en SHARED",
    )
    bot_requests: int = Field(
        default=0,
        ge=0,
        description="Total de interacciones / solicitudes al bot AI",
    )
    usage_pct: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Porcentaje de utilización de créditos asignados o globales",
    )
    safety_status: str = Field(
        default="NORMAL",
        description="Semáforo de seguridad (NORMAL, WARNING, CRITICAL)",
    )

    @classmethod
    def from_domain(
        cls,
        vo: TenantCardVO,
        *,
        usage_pct: Decimal = Decimal("0.00"),
        safety_status: str = "NORMAL",
    ) -> HoldingTenantCardResponse:
        """Fabrica el esquema a partir de un TenantCardVO del dominio."""
        return cls(
            id=vo.id,
            name=vo.nombre,
            schema_name=vo.schema_name,
            operational_status=vo.estado_operativo,
            used_credits=vo.creditos_usados,
            allocated_credits=vo.creditos_asignados,
            bot_requests=vo.solicitudes_bot,
            usage_pct=usage_pct,
            safety_status=safety_status,
        )


# ============================================================================
# 2. DASHBOARD Y RESUMEN INTEGRAL DEL HOLDING
# ============================================================================


class SafetyCapPredictiveStatus(BaseModel):
    """Estado predictivo y proyección de consumo para el Safety Cap corporativo."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., description="Semáforo predictivo: NORMAL, WARNING, CRITICAL")
    burn_rate_daily: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Tasa promedio de consumo diario de créditos IA (Decimal)",
    )
    estimated_days_remaining: int | None = Field(
        default=None,
        ge=0,
        description="Días estimados antes del agotamiento de la bolsa de créditos",
    )
    recommendation: str = Field(
        ...,
        description="Recomendación predictiva para la administración de la bolsa",
    )


class HoldingBriefingResponse(BaseModel):
    """Resumen ejecutivo corporativo generado por IA OppyFy para el Holding."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str = Field(..., description="Identificador UUID de la empresa matriz (Holding)")
    generated_at: datetime = Field(..., description="Marca temporal UTC de generación del briefing")
    summary_paragraphs: list[str] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Resumen ejecutivo inteligente de exactamente 2 párrafos",
    )
    key_achievements: list[str] = Field(
        default_factory=list,
        description="Aciertos y aspectos positivos destacados del holding",
    )
    cost_alerts: list[str] = Field(
        default_factory=list,
        description="Alertas de merma, costos o riesgos operativos detectados",
    )
    safety_cap_prediction: SafetyCapPredictiveStatus = Field(
        ...,
        description="Proyección predictiva del estado de Safety Cap",
    )
    tokens_used: int = Field(..., ge=0, description="Tokens de LLM procesados en la síntesis")
    credits_deducted: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Créditos IA deducidos por la generación del briefing",
    )
    model_name: str = Field(..., description="Nombre del modelo de IA utilizado")

    def __await__(self):
        async def _identity():
            return self

        return _identity().__await__()


class HoldingHubSummaryResponse(BaseModel):
    """Resumen integral del Holding Hub Enterprise."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str = Field(..., description="Identificador UUID de la empresa matriz (Holding)")
    name: str = Field(..., description="Razón o nombre corporativo del Holding")
    credit_balance: int = Field(..., ge=0, description="Saldo actual disponible de créditos IA corporativos")
    total_credits: int = Field(..., ge=0, description="Total de créditos contratados en el periodo actual")
    used_credits: int = Field(..., ge=0, description="Total de créditos consumidos a la fecha")
    distribution_mode: CreditDistributionMode = Field(
        ...,
        description="Modo de distribución de créditos: 'shared' o 'allocated'",
    )
    safety_status: str = Field(
        ...,
        description="Semáforo global de seguridad (NORMAL, WARNING, CRITICAL)",
    )
    usage_pct: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Porcentaje global de consumo de créditos IA del Holding",
    )
    metrics: HoldingMetricsSchema = Field(
        ...,
        description="KPIs globales de ventas, inventario y merma consolidada",
    )
    tenants: list[HoldingTenantCardResponse] = Field(
        default_factory=list,
        description="Lista de sucursales activas asociadas al Holding",
    )
    daily_usage: list[HoldingDailyCreditUsageItem] = Field(
        default_factory=list,
        description="Serie temporal de consumo diario de créditos y tokens",
    )
    ai_briefing: HoldingBriefingResponse | None = Field(
        default=None,
        description="Resumen ejecutivo diario inteligente generado por OppyFy",
    )


# ============================================================================
# 3. DISTRIBUCIÓN DE CRÉDITOS IA
# ============================================================================


class HoldingCreditDistributionRequest(BaseModel):
    """Solicitud de reconfiguración del modo de créditos y asignaciones por sucursal."""

    model_config = ConfigDict(extra="forbid")

    distribution_mode: CreditDistributionMode = Field(
        ...,
        description="Modo de distribución deseado: 'shared' o 'allocated'",
    )
    allocations: dict[str, int] = Field(
        default_factory=dict,
        description="Diccionario {tenant_id: creditos_asignados} requerido si el modo es 'allocated'",
    )

    @field_validator("allocations")
    @classmethod
    def validate_allocations_non_negative(cls, v: dict[str, int]) -> dict[str, int]:
        clean_allocations: dict[str, int] = {}
        for tenant_id, amount in v.items():
            if amount < 0:
                raise ValueError(
                    f"Asignación para sucursal '{tenant_id}' no puede ser negativa: {amount}"
                )
            clean_id = sanitize_text_input(str(tenant_id), field_name="tenant_id", block_polyglots=True)
            clean_allocations[clean_id] = amount
        return clean_allocations


class HoldingCreditDistributionResponse(BaseModel):
    """Resultado de la actualización de la distribución de créditos IA."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="Indica si la distribución fue aplicada con éxito")
    holding_id: str = Field(..., description="Identificador UUID del Holding")
    distribution_mode: CreditDistributionMode = Field(..., description="Modo de distribución activo")
    allocations: dict[str, int] = Field(
        ...,
        description="Distribución final por sucursal {tenant_id: creditos}",
    )
    total_allocated: int = Field(..., ge=0, description="Suma total de créditos asignados a sucursales")
    unallocated_credits: int = Field(..., ge=0, description="Créditos remanentes en la billetera corporativa")
    message: str = Field(..., description="Mensaje informativo del resultado de la operación")


# ============================================================================
# 4. COMPRA DE CRÉDITOS IA
# ============================================================================


class HoldingPurchaseCreditsRequest(BaseModel):
    """Solicitud de compra de paquete de créditos de IA para el Holding."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str = Field(..., description="Identificador UUID del Holding que efectúa la compra")
    credits_amount: int = Field(
        ...,
        gt=0,
        le=10_000_000,
        description="Cantidad de créditos a comprar (entero estrictamente positivo y acotado)",
    )
    currency: str = Field(default="CLP", description="Moneda de pago (CLP, USD, EUR, BRL)")
    payment_method: str = Field(default="credit_card", description="Método de pago utilizado")
    idempotency_key: str | None = Field(
        default=None,
        max_length=128,
        description="Clave de idempotencia para evitar doble facturación",
    )

    @field_validator("currency")
    @classmethod
    def validate_currency_code(cls, v: str) -> str:
        clean = v.strip().upper()
        if clean not in ("CLP", "USD", "EUR", "BRL"):
            raise ValueError(f"Moneda no soportada: {clean}. Permitidas: CLP, USD, EUR, BRL.")
        return clean

    @field_validator("holding_id", "payment_method")
    @classmethod
    def sanitize_strings(cls, v: str) -> str:
        return sanitize_text_input(v.strip())


class HoldingPurchaseCreditsResponse(BaseModel):
    """Confirmación de compra de créditos de IA."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="Indica si la transacción fue completada exitosamente")
    holding_id: str = Field(..., description="Identificador UUID del Holding")
    credits_purchased: int = Field(..., gt=0, description="Cantidad de créditos abonados a la billetera")
    previous_balance: int = Field(..., ge=0, description="Saldo de créditos previo a la compra")
    new_balance: int = Field(..., ge=0, description="Nuevo saldo total de créditos tras el abono")
    amount_paid: Decimal = Field(..., ge=Decimal("0.00"), description="Monto final pagado en la transacción")
    currency: str = Field(..., description="Moneda en la que se efectuó el cobro")
    transaction_id: str = Field(..., description="Identificador único de la transacción de pago")
    purchased_at: datetime = Field(..., description="Marca temporal UTC de la transacción")


# ============================================================================
# 5. GESTIÓN Y UPGRADE DE PLAN COMERCIAL
# ============================================================================


class HoldingPlanChangeRequest(BaseModel):
    """Solicitud de cambio o upgrade de plan comercial corporativo."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str = Field(..., description="Identificador UUID del Holding")
    new_plan_slug: str = Field(..., min_length=2, max_length=64, description="Slug del nuevo plan a contratar")
    effective_immediately: bool = Field(
        default=True,
        description="Si el cambio aplica inmediatamente o al final del ciclo de facturación",
    )
    reason: str | None = Field(default=None, max_length=255, description="Motivo del cambio de plan")

    @field_validator("new_plan_slug")
    @classmethod
    def sanitize_slug(cls, v: str) -> str:
        return sanitize_text_input(v.strip().lower())

    @field_validator("holding_id")
    @classmethod
    def sanitize_holding_id(cls, v: str) -> str:
        return sanitize_text_input(v.strip())

    @field_validator("reason")
    @classmethod
    def sanitize_reason(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return sanitize_text_input(v.strip())


class HoldingPlanChangeResponse(BaseModel):
    """Resultado del cambio de plan comercial corporativo."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="Indica si el cambio de plan fue ejecutado con éxito")
    holding_id: str = Field(..., description="Identificador UUID del Holding")
    previous_plan_slug: str = Field(..., description="Slug del plan anterior")
    new_plan_slug: str = Field(..., description="Slug del nuevo plan asignado")
    monthly_credits: int = Field(..., ge=0, description="Créditos mensuales incluidos en el nuevo plan")
    effective_date: datetime = Field(..., description="Fecha de entrada en vigencia del cambio")
    message: str = Field(..., description="Mensaje informativo del cambio de plan")


# ============================================================================
# 6. BENCHMARKING Y ANALÍTICA CROSS-TENANT
# ============================================================================


class HoldingBenchmarkingResponse(BaseModel):
    """Análisis comparativo (Benchmarking) entre sucursales de un Holding gastronómico."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str = Field(..., description="Identificador UUID del Holding")
    benchmark_period: str = Field(
        ...,
        description="Periodo de evaluación analizado (ej: 'last_30_days', 'current_month')",
    )
    top_performing_tenant: str | None = Field(
        default=None,
        description="Sucursal con mejor desempeño de ventas consolidado",
    )
    highest_ai_consumer: str | None = Field(
        default=None,
        description="Sucursal con mayor consumo de créditos IA",
    )
    average_tenant_sales: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Promedio de ventas por sucursal en el periodo",
    )
    average_waste_pct: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Promedio de merma de inventario de las sucursales",
    )
    tenant_comparisons: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Comparativa detallada sucursal por sucursal",
    )
