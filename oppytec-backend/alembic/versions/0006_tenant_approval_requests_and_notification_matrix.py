"""
0006_tenant_approval_requests_and_notification_matrix.py
Migración correlativa 0006 para el alcance `tenant`:
Crea los modelos de persistencia multi-tenant para el Centro de Notificaciones y Aprobaciones:
- `solicitudes_aprobacion`: Solicitudes operacionales polimórficas (mermas, conteos, compras, etc.).
- `notification_matrix_rules`: Matriz de gobernanza y despacho de alertas/aprobaciones por cargo.
"""
from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_tenant_approval_requests_and_notification_matrix"
down_revision = "0005_tenant_consumption_buffet_and_voice_tables"
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
        return False


def _has_table(table_name: str, schema: str | None = None) -> bool | None:
    try:
        bind = op.get_bind()
        insp = sa.inspect(bind)
        tables = insp.get_table_names(schema=schema)
        return table_name in tables
    except Exception:
        return None


def _has_column(table_name: str, column_name: str, schema: str | None = None) -> bool | None:
    try:
        bind = op.get_bind()
        insp = sa.inspect(bind)
        cols = [c["name"] for c in insp.get_columns(table_name, schema=schema)]
        return column_name in cols
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


def upgrade() -> None:
    """Crea las tablas `solicitudes_aprobacion` y `notification_matrix_rules` en esquemas `tenant_*`."""
    current_schema = _get_current_schema()
    if current_schema == "public":
        return

    is_pg = _is_postgresql()
    uuid_server_default = sa.text("gen_random_uuid()") if is_pg else None
    jsonb_server_default = sa.text("'{}'::jsonb") if is_pg else sa.text("'{}'")
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    # 1. Tabla `solicitudes_aprobacion`
    if _has_table("solicitudes_aprobacion", schema=current_schema) is True:
        # Si existe versión legacy sin columna 'tipo', reemplazar por la nueva estructura
        if _has_column("solicitudes_aprobacion", "tipo", schema=current_schema) is not True:
            op.drop_table("solicitudes_aprobacion", schema=current_schema)

    if _has_table("solicitudes_aprobacion", schema=current_schema) is not True:
        op.create_table(
            "solicitudes_aprobacion",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, server_default=uuid_server_default),
            sa.Column("tipo", sa.String(length=50), nullable=False),
            sa.Column("estado", sa.String(length=30), nullable=False, server_default="pendiente"),
            sa.Column("usuario_id", sa.Integer(), nullable=False),
            sa.Column("bodega_id", sa.BigInteger(), nullable=True),
            sa.Column("area_operativa_id", sa.BigInteger(), nullable=True),
            sa.Column("detalles", json_type, nullable=False, server_default=jsonb_server_default),
            sa.Column("resuelto_por", sa.Integer(), nullable=True),
            sa.Column("motivo_rechazo", sa.Text(), nullable=True),
            sa.Column("resuelto_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_by", sa.Integer(), nullable=True),
            schema=current_schema,
        )

    if _has_table("solicitudes_aprobacion", schema=current_schema) is True:
        if _has_index("solicitudes_aprobacion", "ix_solicitudes_aprobacion_estado_created_at", schema=current_schema) is not True:
            op.create_index(
                "ix_solicitudes_aprobacion_estado_created_at",
                "solicitudes_aprobacion",
                ["estado", "created_at"],
                schema=current_schema,
            )
        if _has_index("solicitudes_aprobacion", "ix_solicitudes_aprobacion_tipo_estado", schema=current_schema) is not True:
            op.create_index(
                "ix_solicitudes_aprobacion_tipo_estado",
                "solicitudes_aprobacion",
                ["tipo", "estado"],
                schema=current_schema,
            )
        if _has_index("solicitudes_aprobacion", "ix_solicitudes_aprobacion_usuario_id", schema=current_schema) is not True:
            op.create_index(
                "ix_solicitudes_aprobacion_usuario_id",
                "solicitudes_aprobacion",
                ["usuario_id"],
                schema=current_schema,
            )
        if _has_index("solicitudes_aprobacion", "ix_solicitudes_aprobacion_area_bodega", schema=current_schema) is not True:
            op.create_index(
                "ix_solicitudes_aprobacion_area_bodega",
                "solicitudes_aprobacion",
                ["area_operativa_id", "bodega_id"],
                schema=current_schema,
            )
        if _has_index("solicitudes_aprobacion", "ix_solicitudes_aprobacion_is_deleted", schema=current_schema) is not True:
            op.create_index(
                "ix_solicitudes_aprobacion_is_deleted",
                "solicitudes_aprobacion",
                ["is_deleted"],
                schema=current_schema,
            )

    # 2. Tabla `notification_matrix_rules`
    if _has_table("notification_matrix_rules", schema=current_schema) is not True:
        op.create_table(
            "notification_matrix_rules",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("cargo", sa.String(length=64), nullable=False),
            sa.Column("tipo_solicitud", sa.String(length=50), nullable=False),
            sa.Column("canal_in_app", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("canal_email", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("canal_push", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("es_aprobador", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_by", sa.Integer(), nullable=True),
            sa.UniqueConstraint("cargo", "tipo_solicitud", name="uq_notification_matrix_rules_cargo_tipo_solicitud"),
            schema=current_schema,
        )

    if _has_table("notification_matrix_rules", schema=current_schema) is True:
        if _has_index("notification_matrix_rules", "ix_notification_matrix_rules_is_deleted", schema=current_schema) is not True:
            op.create_index(
                "ix_notification_matrix_rules_is_deleted",
                "notification_matrix_rules",
                ["is_deleted"],
                schema=current_schema,
            )


def downgrade() -> None:
    """Elimina las tablas creadas en orden simétrico inverso."""
    current_schema = _get_current_schema()
    if current_schema == "public":
        return

    # 1. Revertir `notification_matrix_rules`
    if _has_table("notification_matrix_rules", schema=current_schema) is not False:
        if _has_index("notification_matrix_rules", "ix_notification_matrix_rules_is_deleted", schema=current_schema) is not False:
            op.drop_index("ix_notification_matrix_rules_is_deleted", table_name="notification_matrix_rules", schema=current_schema)
        op.drop_table("notification_matrix_rules", schema=current_schema)

    # 2. Revertir `solicitudes_aprobacion`
    if _has_table("solicitudes_aprobacion", schema=current_schema) is not False:
        if _has_index("solicitudes_aprobacion", "ix_solicitudes_aprobacion_is_deleted", schema=current_schema) is not False:
            op.drop_index("ix_solicitudes_aprobacion_is_deleted", table_name="solicitudes_aprobacion", schema=current_schema)
        if _has_index("solicitudes_aprobacion", "ix_solicitudes_aprobacion_area_bodega", schema=current_schema) is not False:
            op.drop_index("ix_solicitudes_aprobacion_area_bodega", table_name="solicitudes_aprobacion", schema=current_schema)
        if _has_index("solicitudes_aprobacion", "ix_solicitudes_aprobacion_usuario_id", schema=current_schema) is not False:
            op.drop_index("ix_solicitudes_aprobacion_usuario_id", table_name="solicitudes_aprobacion", schema=current_schema)
        if _has_index("solicitudes_aprobacion", "ix_solicitudes_aprobacion_tipo_estado", schema=current_schema) is not False:
            op.drop_index("ix_solicitudes_aprobacion_tipo_estado", table_name="solicitudes_aprobacion", schema=current_schema)
        if _has_index("solicitudes_aprobacion", "ix_solicitudes_aprobacion_estado_created_at", schema=current_schema) is not False:
            op.drop_index("ix_solicitudes_aprobacion_estado_created_at", table_name="solicitudes_aprobacion", schema=current_schema)
        op.drop_table("solicitudes_aprobacion", schema=current_schema)
