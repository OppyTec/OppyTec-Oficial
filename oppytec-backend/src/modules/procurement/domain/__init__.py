"""
Capa de dominio pura del módulo procurement.
Cumple Regla 02 (Clean Architecture: 0 imports de infraestructura, 0% float).
"""
from __future__ import annotations

from src.modules.procurement.domain.entities import (
    PurchaseIncidence,
    PurchaseItem,
    PurchaseOrder,
    Supplier,
)
from src.modules.procurement.domain.exceptions import (
    DomainValidationError,
    InvalidPurchaseStatusTransitionError,
    InvalidRutError,
    NegativeMoneyError,
    NegativeQuantityError,
    ProcurementDomainError,
    ProperNounImmutabilityError,
    ZeroDivisionPPPError,
)
from src.modules.procurement.domain.reconciliation import (
    DocLine,
    MatchStatus,
    ReconciliationResult,
    assert_supplier_name_immutable,
    document_total,
    reconcile_three_way,
)
from src.modules.procurement.domain.value_objects import (
    CHILEAN_RUT_FACTORS,
    INTL_TAX_ID_PATTERN,
    MAX_MONEY_AMOUNT,
    MONEY_QUANT,
    IncidenceResolution,
    IncidenceType,
    MoneyAmount,
    PurchaseStatus,
    RutTaxId,
    calculate_chilean_dv,
    calculate_reception_ppp,
)

__all__ = [
    # Reconciliation
    "DocLine",
    "MatchStatus",
    "ReconciliationResult",
    "assert_supplier_name_immutable",
    "document_total",
    "reconcile_three_way",
    # Exceptions
    "DomainValidationError",
    "InvalidPurchaseStatusTransitionError",
    "InvalidRutError",
    "NegativeMoneyError",
    "NegativeQuantityError",
    "ProcurementDomainError",
    "ProperNounImmutabilityError",
    "ZeroDivisionPPPError",
    # Value Objects
    "CHILEAN_RUT_FACTORS",
    "INTL_TAX_ID_PATTERN",
    "MAX_MONEY_AMOUNT",
    "MONEY_QUANT",
    "IncidenceResolution",
    "IncidenceType",
    "MoneyAmount",
    "PurchaseStatus",
    "RutTaxId",
    "calculate_chilean_dv",
    "calculate_reception_ppp",
    # Entities
    "PurchaseIncidence",
    "PurchaseItem",
    "PurchaseOrder",
    "Supplier",
]
