"""
0003_public_plans_quotas_and_tenant_capacity_overrides.py
Migración correlativa 0003 para el alcance `public`:
Expande `public.system_plans`, `public.holdings` y `public.tenants` con cuotas paramétricas
de capacidad (`max_products`, `max_suppliers`, `max_recipes`, `max_combos`) y overrides por Holding/Tenant.
"""
from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from alembic import op

revision = "0003_public_plans_quotas_and_tenant_capacity_overrides"
down_revision = "0002_tenant_initial_client_rbac_and_core_modules"
branch_labels = None
depends_on = None
migration_scope: Literal["public", "tenant"] = "public"


def upgrade() -> None:
    """Agrega columnas de cuotas de capacidad a `system_plans`, `holdings` y `tenants`."""
    op.add_column(
        "system_plans",
        sa.Column("max_products", sa.Integer(), nullable=False, server_default="500"),
        schema="public",
    )
    op.add_column(
        "system_plans",
        sa.Column("max_suppliers", sa.Integer(), nullable=False, server_default="20"),
        schema="public",
    )
    op.add_column(
        "system_plans",
        sa.Column("max_recipes", sa.Integer(), nullable=False, server_default="0"),
        schema="public",
    )
    op.add_column(
        "system_plans",
        sa.Column("max_combos", sa.Integer(), nullable=False, server_default="0"),
        schema="public",
    )

    for table_name in ("holdings", "tenants"):
        op.add_column(
            table_name,
            sa.Column("custom_max_products_override", sa.Integer(), nullable=True),
            schema="public",
        )
        op.add_column(
            table_name,
            sa.Column("custom_max_suppliers_override", sa.Integer(), nullable=True),
            schema="public",
        )
        op.add_column(
            table_name,
            sa.Column("custom_max_recipes_override", sa.Integer(), nullable=True),
            schema="public",
        )
        op.add_column(
            table_name,
            sa.Column("custom_max_combos_override", sa.Integer(), nullable=True),
            schema="public",
        )


def downgrade() -> None:
    """Revierte las columnas de cuotas paramétricas de capacidad en `public`."""
    for table_name in ("tenants", "holdings"):
        op.drop_column(table_name, "custom_max_combos_override", schema="public")
        op.drop_column(table_name, "custom_max_recipes_override", schema="public")
        op.drop_column(table_name, "custom_max_suppliers_override", schema="public")
        op.drop_column(table_name, "custom_max_products_override", schema="public")

    op.drop_column("system_plans", "max_combos", schema="public")
    op.drop_column("system_plans", "max_recipes", schema="public")
    op.drop_column("system_plans", "max_suppliers", schema="public")
    op.drop_column("system_plans", "max_products", schema="public")
