"""
0007_public_system_plans_extension_and_saas_policy.py
Migración correlativa 0007 para el alcance `public`:
Implementa la Fase 1 de PLAN_MAESTRO_PLANES_Y_TOKENS.md:
- Extensión de `public.system_plans`: description, monthly_ai_credits, tier, is_popular, is_active.
- Creación de tabla singleton `public.saas_ai_policy_config`: política global de conversión de tokens y créditos IA.
- Inserción de seed inicial por defecto en `public.saas_ai_policy_config` (id=1).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

import sqlalchemy as sa
from alembic import op

revision = "0007_public_system_plans_extension_and_saas_policy"
down_revision = "0006_tenant_approval_requests_and_notification_matrix"
branch_labels = None
depends_on = None
migration_scope: Literal["public", "tenant"] = "public"


def _has_table(table_name: str, schema: str = "public") -> bool | None:
    try:
        bind = op.get_bind()
        insp = sa.inspect(bind)
        tables = insp.get_table_names(schema=schema)
        return table_name in tables
    except Exception:
        return None


def _has_column(table_name: str, column_name: str, schema: str = "public") -> bool | None:
    try:
        bind = op.get_bind()
        insp = sa.inspect(bind)
        cols = [c["name"] for c in insp.get_columns(table_name, schema=schema)]
        return column_name in cols
    except Exception:
        return None


def _has_index(table_name: str, index_name: str, schema: str = "public") -> bool | None:
    try:
        bind = op.get_bind()
        insp = sa.inspect(bind)
        indexes = [ix["name"] for ix in insp.get_indexes(table_name, schema=schema)]
        return index_name in indexes
    except Exception:
        return None


def upgrade() -> None:
    """Aplica la extensión de planes comerciales y tabla de política IA en el esquema `public`."""
    # 1. Extensión de columnas en `public.system_plans`
    if _has_column("system_plans", "description", schema="public") is not True:
        op.add_column(
            "system_plans",
            sa.Column("description", sa.Text(), nullable=True),
            schema="public",
        )
    if _has_column("system_plans", "monthly_ai_credits", schema="public") is not True:
        op.add_column(
            "system_plans",
            sa.Column("monthly_ai_credits", sa.Integer(), nullable=False, server_default="1000"),
            schema="public",
        )
    if _has_column("system_plans", "tier", schema="public") is not True:
        op.add_column(
            "system_plans",
            sa.Column("tier", sa.SmallInteger(), nullable=False, server_default="1"),
            schema="public",
        )
    if _has_column("system_plans", "is_popular", schema="public") is not True:
        op.add_column(
            "system_plans",
            sa.Column("is_popular", sa.Boolean(), nullable=False, server_default="false"),
            schema="public",
        )
    if _has_column("system_plans", "is_active", schema="public") is not True:
        op.add_column(
            "system_plans",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            schema="public",
        )

    # Índices en `public.system_plans`
    if _has_index("system_plans", "ix_system_plans_tier", schema="public") is not True:
        op.create_index(
            "ix_system_plans_tier",
            "system_plans",
            ["tier"],
            schema="public",
        )
    if _has_index("system_plans", "ix_system_plans_is_active", schema="public") is not True:
        op.create_index(
            "ix_system_plans_is_active",
            "system_plans",
            ["is_active"],
            schema="public",
        )

    # 2. Creación de tabla `public.saas_ai_policy_config`
    if _has_table("saas_ai_policy_config", schema="public") is not True:
        op.create_table(
            "saas_ai_policy_config",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
            sa.Column("tokens_per_credit", sa.Integer(), nullable=False, server_default="1000"),
            sa.Column("default_monthly_credits", sa.Integer(), nullable=False, server_default="2000"),
            sa.Column("credit_price_clp", sa.Numeric(14, 2), nullable=False, server_default="15.00"),
            sa.Column("credit_price_usd", sa.Numeric(14, 4), nullable=False, server_default="0.0150"),
            sa.Column(
                "updated_by",
                sa.Integer(),
                sa.ForeignKey("public.global_users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema="public",
        )

    # 3. Inserción de seed inicial para el registro singleton id=1
    policy_table = sa.table(
        "saas_ai_policy_config",
        sa.column("id", sa.Integer),
        sa.column("tokens_per_credit", sa.Integer),
        sa.column("default_monthly_credits", sa.Integer),
        sa.column("credit_price_clp", sa.Numeric),
        sa.column("credit_price_usd", sa.Numeric),
    )
    bind = op.get_bind()
    try:
        exists = bind.execute(
            sa.text("SELECT 1 FROM public.saas_ai_policy_config WHERE id = 1")
        ).scalar()
        if not exists:
            op.bulk_insert(
                policy_table,
                [
                    {
                        "id": 1,
                        "tokens_per_credit": 1000,
                        "default_monthly_credits": 2000,
                        "credit_price_clp": Decimal("15.00"),
                        "credit_price_usd": Decimal("0.0150"),
                    }
                ],
            )
    except Exception:  # noqa: S110
        pass


def downgrade() -> None:
    """Revierte simétricamente los cambios de `0007` en el esquema `public`."""
    # 1. Dropear tabla `public.saas_ai_policy_config`
    if _has_table("saas_ai_policy_config", schema="public") is not False:
        op.drop_table("saas_ai_policy_config", schema="public")

    # 2. Dropear índices de `public.system_plans`
    if _has_index("system_plans", "ix_system_plans_is_active", schema="public") is not False:
        op.drop_index("ix_system_plans_is_active", table_name="system_plans", schema="public")
    if _has_index("system_plans", "ix_system_plans_tier", schema="public") is not False:
        op.drop_index("ix_system_plans_tier", table_name="system_plans", schema="public")

    # 3. Dropear columnas añadidas a `public.system_plans`
    if _has_column("system_plans", "is_active", schema="public") is not False:
        op.drop_column("system_plans", "is_active", schema="public")
    if _has_column("system_plans", "is_popular", schema="public") is not False:
        op.drop_column("system_plans", "is_popular", schema="public")
    if _has_column("system_plans", "tier", schema="public") is not False:
        op.drop_column("system_plans", "tier", schema="public")
    if _has_column("system_plans", "monthly_ai_credits", schema="public") is not False:
        op.drop_column("system_plans", "monthly_ai_credits", schema="public")
    if _has_column("system_plans", "description", schema="public") is not False:
        op.drop_column("system_plans", "description", schema="public")
