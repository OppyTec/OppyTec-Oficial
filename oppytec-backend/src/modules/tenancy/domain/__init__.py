"""
oppytec-backend/src/modules/tenancy/domain/__init__.py
Capa de dominio pura para jerarquía corporativa `Holding -> LegalEntity (1:1) -> Tenant`,
cupos de usuarios activos (`Seat Quotas` con liberación instantánea por `soft-delete`),
cuotas de memoria en Cloudflare R2 (`Storage Quotas`), niveles jerárquicos de planes (`PlanTier`),
conversión de tokens a créditos IA y finanzas SaaS (`saas_policy_math`).
"""
from __future__ import annotations

from src.modules.tenancy.domain.quotas import (
    ClientUserSeatState,
    SeatQuotaEvaluation,
    StorageQuotaEvaluation,
    TenantHierarchyAssignment,
    evaluate_seat_quota_for_new_or_restored_user,
    evaluate_storage_quota_bytes,
    resolve_effective_max_storage_mb,
    resolve_effective_max_users,
    validate_holding_legal_entity_tenant_cardinality,
)
from src.modules.tenancy.domain.saas_policy_math import (
    DEFAULT_CREDIT_PRICE_CLP,
    DEFAULT_CREDIT_PRICE_USD,
    DEFAULT_MONTHLY_CREDITS,
    DEFAULT_TOKENS_PER_CREDIT,
    DEFAULT_USD_TO_CLP_RATE,
    GEMINI_FLASH_BLENDED_COST_PER_M,
    GEMINI_FLASH_INPUT_COST_PER_M,
    GEMINI_FLASH_OUTPUT_COST_PER_M,
    GEMINI_PRO_BLENDED_COST_PER_M,
    PlanTier,
    SimulatedProfitMargin,
    TokenCreditConversionRate,
    calculate_real_api_cost_usd,
    calculate_simulated_profit_margin,
)

__all__ = [
    "ClientUserSeatState",
    "DEFAULT_CREDIT_PRICE_CLP",
    "DEFAULT_CREDIT_PRICE_USD",
    "DEFAULT_MONTHLY_CREDITS",
    "DEFAULT_TOKENS_PER_CREDIT",
    "DEFAULT_USD_TO_CLP_RATE",
    "GEMINI_FLASH_BLENDED_COST_PER_M",
    "GEMINI_FLASH_INPUT_COST_PER_M",
    "GEMINI_FLASH_OUTPUT_COST_PER_M",
    "GEMINI_PRO_BLENDED_COST_PER_M",
    "PlanTier",
    "SeatQuotaEvaluation",
    "SimulatedProfitMargin",
    "StorageQuotaEvaluation",
    "TenantHierarchyAssignment",
    "TokenCreditConversionRate",
    "calculate_real_api_cost_usd",
    "calculate_simulated_profit_margin",
    "evaluate_seat_quota_for_new_or_restored_user",
    "evaluate_storage_quota_bytes",
    "resolve_effective_max_storage_mb",
    "resolve_effective_max_users",
    "validate_holding_legal_entity_tenant_cardinality",
]
