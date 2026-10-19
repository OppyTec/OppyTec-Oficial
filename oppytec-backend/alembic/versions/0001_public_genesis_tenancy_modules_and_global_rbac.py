"""
0001_public_genesis_tenancy_modules_and_global_rbac.py
Migración fundacional correlativa `0001` para el esquema global `public` (`PublicBase`).
Crea las tablas de identidad global, jerarquía multi-tenant (`Holding -> LegalEntity 1:1 -> Tenant`),
planes multi-moneda, catálogo de módulos, telemetría `llm_request_logs`, memoria `i18n`, tasas `FX` y backups.
"""
from __future__ import annotations

from typing import Literal

from alembic import op
from sqlalchemy.engine import Connection

from src.modules.audit.infrastructure import models as audit_models
from src.modules.identity.infrastructure import models as identity_models
from src.modules.oppy_ai.infrastructure import models as oppy_ai_models
from src.modules.tenancy.infrastructure import models as tenancy_models
from src.shared.models_base import PublicBase

revision = "0001_public_genesis_tenancy_modules_and_global_rbac"
down_revision = None
branch_labels = None
depends_on = None
migration_scope: Literal["public", "tenant"] = "public"

PUBLIC_MODEL_MODULES = (
    identity_models,
    tenancy_models,
    audit_models,
    oppy_ai_models,
)

PUBLIC_TABLES_IN_ORDER: tuple[str, ...] = (
    "global_users",
    "global_roles",
    "global_permissions",
    "global_user_permission_grants",
    "global_audit_rbac_changes",
    "global_audit_activity_log",
    "system_plans",
    "holdings",
    "legal_entities",
    "tenants",
    "app_modules",
    "tenant_modules",
    "client_users",
    "client_user_tenant_access",
    "i18n_translation_memory",
    "fx_current_rates",
    "fx_rate_history",
    "fx_audit_log",
    "backup_execution_logs",
    "llm_request_logs",
    "audio_request_logs",
    "ai_model_configs",
    "ai_credit_packages",
    "spec_sync_metadata",
    "spec_chunks",
)


def upgrade() -> None:
    """Crea todas las tablas del Plano de Control Global (`PublicBase.metadata`) en `public`."""
    bind: Connection = op.get_bind()
    PublicBase.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    """Elimina en orden inverso todas las tablas del esquema `public` creadas en `0001`."""
    bind: Connection = op.get_bind()
    PublicBase.metadata.drop_all(bind=bind, checkfirst=True)
