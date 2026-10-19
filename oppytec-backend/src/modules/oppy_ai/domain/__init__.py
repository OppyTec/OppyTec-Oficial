"""
Dominio Puro de `OppyFy` (`oppytec-backend/src/modules/oppy_ai/domain/`):
- `oppyfy_rbac.py`: RBAC propio y 100% editable de `OppyFy` con triple caducidad temporal y redacción de costos.
- `credit_wallet.py`: Paquetes de créditos acumulables sin caducidad (`1000 + 10000 = 11000`) y billetera por trabajador.
- `context_meter.py`: Medidor anti-alucinación del porcentaje de ventana de contexto (`Decimal`).
"""
from __future__ import annotations

from src.modules.oppy_ai.domain.context_meter import (
    ContextHealthEvaluation,
    ContextHealthStatus,
    ThreadCompactionSummary,
    compact_thread_for_fresh_handover,
    evaluate_context_usage,
)
from src.modules.oppy_ai.domain.credit_wallet import (
    CreditDeductionResult,
    CreditPackageSpec,
    HoldingCreditPool,
    WorkerCreditWalletState,
    allocate_credits_to_worker,
    deduct_worker_credits,
    stack_credit_packages,
)
from src.modules.oppy_ai.domain.oppyfy_rbac import (
    BLOCKED_UNAUTHORIZED_PROMPT,
    REDACTED_COST_MARKER,
    SENSITIVE_COST_KEYS,
    EditableOppyfyDomainSpec,
    EditableOppyfySubdomainSpec,
    OppyfyAccessDecision,
    OppyfyPermissionGrantSpec,
    evaluate_oppyfy_subdomain_access,
    redact_cost_fields,
)

__all__ = [
    "BLOCKED_UNAUTHORIZED_PROMPT",
    "REDACTED_COST_MARKER",
    "SENSITIVE_COST_KEYS",
    "ContextHealthEvaluation",
    "ContextHealthStatus",
    "CreditDeductionResult",
    "CreditPackageSpec",
    "EditableOppyfyDomainSpec",
    "EditableOppyfySubdomainSpec",
    "HoldingCreditPool",
    "OppyfyAccessDecision",
    "OppyfyPermissionGrantSpec",
    "ThreadCompactionSummary",
    "WorkerCreditWalletState",
    "allocate_credits_to_worker",
    "compact_thread_for_fresh_handover",
    "deduct_worker_credits",
    "evaluate_context_usage",
    "evaluate_oppyfy_subdomain_access",
    "redact_cost_fields",
    "stack_credit_packages",
]
