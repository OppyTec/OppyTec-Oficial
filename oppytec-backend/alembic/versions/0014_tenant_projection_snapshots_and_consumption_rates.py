"""
0014_tenant_projection_snapshots_and_consumption_rates.py
Migración correlativa 0014 para el alcance `tenant`:
Implementa la Fase 1 del PLAN_MAESTRO_PROYECCION.md:
- `daily_consumption_rates`: Tasa histórica móvil de consumo diario (7, 30, 90 días) calculada desde Kardex.
- `projection_snapshots`: Snapshot persistente de proyecciones y simulación FEFO por producto, bodega y horizonte temporal,
  almacenando la curva de simulación en JSONB para lecturas ultrarrápidas (< 25ms).
- Constraints e índices relacionales ON DELETE CASCADE para esquemas dinámicos `tenant_*`.
"""
from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014_tenant_projection_snapshots_and_consumption_rates"
down_revision = "0013_tenant_events_salones_and_reservations"
branch_labels = None
depends_on = None
migration_scope: Literal["public", "tenant"] = "tenant"


def _get_current_schema() -> str | None:
    try:
        bind = op.get_bind()
        return bind.execute(sa.text("SELECT current_schema()")).scalar()
    except Exception:
        return None


def _is_postgresql() -> bool:
    try:
        bind = op.get_bind()
        return bind.dialect.name == "postgresql"
    except Exception:
        return True


def _get_tenant_schemas(bind: sa.engine.Connection) -> list[str]:
    """Descubre todos los esquemas tenant_* dinámicos registrados en PostgreSQL."""
    try:
        res = bind.execute(
            sa.text(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name LIKE 'tenant_%' "
                "ORDER BY schema_name"
            )
        )
        return [row[0] for row in res.fetchall()]
    except Exception:
        return []


def _has_table(table_name: str, schema: str | None = None) -> bool | None:
    try:
        bind = op.get_bind()
        insp = sa.inspect(bind)
        tables = insp.get_table_names(schema=schema)
        return table_name in tables
    except Exception:
        return None


def _has_index(table_name: str, index_name: str, schema: str | None = None) -> bool | None:
    try:
        bind = op.get_bind()
        insp = sa.inspect(bind)
        indexes = [ix["name"] for ix in insp.get_indexes(table_name, schema=schema)]
        return index_name in indexes
    except Exception:
        return None


def _apply_tenant_upgrade_to_schema(schema: str | None) -> None:
    """Aplica las tablas e índices de proyección dentro de un esquema tenant_*."""
    is_pg = _is_postgresql()
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    json_empty_array = sa.text("'[]'::jsonb") if is_pg else sa.text("'[]'")

    prod_fk = f"{schema}.productos.id" if schema else "productos.id"
    bod_fk = f"{schema}.bodegas.id" if schema else "bodegas.id"

    # 1. Tabla `daily_consumption_rates`
    if _has_table("daily_consumption_rates", schema=schema) is not True:
        op.create_table(
            "daily_consumption_rates",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "producto_id",
                sa.BigInteger(),
                sa.ForeignKey(prod_fk, ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "bodega_id",
                sa.BigInteger(),
                sa.ForeignKey(bod_fk, ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column(
                "rate_7d",
                sa.Numeric(12, 4),
                nullable=False,
                server_default=sa.text("0.0000"),
            ),
            sa.Column(
                "rate_30d",
                sa.Numeric(12, 4),
                nullable=False,
                server_default=sa.text("0.0000"),
            ),
            sa.Column(
                "rate_90d",
                sa.Numeric(12, 4),
                nullable=False,
                server_default=sa.text("0.0000"),
            ),
            sa.Column(
                "last_calculated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "producto_id",
                "bodega_id",
                name="uq_daily_consumption_rates_prod_bod",
            ),
            schema=schema,
        )

    if _has_table("daily_consumption_rates", schema=schema) is True:
        if _has_index("daily_consumption_rates", "ix_daily_consumption_rates_producto_id", schema=schema) is not True:
            op.create_index(
                "ix_daily_consumption_rates_producto_id",
                "daily_consumption_rates",
                ["producto_id"],
                schema=schema,
            )
        if _has_index("daily_consumption_rates", "ix_daily_consumption_rates_bodega_id", schema=schema) is not True:
            op.create_index(
                "ix_daily_consumption_rates_bodega_id",
                "daily_consumption_rates",
                ["bodega_id"],
                schema=schema,
            )

    # 2. Tabla `projection_snapshots`
    if _has_table("projection_snapshots", schema=schema) is not True:
        op.create_table(
            "projection_snapshots",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "producto_id",
                sa.BigInteger(),
                sa.ForeignKey(prod_fk, ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "bodega_id",
                sa.BigInteger(),
                sa.ForeignKey(bod_fk, ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column(
                "horizon_days",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("30"),
            ),
            sa.Column(
                "current_stock",
                sa.Numeric(12, 4),
                nullable=False,
                server_default=sa.text("0.0000"),
            ),
            sa.Column(
                "projected_stock",
                sa.Numeric(12, 4),
                nullable=False,
                server_default=sa.text("0.0000"),
            ),
            sa.Column("depletion_date", sa.Date(), nullable=True),
            sa.Column(
                "worst_status",
                sa.String(length=20),
                nullable=False,
                server_default="NORMAL",
            ),
            sa.Column(
                "worst_status_label",
                sa.String(length=64),
                nullable=False,
                server_default="Normal",
            ),
            sa.Column("worst_day", sa.Integer(), nullable=True),
            sa.Column(
                "daily_consumption_rate",
                sa.Numeric(12, 4),
                nullable=False,
                server_default=sa.text("0.0000"),
            ),
            sa.Column(
                "projection_curve",
                json_type,
                nullable=False,
                server_default=json_empty_array,
            ),
            sa.Column(
                "calculated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "is_stale",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column("metadata_payload", json_type, nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "producto_id",
                "bodega_id",
                "horizon_days",
                name="uq_proj_snapshots_prod_bod_horiz",
            ),
            schema=schema,
        )

    if _has_table("projection_snapshots", schema=schema) is True:
        if _has_index("projection_snapshots", "idx_proj_snapshots_lookup", schema=schema) is not True:
            op.create_index(
                "idx_proj_snapshots_lookup",
                "projection_snapshots",
                ["bodega_id", "horizon_days", "worst_status"],
                schema=schema,
            )
        if _has_index("projection_snapshots", "idx_proj_snapshots_prod", schema=schema) is not True:
            op.create_index(
                "idx_proj_snapshots_prod",
                "projection_snapshots",
                ["producto_id", "horizon_days"],
                schema=schema,
            )
        if _has_index("projection_snapshots", "idx_proj_snapshots_calc", schema=schema) is not True:
            op.create_index(
                "idx_proj_snapshots_calc",
                "projection_snapshots",
                ["calculated_at", "is_stale"],
                schema=schema,
            )
        if _has_index("projection_snapshots", "ix_projection_snapshots_producto_id", schema=schema) is not True:
            op.create_index(
                "ix_projection_snapshots_producto_id",
                "projection_snapshots",
                ["producto_id"],
                schema=schema,
            )
        if _has_index("projection_snapshots", "ix_projection_snapshots_bodega_id", schema=schema) is not True:
            op.create_index(
                "ix_projection_snapshots_bodega_id",
                "projection_snapshots",
                ["bodega_id"],
                schema=schema,
            )


def _apply_tenant_downgrade_to_schema(schema: str | None) -> None:
    """Revierte simétricamente tablas e índices de proyección de un esquema tenant_*."""
    # 1. Dropear `projection_snapshots`
    if _has_table("projection_snapshots", schema=schema) is True:
        for idx_name in [
            "ix_projection_snapshots_bodega_id",
            "ix_projection_snapshots_producto_id",
            "idx_proj_snapshots_calc",
            "idx_proj_snapshots_prod",
            "idx_proj_snapshots_lookup",
        ]:
            if _has_index("projection_snapshots", idx_name, schema=schema) is True:
                op.drop_index(idx_name, table_name="projection_snapshots", schema=schema)
        op.drop_table("projection_snapshots", schema=schema)

    # 2. Dropear `daily_consumption_rates`
    if _has_table("daily_consumption_rates", schema=schema) is True:
        for idx_name in [
            "ix_daily_consumption_rates_bodega_id",
            "ix_daily_consumption_rates_producto_id",
        ]:
            if _has_index("daily_consumption_rates", idx_name, schema=schema) is True:
                op.drop_index(idx_name, table_name="daily_consumption_rates", schema=schema)
        op.drop_table("daily_consumption_rates", schema=schema)


def upgrade() -> None:
    """Aplica DDL de proyecciones y tasas de consumo en esquemas `tenant_*`."""
    current_schema = _get_current_schema()
    bind = op.get_bind()

    if current_schema and current_schema.startswith("tenant_"):
        target_schemas = [current_schema]
    elif current_schema == "public":
        target_schemas = _get_tenant_schemas(bind)
    else:
        target_schemas = [current_schema] if current_schema else []

    for schema in target_schemas:
        _apply_tenant_upgrade_to_schema(schema)


def downgrade() -> None:
    """Revierte simétricamente todas las tablas e índices de proyección en esquemas `tenant_*`."""
    current_schema = _get_current_schema()
    bind = op.get_bind()

    if current_schema and current_schema.startswith("tenant_"):
        target_schemas = [current_schema]
    elif current_schema == "public":
        target_schemas = _get_tenant_schemas(bind)
    else:
        target_schemas = [current_schema] if current_schema else []

    for schema in target_schemas:
        _apply_tenant_downgrade_to_schema(schema)
