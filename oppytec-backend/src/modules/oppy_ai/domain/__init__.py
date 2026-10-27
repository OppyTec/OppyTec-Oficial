"""
Dominio Puro de `OppyFy` (`oppytec-backend/src/modules/oppy_ai/domain/`):
- `ai_credit_packs.py`: Primitiva de dominio para paquetes de créditos IA independientes con bonos y descuentos por plan base.
- `context_meter.py`: Medidor anti-alucinación de contexto (semáforo Verde/Ámbar/Rojo, bloqueo al >85% y rollover al 5%).
- `credit_wallet.py`: Billetera de créditos acumulables sin caducidad, comprobación de cupos por trabajador y políticas de cuota.
- `oppyfy_rbac.py`: RBAC propio y 100% editable de `OppyFy` con triple caducidad temporal y redacción de costos en código duro.
"""
from __future__ import annotations

from src.modules.oppy_ai.domain.ai_credit_packs import (
    AiCreditPack,
    evaluate_pack_plan_match,
    stack_ai_credit_packs,
)
from src.modules.oppy_ai.domain.context_meter import (
    AMBER_MAX_PERCENT,
    AMBER_START_PERCENT,
    COMPACTION_REQUIRED_PERCENT,
    DEFAULT_MAX_SAFE_THREAD_TOKENS,
    FRESH_THREAD_INITIAL_PERCENT,
    GREEN_MAX_PERCENT,
    MAX_SAFE_THREAD_TOKENS,
    PREVENTIVE_ALERT_THRESHOLD_PERCENT,
    ContextHealthEvaluation,
    ContextHealthStatus,
    ThreadCompactionSummary,
    calculate_safe_rollover_token_budget,
    compact_thread_for_fresh_handover,
    evaluate_context_usage,
)
from src.modules.oppy_ai.domain.credit_wallet import (
    CreditDeductionResult,
    CreditPackageSpec,
    HoldingCreditPool,
    WorkerCreditWalletState,
    WorkerQuotaPolicy,
    allocate_credits_to_worker,
    calculate_wallet_balance,
    check_worker_quota_policy,
    deduct_worker_credits,
    stack_credit_packages,
)
from src.modules.oppy_ai.domain.oppyfy_rbac import (
    ALLOWED_PROMPT_STATUS,
    BLOCKED_UNAUTHORIZED_PROMPT,
    REDACTED_COST_MARKER,
    SENSITIVE_COST_KEYS,
    EditableOppyfyDomainSpec,
    EditableOppyfySubdomainSpec,
    OppyfyAccessDecision,
    OppyfyCapability,
    OppyfyPermissionGrantSpec,
    consume_grant_quota,
    evaluate_oppyfy_subdomain_access,
    hardcoded_data_stripping,
    is_grant_currently_valid,
    redact_cost_fields,
    validate_hierarchical_delegation,
)

__all__ = [
    "ALLOWED_PROMPT_STATUS",
    "AMBER_MAX_PERCENT",
    "AMBER_START_PERCENT",
    "BLOCKED_UNAUTHORIZED_PROMPT",
    "COMPACTION_REQUIRED_PERCENT",
    "DEFAULT_MAX_SAFE_THREAD_TOKENS",
    "FRESH_THREAD_INITIAL_PERCENT",
    "GREEN_MAX_PERCENT",
    "MAX_SAFE_THREAD_TOKENS",
    "PREVENTIVE_ALERT_THRESHOLD_PERCENT",
    "REDACTED_COST_MARKER",
    "SENSITIVE_COST_KEYS",
    "AiCreditPack",
    "ContextHealthEvaluation",
    "ContextHealthStatus",
    "CreditDeductionResult",
    "CreditPackageSpec",
    "EditableOppyfyDomainSpec",
    "EditableOppyfySubdomainSpec",
    "HoldingCreditPool",
    "OppyfyAccessDecision",
    "OppyfyCapability",
    "OppyfyPermissionGrantSpec",
    "ThreadCompactionSummary",
    "WorkerCreditWalletState",
    "WorkerQuotaPolicy",
    "allocate_credits_to_worker",
    "calculate_safe_rollover_token_budget",
    "calculate_wallet_balance",
    "check_worker_quota_policy",
    "compact_thread_for_fresh_handover",
    "consume_grant_quota",
    "deduct_worker_credits",
    "evaluate_context_usage",
    "evaluate_oppyfy_subdomain_access",
    "evaluate_pack_plan_match",
    "hardcoded_data_stripping",
    "is_grant_currently_valid",
    "redact_cost_fields",
    "stack_ai_credit_packs",
    "stack_credit_packages",
    "validate_hierarchical_delegation",
]
