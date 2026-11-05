"""
oppytec-backend/src/modules/tenancy/domain/holding_hub.py
Capa de dominio pura para Holding Hub Enterprise en OppyTec v2.0:
1. Modelos de Dominio y Value Objects inmutables con `@dataclass(frozen=True)` y `Decimal`.
2. Modos de distribución de créditos de IA (`CreditDistributionMode.SHARED` vs `ALLOCATED`).
3. Reglas de negocio puras para agregación de métricas, semáforos de seguridad (Safety Cap)
   y validación determinista de presupuestos de créditos cross-tenant.
Cumple estrictamente la Regla de Oro: Cero uso de `float` (exclusivamente `Decimal` e `int`),
sin dependencias de infraestructura ni frameworks web (FastAPI, SQLAlchemy, Pydantic).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from src.core.exceptions import DomainValidationError

# ============================================================================
# CONSTANTES DE DOMINIO Y UMBRALES DE SEGURIDAD (SAFETY CAP)
# ============================================================================

ZERO_DECIMAL = Decimal("0.00")
ONE_HUNDRED_DECIMAL = Decimal("100.00")
TWO_DECIMALS_PRECISION = Decimal("0.01")

WARNING_USAGE_PCT_THRESHOLD = Decimal("80.00")
CRITICAL_USAGE_PCT_THRESHOLD = Decimal("95.00")


# ============================================================================
# 1. ENUMS Y VALUE OBJECTS
# ============================================================================


class CreditDistributionMode(StrEnum):
    """
    Modo de distribución de la billetera de créditos IA a nivel de Holding:
    - SHARED: Todas las sucursales consumen de un pozo único centralizado.
    - ALLOCATED: Cada sucursal tiene un cupo fijo preasignado que no puede exceder.
    """

    SHARED = "shared"
    ALLOCATED = "allocated"


@dataclass(frozen=True)
class HoldingMetricsVO:
    """
    Métricas consolidadas de negocio de un Holding gastronómico.
    Garantiza Cero floats: todos los valores monetarios y porcentuales son `Decimal`.
    """

    total_sales: Decimal
    inventory_value: Decimal
    waste_pct: Decimal

    def __post_init__(self) -> None:
        if (
            type(self.total_sales).__name__ == "float"
            or type(self.inventory_value).__name__ == "float"
            or type(self.waste_pct).__name__ == "float"
        ):
            raise DomainValidationError(
                "Prohibido el uso de float en HoldingMetricsVO (Regla de Oro). Use Decimal."
            )

        if not isinstance(self.total_sales, Decimal):
            object.__setattr__(self, "total_sales", Decimal(str(self.total_sales)))
        if not isinstance(self.inventory_value, Decimal):
            object.__setattr__(self, "inventory_value", Decimal(str(self.inventory_value)))
        if not isinstance(self.waste_pct, Decimal):
            object.__setattr__(self, "waste_pct", Decimal(str(self.waste_pct)))

        if self.total_sales < ZERO_DECIMAL:
            raise DomainValidationError("total_sales cannot be negative")
        if self.inventory_value < ZERO_DECIMAL:
            raise DomainValidationError("inventory_value cannot be negative")
        if self.waste_pct < ZERO_DECIMAL or self.waste_pct > ONE_HUNDRED_DECIMAL:
            raise DomainValidationError("waste_pct must be between 0.00 and 100.00")

    @property
    def ventas_totales(self) -> Decimal:
        """Alias en español para paridad de lenguaje ubicuo."""
        return self.total_sales

    @property
    def valor_inventario(self) -> Decimal:
        """Alias en español para paridad de lenguaje ubicuo."""
        return self.inventory_value

    @property
    def merma_porcentual(self) -> Decimal:
        """Alias en español para paridad de lenguaje ubicuo."""
        return self.waste_pct


@dataclass(frozen=True, init=False)
class TenantCardVO:
    """
    Ficha representativa de una sucursal (Tenant) dentro de la vista Holding Hub.
    Inmutable, soporta constructores tanto con campos en español como en inglés.
    """

    id: str
    nombre: str
    schema_name: str
    estado_operativo: str
    creditos_usados: int
    creditos_asignados: int
    solicitudes_bot: int

    def __init__(
        self,
        id: str | None = None,
        nombre: str | None = None,
        schema_name: str = "",
        estado_operativo: str = "active",
        creditos_usados: int = 0,
        creditos_asignados: int = 0,
        solicitudes_bot: int = 0,
        *,
        tenant_id: str | None = None,
        name: str | None = None,
        operational_status: str | None = None,
        used_credits: int | None = None,
        allocated_credits: int | None = None,
        bot_requests: int | None = None,
    ) -> None:
        resolved_id = id if id is not None else tenant_id
        resolved_name = nombre if nombre is not None else name
        resolved_status = (
            estado_operativo if operational_status is None else operational_status
        )
        resolved_used = (
            creditos_usados if used_credits is None else used_credits
        )
        resolved_allocated = (
            creditos_asignados if allocated_credits is None else allocated_credits
        )
        resolved_requests = (
            solicitudes_bot if bot_requests is None else bot_requests
        )

        if not resolved_id or not str(resolved_id).strip():
            raise DomainValidationError("TenantCardVO requires a non-empty id")
        if not resolved_name or not str(resolved_name).strip():
            raise DomainValidationError("TenantCardVO requires a non-empty nombre/name")
        if not schema_name or not str(schema_name).strip():
            raise DomainValidationError("TenantCardVO requires a non-empty schema_name")

        for num_val, field_name in (
            (resolved_used, "used_credits"),
            (resolved_allocated, "allocated_credits"),
            (resolved_requests, "bot_requests"),
        ):
            if type(num_val).__name__ == "float":
                raise DomainValidationError(
                    f"Prohibido el uso de float en TenantCardVO para '{field_name}'. Use int."
                )
            if not isinstance(num_val, int):
                raise DomainValidationError(
                    f"El campo '{field_name}' de TenantCardVO debe ser un entero."
                )
            if num_val < 0:
                raise DomainValidationError(
                    f"El campo '{field_name}' de TenantCardVO no puede ser negativo."
                )

        object.__setattr__(self, "id", str(resolved_id).strip())
        object.__setattr__(self, "nombre", str(resolved_name).strip())
        object.__setattr__(self, "schema_name", str(schema_name).strip())
        object.__setattr__(self, "estado_operativo", str(resolved_status).strip())
        object.__setattr__(self, "creditos_usados", resolved_used)
        object.__setattr__(self, "creditos_asignados", resolved_allocated)
        object.__setattr__(self, "solicitudes_bot", resolved_requests)

    @property
    def tenant_id(self) -> str:
        return self.id

    @property
    def name(self) -> str:
        return self.nombre

    @property
    def operational_status(self) -> str:
        return self.estado_operativo

    @property
    def used_credits(self) -> int:
        return self.creditos_usados

    @property
    def allocated_credits(self) -> int:
        return self.creditos_asignados

    @property
    def bot_requests(self) -> int:
        return self.solicitudes_bot


@dataclass(frozen=True)
class DailyUsagePointVO:
    """
    Punto diario de telemetría de consumo IA en la serie temporal del Holding.
    Garantiza cero floats y no negatividad.
    """

    date: str
    credits: int
    tokens: int
    requests: int

    def __post_init__(self) -> None:
        if not self.date or not str(self.date).strip():
            raise DomainValidationError("DailyUsagePointVO requires a non-empty date")

        for num_val, field_name in (
            (self.credits, "credits"),
            (self.tokens, "tokens"),
            (self.requests, "requests"),
        ):
            if type(num_val).__name__ == "float":
                raise DomainValidationError(
                    f"Prohibido el uso de float en DailyUsagePointVO para '{field_name}'. Use int."
                )
            if not isinstance(num_val, int):
                raise DomainValidationError(
                    f"El campo '{field_name}' de DailyUsagePointVO debe ser un entero."
                )
            if num_val < 0:
                raise DomainValidationError(
                    f"El campo '{field_name}' de DailyUsagePointVO no puede ser negativo."
                )


@dataclass(frozen=True, init=False)
class HoldingSummaryVO:
    """
    Resumen corporativo inmutable del Holding Hub con sus KPIs consolidados,
    balance central de créditos IA, modo de distribución y árbol de sucursales.
    """

    holding_id: str
    nombre: str
    balance_creditos: int
    modo_distribucion: CreditDistributionMode
    sucursales: tuple[TenantCardVO, ...]
    kpis_globales: HoldingMetricsVO

    def __init__(
        self,
        holding_id: str,
        nombre: str | None = None,
        balance_creditos: int | None = None,
        modo_distribucion: CreditDistributionMode | str | None = None,
        sucursales: Sequence[TenantCardVO] | None = None,
        kpis_globales: HoldingMetricsVO | None = None,
        *,
        name: str | None = None,
        credit_balance: int | None = None,
        distribution_mode: CreditDistributionMode | str | None = None,
        tenants: Sequence[TenantCardVO] | None = None,
        metrics: HoldingMetricsVO | None = None,
    ) -> None:
        if not holding_id or not str(holding_id).strip():
            raise DomainValidationError("HoldingSummaryVO requires a non-empty holding_id")

        resolved_name = nombre if nombre is not None else name
        if not resolved_name or not str(resolved_name).strip():
            raise DomainValidationError("HoldingSummaryVO requires a non-empty nombre/name")

        resolved_balance = (
            balance_creditos if credit_balance is None else credit_balance
        )
        if resolved_balance is None:
            raise DomainValidationError("HoldingSummaryVO requires balance_creditos/credit_balance")
        if type(resolved_balance).__name__ == "float":
            raise DomainValidationError("Prohibido el uso de float para balance_creditos. Use int.")
        if not isinstance(resolved_balance, int):
            raise DomainValidationError("balance_creditos debe ser un entero.")
        if resolved_balance < 0:
            raise DomainValidationError("balance_creditos cannot be negative")

        resolved_mode_raw = (
            modo_distribucion if distribution_mode is None else distribution_mode
        )
        if resolved_mode_raw is None:
            resolved_mode = CreditDistributionMode.SHARED
        elif isinstance(resolved_mode_raw, CreditDistributionMode):
            resolved_mode = resolved_mode_raw
        elif isinstance(resolved_mode_raw, str):
            try:
                resolved_mode = CreditDistributionMode(resolved_mode_raw.lower())
            except ValueError as err:
                raise DomainValidationError(
                    f"Modo de distribución inválido: '{resolved_mode_raw}'. Use 'shared' o 'allocated'."
                ) from err
        else:
            raise DomainValidationError("modo_distribucion debe ser CreditDistributionMode o str")

        resolved_tenants_raw = sucursales if tenants is None else tenants
        if resolved_tenants_raw is None:
            resolved_tenants: tuple[TenantCardVO, ...] = ()
        else:
            for item in resolved_tenants_raw:
                if not isinstance(item, TenantCardVO):
                    raise DomainValidationError(
                        f"Elemento de sucursales debe ser instancia de TenantCardVO, recibido: {type(item)}"
                    )
            resolved_tenants = tuple(resolved_tenants_raw)

        resolved_metrics = kpis_globales if metrics is None else metrics
        if resolved_metrics is None:
            raise DomainValidationError("HoldingSummaryVO requires kpis_globales/metrics")
        if not isinstance(resolved_metrics, HoldingMetricsVO):
            raise DomainValidationError(
                f"kpis_globales debe ser instancia de HoldingMetricsVO, recibido: {type(resolved_metrics)}"
            )

        object.__setattr__(self, "holding_id", str(holding_id).strip())
        object.__setattr__(self, "nombre", str(resolved_name).strip())
        object.__setattr__(self, "balance_creditos", resolved_balance)
        object.__setattr__(self, "modo_distribucion", resolved_mode)
        object.__setattr__(self, "sucursales", resolved_tenants)
        object.__setattr__(self, "kpis_globales", resolved_metrics)

    @property
    def name(self) -> str:
        return self.nombre

    @property
    def credit_balance(self) -> int:
        return self.balance_creditos

    @property
    def distribution_mode(self) -> CreditDistributionMode:
        return self.modo_distribucion

    @property
    def tenants(self) -> tuple[TenantCardVO, ...]:
        return self.sucursales

    @property
    def metrics(self) -> HoldingMetricsVO:
        return self.kpis_globales


# ============================================================================
# 2. REGLAS PURAS DE DOMINIO (CERO FLOATS, ESTRICTO INT Y DECIMAL)
# ============================================================================


def validate_credit_distribution_sum(
    total_holding_credits: int,
    allocations: dict[str, int],
) -> tuple[bool, str | None]:
    """
    Valida que la suma de créditos asignados a las sucursales no exceda
    el saldo total disponible en la billetera corporativa del Holding.

    Invariantes:
    1. Cero floats permitidos.
    2. total_holding_credits >= 0.
    3. Ninguna asignación individual puede ser negativa.
    4. sum(allocations.values()) <= total_holding_credits.
    """
    if type(total_holding_credits).__name__ == "float":
        raise DomainValidationError("Prohibido el uso de float en total_holding_credits. Use int.")

    if not isinstance(total_holding_credits, int):
        raise DomainValidationError("total_holding_credits debe ser un entero.")

    if total_holding_credits < 0:
        return (False, "Total holding credits cannot be negative")

    total_allocated = 0
    for tenant_id, amount in allocations.items():
        if type(amount).__name__ == "float":
            raise DomainValidationError(
                f"Prohibido el uso de float en asignación para tenant '{tenant_id}'. Use int."
            )
        if not isinstance(amount, int):
            raise DomainValidationError(
                f"Asignación para tenant '{tenant_id}' debe ser un entero."
            )
        if amount < 0:
            return (
                False,
                f"Allocation for tenant '{tenant_id}' cannot be negative: {amount}",
            )
        total_allocated += amount

    if total_allocated > total_holding_credits:
        return (
            False,
            f"Allocated credits sum ({total_allocated}) exceeds holding total credits ({total_holding_credits})",
        )

    return (True, None)


def calculate_holding_ai_usage_pct(
    used_credits: int,
    total_credits: int,
) -> Decimal:
    """
    Calcula el porcentaje de utilización de créditos IA del Holding con precisión
    de 2 decimales (`ROUND_HALF_UP`). Cero floats garantizado.

    Invariantes:
    - used_credits >= 0, total_credits >= 0.
    - Si total_credits == 0:
        - Si used_credits == 0 -> Decimal("0.00")
        - Si used_credits > 0 -> Decimal("100.00")
    - pct = (used_credits / total_credits * 100).quantize(Decimal("0.01"))
    """
    if type(used_credits).__name__ == "float" or type(total_credits).__name__ == "float":
        raise DomainValidationError(
            "Prohibido el uso de float en calculate_holding_ai_usage_pct. Use int."
        )

    if not isinstance(used_credits, int) or not isinstance(total_credits, int):
        raise DomainValidationError("used_credits y total_credits deben ser enteros.")

    if used_credits < 0:
        raise DomainValidationError("used_credits cannot be negative")
    if total_credits < 0:
        raise DomainValidationError("total_credits cannot be negative")

    if total_credits == 0:
        if used_credits == 0:
            return ZERO_DECIMAL
        return ONE_HUNDRED_DECIMAL

    pct = (
        Decimal(used_credits) / Decimal(total_credits) * ONE_HUNDRED_DECIMAL
    ).quantize(TWO_DECIMALS_PRECISION, rounding=ROUND_HALF_UP)
    return pct


def compute_safety_cap_status(
    used_credits: int,
    total_credits: int,
) -> str:
    """
    Determina el estado del semáforo de seguridad (Safety Cap) para el Holding:
    - NORMAL: Consumo < 80.00%
    - WARNING: 80.00% <= Consumo < 95.00%
    - CRITICAL: Consumo >= 95.00%
    """
    usage_pct = calculate_holding_ai_usage_pct(
        used_credits=used_credits,
        total_credits=total_credits,
    )

    if usage_pct < WARNING_USAGE_PCT_THRESHOLD:
        return "NORMAL"
    if usage_pct < CRITICAL_USAGE_PCT_THRESHOLD:
        return "WARNING"
    return "CRITICAL"
