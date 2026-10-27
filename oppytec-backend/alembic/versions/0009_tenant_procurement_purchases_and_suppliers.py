"""
0009_tenant_procurement_purchases_and_suppliers.py
Migración correlativa 0009 para el alcance `tenant`:
Crea y expande los modelos de persistencia multi-tenant para Compras, Proveedores y Recepción:
- `proveedores`: telefono, direccion, estado, notas.
- `producto_proveedores`: tiempo_entrega_dias, es_proveedor_principal.
- `compras`: numero_orden (unique), notas, solicitante_user_id, receptor_user_id, e índice (proveedor_id, estado).
- `compra_items`: subtotal_linea, lote_codigo, fecha_vencimiento.
- `compra_incidencias`: tabla nueva para discrepancias, mermas de recepción y reclamos a proveedores.
"""
from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from alembic import op

revision = "0009_tenant_procurement_purchases_and_suppliers"
down_revision = "0008_tenant_recipes_combos_dynamic_option_groups"
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
    """Aplica DDL de compras, proveedores e incidencias en esquemas `tenant_*`."""
    current_schema = _get_current_schema()
    if current_schema == "public":
        return

    # ---------------------------------------------------------
    # 1. Enriquecimiento de `proveedores`
    # ---------------------------------------------------------
    if _has_table("proveedores", schema=current_schema) is True:
        if _has_column("proveedores", "telefono", schema=current_schema) is not True:
            op.add_column(
                "proveedores",
                sa.Column("telefono", sa.String(length=50), nullable=True),
                schema=current_schema,
            )
        if _has_column("proveedores", "direccion", schema=current_schema) is not True:
            op.add_column(
                "proveedores",
                sa.Column("direccion", sa.String(length=255), nullable=True),
                schema=current_schema,
            )
        if _has_column("proveedores", "estado", schema=current_schema) is not True:
            op.add_column(
                "proveedores",
                sa.Column("estado", sa.String(length=32), nullable=False, server_default="ACTIVO"),
                schema=current_schema,
            )
        if _has_column("proveedores", "notas", schema=current_schema) is not True:
            op.add_column(
                "proveedores",
                sa.Column("notas", sa.Text(), nullable=True),
                schema=current_schema,
            )

    # ---------------------------------------------------------
    # 2. Enriquecimiento de `producto_proveedores`
    # ---------------------------------------------------------
    if _has_table("producto_proveedores", schema=current_schema) is True:
        if _has_column("producto_proveedores", "tiempo_entrega_dias", schema=current_schema) is not True:
            op.add_column(
                "producto_proveedores",
                sa.Column("tiempo_entrega_dias", sa.Integer(), nullable=True),
                schema=current_schema,
            )
        if _has_column("producto_proveedores", "es_proveedor_principal", schema=current_schema) is not True:
            op.add_column(
                "producto_proveedores",
                sa.Column("es_proveedor_principal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
                schema=current_schema,
            )

    # ---------------------------------------------------------
    # 3. Enriquecimiento de `compras`
    # ---------------------------------------------------------
    if _has_table("compras", schema=current_schema) is True:
        if _has_column("compras", "numero_orden", schema=current_schema) is not True:
            op.add_column(
                "compras",
                sa.Column("numero_orden", sa.String(length=64), nullable=True, server_default=sa.text("''")),
                schema=current_schema,
            )
            # Población retroactiva segura si hubiera registros legacy
            table_prefix = f'"{current_schema}".' if current_schema else ""
            try:
                op.execute(
                    sa.text(
                        f"UPDATE {table_prefix}compras SET numero_orden = 'OC-' || id "
                        f"WHERE numero_orden = '' OR numero_orden IS NULL"
                    )
                )
            except Exception:
                pass
            op.alter_column(
                "compras",
                "numero_orden",
                nullable=False,
                schema=current_schema,
            )

        if _has_index("compras", "ix_compras_numero_orden", schema=current_schema) is not True:
            op.create_index(
                "ix_compras_numero_orden",
                "compras",
                ["numero_orden"],
                unique=True,
                schema=current_schema,
            )

        if _has_column("compras", "notas", schema=current_schema) is not True:
            op.add_column(
                "compras",
                sa.Column("notas", sa.Text(), nullable=True),
                schema=current_schema,
            )

        if _has_column("compras", "solicitante_user_id", schema=current_schema) is not True:
            op.add_column(
                "compras",
                sa.Column("solicitante_user_id", sa.Integer(), nullable=True),
                schema=current_schema,
            )

        if _has_column("compras", "receptor_user_id", schema=current_schema) is not True:
            op.add_column(
                "compras",
                sa.Column("receptor_user_id", sa.Integer(), nullable=True),
                schema=current_schema,
            )

        if _has_index("compras", "ix_compras_proveedor_estado", schema=current_schema) is not True:
            op.create_index(
                "ix_compras_proveedor_estado",
                "compras",
                ["proveedor_id", "estado"],
                unique=False,
                schema=current_schema,
            )

    # ---------------------------------------------------------
    # 4. Enriquecimiento de `compra_items`
    # ---------------------------------------------------------
    if _has_table("compra_items", schema=current_schema) is True:
        if _has_column("compra_items", "subtotal_linea", schema=current_schema) is not True:
            op.add_column(
                "compra_items",
                sa.Column("subtotal_linea", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
                schema=current_schema,
            )
        if _has_column("compra_items", "lote_codigo", schema=current_schema) is not True:
            op.add_column(
                "compra_items",
                sa.Column("lote_codigo", sa.String(length=64), nullable=True),
                schema=current_schema,
            )
        if _has_column("compra_items", "fecha_vencimiento", schema=current_schema) is not True:
            op.add_column(
                "compra_items",
                sa.Column("fecha_vencimiento", sa.Date(), nullable=True),
                schema=current_schema,
            )

    # ---------------------------------------------------------
    # 5. Tabla `compra_incidencias`
    # ---------------------------------------------------------
    if _has_table("compra_incidencias", schema=current_schema) is not True:
        op.create_table(
            "compra_incidencias",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "compra_id",
                sa.Integer(),
                sa.ForeignKey("compras.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "compra_item_id",
                sa.Integer(),
                sa.ForeignKey("compra_items.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("tipo_incidencia", sa.String(length=50), nullable=False),
            sa.Column("cantidad_afectada", sa.Numeric(12, 4), nullable=False, server_default="0.0000"),
            sa.Column("monto_disputa", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("resolucion", sa.String(length=50), nullable=False, server_default="PENDIENTE"),
            sa.Column("descripcion", sa.Text(), nullable=False),
            sa.Column("foto_evidencia_url", sa.String(length=500), nullable=True),
            sa.Column("registrado_por_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema=current_schema,
        )

    if _has_table("compra_incidencias", schema=current_schema) is True:
        if _has_index("compra_incidencias", "ix_compra_incidencias_compra_id", schema=current_schema) is not True:
            op.create_index(
                "ix_compra_incidencias_compra_id",
                "compra_incidencias",
                ["compra_id"],
                schema=current_schema,
            )
        if _has_index("compra_incidencias", "ix_compra_incidencias_compra_item_id", schema=current_schema) is not True:
            op.create_index(
                "ix_compra_incidencias_compra_item_id",
                "compra_incidencias",
                ["compra_item_id"],
                schema=current_schema,
            )


def downgrade() -> None:
    """Revierte simétricamente los cambios DDL de compras y proveedores en el esquema `tenant_*` activo."""
    current_schema = _get_current_schema()
    if current_schema == "public":
        return

    # 1. Revertir `compra_incidencias`
    if _has_table("compra_incidencias", schema=current_schema) is not False:
        if _has_index("compra_incidencias", "ix_compra_incidencias_compra_item_id", schema=current_schema) is not False:
            op.drop_index(
                "ix_compra_incidencias_compra_item_id",
                table_name="compra_incidencias",
                schema=current_schema,
            )
        if _has_index("compra_incidencias", "ix_compra_incidencias_compra_id", schema=current_schema) is not False:
            op.drop_index(
                "ix_compra_incidencias_compra_id",
                table_name="compra_incidencias",
                schema=current_schema,
            )
        op.drop_table("compra_incidencias", schema=current_schema)

    # 2. Revertir `compra_items`
    if _has_column("compra_items", "fecha_vencimiento", schema=current_schema) is not False:
        op.drop_column("compra_items", "fecha_vencimiento", schema=current_schema)
    if _has_column("compra_items", "lote_codigo", schema=current_schema) is not False:
        op.drop_column("compra_items", "lote_codigo", schema=current_schema)
    if _has_column("compra_items", "subtotal_linea", schema=current_schema) is not False:
        op.drop_column("compra_items", "subtotal_linea", schema=current_schema)

    # 3. Revertir `compras`
    if _has_index("compras", "ix_compras_proveedor_estado", schema=current_schema) is not False:
        op.drop_index("ix_compras_proveedor_estado", table_name="compras", schema=current_schema)
    if _has_index("compras", "ix_compras_numero_orden", schema=current_schema) is not False:
        op.drop_index("ix_compras_numero_orden", table_name="compras", schema=current_schema)
    if _has_column("compras", "receptor_user_id", schema=current_schema) is not False:
        op.drop_column("compras", "receptor_user_id", schema=current_schema)
    if _has_column("compras", "solicitante_user_id", schema=current_schema) is not False:
        op.drop_column("compras", "solicitante_user_id", schema=current_schema)
    if _has_column("compras", "notas", schema=current_schema) is not False:
        op.drop_column("compras", "notas", schema=current_schema)
    if _has_column("compras", "numero_orden", schema=current_schema) is not False:
        op.drop_column("compras", "numero_orden", schema=current_schema)

    # 4. Revertir `producto_proveedores`
    if _has_column("producto_proveedores", "es_proveedor_principal", schema=current_schema) is not False:
        op.drop_column("producto_proveedores", "es_proveedor_principal", schema=current_schema)
    if _has_column("producto_proveedores", "tiempo_entrega_dias", schema=current_schema) is not False:
        op.drop_column("producto_proveedores", "tiempo_entrega_dias", schema=current_schema)

    # 5. Revertir `proveedores`
    if _has_column("proveedores", "notas", schema=current_schema) is not False:
        op.drop_column("proveedores", "notas", schema=current_schema)
    if _has_column("proveedores", "estado", schema=current_schema) is not False:
        op.drop_column("proveedores", "estado", schema=current_schema)
    if _has_column("proveedores", "direccion", schema=current_schema) is not False:
        op.drop_column("proveedores", "direccion", schema=current_schema)
    if _has_column("proveedores", "telefono", schema=current_schema) is not False:
        op.drop_column("proveedores", "telefono", schema=current_schema)
