"""
oppytec-backend/src/modules/tenancy/application/credit_quota_adjustment_service.py
Servicio de ajuste y gobernabilidad de cupos de créditos de IA para Holdings y Tenants.
Permite modificar el límite mensual y el modo de distribución (shared vs per_tenant).
Emite eventos WebSocket en tiempo real 'oppyfy.quota_adjusted'.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from opentelemetry import trace

from src.core.exceptions import DomainValidationError
from src.core.observability import trace_span
from src.core.realtime.router import get_realtime_publisher
from src.core.realtime.schemas import RealtimeEventEnvelope

logger = logging.getLogger("oppytec.tenancy.credit_quota")
tracer = trace.get_tracer("oppytec.tenancy.credit_quota")
_background_tasks: set[asyncio.Task[None]] = set()


@dataclass
class HoldingCreditQuotaDTO:
    """Estado de cuota de créditos de IA a nivel de Holding."""

    holding_id: str
    monthly_credits: int
    distribution_mode: Literal["shared", "per_tenant"]
    balance: Decimal = Decimal("0.00")


@dataclass
class TenantCreditQuotaDTO:
    """Estado de cuota de créditos de IA a nivel de Tenant individual."""

    tenant_id: str
    monthly_credits: int
    balance: Decimal = Decimal("0.00")


class CreditQuotaAdjustmentService:
    """
    Servicio de aplicación para mutación de cuotas de créditos de IA por cliente.
    """

    def __init__(self) -> None:
        self._holding_quotas: dict[str, HoldingCreditQuotaDTO] = {
            "holding_genesis": HoldingCreditQuotaDTO(
                holding_id="holding_genesis",
                monthly_credits=5000,
                distribution_mode="shared",
                balance=Decimal("5000.00"),
            ),
            "holding_pacifico": HoldingCreditQuotaDTO(
                holding_id="holding_pacifico",
                monthly_credits=10000,
                distribution_mode="per_tenant",
                balance=Decimal("10000.00"),
            ),
        }
        self._tenant_quotas: dict[str, TenantCreditQuotaDTO] = {
            "tenant_genesis": TenantCreditQuotaDTO(
                tenant_id="tenant_genesis",
                monthly_credits=2500,
                balance=Decimal("2500.00"),
            ),
            "tenant_pacifico_centro": TenantCreditQuotaDTO(
                tenant_id="tenant_pacifico_centro",
                monthly_credits=5000,
                balance=Decimal("5000.00"),
            ),
        }

    def reset(self) -> None:
        """Reinicia el estado en memoria para aislamiento de pruebas unitarias."""
        self._holding_quotas = {
            "holding_genesis": HoldingCreditQuotaDTO(
                holding_id="holding_genesis",
                monthly_credits=5000,
                distribution_mode="shared",
                balance=Decimal("5000.00"),
            ),
            "holding_pacifico": HoldingCreditQuotaDTO(
                holding_id="holding_pacifico",
                monthly_credits=10000,
                distribution_mode="per_tenant",
                balance=Decimal("10000.00"),
            ),
        }
        self._tenant_quotas = {
            "tenant_genesis": TenantCreditQuotaDTO(
                tenant_id="tenant_genesis",
                monthly_credits=2500,
                balance=Decimal("2500.00"),
            ),
            "tenant_pacifico_centro": TenantCreditQuotaDTO(
                tenant_id="tenant_pacifico_centro",
                monthly_credits=5000,
                balance=Decimal("5000.00"),
            ),
        }

    def get_holding_quota(self, holding_id: str) -> HoldingCreditQuotaDTO:
        """Obtiene la cuota de créditos de un Holding o la inicializa con valores por defecto."""
        if holding_id not in self._holding_quotas:
            self._holding_quotas[holding_id] = HoldingCreditQuotaDTO(
                holding_id=holding_id,
                monthly_credits=2000,
                distribution_mode="shared",
                balance=Decimal("2000.00"),
            )
        return self._holding_quotas[holding_id]

    def get_tenant_quota(self, tenant_id: str) -> TenantCreditQuotaDTO:
        """Obtiene la cuota de créditos de un Tenant o la inicializa con valores por defecto."""
        if tenant_id not in self._tenant_quotas:
            self._tenant_quotas[tenant_id] = TenantCreditQuotaDTO(
                tenant_id=tenant_id,
                monthly_credits=1000,
                balance=Decimal("1000.00"),
            )
        return self._tenant_quotas[tenant_id]

    def update_holding_credits(
        self,
        *,
        holding_id: str,
        monthly_credits: int,
        distribution_mode: Literal["shared", "per_tenant"] = "shared",
        actor_id: int | None = None,
    ) -> HoldingCreditQuotaDTO:
        """Actualiza el cupo mensual de créditos y modo de bolsa del Holding."""
        with trace_span(
            "platform_admin.tokens.quota_adjust",
            attributes={
                "target_type": "holding",
                "holding_id": holding_id,
                "monthly_credits": str(monthly_credits),
            },
            tracer_name="oppytec.tenancy.credit_quota",
        ):
            if monthly_credits < 0:
                raise DomainValidationError("monthly_credits no puede ser negativo")
            if distribution_mode not in ("shared", "per_tenant"):
                raise DomainValidationError(f"distribution_mode inválido: {distribution_mode}")

            quota = self.get_holding_quota(holding_id)
            quota.monthly_credits = monthly_credits
            quota.distribution_mode = distribution_mode
            quota.balance = Decimal(str(monthly_credits))

            # Notificar WebSocket
            with suppress(Exception):
                publisher = get_realtime_publisher()
                import asyncio
                envelope = RealtimeEventEnvelope(
                    event_type="oppyfy.quota_adjusted",
                    required_permission="platform_admin.tokens.read",
                    payload={
                        "target_type": "holding",
                        "holding_id": holding_id,
                        "monthly_credits": monthly_credits,
                        "distribution_mode": distribution_mode,
                        "actor_id": actor_id,
                    },
                )
                try:
                    loop = asyncio.get_running_loop()
                    task = loop.create_task(publisher.publish_event(envelope))
                    _background_tasks.add(task)
                    task.add_done_callback(_background_tasks.discard)
                except RuntimeError:
                    asyncio.run(publisher.publish_event(envelope))

            return quota

    def update_tenant_credits(
        self,
        *,
        tenant_id: str,
        monthly_credits: int,
        actor_id: int | None = None,
    ) -> TenantCreditQuotaDTO:
        """Actualiza el cupo mensual individual de créditos de una sucursal/tenant."""
        with trace_span(
            "platform_admin.tokens.quota_adjust",
            attributes={
                "target_type": "tenant",
                "tenant_id": tenant_id,
                "monthly_credits": str(monthly_credits),
            },
            tracer_name="oppytec.tenancy.credit_quota",
        ):
            if monthly_credits < 0:
                raise DomainValidationError("monthly_credits no puede ser negativo")

            quota = self.get_tenant_quota(tenant_id)
            quota.monthly_credits = monthly_credits
            quota.balance = Decimal(str(monthly_credits))

            # Notificar WebSocket
            with suppress(Exception):
                publisher = get_realtime_publisher()
                import asyncio
                envelope = RealtimeEventEnvelope(
                    event_type="oppyfy.quota_adjusted",
                    required_permission="platform_admin.tokens.read",
                    payload={
                        "target_type": "tenant",
                        "tenant_id": tenant_id,
                        "monthly_credits": monthly_credits,
                        "actor_id": actor_id,
                    },
                )
                try:
                    loop = asyncio.get_running_loop()
                    task = loop.create_task(publisher.publish_event(envelope))
                    _background_tasks.add(task)
                    task.add_done_callback(_background_tasks.discard)
                except RuntimeError:
                    asyncio.run(publisher.publish_event(envelope))

            return quota
