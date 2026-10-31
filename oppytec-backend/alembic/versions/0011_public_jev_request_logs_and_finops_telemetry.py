"""
0011_public_jev_request_logs_and_finops_telemetry.py
Migración correlativa 0011 para el alcance `public`:
Implementa la Fase 1 del Motor JEV y telemetría de decisiones sub-simbólicas:
- Creación de tabla `public.jev_request_logs`: Bitácora inmutable Append-Only de decisiones JEV,
  evaluaciones de confianza calibrada, micro-costos FinOps y métricas de latencia.
- Índices de rendimiento y agregación: `idx_jev_logs_tenant_created`, `idx_jev_logs_holding_created`,
  `idx_jev_logs_feature`, `idx_jev_logs_confidence`.
"""
from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from alembic import op

revision = "0011_public_jev_request_logs_and_finops_telemetry"
down_revision = "0010_tenant_oppyfy_custom_rbac_and_credit_wallets"
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


def _has_index(table_name: str, index_name: str, schema: str = "public") -> bool | None:
    try:
        bind = op.get_bind()
        insp = sa.inspect(bind)
        indexes = [ix["name"] for ix in insp.get_indexes(table_name, schema=schema)]
        return index_name in indexes
    except Exception:
        return None


def upgrade() -> None:
    """Crea la tabla `public.jev_request_logs` con sus columnas e índices de alta concurrencia."""
    is_pg = _is_postgresql()
    uuid_server_default = sa.text("gen_random_uuid()") if is_pg else None

    # 1. Creación de tabla `public.jev_request_logs`
    if _has_table("jev_request_logs", schema="public") is not True:
        op.create_table(
            "jev_request_logs",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=uuid_server_default),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("holding_id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("tenant_schema", sa.String(length=63), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("trace_id", sa.String(length=64), nullable=True),
            sa.Column("caller_feature", sa.String(length=64), nullable=False),
            sa.Column("decision_id", sa.String(length=64), nullable=False),
            sa.Column("decision_primitive", sa.String(length=16), nullable=False),
            sa.Column("input_summary", sa.String(length=255), nullable=False),
            sa.Column("result_value", sa.String(length=128), nullable=False),
            sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False),
            sa.Column("calibrated_action", sa.String(length=24), nullable=False),
            sa.Column("model_name", sa.String(length=64), nullable=False),
            sa.Column("estimated_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("provider_cost_usd", sa.Numeric(14, 6), nullable=False, server_default="0.000000"),
            sa.Column("provider_cost_clp", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("credits_deducted", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
            sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("error_message", sa.Text(), nullable=True),
            schema="public",
        )

    # 2. Creación de índices en `public.jev_request_logs`
    if _has_index("jev_request_logs", "idx_jev_logs_tenant_created", schema="public") is not True:
        op.create_index(
            "idx_jev_logs_tenant_created",
            "jev_request_logs",
            ["tenant_id", "created_at"],
            schema="public",
        )
    if _has_index("jev_request_logs", "idx_jev_logs_holding_created", schema="public") is not True:
        op.create_index(
            "idx_jev_logs_holding_created",
            "jev_request_logs",
            ["holding_id", "created_at"],
            schema="public",
        )
    if _has_index("jev_request_logs", "idx_jev_logs_feature", schema="public") is not True:
        op.create_index(
            "idx_jev_logs_feature",
            "jev_request_logs",
            ["caller_feature"],
            schema="public",
        )
    if _has_index("jev_request_logs", "idx_jev_logs_confidence", schema="public") is not True:
        op.create_index(
            "idx_jev_logs_confidence",
            "jev_request_logs",
            ["confidence_score"],
            schema="public",
        )
    if _has_index("jev_request_logs", "ix_jev_request_logs_tenant_schema", schema="public") is not True:
        op.create_index(
            "ix_jev_request_logs_tenant_schema",
            "jev_request_logs",
            ["tenant_schema"],
            schema="public",
        )
    if _has_index("jev_request_logs", "ix_jev_request_logs_user_id", schema="public") is not True:
        op.create_index(
            "ix_jev_request_logs_user_id",
            "jev_request_logs",
            ["user_id"],
            schema="public",
        )
    if _has_index("jev_request_logs", "ix_jev_request_logs_created_at", schema="public") is not True:
        op.create_index(
            "ix_jev_request_logs_created_at",
            "jev_request_logs",
            ["created_at"],
            schema="public",
        )


def downgrade() -> None:
    """Revierte simétricamente la creación de `public.jev_request_logs`."""
    if _has_table("jev_request_logs", schema="public") is not False:
        for idx in (
            "ix_jev_request_logs_created_at",
            "ix_jev_request_logs_user_id",
            "ix_jev_request_logs_tenant_schema",
            "idx_jev_logs_confidence",
            "idx_jev_logs_feature",
            "idx_jev_logs_holding_created",
            "idx_jev_logs_tenant_created",
        ):
            if _has_index("jev_request_logs", idx, schema="public") is True:
                op.drop_index(idx, table_name="jev_request_logs", schema="public")
        op.drop_table("jev_request_logs", schema="public")
