"""Capa de dominio pura del módulo operations."""
from __future__ import annotations

from src.modules.operations.domain.approvals import (
    ApprovalCategory,
    ApprovalDomainError,
    ApprovalRequest,
    ApprovalRequestId,
    ApprovalStatus,
    ApprovalType,
    InvalidApprovalTransitionError,
    InvalidRejectionReasonError,
    MoneyAmount,
    get_approval_category,
)
from src.modules.operations.domain.pos_consumption import (
    SaleItem,
    buffet_cost_per_pax,
    explode_sale_consumption,
)

__all__ = [
    "ApprovalCategory",
    "ApprovalDomainError",
    "ApprovalRequest",
    "ApprovalRequestId",
    "ApprovalStatus",
    "ApprovalType",
    "InvalidApprovalTransitionError",
    "InvalidRejectionReasonError",
    "MoneyAmount",
    "SaleItem",
    "buffet_cost_per_pax",
    "explode_sale_consumption",
    "get_approval_category",
]
