"""
oppytec-backend/src/modules/invoices/domain/__init__.py
Capa de Dominio del Módulo de Facturas y Contabilidad de OppyTec v2.0.
"""
from __future__ import annotations

from src.modules.invoices.domain.entities import (
    Invoice,
    InvoiceAuditFlag,
    InvoiceLineItem,
    SupplierProductAlias,
)
from src.modules.invoices.domain.exceptions import (
    InvalidInvoiceStatusTransitionError,
    InvalidPackagingFactorError,
    InvalidRUTError,
    InvoiceDomainError,
    InvoiceTotalMismatchError,
    PriceDriftThresholdExceededError,
    SupplierAliasAlreadyExistsError,
)
from src.modules.invoices.domain.ports import (
    DTEValidatorPort,
    InvoiceRepositoryPort,
    InvoiceStoragePort,
    SupplierAliasRepositoryPort,
)
from src.modules.invoices.domain.value_objects import (
    AuditRuleCode,
    AuditSeverity,
    DTEType,
    InvoiceStatus,
    MatchStatus,
    PackagingFactor,
    PriceDrift,
    TaxId,
    calculate_chilean_dv,
)

__all__ = [
    # Entities
    "Invoice",
    "InvoiceLineItem",
    "SupplierProductAlias",
    "InvoiceAuditFlag",
    # Value Objects
    "TaxId",
    "DTEType",
    "InvoiceStatus",
    "MatchStatus",
    "AuditSeverity",
    "AuditRuleCode",
    "PackagingFactor",
    "PriceDrift",
    "calculate_chilean_dv",
    # Exceptions
    "InvoiceDomainError",
    "InvalidRUTError",
    "InvoiceTotalMismatchError",
    "InvalidPackagingFactorError",
    "SupplierAliasAlreadyExistsError",
    "InvalidInvoiceStatusTransitionError",
    "PriceDriftThresholdExceededError",
    # Ports
    "InvoiceRepositoryPort",
    "SupplierAliasRepositoryPort",
    "InvoiceStoragePort",
    "DTEValidatorPort",
]
