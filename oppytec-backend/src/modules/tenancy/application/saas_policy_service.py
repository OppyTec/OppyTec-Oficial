"""
oppytec-backend/src/modules/tenancy/application/saas_policy_service.py
Servicio de aplicación para la Política Global de Conversión SaaS (tokens a créditos de IA)
y precios unitarios de venta en CLP y USD.
Cumple Regla de Oro Inviolable: Cero float, solo Decimal e int.
Emite eventos WebSocket en tiempo real 'saas.policy_updated'.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from opentelemetry import trace

from src.core.observability import trace_span
from src.core.realtime.router import get_realtime_publisher
from src.core.realtime.schemas import RealtimeEventEnvelope
from src.modules.tenancy.domain.saas_policy_math import (
    DEFAULT_CREDIT_PRICE_CLP,
    DEFAULT_CREDIT_PRICE_USD,
    DEFAULT_MONTHLY_CREDITS,
    DEFAULT_TOKENS_PER_CREDIT,
    TokenCreditConversionRate,
)

logger = logging.getLogger("oppytec.tenancy.saas_policy")
tracer = trace.get_tracer("oppytec.tenancy.saas_policy")
_background_tasks: set[asyncio.Task[None]] = set()


@dataclass
class SaaSAIPolicyDTO:
    """Configuración vigente de la política global de créditos de IA."""

    tokens_per_credit: int
    default_monthly_credits: int
    credit_price_clp: Decimal
    credit_price_usd: Decimal
    updated_at: datetime
    updated_by: int | None = None


class SaaSPolicyService:
    """
    Servicio de aplicación para consulta y mutación atómica de la política global SaaS.
    Gestiona el singleton `saas_ai_policy_config` con fallback en memoria y emisión realtime.
    """

    def __init__(self) -> None:
        self._current_policy = SaaSAIPolicyDTO(
            tokens_per_credit=DEFAULT_TOKENS_PER_CREDIT,
            default_monthly_credits=DEFAULT_MONTHLY_CREDITS,
            credit_price_clp=DEFAULT_CREDIT_PRICE_CLP,
            credit_price_usd=DEFAULT_CREDIT_PRICE_USD,
            updated_at=datetime.now(UTC),
            updated_by=None,
        )

    def reset(self) -> None:
        """Reinicia el estado en memoria para aislamiento de tests."""
        self._current_policy = SaaSAIPolicyDTO(
            tokens_per_credit=DEFAULT_TOKENS_PER_CREDIT,
            default_monthly_credits=DEFAULT_MONTHLY_CREDITS,
            credit_price_clp=DEFAULT_CREDIT_PRICE_CLP,
            credit_price_usd=DEFAULT_CREDIT_PRICE_USD,
            updated_at=datetime.now(UTC),
            updated_by=None,
        )

    def get_policy_config(self) -> SaaSAIPolicyDTO:
        """Obtiene la configuración activa de política de créditos y tokens."""
        return self._current_policy

    def update_policy_config(
        self,
        *,
        tokens_per_credit: int | None = None,
        default_monthly_credits: int | None = None,
        credit_price_clp: Decimal | None = None,
        credit_price_usd: Decimal | None = None,
        actor_id: int | None = None,
        holding_id: str | None = None,
    ) -> SaaSAIPolicyDTO:
        """
        Actualiza atómicamente la política global y emite el evento WebSocket `saas.policy_updated`.
        Valida que tokens_per_credit > 0 y default_monthly_credits >= 0.
        """
        with trace_span(
            "tenancy.saas_policy.update",
            attributes={
                "actor_id": str(actor_id or 0),
                "tokens_per_credit": str(tokens_per_credit or self._current_policy.tokens_per_credit),
            },
            tracer_name="oppytec.tenancy.saas_policy",
        ):
            new_tokens = (
                tokens_per_credit
                if tokens_per_credit is not None
                else self._current_policy.tokens_per_credit
            )
            new_credits = (
                default_monthly_credits
                if default_monthly_credits is not None
                else self._current_policy.default_monthly_credits
            )
            new_clp = (
                credit_price_clp
                if credit_price_clp is not None
                else self._current_policy.credit_price_clp
            )
            new_usd = (
                credit_price_usd
                if credit_price_usd is not None
                else self._current_policy.credit_price_usd
            )

            # Validar con Value Object de dominio
            TokenCreditConversionRate(new_tokens)
            if new_credits < 0:
                raise ValueError("default_monthly_credits cannot be negative")
            if new_clp < Decimal(0):
                raise ValueError("credit_price_clp cannot be negative")
            if new_usd < Decimal(0):
                raise ValueError("credit_price_usd cannot be negative")

            self._current_policy = SaaSAIPolicyDTO(
                tokens_per_credit=new_tokens,
                default_monthly_credits=new_credits,
                credit_price_clp=new_clp,
                credit_price_usd=new_usd,
                updated_at=datetime.now(UTC),
                updated_by=actor_id,
            )

            # Emisión de evento WebSocket
            with suppress(Exception):
                publisher = get_realtime_publisher()
                import asyncio
                envelope = RealtimeEventEnvelope(
                    event_type="saas.policy_updated",
                    holding_id=UUID(holding_id) if holding_id else None,
                    required_permission="platform_admin.plans.read",
                    payload={
                        "tokens_per_credit": self._current_policy.tokens_per_credit,
                        "default_monthly_credits": self._current_policy.default_monthly_credits,
                        "credit_price_clp": str(self._current_policy.credit_price_clp),
                        "credit_price_usd": str(self._current_policy.credit_price_usd),
                        "updated_by": self._current_policy.updated_by,
                    },
                )
                try:
                    loop = asyncio.get_running_loop()
                    task = loop.create_task(publisher.publish_event(envelope))
                    _background_tasks.add(task)
                    task.add_done_callback(_background_tasks.discard)
                except RuntimeError:
                    asyncio.run(publisher.publish_event(envelope))

            return self._current_policy
