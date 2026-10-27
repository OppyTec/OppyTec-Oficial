"""
oppytec-backend/src/modules/tenancy/application/__init__.py
Servicios de aplicación para aprovisionamiento de esquemas PostgreSQL (`tenant_*`),
gestión de cupos de usuarios con `soft-delete`, gestión de cuota de almacenamiento R2 con deduplicación SHA-256,
administración de planes comerciales (`AdminPlansService`), política global SaaS (`SaaSPolicyService`)
y ajuste de cupos de créditos de IA (`CreditQuotaAdjustmentService`).
"""
from __future__ import annotations

from src.modules.tenancy.application.admin_plans_service import (
    AdminPlansService,
    SystemPlanDetailDTO,
)
from src.modules.tenancy.application.credit_quota_adjustment_service import (
    CreditQuotaAdjustmentService,
    HoldingCreditQuotaDTO,
    TenantCreditQuotaDTO,
)
from src.modules.tenancy.application.quota_service import SeatQuotaService
from src.modules.tenancy.application.saas_policy_service import (
    SaaSAIPolicyDTO,
    SaaSPolicyService,
)
from src.modules.tenancy.application.schema_provisioner import (
    ProvisionedTenantSchema,
    TenantSchemaProvisioner,
)
from src.modules.tenancy.application.storage_quota_service import (
    MediaLedgerEntry,
    StorageQuotaService,
)

__all__ = [
    "AdminPlansService",
    "CreditQuotaAdjustmentService",
    "HoldingCreditQuotaDTO",
    "MediaLedgerEntry",
    "ProvisionedTenantSchema",
    "SaaSAIPolicyDTO",
    "SaaSPolicyService",
    "SeatQuotaService",
    "StorageQuotaService",
    "SystemPlanDetailDTO",
    "TenantCreditQuotaDTO",
    "TenantSchemaProvisioner",
]
