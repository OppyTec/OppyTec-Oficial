"""
oppytec-backend/src/modules/oppy_ai/application/token_consumption_service.py
Servicio de agregación y reportería FinOps de consumo de tokens y créditos IA (`public.llm_request_logs`).
Agrupa jerárquicamente en 3 niveles: Holdings -> Tenants -> Logs individuales.
Calcula tokens de entrada/salida, costos estimados en USD/CLP (multi-moneda Decimal)
y créditos consumidos en base a la tasa de conversión activa de la política SaaS.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from src.modules.tenancy.domain.saas_policy_math import (
    DEFAULT_TOKENS_PER_CREDIT,
    DEFAULT_USD_TO_CLP_RATE,
    calculate_real_api_cost_usd,
)

logger = logging.getLogger("oppytec.oppy_ai.token_consumption")


@dataclass
class TokenLogItemDTO:
    """Registro individual de consulta a modelo de IA."""

    id: int
    created_at: datetime
    holding_id: str
    holding_name: str
    tenant_id: str
    tenant_name: str
    user_id: int
    user_name: str
    caller_feature: str
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: Decimal
    estimated_cost_clp: Decimal
    credits_deducted: Decimal
    request_duration_ms: int
    api_success: bool
    error_message: str | None = None


@dataclass
class TenantGroupDTO:
    """Grupo acumulado de consumo de tokens para un Tenant específico."""

    tenant_id: str
    tenant_name: str
    total_requests: int
    total_tokens: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: Decimal
    estimated_cost_clp: Decimal
    monthly_credit_limit: int
    credits_used: int
    credits_remaining: int
    credit_usage_pct: Decimal
    logs: list[TokenLogItemDTO] = field(default_factory=list)


@dataclass
class HoldingGroupDTO:
    """Grupo acumulado de consumo de tokens para un Holding (con sus sucursales)."""

    holding_id: str
    holding_name: str
    total_requests: int
    total_tokens: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: Decimal
    estimated_cost_clp: Decimal
    monthly_credit_limit: int
    credit_distribution_mode: str
    credits_used: int
    credits_remaining: int
    credit_usage_pct: Decimal
    tenants: list[TenantGroupDTO] = field(default_factory=list)


@dataclass
class TokenConsumptionSummaryDTO:
    """Resumen consolidado de auditoría FinOps de tokens y créditos IA."""

    holdings: list[HoldingGroupDTO]
    logs: list[TokenLogItemDTO]
    total_records: int
    total_tokens_all: int
    total_cost_usd_all: Decimal
    total_cost_clp_all: Decimal
    total_credits_used_all: int
    tokens_per_credit: int
    page: int
    page_size: int


def _build_default_sample_logs() -> list[TokenLogItemDTO]:
    """Genera logs de ejemplo representativos para Holdings y Tenants existentes."""
    now = datetime.now(UTC)
    return [
        TokenLogItemDTO(
            id=1,
            created_at=now - timedelta(minutes=45),
            holding_id="holding_genesis",
            holding_name="Holding Principal Génesis",
            tenant_id="tenant_genesis",
            tenant_name="Local Central Génesis",
            user_id=101,
            user_name="Administrador Central",
            caller_feature="recipes_kitchen",
            model_name="gemini-1.5-flash",
            input_tokens=1200,
            output_tokens=350,
            total_tokens=1550,
            estimated_cost_usd=Decimal("0.000195"),
            estimated_cost_clp=Decimal("185.25"),
            credits_deducted=Decimal("2.00"),
            request_duration_ms=450,
            api_success=True,
        ),
        TokenLogItemDTO(
            id=2,
            created_at=now - timedelta(minutes=25),
            holding_id="holding_genesis",
            holding_name="Holding Principal Génesis",
            tenant_id="tenant_genesis",
            tenant_name="Local Central Génesis",
            user_id=102,
            user_name="Chef Ejecutivo",
            caller_feature="inventory_stock",
            model_name="gemini-1.5-flash",
            input_tokens=850,
            output_tokens=220,
            total_tokens=1070,
            estimated_cost_usd=Decimal("0.000130"),
            estimated_cost_clp=Decimal("123.50"),
            credits_deducted=Decimal("2.00"),
            request_duration_ms=380,
            api_success=True,
        ),
        TokenLogItemDTO(
            id=3,
            created_at=now - timedelta(minutes=10),
            holding_id="holding_pacifico",
            holding_name="Grupo Gastronómico Pacífico SpA",
            tenant_id="tenant_pacifico_centro",
            tenant_name="Sucursal Pacífico Centro",
            user_id=201,
            user_name="Gerente Operaciones",
            caller_feature="executive_analytics",
            model_name="gemini-1.5-pro",
            input_tokens=4500,
            output_tokens=1200,
            total_tokens=5700,
            estimated_cost_usd=Decimal("0.028350"),
            estimated_cost_clp=Decimal("26932.50"),
            credits_deducted=Decimal("6.00"),
            request_duration_ms=1250,
            api_success=True,
        ),
        TokenLogItemDTO(
            id=4,
            created_at=now - timedelta(minutes=2),
            holding_id="holding_pacifico",
            holding_name="Grupo Gastronómico Pacífico SpA",
            tenant_id="tenant_pacifico_centro",
            tenant_name="Sucursal Pacífico Centro",
            user_id=202,
            user_name="Barista Principal",
            caller_feature="recipes_kitchen",
            model_name="gemini-1.5-flash",
            input_tokens=400,
            output_tokens=0,
            total_tokens=400,
            estimated_cost_usd=Decimal("0.000030"),
            estimated_cost_clp=Decimal("28.50"),
            credits_deducted=Decimal("0.00"),
            request_duration_ms=120,
            api_success=False,
            error_message="Error de timeout en upstream provider",
        ),
    ]


class TokenConsumptionAggregatorService:
    """
    Servicio de consolidación jerárquica de consumo de tokens y costos FinOps.
    """

    def __init__(self) -> None:
        self._logs: list[TokenLogItemDTO] = _build_default_sample_logs()
        self._next_id: int = 100

    def reset(self) -> None:
        """Reinicia la lista de logs a la muestra predeterminada para tests."""
        self._logs = _build_default_sample_logs()
        self._next_id = 100

    def record_log(
        self,
        *,
        holding_id: str,
        holding_name: str,
        tenant_id: str,
        tenant_name: str,
        user_id: int,
        user_name: str,
        caller_feature: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        provider_cost_usd: Decimal | None = None,
        provider_cost_clp: Decimal | None = None,
        credits_deducted: Decimal | None = None,
        request_duration_ms: int = 250,
        api_success: bool = True,
        error_message: str | None = None,
        fx_rate: Decimal = DEFAULT_USD_TO_CLP_RATE,
        tokens_per_credit: int = DEFAULT_TOKENS_PER_CREDIT,
    ) -> TokenLogItemDTO:
        """Registra un nuevo log de consumo de IA para telemetría y auditoría."""
        total_tokens = input_tokens + output_tokens
        if provider_cost_usd is None:
            pricing_tier = "gemini-1.5-pro" if "pro" in model_name.lower() else "gemini-1.5-flash"
            cost_usd = calculate_real_api_cost_usd(
                tokens=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=pricing_tier,
            )
        else:
            cost_usd = provider_cost_usd

        cost_clp = provider_cost_clp or (cost_usd * fx_rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
        credits_dec = credits_deducted or Decimal(
            str(max(1, (total_tokens + tokens_per_credit - 1) // tokens_per_credit))
        )

        item = TokenLogItemDTO(
            id=self._next_id,
            created_at=datetime.now(UTC),
            holding_id=holding_id,
            holding_name=holding_name,
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            user_id=user_id,
            user_name=user_name,
            caller_feature=caller_feature,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost_usd,
            estimated_cost_clp=cost_clp,
            credits_deducted=credits_dec,
            request_duration_ms=request_duration_ms,
            api_success=api_success,
            error_message=error_message,
        )
        self._next_id += 1
        self._logs.insert(0, item)
        return item

    def get_token_consumption_summary(
        self,
        *,
        search: str | None = None,
        model_name: str | None = None,
        api_success: bool | None = None,
        holding_id: str | None = None,
        tenant_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
        tokens_per_credit: int = DEFAULT_TOKENS_PER_CREDIT,
        holding_quotas: dict[str, Any] | None = None,
        tenant_quotas: dict[str, Any] | None = None,
    ) -> TokenConsumptionSummaryDTO:
        """
        Agrega logs y construye la jerarquía Holding -> Tenant -> Logs
        aplicando filtros, ordenación y paginación.
        """
        filtered = list(self._logs)

        # Filtros server-side
        if search:
            s_clean = search.strip().lower()
            filtered = [
                log
                for log in filtered
                if s_clean in log.holding_name.lower()
                or s_clean in log.tenant_name.lower()
                or s_clean in log.user_name.lower()
                or s_clean in log.model_name.lower()
                or s_clean in log.caller_feature.lower()
            ]

        if model_name:
            filtered = [log for log in filtered if log.model_name.lower() == model_name.strip().lower()]

        if api_success is not None:
            filtered = [log for log in filtered if log.api_success is api_success]

        if holding_id:
            filtered = [log for log in filtered if log.holding_id == holding_id]

        if tenant_id:
            filtered = [log for log in filtered if log.tenant_id == tenant_id]

        # Totales globales de los registros filtrados
        total_records = len(filtered)
        total_tokens_all = sum(log.total_tokens for log in filtered)
        total_cost_usd_all = sum(log.estimated_cost_usd for log in filtered)
        total_cost_clp_all = sum(log.estimated_cost_clp for log in filtered)

        # Conversión de créditos globales:
        total_credits_used_all = (
            (total_tokens_all + tokens_per_credit - 1) // tokens_per_credit
            if total_tokens_all > 0
            else 0
        )

        # Agrupación jerárquica: Holding -> Tenant -> Logs
        holdings_dict: dict[str, dict[str, Any]] = {}
        for log in filtered:
            h_id = log.holding_id
            if h_id not in holdings_dict:
                h_quota = holding_quotas.get(h_id) if holding_quotas else None
                monthly_limit = getattr(h_quota, "monthly_credits", 5000) if h_quota else 5000
                dist_mode = getattr(h_quota, "distribution_mode", "shared") if h_quota else "shared"

                holdings_dict[h_id] = {
                    "holding_id": h_id,
                    "holding_name": log.holding_name,
                    "total_requests": 0,
                    "total_tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "estimated_cost_usd": Decimal("0.000000"),
                    "estimated_cost_clp": Decimal("0.00"),
                    "monthly_credit_limit": monthly_limit,
                    "credit_distribution_mode": dist_mode,
                    "tenants": {},
                }

            h_entry = holdings_dict[h_id]
            h_entry["total_requests"] += 1
            h_entry["total_tokens"] += log.total_tokens
            h_entry["input_tokens"] += log.input_tokens
            h_entry["output_tokens"] += log.output_tokens
            h_entry["estimated_cost_usd"] += log.estimated_cost_usd
            h_entry["estimated_cost_clp"] += log.estimated_cost_clp

            t_id = log.tenant_id
            if t_id not in h_entry["tenants"]:
                t_quota = tenant_quotas.get(t_id) if tenant_quotas else None
                t_monthly = getattr(t_quota, "monthly_credits", 2500) if t_quota else 2500

                h_entry["tenants"][t_id] = {
                    "tenant_id": t_id,
                    "tenant_name": log.tenant_name,
                    "total_requests": 0,
                    "total_tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "estimated_cost_usd": Decimal("0.000000"),
                    "estimated_cost_clp": Decimal("0.00"),
                    "monthly_credit_limit": t_monthly,
                    "logs": [],
                }

            t_entry = h_entry["tenants"][t_id]
            t_entry["total_requests"] += 1
            t_entry["total_tokens"] += log.total_tokens
            t_entry["input_tokens"] += log.input_tokens
            t_entry["output_tokens"] += log.output_tokens
            t_entry["estimated_cost_usd"] += log.estimated_cost_usd
            t_entry["estimated_cost_clp"] += log.estimated_cost_clp
            t_entry["logs"].append(log)

        # Construcción de HoldingGroupDTOs y TenantGroupDTOs
        holding_groups: list[HoldingGroupDTO] = []
        for h_data in holdings_dict.values():
            h_tokens = h_data["total_tokens"]
            h_credits_used = (
                (h_tokens + tokens_per_credit - 1) // tokens_per_credit if h_tokens > 0 else 0
            )
            h_limit = h_data["monthly_credit_limit"]
            h_remaining = max(0, h_limit - h_credits_used)
            h_pct = (
                (Decimal(str(h_credits_used)) / Decimal(str(h_limit)) * Decimal(100)).quantize(
                    Decimal("0.1"), ROUND_HALF_UP
                )
                if h_limit > 0
                else Decimal("0.0")
            )

            tenant_groups: list[TenantGroupDTO] = []
            for t_data in h_data["tenants"].values():
                t_tokens = t_data["total_tokens"]
                t_credits_used = (
                    (t_tokens + tokens_per_credit - 1) // tokens_per_credit if t_tokens > 0 else 0
                )
                t_limit = t_data["monthly_credit_limit"]
                t_remaining = max(0, t_limit - t_credits_used)
                t_pct = (
                    (Decimal(str(t_credits_used)) / Decimal(str(t_limit)) * Decimal(100)).quantize(
                        Decimal("0.1"), ROUND_HALF_UP
                    )
                    if t_limit > 0
                    else Decimal("0.0")
                )

                tenant_groups.append(
                    TenantGroupDTO(
                        tenant_id=t_data["tenant_id"],
                        tenant_name=t_data["tenant_name"],
                        total_requests=t_data["total_requests"],
                        total_tokens=t_tokens,
                        input_tokens=t_data["input_tokens"],
                        output_tokens=t_data["output_tokens"],
                        estimated_cost_usd=t_data["estimated_cost_usd"],
                        estimated_cost_clp=t_data["estimated_cost_clp"],
                        monthly_credit_limit=t_limit,
                        credits_used=t_credits_used,
                        credits_remaining=t_remaining,
                        credit_usage_pct=t_pct,
                        logs=t_data["logs"],
                    )
                )

            holding_groups.append(
                HoldingGroupDTO(
                    holding_id=h_data["holding_id"],
                    holding_name=h_data["holding_name"],
                    total_requests=h_data["total_requests"],
                    total_tokens=h_tokens,
                    input_tokens=h_data["input_tokens"],
                    output_tokens=h_data["output_tokens"],
                    estimated_cost_usd=h_data["estimated_cost_usd"],
                    estimated_cost_clp=h_data["estimated_cost_clp"],
                    monthly_credit_limit=h_limit,
                    credit_distribution_mode=h_data["credit_distribution_mode"],
                    credits_used=h_credits_used,
                    credits_remaining=h_remaining,
                    credit_usage_pct=h_pct,
                    tenants=tenant_groups,
                )
            )

        # Paginación sobre la lista plana de logs
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_logs = filtered[start_idx:end_idx]

        return TokenConsumptionSummaryDTO(
            holdings=holding_groups,
            logs=paginated_logs,
            total_records=total_records,
            total_tokens_all=total_tokens_all,
            total_cost_usd_all=total_cost_usd_all,
            total_cost_clp_all=total_cost_clp_all,
            total_credits_used_all=total_credits_used_all,
            tokens_per_credit=tokens_per_credit,
            page=page,
            page_size=page_size,
        )

    def get_finops_analytics(
        self,
        *,
        credit_sale_price_clp: Decimal = Decimal("10.00"),
    ) -> FinOpsAnalyticsDTO:
        """Calcula márgenes brutos y desglose por modelo/proveedor para la consola FinOps."""
        filtered = self._logs
        total_tokens = sum(log.total_tokens for log in filtered)
        total_cost_usd = sum(log.estimated_cost_usd for log in filtered)
        total_cost_clp = sum(log.estimated_cost_clp for log in filtered)
        total_credits = sum(log.credits_deducted for log in filtered)
        revenue_clp = (total_credits * credit_sale_price_clp).quantize(Decimal("0.01"), ROUND_HALF_UP)
        margin_clp = revenue_clp - total_cost_clp
        margin_pct = (
            (margin_clp / revenue_clp * Decimal("100.00")).quantize(Decimal("0.01"), ROUND_HALF_UP)
            if revenue_clp > Decimal("0.00")
            else Decimal("0.00")
        )
        model_breakdown: dict[str, dict[str, Any]] = {}
        for log in filtered:
            m = log.model_name
            if m not in model_breakdown:
                model_breakdown[m] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost_usd": Decimal("0.000000"),
                    "cost_clp": Decimal("0.00"),
                }
            model_breakdown[m]["requests"] += 1
            model_breakdown[m]["tokens"] += log.total_tokens
            model_breakdown[m]["cost_usd"] += log.estimated_cost_usd
            model_breakdown[m]["cost_clp"] += log.estimated_cost_clp

        return FinOpsAnalyticsDTO(
            total_tokens=total_tokens,
            provider_cost_usd=total_cost_usd,
            provider_cost_clp=total_cost_clp,
            credits_revenue_clp=revenue_clp,
            gross_margin_clp=margin_clp,
            gross_margin_pct=margin_pct,
            model_breakdown=model_breakdown,
        )


@dataclass(frozen=True)
class FinOpsAnalyticsDTO:
    """Métricas consolidadas de rentabilidad y margen bruto para FinOps Platform Admin."""

    total_tokens: int
    provider_cost_usd: Decimal
    provider_cost_clp: Decimal
    credits_revenue_clp: Decimal
    gross_margin_clp: Decimal
    gross_margin_pct: Decimal
    model_breakdown: dict[str, dict[str, Any]]

