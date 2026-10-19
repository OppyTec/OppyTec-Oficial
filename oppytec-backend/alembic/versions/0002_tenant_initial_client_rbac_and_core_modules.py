"""
0002_tenant_initial_client_rbac_and_core_modules.py
Migración fundacional correlativa `0002` para los esquemas aislados `tenant_<slug>` (`TenantBase`).
Crea las tablas de RBAC del cliente, permisos JIT, doble auditoría forense, gobernanza `OppyFy`,
cuota de imágenes `tenant_media_assets` y los módulos operativos (Catálogo, Inventario, Recetas, Compras, Ventas, Analítica).
"""
from __future__ import annotations

from typing import Literal

from alembic import op
from sqlalchemy.engine import Connection

from src.modules.analytics.infrastructure import models as analytics_models
from src.modules.audit.infrastructure import models as audit_models
from src.modules.catalog.infrastructure import models as catalog_models
from src.modules.identity.infrastructure import models as identity_models
from src.modules.inventory.infrastructure import models as inventory_models
from src.modules.operations.infrastructure import models as operations_models
from src.modules.oppy_ai.infrastructure import models as oppy_ai_models
from src.modules.procurement.infrastructure import models as procurement_models
from src.modules.recipes.infrastructure import models as recipes_models
from src.modules.tenancy.infrastructure import models as tenancy_models
from src.shared.models_base import TenantBase

revision = "0002_tenant_initial_client_rbac_and_core_modules"
down_revision = "0001_public_genesis_tenancy_modules_and_global_rbac"
branch_labels = None
depends_on = None
migration_scope: Literal["public", "tenant"] = "tenant"

TENANT_MODEL_MODULES = (
    identity_models,
    tenancy_models,
    audit_models,
    catalog_models,
    inventory_models,
    recipes_models,
    procurement_models,
    operations_models,
    analytics_models,
    oppy_ai_models,
)

TENANT_TABLES_IN_ORDER: tuple[str, ...] = (
    "roles",
    "cargos",
    "permissions",
    "user_tenant_roles",
    "user_permission_grants",
    "audit_rbac_changes",
    "audit_activity_log",
    "tenant_media_assets",
    "categorias",
    "familias_producto",
    "marcas",
    "tipos_envase",
    "etiquetas_producto",
    "productos",
    "bodegas",
    "areas_operativas",
    "producto_bodegas",
    "registro_stock",
    "conteos_inventario",
    "conteo_items",
    "mermas",
    "solicitudes_aprobacion",
    "recetas",
    "receta_ingredientes",
    "combos",
    "combo_items",
    "grupos_opciones",
    "grupo_opciones_items",
    "proveedores",
    "producto_proveedores",
    "compras",
    "compra_items",
    "invoices",
    "ventas",
    "venta_recetas",
    "salones",
    "eventos",
    "buffet_templates",
    "buffet_sessions",
    "buffet_stations",
    "turnos_horarios",
    "notas_personales",
    "notas_equipo",
    "tareas",
    "kpi_snapshots",
    "financial_projections",
    "oppyfy_domains",
    "oppyfy_subdomains",
    "oppyfy_permission_grants",
    "oppyfy_worker_credit_wallets",
    "oppyfy_prompt_audit_log",
    "tenant_documents",
    "document_chunks",
    "tenant_ai_memories",
    "ai_chat_threads",
    "ai_chat_messages",
)


def upgrade() -> None:
    """Crea todas las tablas operativas de inquilino (`TenantBase.metadata`) en el esquema activo."""
    bind: Connection = op.get_bind()
    TenantBase.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    """Elimina en orden inverso todas las tablas de `TenantBase.metadata` creadas en `0002`."""
    bind: Connection = op.get_bind()
    TenantBase.metadata.drop_all(bind=bind, checkfirst=True)
