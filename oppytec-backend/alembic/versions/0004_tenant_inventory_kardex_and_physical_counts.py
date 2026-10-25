"""
0004_tenant_inventory_kardex_and_physical_counts.py
Migración correlativa 0004 para el alcance `tenant`:
Enriquece el modelo de Inventario en esquemas `tenant_*`:
- `producto_bodegas`: stock_minimo, stock_maximo, punto_reorden, pasillo, estante, nivel.
- `registro_stock`: costo_unitario_ppp, costo_total_movimiento, lote_codigo, fecha_vencimiento_lote, transfer_id e índices.
- `stock_transfers`: tabla nueva para transferencias inter-bodegas con transfer_uuid e historial de responsables.
- `conteos_inventario`: area_operativa_id, aprobador_user_id, notas, completed_at.
- `conteo_items`: lote_codigo, fecha_vencimiento, costo_unitario_ppp, valorizacion_diferencia.
"""
from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from alembic import op

revision = "0004_tenant_inventory_kardex_and_physical_counts"
down_revision = "0003_public_plans_quotas_and_tenant_capacity_overrides"
branch_labels = None
depends_on = None
migration_scope: Literal["public", "tenant"] = "tenant"


def _get_current_schema() -> str | None:
    try:
        bind = op.get_bind()
        return bind.execute(sa.text("SELECT current_schema()")).scalar()
    except Exception:
        return None


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
    """Aplica DDL de inventario enriquecido (Kardex PPP, transfers, conteos) en esquemas `tenant_*`."""
    current_schema = _get_current_schema()
    if current_schema == "public":
        return

    # 1. Tabla nueva `stock_transfers`
    if _has_table("stock_transfers", schema=current_schema) is not True:
        op.create_table(
            "stock_transfers",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("transfer_uuid", sa.Uuid(as_uuid=True), nullable=False, unique=True),
            sa.Column(
                "bodega_origen_id",
                sa.Integer(),
                sa.ForeignKey("bodegas.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "bodega_destino_id",
                sa.Integer(),
                sa.ForeignKey("bodegas.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("estado", sa.String(length=32), nullable=False, server_default="SOLICITADA"),
            sa.Column("solicitante_user_id", sa.Integer(), nullable=False),
            sa.Column("despachador_user_id", sa.Integer(), nullable=True),
            sa.Column("receptor_user_id", sa.Integer(), nullable=True),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema=current_schema,
        )

    if _has_table("stock_transfers", schema=current_schema) is True:
        if _has_index("stock_transfers", "ix_stock_transfers_transfer_uuid", schema=current_schema) is not True:
            op.create_index(
                "ix_stock_transfers_transfer_uuid",
                "stock_transfers",
                ["transfer_uuid"],
                schema=current_schema,
            )
        if _has_index("stock_transfers", "ix_stock_transfers_bodega_origen_id", schema=current_schema) is not True:
            op.create_index(
                "ix_stock_transfers_bodega_origen_id",
                "stock_transfers",
                ["bodega_origen_id"],
                schema=current_schema,
            )
        if _has_index("stock_transfers", "ix_stock_transfers_bodega_destino_id", schema=current_schema) is not True:
            op.create_index(
                "ix_stock_transfers_bodega_destino_id",
                "stock_transfers",
                ["bodega_destino_id"],
                schema=current_schema,
            )

    # 2. Enriquecimiento de `producto_bodegas`
    if _has_column("producto_bodegas", "stock_minimo", schema=current_schema) is not True:
        op.add_column(
            "producto_bodegas",
            sa.Column("stock_minimo", sa.Numeric(12, 4), nullable=False, server_default="0.0000"),
            schema=current_schema,
        )
    if _has_column("producto_bodegas", "stock_maximo", schema=current_schema) is not True:
        op.add_column(
            "producto_bodegas",
            sa.Column("stock_maximo", sa.Numeric(12, 4), nullable=True),
            schema=current_schema,
        )
    if _has_column("producto_bodegas", "punto_reorden", schema=current_schema) is not True:
        op.add_column(
            "producto_bodegas",
            sa.Column("punto_reorden", sa.Numeric(12, 4), nullable=True),
            schema=current_schema,
        )
    if _has_column("producto_bodegas", "pasillo", schema=current_schema) is not True:
        op.add_column(
            "producto_bodegas",
            sa.Column("pasillo", sa.String(length=20), nullable=True),
            schema=current_schema,
        )
    if _has_column("producto_bodegas", "estante", schema=current_schema) is not True:
        op.add_column(
            "producto_bodegas",
            sa.Column("estante", sa.String(length=20), nullable=True),
            schema=current_schema,
        )
    if _has_column("producto_bodegas", "nivel", schema=current_schema) is not True:
        op.add_column(
            "producto_bodegas",
            sa.Column("nivel", sa.String(length=20), nullable=True),
            schema=current_schema,
        )

    # 3. Enriquecimiento de `registro_stock` (Kardex PPP y Transferencias)
    if _has_column("registro_stock", "costo_unitario_ppp", schema=current_schema) is not True:
        op.add_column(
            "registro_stock",
            sa.Column("costo_unitario_ppp", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            schema=current_schema,
        )
    if _has_column("registro_stock", "costo_total_movimiento", schema=current_schema) is not True:
        op.add_column(
            "registro_stock",
            sa.Column("costo_total_movimiento", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            schema=current_schema,
        )
    if _has_column("registro_stock", "lote_codigo", schema=current_schema) is not True:
        op.add_column(
            "registro_stock",
            sa.Column("lote_codigo", sa.String(length=64), nullable=True),
            schema=current_schema,
        )
    if _has_column("registro_stock", "fecha_vencimiento_lote", schema=current_schema) is not True:
        op.add_column(
            "registro_stock",
            sa.Column("fecha_vencimiento_lote", sa.Date(), nullable=True),
            schema=current_schema,
        )
    if _has_column("registro_stock", "transfer_id", schema=current_schema) is not True:
        op.add_column(
            "registro_stock",
            sa.Column("transfer_id", sa.Uuid(as_uuid=True), nullable=True),
            schema=current_schema,
        )

    # Índices en `registro_stock`
    if _has_index("registro_stock", "ix_registro_stock_bodega_producto", schema=current_schema) is not True:
        op.create_index(
            "ix_registro_stock_bodega_producto",
            "registro_stock",
            ["bodega_id", "producto_id"],
            schema=current_schema,
        )
    if _has_index("registro_stock", "ix_registro_stock_created_tipo", schema=current_schema) is not True:
        op.create_index(
            "ix_registro_stock_created_tipo",
            "registro_stock",
            ["created_at", "tipo_movimiento"],
            schema=current_schema,
        )
    if _has_index("registro_stock", "ix_registro_stock_transfer_id", schema=current_schema) is not True:
        op.create_index(
            "ix_registro_stock_transfer_id",
            "registro_stock",
            ["transfer_id"],
            schema=current_schema,
        )

    # 4. Enriquecimiento de `conteos_inventario`
    if _has_column("conteos_inventario", "area_operativa_id", schema=current_schema) is not True:
        op.add_column(
            "conteos_inventario",
            sa.Column(
                "area_operativa_id",
                sa.Integer(),
                sa.ForeignKey("areas_operativas.id", ondelete="RESTRICT"),
                nullable=True,
            ),
            schema=current_schema,
        )
    if _has_column("conteos_inventario", "aprobador_user_id", schema=current_schema) is not True:
        op.add_column(
            "conteos_inventario",
            sa.Column("aprobador_user_id", sa.Integer(), nullable=True),
            schema=current_schema,
        )
    if _has_column("conteos_inventario", "notas", schema=current_schema) is not True:
        op.add_column(
            "conteos_inventario",
            sa.Column("notas", sa.Text(), nullable=True),
            schema=current_schema,
        )
    if _has_column("conteos_inventario", "completed_at", schema=current_schema) is not True:
        op.add_column(
            "conteos_inventario",
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            schema=current_schema,
        )
    if _has_index("conteos_inventario", "ix_conteos_inventario_area_operativa_id", schema=current_schema) is not True:
        op.create_index(
            "ix_conteos_inventario_area_operativa_id",
            "conteos_inventario",
            ["area_operativa_id"],
            schema=current_schema,
        )

    # 5. Enriquecimiento de `conteo_items`
    if _has_column("conteo_items", "lote_codigo", schema=current_schema) is not True:
        op.add_column(
            "conteo_items",
            sa.Column("lote_codigo", sa.String(length=64), nullable=True),
            schema=current_schema,
        )
    if _has_column("conteo_items", "fecha_vencimiento", schema=current_schema) is not True:
        op.add_column(
            "conteo_items",
            sa.Column("fecha_vencimiento", sa.Date(), nullable=True),
            schema=current_schema,
        )
    if _has_column("conteo_items", "costo_unitario_ppp", schema=current_schema) is not True:
        op.add_column(
            "conteo_items",
            sa.Column("costo_unitario_ppp", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            schema=current_schema,
        )
    if _has_column("conteo_items", "valorizacion_diferencia", schema=current_schema) is not True:
        op.add_column(
            "conteo_items",
            sa.Column("valorizacion_diferencia", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            schema=current_schema,
        )


def downgrade() -> None:
    """Revierte simétricamente los cambios DDL de inventario en el esquema `tenant_*` activo."""
    current_schema = _get_current_schema()
    if current_schema == "public":
        return

    # 1. Revertir `conteo_items`
    if _has_column("conteo_items", "valorizacion_diferencia", schema=current_schema) is not False:
        op.drop_column("conteo_items", "valorizacion_diferencia", schema=current_schema)
    if _has_column("conteo_items", "costo_unitario_ppp", schema=current_schema) is not False:
        op.drop_column("conteo_items", "costo_unitario_ppp", schema=current_schema)
    if _has_column("conteo_items", "fecha_vencimiento", schema=current_schema) is not False:
        op.drop_column("conteo_items", "fecha_vencimiento", schema=current_schema)
    if _has_column("conteo_items", "lote_codigo", schema=current_schema) is not False:
        op.drop_column("conteo_items", "lote_codigo", schema=current_schema)

    # 2. Revertir `conteos_inventario`
    if _has_index("conteos_inventario", "ix_conteos_inventario_area_operativa_id", schema=current_schema) is not False:
        op.drop_index("ix_conteos_inventario_area_operativa_id", table_name="conteos_inventario", schema=current_schema)
    if _has_column("conteos_inventario", "completed_at", schema=current_schema) is not False:
        op.drop_column("conteos_inventario", "completed_at", schema=current_schema)
    if _has_column("conteos_inventario", "notas", schema=current_schema) is not False:
        op.drop_column("conteos_inventario", "notas", schema=current_schema)
    if _has_column("conteos_inventario", "aprobador_user_id", schema=current_schema) is not False:
        op.drop_column("conteos_inventario", "aprobador_user_id", schema=current_schema)
    if _has_column("conteos_inventario", "area_operativa_id", schema=current_schema) is not False:
        op.drop_column("conteos_inventario", "area_operativa_id", schema=current_schema)

    # 3. Revertir `registro_stock`
    if _has_index("registro_stock", "ix_registro_stock_transfer_id", schema=current_schema) is not False:
        op.drop_index("ix_registro_stock_transfer_id", table_name="registro_stock", schema=current_schema)
    if _has_index("registro_stock", "ix_registro_stock_created_tipo", schema=current_schema) is not False:
        op.drop_index("ix_registro_stock_created_tipo", table_name="registro_stock", schema=current_schema)
    if _has_index("registro_stock", "ix_registro_stock_bodega_producto", schema=current_schema) is not False:
        op.drop_index("ix_registro_stock_bodega_producto", table_name="registro_stock", schema=current_schema)
    if _has_column("registro_stock", "transfer_id", schema=current_schema) is not False:
        op.drop_column("registro_stock", "transfer_id", schema=current_schema)
    if _has_column("registro_stock", "fecha_vencimiento_lote", schema=current_schema) is not False:
        op.drop_column("registro_stock", "fecha_vencimiento_lote", schema=current_schema)
    if _has_column("registro_stock", "lote_codigo", schema=current_schema) is not False:
        op.drop_column("registro_stock", "lote_codigo", schema=current_schema)
    if _has_column("registro_stock", "costo_total_movimiento", schema=current_schema) is not False:
        op.drop_column("registro_stock", "costo_total_movimiento", schema=current_schema)
    if _has_column("registro_stock", "costo_unitario_ppp", schema=current_schema) is not False:
        op.drop_column("registro_stock", "costo_unitario_ppp", schema=current_schema)

    # 4. Revertir `producto_bodegas`
    if _has_column("producto_bodegas", "nivel", schema=current_schema) is not False:
        op.drop_column("producto_bodegas", "nivel", schema=current_schema)
    if _has_column("producto_bodegas", "estante", schema=current_schema) is not False:
        op.drop_column("producto_bodegas", "estante", schema=current_schema)
    if _has_column("producto_bodegas", "pasillo", schema=current_schema) is not False:
        op.drop_column("producto_bodegas", "pasillo", schema=current_schema)
    if _has_column("producto_bodegas", "punto_reorden", schema=current_schema) is not False:
        op.drop_column("producto_bodegas", "punto_reorden", schema=current_schema)
    if _has_column("producto_bodegas", "stock_maximo", schema=current_schema) is not False:
        op.drop_column("producto_bodegas", "stock_maximo", schema=current_schema)
    if _has_column("producto_bodegas", "stock_minimo", schema=current_schema) is not False:
        op.drop_column("producto_bodegas", "stock_minimo", schema=current_schema)

    # 5. Revertir `stock_transfers`
    if _has_table("stock_transfers", schema=current_schema) is not False:
        if _has_index("stock_transfers", "ix_stock_transfers_bodega_destino_id", schema=current_schema) is not False:
            op.drop_index("ix_stock_transfers_bodega_destino_id", table_name="stock_transfers", schema=current_schema)
        if _has_index("stock_transfers", "ix_stock_transfers_bodega_origen_id", schema=current_schema) is not False:
            op.drop_index("ix_stock_transfers_bodega_origen_id", table_name="stock_transfers", schema=current_schema)
        if _has_index("stock_transfers", "ix_stock_transfers_transfer_uuid", schema=current_schema) is not False:
            op.drop_index("ix_stock_transfers_transfer_uuid", table_name="stock_transfers", schema=current_schema)
        op.drop_table("stock_transfers", schema=current_schema)
