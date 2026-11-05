"""
0018_public_holding_hub_credit_distribution_and_purchases.py
Migración correlativa 0018 para el alcance `public`:
Implementa la base de datos para la Etapa 1 del Holding Hub Enterprise:
- Agrega `credit_distribution_mode` a `public.holdings` ('shared' | 'per_tenant').
- Crea `public.holding_credit_distributions` para reparto de cuotas mensuales de IA por tenant.
- Crea `public.holding_credit_purchases` para compras de paquetes de créditos de IA con montos Decimal/Numeric.
"""
from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0018_public_holding_hub_credit_distribution_and_purchases"
down_revision = "0017_public_ai_benchmarks_and_tenant_feedback"
branch_labels = None
depends_on = None
migration_scope: Literal["public", "tenant"] = "public"


def _is_postgresql() -> bool:
    try:
        bind = op.get_bind()
        return bind.dialect.name == "postgresql"
    except Exception:
        return True


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


def upgrade() -> None:
    """Aplica la adición de columnas y tablas del Holding Hub en el esquema `public`."""
    is_pg = _is_postgresql()
    uuid_type = postgresql.UUID(as_uuid=True) if is_pg else sa.Uuid()

    # 1. Modificar public.holdings agregando credit_distribution_mode
    if _has_column("holdings", "credit_distribution_mode", schema="public") is not True:
        op.add_column(
            "holdings",
            sa.Column(
                "credit_distribution_mode",
                sa.String(20),
                server_default="shared",
                nullable=False,
            ),
            schema="public",
        )

    # 2. Crear tabla public.holding_credit_distributions
    if _has_table("holding_credit_distributions", schema="public") is not True:
        op.create_table(
            "holding_credit_distributions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "holding_id",
                uuid_type,
                sa.ForeignKey("public.holdings.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "tenant_id",
                uuid_type,
                sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("monthly_ai_credits", sa.Integer(), server_default="2000", nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.UniqueConstraint("holding_id", "tenant_id", name="uq_holding_tenant_credit_distribution"),
            schema="public",
        )

    # 3. Crear tabla public.holding_credit_purchases
    if _has_table("holding_credit_purchases", schema="public") is not True:
        op.create_table(
            "holding_credit_purchases",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "holding_id",
                uuid_type,
                sa.ForeignKey("public.holdings.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("credits_amount", sa.Integer(), nullable=False),
            sa.Column("price_clp", sa.Numeric(14, 2), nullable=False),
            sa.Column("price_usd", sa.Numeric(14, 4), nullable=False),
            sa.Column("status", sa.String(32), server_default="COMPLETED", nullable=False),
            sa.Column(
                "purchased_by_user_id",
                sa.Integer(),
                sa.ForeignKey("public.global_users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            schema="public",
        )


def downgrade() -> None:
    """Revierte simétricamente en orden LIFO las tablas y columnas creadas en public."""
    # 1. Eliminar tabla public.holding_credit_purchases
    if _has_table("holding_credit_purchases", schema="public") is not False:
        op.drop_table("holding_credit_purchases", schema="public")

    # 2. Eliminar tabla public.holding_credit_distributions
    if _has_table("holding_credit_distributions", schema="public") is not False:
        op.drop_table("holding_credit_distributions", schema="public")

    # 3. Eliminar columna credit_distribution_mode de public.holdings
    if _has_column("holdings", "credit_distribution_mode", schema="public") is not False:
        op.drop_column("holdings", "credit_distribution_mode", schema="public")
