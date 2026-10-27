"""
oppytec-backend/src/modules/tenancy/application/admin_plans_service.py
Servicio de administración de Planes Comerciales de OppyTec v2.0 (`public.system_plans`):
- Listado con recuento dinámico de clientes activos (`active_clients_count`) y ordenación `tier ASC`.
- Creación con validación de slug y cuotas extendidas (`monthly_ai_credits`, `tier`, `is_popular`, `is_active`).
- Actualización de precios multi-moneda (`Decimal`) y cuotas paramétricas.
- Eliminación segura con bloqueo HTTP 409 Conflict si existen clientes asociados.
- Notificaciones WebSocket en tiempo real 'saas.plan_changed'.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from opentelemetry import trace

from src.core.bootstrap import DEFAULT_SYSTEM_PLANS, PLAN_BASICO_10_MODULES
from src.core.exceptions import (
    DomainValidationError,
    QuotaExceededError,
    ResourceNotFoundError,
)
from src.core.observability import trace_span
from src.core.realtime.router import get_realtime_publisher
from src.core.realtime.schemas import RealtimeEventEnvelope
from src.modules.tenancy.domain.saas_policy_math import PlanTier

logger = logging.getLogger("oppytec.tenancy.admin_plans")
tracer = trace.get_tracer("oppytec.tenancy.admin_plans")
_background_tasks: set[asyncio.Task[None]] = set()


@dataclass
class SystemPlanDetailDTO:
    """Detalle completo de un Plan Comercial con cuotas, créditos de IA y métricas activas."""

    slug: str
    name: str
    tier: int
    monthly_ai_credits: int
    description: str | None = None
    is_popular: bool = False
    is_active: bool = True
    max_active_users: int = 10
    max_products: int = 500
    max_suppliers: int = 20
    max_recipes: int = 0
    max_combos: int = 0
    max_storage_mb: int = 1024
    included_modules: list[str] = field(default_factory=list)
    anchor_currency: str = "CLP"
    price_clp: Decimal = Decimal("0.00")
    price_usd: Decimal = Decimal("0.00")
    price_eur: Decimal = Decimal("0.00")
    price_brl: Decimal = Decimal("0.00")
    auto_convert_fx: bool = True
    active_clients_count: int = 0


def _build_default_plans() -> dict[str, SystemPlanDetailDTO]:
    """Construye el catálogo inicial de planes con tiers e IA credits predeterminados."""
    tier_map = {"basic": 1, "starter": 2, "enterprise": 3}
    credits_map = {"basic": 1000, "starter": 2500, "enterprise": 10000}
    popular_map = {"starter": True}

    plans: dict[str, SystemPlanDetailDTO] = {}
    for p in DEFAULT_SYSTEM_PLANS:
        plans[p.slug] = SystemPlanDetailDTO(
            slug=p.slug,
            name=p.name,
            tier=tier_map.get(p.slug, 1),
            monthly_ai_credits=credits_map.get(p.slug, 1000),
            description=f"Plan comercial {p.name} con cuota mensual de IA.",
            is_popular=popular_map.get(p.slug, False),
            is_active=True,
            max_active_users=p.max_active_users,
            max_products=p.max_products,
            max_suppliers=p.max_suppliers,
            max_recipes=p.max_recipes,
            max_combos=p.max_combos,
            max_storage_mb=p.max_storage_mb,
            included_modules=list(p.included_modules),
            anchor_currency="CLP",
            price_clp=p.price_clp,
            price_usd=p.price_usd,
            price_eur=p.price_eur,
            price_brl=p.price_brl,
            auto_convert_fx=True,
            active_clients_count=0,
        )
    return plans


class AdminPlansService:
    """
    Servicio de aplicación para el ciclo de vida y gobernanza de Planes Comerciales.
    Calcula dinámicamente cuántos Holdings/Tenants están suscritos y previene borrados destructivos.
    """

    def __init__(self) -> None:
        self._plans: dict[str, SystemPlanDetailDTO] = _build_default_plans()
        # Referencia opcional a stores externos para recuento de clientes
        self._external_holdings_ref: dict[str, Any] | None = None
        self._external_tenants_ref: dict[str, Any] | None = None

    def set_clients_stores(
        self,
        holdings_store: dict[str, Any],
        tenants_store: dict[str, Any] | None = None,
    ) -> None:
        """Enlaza los almacenes de Holdings y Tenants para cómputo dinámico de clientes suscritos."""
        self._external_holdings_ref = holdings_store
        self._external_tenants_ref = tenants_store

    def reset(self) -> None:
        """Reinicia el catálogo de planes en memoria a su estado inicial."""
        self._plans = _build_default_plans()

    def _count_active_clients_for_plan(self, plan_slug: str) -> int:
        """Calcula cuántos Holdings o Tenants tienen contratado el plan."""
        count = 0
        if self._external_holdings_ref:
            for h in self._external_holdings_ref.values():
                h_slug = getattr(h, "plan_slug", None) or (
                    h.get("plan_slug") if isinstance(h, dict) else None
                )
                if h_slug == plan_slug:
                    count += 1
        return count

    def _emit_plan_event(self, action: str, plan: SystemPlanDetailDTO) -> None:
        with suppress(Exception):
            publisher = get_realtime_publisher()
            envelope = RealtimeEventEnvelope(
                event_type="saas.plan_changed",
                required_permission="platform_admin.plans.read",
                payload={
                    "action": action,
                    "slug": plan.slug,
                    "name": plan.name,
                    "tier": plan.tier,
                    "is_active": plan.is_active,
                },
            )
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(publisher.publish_event(envelope))
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)
            except RuntimeError:
                asyncio.run(publisher.publish_event(envelope))

    def list_plans(self) -> list[SystemPlanDetailDTO]:
        """
        Retorna la lista de planes comerciales ordenada por `tier ASC`,
        calculando dinámicamente `active_clients_count`.
        """
        results: list[SystemPlanDetailDTO] = []
        for plan in self._plans.values():
            active_clients = self._count_active_clients_for_plan(plan.slug)
            plan.active_clients_count = active_clients
            results.append(plan)

        # Ordenar por tier ASC, luego por precio CLP ASC
        results.sort(key=lambda p: (p.tier, p.price_clp))
        return results

    def get_plan(self, slug: str) -> SystemPlanDetailDTO:
        """Obtiene un plan por su slug único."""
        plan = self._plans.get(slug)
        if plan is None:
            raise ResourceNotFoundError(
                f"Plan comercial '{slug}' no encontrado",
                context={"slug": slug},
            )
        plan.active_clients_count = self._count_active_clients_for_plan(slug)
        return plan

    def create_plan(
        self,
        payload: dict[str, Any],
        actor_id: int | None = None,
    ) -> SystemPlanDetailDTO:
        """
        Crea un nuevo Plan Comercial validando unicidad de `slug` y cuotas válidas.
        Emite evento WebSocket `saas.plan_changed`.
        """
        _ = actor_id
        slug = str(payload.get("slug", "")).strip().lower()
        if not slug:
            raise DomainValidationError("Slug de plan es obligatorio")
        if slug in self._plans:
            raise DomainValidationError(
                f"Ya existe un plan comercial con el slug '{slug}'",
                context={"slug": slug},
            )

        tier_val = int(payload.get("tier", 1))
        PlanTier(tier_val)  # Valida tier > 0

        name = str(payload.get("name", "")).strip()
        if not name:
            raise DomainValidationError("Nombre del plan es obligatorio")

        new_plan = SystemPlanDetailDTO(
            slug=slug,
            name=name,
            tier=tier_val,
            monthly_ai_credits=int(payload.get("monthly_ai_credits", 1000)),
            description=payload.get("description"),
            is_popular=bool(payload.get("is_popular", False)),
            is_active=bool(payload.get("is_active", True)),
            max_active_users=int(payload.get("max_active_users", 10)),
            max_products=int(payload.get("max_products", 500)),
            max_suppliers=int(payload.get("max_suppliers", 20)),
            max_recipes=int(payload.get("max_recipes", 0)),
            max_combos=int(payload.get("max_combos", 0)),
            max_storage_mb=int(payload.get("max_storage_mb", 1024)),
            included_modules=list(payload.get("included_modules", PLAN_BASICO_10_MODULES)),
            anchor_currency=str(payload.get("anchor_currency", "CLP")),
            price_clp=Decimal(str(payload.get("price_clp", "0.00"))),
            price_usd=Decimal(str(payload.get("price_usd", "0.00"))),
            price_eur=Decimal(str(payload.get("price_eur", "0.00"))),
            price_brl=Decimal(str(payload.get("price_brl", "0.00"))),
            auto_convert_fx=bool(payload.get("auto_convert_fx", True)),
            active_clients_count=0,
        )

        with trace_span(
            "platform_admin.plans.upsert",
            attributes={
                "action": "create",
                "plan_slug": slug,
                "tier": str(new_plan.tier),
            },
            tracer_name="oppytec.tenancy.admin_plans",
        ):
            self._plans[slug] = new_plan
            self._emit_plan_event("CREATED", new_plan)
            return new_plan

    def update_plan(
        self,
        slug: str,
        payload: dict[str, Any],
        actor_id: int | None = None,
    ) -> SystemPlanDetailDTO:
        """
        Actualiza un plan existente conservando unicidad y emitiendo `saas.plan_changed`.
        """
        _ = actor_id
        plan = self.get_plan(slug)

        with trace_span(
            "platform_admin.plans.upsert",
            attributes={
                "action": "update",
                "plan_slug": slug,
                "tier": str(plan.tier),
            },
            tracer_name="oppytec.tenancy.admin_plans",
        ):
            if payload.get("name"):
                plan.name = str(payload["name"]).strip()
            if "tier" in payload and payload["tier"] is not None:
                plan.tier = int(PlanTier(int(payload["tier"])))
            if "monthly_ai_credits" in payload and payload["monthly_ai_credits"] is not None:
                plan.monthly_ai_credits = int(payload["monthly_ai_credits"])
            if "description" in payload:
                plan.description = payload["description"]
            if "is_popular" in payload and payload["is_popular"] is not None:
                plan.is_popular = bool(payload["is_popular"])
            if "is_active" in payload and payload["is_active"] is not None:
                plan.is_active = bool(payload["is_active"])
            if "max_active_users" in payload and payload["max_active_users"] is not None:
                plan.max_active_users = int(payload["max_active_users"])
            if "max_products" in payload and payload["max_products"] is not None:
                plan.max_products = int(payload["max_products"])
            if "max_suppliers" in payload and payload["max_suppliers"] is not None:
                plan.max_suppliers = int(payload["max_suppliers"])
            if "max_recipes" in payload and payload["max_recipes"] is not None:
                plan.max_recipes = int(payload["max_recipes"])
            if "max_combos" in payload and payload["max_combos"] is not None:
                plan.max_combos = int(payload["max_combos"])
            if "max_storage_mb" in payload and payload["max_storage_mb"] is not None:
                plan.max_storage_mb = int(payload["max_storage_mb"])
            if "included_modules" in payload and payload["included_modules"] is not None:
                plan.included_modules = list(payload["included_modules"])
            if "price_clp" in payload and payload["price_clp"] is not None:
                plan.price_clp = Decimal(str(payload["price_clp"]))
            if "price_usd" in payload and payload["price_usd"] is not None:
                plan.price_usd = Decimal(str(payload["price_usd"]))
            if "price_eur" in payload and payload["price_eur"] is not None:
                plan.price_eur = Decimal(str(payload["price_eur"]))
            if "price_brl" in payload and payload["price_brl"] is not None:
                plan.price_brl = Decimal(str(payload["price_brl"]))
            if "auto_convert_fx" in payload and payload["auto_convert_fx"] is not None:
                plan.auto_convert_fx = bool(payload["auto_convert_fx"])

            self._emit_plan_event("UPDATED", plan)
            return plan

    def delete_plan(
        self,
        slug: str,
        actor_id: int | None = None,
    ) -> SystemPlanDetailDTO:
        """
        Elimina un Plan Comercial.
        Bloquea la operación con HTTP 409 Conflict si existen Holdings o Tenants activos que lo tengan suscrito.
        """
        _ = actor_id
        plan = self.get_plan(slug)
        active_count = self._count_active_clients_for_plan(slug)

        if active_count > 0:
            raise QuotaExceededError(
                f"No se puede eliminar el plan '{slug}': existen {active_count} holding(s)/cliente(s) suscritos a él.",
                error_code="PLAN_IN_USE_CONFLICT",
                status_code=409,
                i18n_key="tenancy:errors.plan_in_use_cannot_delete",
                context={"slug": slug, "active_clients": active_count},
            )

        with trace_span(
            "platform_admin.plans.delete",
            attributes={
                "action": "delete",
                "plan_slug": slug,
            },
            tracer_name="oppytec.tenancy.admin_plans",
        ):
            self._plans.pop(slug)
            self._emit_plan_event("DELETED", plan)
            return plan
