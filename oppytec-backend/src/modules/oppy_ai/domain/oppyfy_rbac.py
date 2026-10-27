"""
Motor de Dominio del RBAC Exclusivo y 100% Editable de `OppyFy` (`src/modules/oppy_ai/domain/oppyfy_rbac.py`).
- Dominios y Sub-dominios personalizados creados/editados por el Propietario del Tenant.
- Capacidades de dominio (`OppyfyCapability`).
- Evaluación de permisos permanentes o temporales con triple control de caducidad automática:
  1. Fecha y hora (`expires_at`).
  2. Cantidad máxima de prompts (`used_prompts < max_prompts`).
  3. Techo temporal de créditos (`credits_used_in_grant + estimated_cost <= temp_credit_ceiling`).
- Denegación auditada con código `"BLOCKED_UNAUTHORIZED_PROMPT"`.
- Redacción física en código duro (`redact_cost_fields`) cuando `can_view_costs=False`.
"""
from __future__ import annotations

import functools
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

BLOCKED_UNAUTHORIZED_PROMPT: str = "BLOCKED_UNAUTHORIZED_PROMPT"
ALLOWED_PROMPT_STATUS: str = "ALLOWED"
REDACTED_COST_MARKER: str = "[REDACTED_COST]"

SENSITIVE_COST_KEYS: frozenset[str] = frozenset(
    {
        "costo_unitario",
        "costo_neto",
        "costo_total",
        "costo_receta",
        "costo_total_merma",
        "costo_teorico_clp",
        "costo_real_clp",
        "precio_compra",
        "last_purchase_price",
        "historical_avg_price",
        "total_neto",
        "total_bruto_clp",
        "subtotal_neto",
        "iva_clp",
        "total_draft_neto_clp",
        "total_draft_bruto_clp",
        "total_estimated_reorder_cost",
        "total_at_risk_cost",
        "total_shortage_cost_neto",
        "margen",
        "margen_bruto",
        "unit_cost",
        "total_cost",
        "purchase_price",
        "profit_margin",
        "food_cost_amount",
        "ventas_totales_clp",
        "ticket_promedio_clp",
        "gasto_total",
        "total_monetario",
        "monto_total",
    }
)

GrantEffectLiteral = Literal["ALLOW", "DENY"]


class OppyfyCapability(str, Enum):
    """Capacidades granulares dentro de los dominios y subdominios de OppyFy."""

    QUERY_AI = "oppyfy.capability.query_ai"
    VIEW_FINANCIAL_COSTS = "oppyfy.capability.view_financial_costs"
    EXECUTE_OPERATIONAL_TOOLS = "oppyfy.capability.execute_operational_tools"
    EXPORT_CANVAS_ARTIFACTS = "oppyfy.capability.export_canvas_artifacts"


@dataclass(frozen=True)
class EditableOppyfyDomainSpec:
    """Especificación de un Dominio de `OppyFy` editable por el Propietario del local."""

    id: int
    slug: str
    name: str
    is_enabled: bool = True
    icon: str = "sparkles"
    sort_order: int = 0


@dataclass(frozen=True)
class EditableOppyfySubdomainSpec:
    """Sub-dominio editable por el Propietario, asociado a herramientas en código duro y documentos."""

    id: int
    domain_id: int
    slug: str
    name: str
    bound_tool_codes: tuple[str, ...]
    module_slug: str = "oppy_ai"
    can_view_costs_default: bool = False


@dataclass(frozen=True)
class OppyfyPermissionGrantSpec:
    """
    Concesión de permiso permanente o temporal sobre un sub-dominio de `OppyFy`.
    Soporta triple caducidad automática (`expires_at`, `max_prompts`, `temp_credit_ceiling`).
    """

    grant_id: uuid.UUID
    subdomain_id: int
    subdomain_slug: str
    user_id: int | None = None
    role_id: int | None = None
    effect: GrantEffectLiteral = "ALLOW"
    can_query: bool = True
    can_view_costs: bool = False
    expires_at: datetime | None = None
    max_prompts: int | None = None
    used_prompts: int = 0
    temp_credit_ceiling: Decimal | None = None
    credits_used_in_grant: Decimal = Decimal("0.00")


@dataclass(frozen=True)
class OppyfyAccessDecision:
    """Resultado inmutable de la evaluación RBAC de `OppyFy`."""

    allowed: bool
    audit_code: str
    subdomain_slug: str
    can_view_costs: bool
    matched_grant_id: uuid.UUID | None
    denial_reason: str | None = None


def is_grant_currently_valid(
    grant: OppyfyPermissionGrantSpec,
    *,
    estimated_cost: Decimal,
    now: datetime | None = None,
) -> tuple[bool, str | None]:
    """
    Verifica si una concesión de permiso (`OppyfyPermissionGrantSpec`) sigue activa bajo
    el triple control de caducidad automática:
    1. Timestamp de expiración (`expires_at`).
    2. Límite de prompts utilizados (`used_prompts < max_prompts`).
    3. Techo temporal de créditos acumulados (`credits_used_in_grant + estimated_cost <= temp_credit_ceiling`).
    """
    current_time = now or datetime.now(UTC)

    if grant.expires_at is not None and current_time >= grant.expires_at:
        return False, "GRANT_EXPIRED_BY_TIMESTAMP"

    if grant.max_prompts is not None and grant.used_prompts >= grant.max_prompts:
        return False, "GRANT_EXPIRED_BY_MAX_PROMPTS"

    if (
        grant.temp_credit_ceiling is not None
        and (grant.credits_used_in_grant + estimated_cost) > grant.temp_credit_ceiling
    ):
        return False, "GRANT_EXPIRED_BY_CREDIT_CEILING"

    return True, None


def consume_grant_quota(
    grant: OppyfyPermissionGrantSpec,
    *,
    credits_spent: Decimal = Decimal("1.00"),
) -> OppyfyPermissionGrantSpec:
    """
    Primitiva pura que incrementa el contador de prompts y créditos utilizados en una concesión.
    """
    return OppyfyPermissionGrantSpec(
        grant_id=grant.grant_id,
        subdomain_id=grant.subdomain_id,
        subdomain_slug=grant.subdomain_slug,
        user_id=grant.user_id,
        role_id=grant.role_id,
        effect=grant.effect,
        can_query=grant.can_query,
        can_view_costs=grant.can_view_costs,
        expires_at=grant.expires_at,
        max_prompts=grant.max_prompts,
        used_prompts=grant.used_prompts + 1,
        temp_credit_ceiling=grant.temp_credit_ceiling,
        credits_used_in_grant=(grant.credits_used_in_grant + credits_spent).quantize(
            Decimal("0.01")
        ),
    )


def evaluate_oppyfy_subdomain_access(
    *,
    user_id: int,
    role_ids: Sequence[int],
    hierarchy_rank: int,
    target_subdomain_slug: str,
    grants: Sequence[OppyfyPermissionGrantSpec],
    estimated_cost: Decimal = Decimal("1.00"),
    contracted_modules: Sequence[str] | None = None,
    subdomain_module_slug: str = "oppy_ai",
    now: datetime | None = None,
) -> OppyfyAccessDecision:
    """
    Evalúa si el trabajador tiene permiso sobre `target_subdomain_slug`:
    - Si el módulo requerido no está contratado en el plan del Tenant, deniega.
    - El Propietario del Tenant (`hierarchy_rank == 0`) tiene acceso total y `can_view_costs=True`
      sobre todos los módulos contratados.
    - Para cualquier otro trabajador, evalúa `grants` (por `user_id` o `role_id`):
      * Si existe un `DENY` explícito vigente, bloquea inmediatamente.
      * Si existe al menos un `ALLOW` vigente (no expirado por `expires_at`, `max_prompts` ni
        `temp_credit_ceiling`), autoriza y propaga `can_view_costs`.
      * En caso contrario, retorna decisión denegada con `audit_code="BLOCKED_UNAUTHORIZED_PROMPT"`.
    """
    if contracted_modules is not None and subdomain_module_slug not in contracted_modules:
        return OppyfyAccessDecision(
            allowed=False,
            audit_code=BLOCKED_UNAUTHORIZED_PROMPT,
            subdomain_slug=target_subdomain_slug,
            can_view_costs=False,
            matched_grant_id=None,
            denial_reason="MODULE_NOT_CONTRACTED_IN_PLAN",
        )

    if hierarchy_rank == 0:
        return OppyfyAccessDecision(
            allowed=True,
            audit_code=ALLOWED_PROMPT_STATUS,
            subdomain_slug=target_subdomain_slug,
            can_view_costs=True,
            matched_grant_id=None,
            denial_reason=None,
        )

    role_id_set = set(role_ids)
    relevant_grants = [
        g
        for g in grants
        if g.subdomain_slug == target_subdomain_slug
        and (g.user_id == user_id or (g.role_id is not None and g.role_id in role_id_set))
    ]

    if not relevant_grants:
        return OppyfyAccessDecision(
            allowed=False,
            audit_code=BLOCKED_UNAUTHORIZED_PROMPT,
            subdomain_slug=target_subdomain_slug,
            can_view_costs=False,
            matched_grant_id=None,
            denial_reason="NO_MATCHING_OPPYFY_GRANT",
        )

    last_expiration_reason: str | None = None
    valid_allow_grants: list[OppyfyPermissionGrantSpec] = []

    for grant in relevant_grants:
        is_valid, expiration_reason = is_grant_currently_valid(
            grant,
            estimated_cost=estimated_cost,
            now=now,
        )
        if not is_valid:
            last_expiration_reason = expiration_reason
            continue

        if grant.effect == "DENY":
            return OppyfyAccessDecision(
                allowed=False,
                audit_code=BLOCKED_UNAUTHORIZED_PROMPT,
                subdomain_slug=target_subdomain_slug,
                can_view_costs=False,
                matched_grant_id=grant.grant_id,
                denial_reason="EXPLICIT_DENY_GRANT",
            )
        valid_allow_grants.append(grant)

    if not valid_allow_grants:
        return OppyfyAccessDecision(
            allowed=False,
            audit_code=BLOCKED_UNAUTHORIZED_PROMPT,
            subdomain_slug=target_subdomain_slug,
            can_view_costs=False,
            matched_grant_id=None,
            denial_reason=last_expiration_reason or "ALL_GRANTS_EXPIRED",
        )

    chosen_grant = valid_allow_grants[0]
    can_view_costs = any(g.can_view_costs for g in valid_allow_grants)
    return OppyfyAccessDecision(
        allowed=True,
        audit_code=ALLOWED_PROMPT_STATUS,
        subdomain_slug=target_subdomain_slug,
        can_view_costs=can_view_costs,
        matched_grant_id=chosen_grant.grant_id,
        denial_reason=None,
    )


def validate_hierarchical_delegation(
    *,
    grantor_rank: int,
    grantee_rank: int,
    grantor_has_subdomain_permission: bool,
) -> bool:
    """
    Verifica la regla de delegación por rango (`hierarchy_rank`):
    - El Propietario (`Rank 0`) puede delegar a cualquier rango (`> 0`).
    - Un superior (`grantor_rank < grantee_rank`) solo puede otorgar permisos que él mismo posea.
    """
    if grantor_rank == 0:
        return True
    if grantor_rank >= grantee_rank:
        return False
    return grantor_has_subdomain_permission


PayloadValue = str | int | Decimal | bool | list[dict[str, str | int | Decimal | bool]]


def _redact_value(val: Any) -> Any:
    if isinstance(val, Mapping):
        clean_dict: dict[str, Any] = {}
        for k, v in val.items():
            k_lower = str(k).lower()
            if k_lower in SENSITIVE_COST_KEYS or any(
                token in k_lower for token in (
                    "costo", "cost", "margen", "margin", "precio", "gasto", "monetario", "monto", "tarifa", "fee", "presupuesto"
                )
            ):
                clean_dict[k] = REDACTED_COST_MARKER
            else:
                clean_dict[k] = _redact_value(v)
        return clean_dict
    if isinstance(val, (list, tuple)):
        return [_redact_value(item) for item in val]
    return val


def redact_cost_fields(
    payload: Mapping[str, PayloadValue],
    *,
    can_view_costs: bool,
) -> dict[str, PayloadValue]:
    """
    Redacta físicamente en código duro (`"[REDACTED_COST]"`) todos los campos financieros y de costo
    cuando `can_view_costs=False`, garantizando que el LLM jamás reciba información sensible.
    """
    if can_view_costs:
        return dict(payload)

    redacted: dict[str, PayloadValue] = {}
    for key, val in payload.items():
        key_lower = str(key).lower()
        is_sensitive = key_lower in SENSITIVE_COST_KEYS or any(
            token in key_lower for token in (
                "costo", "cost", "margen", "margin", "precio", "gasto", "monetario", "monto", "tarifa", "fee", "presupuesto"
            )
        )
        if is_sensitive:
            redacted[key] = REDACTED_COST_MARKER
        elif isinstance(val, Mapping):
            redacted[key] = _redact_value(val)
        elif isinstance(val, (list, tuple)):
            redacted[key] = [_redact_value(item) for item in val]
        else:
            redacted[key] = val
    return redacted


def hardcoded_data_stripping(
    func: Any,
) -> Any:
    """
    Decorador para herramientas operativas deterministas (JEV Layer 2).
    Garantiza la redacción en código duro de campos financieros y de costo
    cuando `can_view_costs=False`. Si no se especifica `can_view_costs`,
    se asume `True` para preservar el payload original del cálculo interno.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, can_view_costs: bool = True, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)
        if isinstance(result, Mapping):
            return redact_cost_fields(result, can_view_costs=can_view_costs)
        return result

    return wrapper

