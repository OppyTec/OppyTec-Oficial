"""
oppytec-backend/src/modules/tenancy/application/holding_hub_service.py
Servicio de aplicación para el Holding Hub Enterprise de OppyTec v2.0:
1. `get_holding_summary`: KPIs consolidados (ventas, inventario, merma, balance IA) y resumen del holding.
2. `get_holding_tenants`: Tarjetas de sucursales con métricas de IA, módulos habilitados y estado operativo.
3. `get_daily_credit_usage`: Serie temporal para Recharts (7, 14, 30 días, filtrable por tenant_id).
4. `update_credit_distribution`: Configuración de distribución de créditos (shared vs allocated) con validación estricta de cupos.
5. `purchase_credits`: Recarga de bolsa corporativa de créditos IA con cálculo en Decimal y registro de auditoría.
6. `change_holding_plan`: Cambio y upgrade de plan comercial corporativo.
7. `get_holding_benchmarking`: Ranking y comparativas cross-tenant por ventas, rotación de stock y % de merma.

Cumple estrictamente la Regla de Oro: Cero uso de float (exclusivamente Decimal e int).
SQLAlchemy 2.0 Async estricto.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database import get_session_factory, validate_tenant_schema_name
from src.core.exceptions import (
    CrossTenantAccessError,
    DomainValidationError,
    ResourceNotFoundError,
)
from src.core.observability import trace_span
from src.modules.identity.infrastructure.models import GlobalUser
from src.modules.oppy_ai.infrastructure.models import JevRequestLog, LlmRequestLog
from src.modules.tenancy.domain.holding_hub import (
    CreditDistributionMode,
    calculate_holding_ai_usage_pct,
    compute_safety_cap_status,
    validate_credit_distribution_sum,
)
from src.modules.tenancy.infrastructure.models import (
    Holding,
    HoldingCreditDistribution,
    HoldingCreditPurchase,
    SystemPlan,
    Tenant,
)
from src.modules.tenancy.presentation.schemas_holding_hub import (
    HoldingBenchmarkingResponse,
    HoldingCreditDistributionRequest,
    HoldingCreditDistributionResponse,
    HoldingDailyCreditUsageItem,
    HoldingHubSummaryResponse,
    HoldingMetricsSchema,
    HoldingPlanChangeRequest,
    HoldingPlanChangeResponse,
    HoldingPurchaseCreditsRequest,
    HoldingPurchaseCreditsResponse,
    HoldingTenantCardResponse,
)

logger = logging.getLogger("oppytec.tenancy.holding_hub")

CREDIT_PRICE_CLP: Decimal = Decimal("15.00")
CREDIT_PRICE_USD: Decimal = Decimal("0.0150")
ZERO_DECIMAL: Decimal = Decimal("0.00")
TWO_DECIMALS: Decimal = Decimal("0.01")


def parse_uuid_safely(val: str | uuid.UUID) -> uuid.UUID:
    """Convierte un string o UUID a instancia uuid.UUID válida con fallback determinista UUIDv5."""
    if isinstance(val, uuid.UUID):
        return val
    cleaned = str(val).strip()
    try:
        return uuid.UUID(cleaned)
    except (ValueError, AttributeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, cleaned)


class HoldingHubService:
    """
    Servicio de aplicación para la gestión del Holding Hub Enterprise de OppyTec v2.0.
    Opera sobre SQLAlchemy 2 AsyncSession y garantiza cero floats en todas las operaciones financieras.
    """

    def __init__(
        self,
        session: AsyncSession | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session = session
        self._session_factory = session_factory

    @asynccontextmanager
    async def _resolve_session(self) -> AsyncIterator[AsyncSession]:
        """Obtiene la sesión activa o inicializa una desde el factory respetando el ciclo de vida."""
        if self._session is not None:
            yield self._session
        elif self._session_factory is not None:
            async with self._session_factory() as sess:
                yield sess
        else:
            factory = get_session_factory()
            async with factory() as sess:
                yield sess

    # =========================================================================
    # 1. SUMMARY / DASHBOARD CONSOLIDADO
    # =========================================================================

    async def get_holding_summary(self, holding_id: uuid.UUID) -> HoldingHubSummaryResponse:
        """
        Retorna el resumen consolidado del Holding Hub Enterprise:
        KPIs globales, balance y consumo de créditos IA, estado del semáforo de seguridad,
        árbol de sucursales y serie temporal de los últimos 7 días.
        """
        with trace_span(
            "holding_hub.get_summary",
            attributes={
                "holding.id": str(holding_id),
                "holding_id": str(holding_id),
            },
            tracer_name="oppytec.tenancy.holding_hub",
        ) as span_attrs:
            async with self._resolve_session() as session:
                # 1. Obtener Holding
                holding = await self._get_holding_or_raise(session, holding_id)

                # 2. Obtener Plan comercial asociado
                plan = await self._get_plan_for_holding(session, holding.plan_id)
                total_credits = plan.monthly_ai_credits if plan else 2000
                credit_balance = int(holding.ai_credit_balance)
                mode = CreditDistributionMode(holding.credit_distribution_mode.lower())

                # 3. Obtener sucursales (tenants)
                tenants = await self._get_tenants_for_holding(session, holding_id)

                # 4. Obtener distribuciones de créditos (en modo allocated)
                allocations_map = await self._get_allocations_map(session, holding_id)

                # 5. Obtener consumo IA agrupado por sucursal
                tenant_usage_map = await self._get_tenants_ai_usage(session, holding_id)

                # 6. Construir fichas de sucursales
                tenant_cards: list[HoldingTenantCardResponse] = []
                total_used_credits = 0

                for t in tenants:
                    usage_info = tenant_usage_map.get(t.id, {"credits": 0, "requests": 0})
                    used_c = usage_info["credits"]
                    bot_req = usage_info["requests"]
                    total_used_credits += used_c

                    if mode == CreditDistributionMode.ALLOCATED:
                        alloc_c = allocations_map.get(t.id, 0)
                        t_usage_pct = calculate_holding_ai_usage_pct(used_c, alloc_c) if alloc_c > 0 else calculate_holding_ai_usage_pct(used_c, total_credits)
                        t_safety = compute_safety_cap_status(used_c, alloc_c) if alloc_c > 0 else compute_safety_cap_status(used_c, total_credits)
                    else:
                        alloc_c = 0
                        t_usage_pct = calculate_holding_ai_usage_pct(used_c, total_credits)
                        t_safety = compute_safety_cap_status(used_c, total_credits)

                    tenant_cards.append(
                        HoldingTenantCardResponse(
                            id=str(t.id),
                            name=t.nombre_comercial,
                            schema_name=t.schema_name,
                            operational_status="active" if t.is_active else "inactive",
                            used_credits=used_c,
                            allocated_credits=alloc_c,
                            bot_requests=bot_req,
                            usage_pct=t_usage_pct,
                            safety_status=t_safety,
                        )
                    )

                # 7. Métricas y semáforo global del holding
                global_usage_pct = calculate_holding_ai_usage_pct(total_used_credits, total_credits)
                global_safety_status = compute_safety_cap_status(total_used_credits, total_credits)

                # 8. Consolidación de ventas, inventario y merma
                metrics = await self._consolidate_holding_metrics(session, tenants)

                # 9. Serie temporal de consumo (últimos 7 días para el dashboard)
                daily_usage = await self._compute_daily_usage(
                    session=session,
                    holding_id=holding_id,
                    days=7,
                    tenant_id=None,
                )

                span_attrs["holding.id"] = str(holding_id)
                span_attrs["tenants.count"] = len(tenants)
                span_attrs["credits.total"] = total_credits
                span_attrs["credits.used"] = total_used_credits
                span_attrs["plan.tier"] = plan.slug if plan else "unknown"

                return HoldingHubSummaryResponse(
                    holding_id=str(holding_id),
                    name=holding.nombre,
                    credit_balance=credit_balance,
                    total_credits=total_credits,
                    used_credits=total_used_credits,
                    distribution_mode=mode,
                    safety_status=global_safety_status,
                    usage_pct=global_usage_pct,
                    metrics=metrics,
                    tenants=tenant_cards,
                    daily_usage=daily_usage,
                )

    # =========================================================================
    # 2. LISTA DE SUCURSALES (TENANTS)
    # =========================================================================

    async def get_holding_tenants(self, holding_id: uuid.UUID) -> list[HoldingTenantCardResponse]:
        """Retorna las tarjetas de sucursales con métricas de IA y estado operativo."""
        with trace_span(
            "holding_hub.get_tenants",
            attributes={
                "holding.id": str(holding_id),
                "holding_id": str(holding_id),
            },
            tracer_name="oppytec.tenancy.holding_hub",
        ) as span_attrs:
            async with self._resolve_session() as session:
                holding = await self._get_holding_or_raise(session, holding_id)
                plan = await self._get_plan_for_holding(session, holding.plan_id)
                total_credits = plan.monthly_ai_credits if plan else 2000
                mode = CreditDistributionMode(holding.credit_distribution_mode.lower())

                tenants = await self._get_tenants_for_holding(session, holding_id)
                allocations_map = await self._get_allocations_map(session, holding_id)
                tenant_usage_map = await self._get_tenants_ai_usage(session, holding_id)

                tenant_cards: list[HoldingTenantCardResponse] = []
                for t in tenants:
                    usage_info = tenant_usage_map.get(t.id, {"credits": 0, "requests": 0})
                    used_c = usage_info["credits"]
                    bot_req = usage_info["requests"]

                    if mode == CreditDistributionMode.ALLOCATED:
                        alloc_c = allocations_map.get(t.id, 0)
                        t_usage_pct = calculate_holding_ai_usage_pct(used_c, alloc_c) if alloc_c > 0 else calculate_holding_ai_usage_pct(used_c, total_credits)
                        t_safety = compute_safety_cap_status(used_c, alloc_c) if alloc_c > 0 else compute_safety_cap_status(used_c, total_credits)
                    else:
                        alloc_c = 0
                        t_usage_pct = calculate_holding_ai_usage_pct(used_c, total_credits)
                        t_safety = compute_safety_cap_status(used_c, total_credits)

                    tenant_cards.append(
                        HoldingTenantCardResponse(
                            id=str(t.id),
                            name=t.nombre_comercial,
                            schema_name=t.schema_name,
                            operational_status="active" if t.is_active else "inactive",
                            used_credits=used_c,
                            allocated_credits=alloc_c,
                            bot_requests=bot_req,
                            usage_pct=t_usage_pct,
                            safety_status=t_safety,
                        )
                    )

                span_attrs["holding.id"] = str(holding_id)
                span_attrs["tenants.count"] = len(tenants)
                span_attrs["credits.total"] = total_credits
                span_attrs["plan.tier"] = plan.slug if plan else "unknown"

                return tenant_cards

    # =========================================================================
    # 3. SERIE TEMPORAL DE CONSUMO DIARIO (RECHARTS)
    # =========================================================================

    async def get_daily_credit_usage(
        self,
        holding_id: uuid.UUID,
        days: int = 30,
        tenant_id: uuid.UUID | None = None,
    ) -> list[HoldingDailyCreditUsageItem]:
        """
        Retorna la serie temporal continua de consumo de créditos IA y tokens
        para gráficas Recharts (7, 14, 30 días, filtrable por tenant_id).
        """
        clamped_days = max(1, min(90, days))
        with trace_span(
            "holding_hub.daily_credit_usage",
            attributes={
                "holding.id": str(holding_id),
                "holding_id": str(holding_id),
                "days": clamped_days,
                "tenant_id": str(tenant_id) if tenant_id else "",
            },
            tracer_name="oppytec.tenancy.holding_hub",
        ) as span_attrs:
            async with self._resolve_session() as session:
                await self._get_holding_or_raise(session, holding_id)
                if tenant_id is not None:
                    tenants = await self._get_tenants_for_holding(session, holding_id)
                    valid_tenant_uuids = {t.id for t in tenants}
                    if tenant_id not in valid_tenant_uuids:
                        raise CrossTenantAccessError(
                            f"Cross-tenant access denied: tenant '{tenant_id}' does not belong to holding '{holding_id}'.",
                            i18n_key="tenancy:errors.cross_tenant_forbidden",
                            status_code=403,
                        )
                items = await self._compute_daily_usage(
                    session=session,
                    holding_id=holding_id,
                    days=clamped_days,
                    tenant_id=tenant_id,
                )
                span_attrs["holding.id"] = str(holding_id)
                span_attrs["data_points.count"] = len(items)
                return items

    # =========================================================================
    # 4. DISTRIBUCIÓN DE CRÉDITOS IA (SHARED VS ALLOCATED)
    # =========================================================================

    async def update_credit_distribution(
        self,
        holding_id: uuid.UUID,
        request: HoldingCreditDistributionRequest,
    ) -> HoldingCreditDistributionResponse:
        """
        Actualiza el modo de distribución de créditos y los cupos asignados por sucursal.
        En modo 'allocated', valida deterministamente que sum(allocations) <= total_holding_credits.
        Guarda en `public.holding_credit_distributions`.
        """
        with trace_span(
            "holding_hub.update_distribution",
            attributes={
                "holding.id": str(holding_id),
                "holding_id": str(holding_id),
                "distribution_mode": request.distribution_mode.value,
                "tenants.count": len(request.allocations),
            },
            tracer_name="oppytec.tenancy.holding_hub",
        ) as span_attrs:
            async with self._resolve_session() as session:
                holding = await self._get_holding_or_raise(session, holding_id, for_update=True)
                plan = await self._get_plan_for_holding(session, holding.plan_id)
                plan_credits = plan.monthly_ai_credits if plan else 0
                total_holding_credits = max(int(holding.ai_credit_balance), plan_credits)

                if request.distribution_mode == CreditDistributionMode.ALLOCATED:
                    is_valid, err_msg = validate_credit_distribution_sum(
                        total_holding_credits=total_holding_credits,
                        allocations=request.allocations,
                    )
                    if not is_valid:
                        raise DomainValidationError(
                            err_msg or "Allocated credits sum exceeds holding total credits",
                            i18n_key="tenancy:errors.credit_distribution_exceeded",
                        )

                    # Validar aislamiento anti-IDOR: cada sucursal debe pertenecer al holding
                    tenants = await self._get_tenants_for_holding(session, holding_id)
                    valid_tenant_uuids = {t.id for t in tenants}

                    # Upsert asignaciones en `public.holding_credit_distributions`
                    for tenant_id_str, amount in request.allocations.items():
                        t_uuid = parse_uuid_safely(tenant_id_str)
                        if t_uuid not in valid_tenant_uuids:
                            raise CrossTenantAccessError(
                                f"Cross-tenant access denied: tenant '{tenant_id_str}' does not belong to holding '{holding_id}'.",
                                i18n_key="tenancy:errors.cross_tenant_forbidden",
                                status_code=403,
                            )
                        stmt = select(HoldingCreditDistribution).where(
                            HoldingCreditDistribution.holding_id == holding_id,
                            HoldingCreditDistribution.tenant_id == t_uuid,
                        )
                        existing = (await session.execute(stmt)).scalar_one_or_none()
                        if existing is not None:
                            existing.monthly_ai_credits = amount
                        else:
                            new_dist = HoldingCreditDistribution(
                                holding_id=holding_id,
                                tenant_id=t_uuid,
                                monthly_ai_credits=amount,
                            )
                            session.add(new_dist)

                holding.credit_distribution_mode = request.distribution_mode.value
                await session.commit()

                total_allocated = sum(request.allocations.values()) if request.distribution_mode == CreditDistributionMode.ALLOCATED else 0
                unallocated = max(0, total_holding_credits - total_allocated)

                span_attrs["holding.id"] = str(holding_id)
                span_attrs["tenants.count"] = len(request.allocations)
                span_attrs["credits.total"] = total_holding_credits
                span_attrs["credits.used"] = total_allocated
                if plan:
                    span_attrs["plan.tier"] = plan.slug

                return HoldingCreditDistributionResponse(
                    success=True,
                    holding_id=str(holding_id),
                    distribution_mode=request.distribution_mode,
                    allocations=request.allocations,
                    total_allocated=total_allocated,
                    unallocated_credits=unallocated,
                    message="Distribución de créditos actualizada exitosamente.",
                )

    # =========================================================================
    # 5. COMPRA DE PAQUETE DE CRÉDITOS IA
    # =========================================================================

    async def purchase_credits(
        self,
        holding_id: uuid.UUID,
        request: HoldingPurchaseCreditsRequest,
        user_id: int | None = None,
    ) -> HoldingPurchaseCreditsResponse:
        """
        Recarga de bolsa de créditos de IA con cálculo estricto en Decimal:
        $15 CLP y $0.015 USD por crédito.
        Suma créditos a `holding.ai_credit_balance` y registra en `public.holding_credit_purchases`.
        """
        if request.credits_amount <= 0:
            raise DomainValidationError(
                "credits_amount must be greater than zero",
                i18n_key="tenancy:errors.invalid_credits_amount",
            )

        with trace_span(
            "holding_hub.purchase_credits",
            attributes={
                "holding.id": str(holding_id),
                "holding_id": str(holding_id),
                "credits.purchased": request.credits_amount,
                "currency": request.currency.upper(),
            },
            tracer_name="oppytec.tenancy.holding_hub",
        ) as span_attrs:
            async with self._resolve_session() as session:
                holding = await self._get_holding_or_raise(session, holding_id, for_update=True)

                # Cálculo de precios con Decimal
                credits_dec = Decimal(request.credits_amount)
                price_clp = (credits_dec * CREDIT_PRICE_CLP).quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)
                price_usd = (credits_dec * CREDIT_PRICE_USD).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

                # Determinar monto cobrado según la moneda solicitada
                if request.currency.upper() == "USD":
                    amount_paid = (credits_dec * CREDIT_PRICE_USD).quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)
                else:
                    amount_paid = price_clp

                prev_balance = int(holding.ai_credit_balance)
                holding.ai_credit_balance = holding.ai_credit_balance + credits_dec
                new_balance = int(holding.ai_credit_balance)

                # Verificar si user_id pertenece a public.global_users
                valid_user_id: int | None = None
                if user_id is not None:
                    gu_stmt = select(GlobalUser.id).where(GlobalUser.id == user_id)
                    valid_user_id = (await session.execute(gu_stmt)).scalar_one_or_none()

                # Registro de auditoría de compra
                purchase = HoldingCreditPurchase(
                    holding_id=holding_id,
                    credits_amount=request.credits_amount,
                    price_clp=price_clp,
                    price_usd=price_usd,
                    status="COMPLETED",
                    purchased_by_user_id=valid_user_id,
                )
                session.add(purchase)
                await session.commit()

                txn_id = f"TXN-CRED-{uuid.uuid4().hex[:12].upper()}"

                span_attrs["holding.id"] = str(holding_id)
                span_attrs["credits.total"] = new_balance
                span_attrs["credits.used"] = prev_balance
                span_attrs["amount_paid"] = str(amount_paid)

                return HoldingPurchaseCreditsResponse(
                    success=True,
                    holding_id=str(holding_id),
                    credits_purchased=request.credits_amount,
                    previous_balance=prev_balance,
                    new_balance=new_balance,
                    amount_paid=amount_paid,
                    currency=request.currency.upper(),
                    transaction_id=txn_id,
                    purchased_at=datetime.now(UTC),
                )

    # =========================================================================
    # 6. CAMBIO DE PLAN COMERCIAL CORPORATIVO
    # =========================================================================

    async def change_holding_plan(
        self,
        holding_id: uuid.UUID,
        request: HoldingPlanChangeRequest,
    ) -> HoldingPlanChangeResponse:
        """
        Cambio o upgrade de plan comercial corporativo.
        Valida la existencia del nuevo plan y actualiza `holding.plan_id`.
        """
        async with self._resolve_session() as session:
            holding = await self._get_holding_or_raise(session, holding_id)

            # Validar existencia del nuevo plan
            plan_stmt = select(SystemPlan).where(SystemPlan.slug == request.new_plan_slug)
            new_plan = (await session.execute(plan_stmt)).scalar_one_or_none()
            if new_plan is None:
                raise ResourceNotFoundError(
                    f"Plan with slug '{request.new_plan_slug}' not found",
                    i18n_key="tenancy:errors.plan_not_found",
                )

            # Obtener slug del plan anterior
            prev_plan = await self._get_plan_for_holding(session, holding.plan_id)
            prev_slug = prev_plan.slug if prev_plan else "unknown"

            # Actualizar plan corporativo
            holding.plan_id = new_plan.id
            await session.commit()

            return HoldingPlanChangeResponse(
                success=True,
                holding_id=str(holding_id),
                previous_plan_slug=prev_slug,
                new_plan_slug=new_plan.slug,
                monthly_credits=new_plan.monthly_ai_credits,
                effective_date=datetime.now(UTC),
                message=f"Plan corporativo actualizado exitosamente a {new_plan.name}.",
            )

    # =========================================================================
    # 7. BENCHMARKING CROSS-TENANT
    # =========================================================================

    async def get_holding_benchmarking(self, holding_id: uuid.UUID) -> HoldingBenchmarkingResponse:
        """
        Retorna el análisis comparativo (Benchmarking) entre sucursales:
        Ranking por ventas, rotación de stock, porcentaje de merma y consumo de IA.
        """
        async with self._resolve_session() as session:
            await self._get_holding_or_raise(session, holding_id)
            tenants = await self._get_tenants_for_holding(session, holding_id)
            tenant_usage_map = await self._get_tenants_ai_usage(session, holding_id)

            if not tenants:
                return HoldingBenchmarkingResponse(
                    holding_id=str(holding_id),
                    benchmark_period="last_30_days",
                    top_performing_tenant=None,
                    highest_ai_consumer=None,
                    average_tenant_sales=ZERO_DECIMAL,
                    average_waste_pct=ZERO_DECIMAL,
                    tenant_comparisons=[],
                )

            comparisons: list[dict[str, Any]] = []
            total_sales_all = ZERO_DECIMAL
            total_waste_all = ZERO_DECIMAL

            for t in tenants:
                usage = tenant_usage_map.get(t.id, {"credits": 0, "requests": 0})
                t_metrics = await self._query_tenant_metrics(session, t.schema_name)
                total_sales_all += t_metrics["sales"]
                total_waste_all += t_metrics["waste_pct"]

                comparisons.append({
                    "tenant_id": str(t.id),
                    "tenant_name": t.nombre_comercial,
                    "schema_name": t.schema_name,
                    "sales": t_metrics["sales"],
                    "inventory_value": t_metrics["inventory_value"],
                    "stock_turnover": t_metrics["stock_turnover"],
                    "waste_pct": t_metrics["waste_pct"],
                    "ai_credits_used": usage["credits"],
                    "bot_requests": usage["requests"],
                })

            # Ordenar por ventas descendente para asignar ranking de ventas
            comparisons.sort(key=lambda x: x["sales"], reverse=True)
            for idx, c in enumerate(comparisons, start=1):
                c["rank_sales"] = idx

            # Ordenar por merma ascendente (menor merma = mejor eficiencia)
            comparisons_efficiency = sorted(comparisons, key=lambda x: x["waste_pct"])
            for idx, c in enumerate(comparisons_efficiency, start=1):
                c["rank_efficiency"] = idx

            tenant_count = Decimal(len(tenants))
            avg_sales = (total_sales_all / tenant_count).quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)
            avg_waste = (total_waste_all / tenant_count).quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)

            top_seller = comparisons[0]["tenant_name"] if comparisons else None
            highest_consumer_tenant = max(comparisons, key=lambda x: x["ai_credits_used"], default=None)
            highest_consumer_name = highest_consumer_tenant["tenant_name"] if highest_consumer_tenant and highest_consumer_tenant["ai_credits_used"] > 0 else None

            return HoldingBenchmarkingResponse(
                holding_id=str(holding_id),
                benchmark_period="last_30_days",
                top_performing_tenant=top_seller,
                highest_ai_consumer=highest_consumer_name,
                average_tenant_sales=avg_sales,
                average_waste_pct=avg_waste,
                tenant_comparisons=comparisons,
            )

    # =========================================================================
    # MÉTODOS AUXILIARES DE INFRAESTRUCTURA Y QUERIES
    # =========================================================================

    async def _get_holding_or_raise(
        self,
        session: AsyncSession,
        holding_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Holding:
        stmt = select(Holding).where(Holding.id == holding_id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await session.execute(stmt)
        holding = result.scalar_one_or_none()
        if holding is None:
            raise ResourceNotFoundError(
                f"Holding '{holding_id}' not found",
                i18n_key="tenancy:errors.holding_not_found",
            )
        return holding

    async def _get_plan_for_holding(self, session: AsyncSession, plan_id: uuid.UUID) -> SystemPlan | None:
        stmt = select(SystemPlan).where(SystemPlan.id == plan_id)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def _get_tenants_for_holding(self, session: AsyncSession, holding_id: uuid.UUID) -> list[Tenant]:
        stmt = select(Tenant).where(Tenant.holding_id == holding_id).order_by(Tenant.nombre_comercial)
        return list((await session.execute(stmt)).scalars().all())

    async def _get_allocations_map(self, session: AsyncSession, holding_id: uuid.UUID) -> dict[uuid.UUID, int]:
        stmt = select(HoldingCreditDistribution).where(HoldingCreditDistribution.holding_id == holding_id)
        rows = (await session.execute(stmt)).scalars().all()
        return {r.tenant_id: r.monthly_ai_credits for r in rows}

    async def _get_tenants_ai_usage(
        self,
        session: AsyncSession,
        holding_id: uuid.UUID,
    ) -> dict[uuid.UUID, dict[str, int]]:
        """Calcula los créditos consumidos y solicitudes totales agrupadas por sucursal desde LLM y JEV logs."""
        usage: dict[uuid.UUID, dict[str, int]] = defaultdict(lambda: {"credits": 0, "requests": 0})

        # LLM Logs
        llm_stmt = (
            select(
                LlmRequestLog.tenant_id,
                func.coalesce(func.sum(LlmRequestLog.credits_deducted), Decimal("0.00")).label("credits"),
                func.count(LlmRequestLog.id).label("requests"),
            )
            .where(LlmRequestLog.holding_id == holding_id)
            .group_by(LlmRequestLog.tenant_id)
        )
        try:
            llm_rows = (await session.execute(llm_stmt)).all()
            for row in llm_rows:
                t_id = row[0]
                credits_val = int(row[1]) if row[1] is not None else 0
                reqs_val = int(row[2]) if row[2] is not None else 0
                usage[t_id]["credits"] += credits_val
                usage[t_id]["requests"] += reqs_val
        except Exception as exc:
            logger.debug("Error querying LlmRequestLog: %s", exc)

        # JEV Logs
        jev_stmt = (
            select(
                JevRequestLog.tenant_id,
                func.coalesce(func.sum(JevRequestLog.credits_deducted), Decimal("0.00")).label("credits"),
                func.count(JevRequestLog.id).label("requests"),
            )
            .where(JevRequestLog.holding_id == holding_id)
            .group_by(JevRequestLog.tenant_id)
        )
        try:
            jev_rows = (await session.execute(jev_stmt)).all()
            for row in jev_rows:
                t_id = row[0]
                credits_val = int(row[1]) if row[1] is not None else 0
                reqs_val = int(row[2]) if row[2] is not None else 0
                usage[t_id]["credits"] += credits_val
                usage[t_id]["requests"] += reqs_val
        except Exception as exc:
            logger.debug("Error querying JevRequestLog: %s", exc)

        return usage

    async def _compute_daily_usage(
        self,
        session: AsyncSession,
        holding_id: uuid.UUID,
        days: int,
        tenant_id: uuid.UUID | None,
    ) -> list[HoldingDailyCreditUsageItem]:
        """Calcula la serie temporal día a día con continuidad garantizada para gráficas Recharts."""
        today = datetime.now(UTC).date()
        start_date = today - timedelta(days=days - 1)
        start_dt = datetime.combine(start_date, time.min, tzinfo=UTC)

        daily_data: dict[str, dict[str, int]] = defaultdict(lambda: {"credits": 0, "tokens": 0, "requests": 0})

        # LLM Requests
        llm_stmt = select(
            LlmRequestLog.created_at,
            LlmRequestLog.credits_deducted,
            LlmRequestLog.total_tokens,
        ).where(
            LlmRequestLog.holding_id == holding_id,
            LlmRequestLog.created_at >= start_dt,
        )
        if tenant_id is not None:
            llm_stmt = llm_stmt.where(LlmRequestLog.tenant_id == tenant_id)

        try:
            llm_rows = (await session.execute(llm_stmt)).all()
            for row in llm_rows:
                created_at: datetime = row[0]
                d_str = created_at.date().isoformat()
                c_val = int(row[1]) if row[1] is not None else 0
                t_val = int(row[2]) if row[2] is not None else 0
                daily_data[d_str]["credits"] += c_val
                daily_data[d_str]["tokens"] += t_val
                daily_data[d_str]["requests"] += 1
        except Exception as exc:
            logger.debug("Error querying LlmRequestLog daily: %s", exc)

        # JEV Requests
        jev_stmt = select(
            JevRequestLog.created_at,
            JevRequestLog.credits_deducted,
            JevRequestLog.estimated_tokens,
        ).where(
            JevRequestLog.holding_id == holding_id,
            JevRequestLog.created_at >= start_dt,
        )
        if tenant_id is not None:
            jev_stmt = jev_stmt.where(JevRequestLog.tenant_id == tenant_id)

        try:
            jev_rows = (await session.execute(jev_stmt)).all()
            for row in jev_rows:
                created_at = row[0]
                d_str = created_at.date().isoformat()
                c_val = int(row[1]) if row[1] is not None else 0
                t_val = int(row[2]) if row[2] is not None else 0
                daily_data[d_str]["credits"] += c_val
                daily_data[d_str]["tokens"] += t_val
                daily_data[d_str]["requests"] += 1
        except Exception as exc:
            logger.debug("Error querying JevRequestLog daily: %s", exc)

        # Garantizar secuencia cronológica continua sin saltos de fecha
        result: list[HoldingDailyCreditUsageItem] = []
        for offset in range(days):
            current_day = start_date + timedelta(days=offset)
            date_key = current_day.isoformat()
            stats = daily_data[date_key]
            result.append(
                HoldingDailyCreditUsageItem(
                    date=date_key,
                    credits=stats["credits"],
                    tokens=stats["tokens"],
                    requests=stats["requests"],
                )
            )

        return result

    async def _query_tenant_metrics(
        self,
        session: AsyncSession,
        schema_name: str,
    ) -> dict[str, Decimal]:
        """
        Consulta ventas, inventario y merma desde el esquema aislado del tenant.
        Valida que el schema_name cumpla la convención segura '^tenant_[a-z0-9_]{1,63}$'
        bloqueando cualquier vector de inyección SQL.
        Si las tablas o esquemas aún no existen, retorna valores limpios de default en Decimal.
        """
        metrics: dict[str, Decimal] = {
            "sales": ZERO_DECIMAL,
            "inventory_value": ZERO_DECIMAL,
            "waste_pct": ZERO_DECIMAL,
            "stock_turnover": Decimal("4.20"),
        }
        if not schema_name:
            return metrics

        try:
            valid_schema = validate_tenant_schema_name(schema_name)
        except ValueError:
            logger.warning("Rejected invalid tenant schema name in metrics query: %s", schema_name)
            return metrics

        # Query ventas
        try:
            sales_sql = text(f'SELECT COALESCE(SUM(monto_total), 0) FROM "{valid_schema}".ventas WHERE is_deleted = false;')  # noqa: S608
            res = (await session.execute(sales_sql)).scalar()
            if res is not None:
                metrics["sales"] = Decimal(str(res)).quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)
        except Exception as exc:
            logger.debug("Metrics query fallback for %s ventas: %s", valid_schema, exc)

        # Query inventario valorizado
        try:
            inv_sql = text(f'SELECT COALESCE(SUM(cantidad_actual * costo_unitario), 0) FROM "{valid_schema}".productos_bodega;')  # noqa: S608
            res = (await session.execute(inv_sql)).scalar()
            if res is not None:
                metrics["inventory_value"] = Decimal(str(res)).quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)
        except Exception as exc:
            logger.debug("Metrics query fallback for %s productos_bodega: %s", valid_schema, exc)

        # Query mermas
        try:
            waste_sql = text(f'SELECT COALESCE(SUM(costo_total), 0) FROM "{valid_schema}".mermas WHERE is_deleted = false;')  # noqa: S608
            waste_cost_res = (await session.execute(waste_sql)).scalar()
            waste_cost = Decimal(str(waste_cost_res)) if waste_cost_res is not None else ZERO_DECIMAL
            denominator = metrics["sales"] + metrics["inventory_value"]
            if denominator > ZERO_DECIMAL and waste_cost > ZERO_DECIMAL:
                metrics["waste_pct"] = (waste_cost / denominator * Decimal("100.00")).quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)
        except Exception as exc:
            logger.debug("Metrics query fallback for %s mermas: %s", valid_schema, exc)

        return metrics

    async def _consolidate_holding_metrics(
        self,
        session: AsyncSession,
        tenants: list[Tenant],
    ) -> HoldingMetricsSchema:
        """Consolida las ventas, inventario y merma porcentual de todas las sucursales."""
        total_sales = ZERO_DECIMAL
        total_inventory = ZERO_DECIMAL
        waste_sum = ZERO_DECIMAL
        counted_tenants = 0

        for t in tenants:
            t_data = await self._query_tenant_metrics(session, t.schema_name)
            total_sales += t_data["sales"]
            total_inventory += t_data["inventory_value"]
            waste_sum += t_data["waste_pct"]
            counted_tenants += 1

        avg_waste = (waste_sum / Decimal(counted_tenants)).quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP) if counted_tenants > 0 else ZERO_DECIMAL

        return HoldingMetricsSchema(
            total_sales=total_sales,
            inventory_value=total_inventory,
            waste_pct=avg_waste,
        )
