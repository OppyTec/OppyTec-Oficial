"""
0016_tenant_invoices_dte_and_supplier_aliases.py
Migración correlativa 0016 para el alcance `tenant`:
Implementa la Fase 1 del Plan Maestro Oficial de Facturas, DTE, Ingesta Inteligente y Alias de Proveedores:
- `invoices`: Documentos tributarios electrónicos (DTE) con metadatos, montos exactos Numeric(14, 4), tokens IA y trazabilidad.
- `invoice_lines`: Detalle de líneas de factura con desacoplamiento de empaque mayorista a cocina y referencias a catálogo/bodegas.
- `supplier_product_aliases`: Memoria de aprendizaje asociativa entre nombres de proveedor y catálogo maestro.
- `invoice_audit_flags`: Registro estructurado de discrepancias tributarias, descalces de IVA y alertas de auditoría.
- Índices B-Tree para filtrado rápido e índices Trigram GIN para búsqueda difusa (`pg_trgm`).
"""
from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0016_tenant_invoices_dte_and_supplier_aliases"
down_revision = "0015_tenant_actividades_triada_enriquecida"
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


def _apply_tenant_upgrade_to_schema(schema: str | None) -> None:
    """Aplica la creación de tablas DTE, líneas, aliases y flags de auditoría en un esquema tenant_*."""
    bind = op.get_bind()
    is_pg = _is_postgresql()
    uuid_type = postgresql.UUID(as_uuid=True) if is_pg else sa.Uuid()
    uuid_default = sa.text("gen_random_uuid()") if is_pg else None
    prefix = f'"{schema}".' if schema else ""

    # Habilitar extensión pg_trgm para índices de búsqueda difusa si es PostgreSQL
    if is_pg:
        try:
            bind.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        except Exception:
            pass

    # =========================================================================
    # 1. Tabla `invoices`
    # =========================================================================
    # Si existe una versión previa placeholder sin tenant_id, se reemplaza limpiamente
    if _has_table("invoices", schema=schema) is True:
        if not _has_column("invoices", "tenant_id", schema=schema):
            op.drop_table("invoices", schema=schema)

    if _has_table("invoices", schema=schema) is not True:
        op.create_table(
            "invoices",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
            sa.Column("tenant_id", uuid_type, nullable=False, index=True),
            sa.Column("file_path", sa.String(length=500), nullable=True),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("file_type", sa.String(length=10), nullable=False),
            sa.Column("vendor_name", sa.String(length=255), nullable=True),
            sa.Column("vendor_tax_id", sa.String(length=30), nullable=True, index=True),
            sa.Column("vendor_address", sa.Text(), nullable=True),
            sa.Column("invoice_number", sa.String(length=50), nullable=True, index=True),
            sa.Column("invoice_date", sa.DateTime(timezone=True), nullable=True, index=True),
            sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="CLP"),
            sa.Column("exchange_rate", sa.Numeric(14, 4), nullable=False, server_default="1.0000"),
            sa.Column("net_amount", sa.Numeric(14, 4), nullable=False, server_default="0.0000"),
            sa.Column("tax_amount", sa.Numeric(14, 4), nullable=False, server_default="0.0000"),
            sa.Column("total_amount", sa.Numeric(14, 4), nullable=False, server_default="0.0000"),
            sa.Column("dte_type", sa.Integer(), nullable=False, server_default="33"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING", index=True),
            sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
            sa.Column("gemini_tokens_used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("gemini_cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0.000000"),
            sa.Column("is_stock_ingested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            schema=schema,
        )

    # Índice Trigram GIN sobre vendor_name en `invoices`
    if is_pg and _has_table("invoices", schema=schema) is True:
        if not _has_index("invoices", "ix_invoices_vendor_name_trgm", schema=schema):
            try:
                op.execute(
                    sa.text(
                        f'CREATE INDEX IF NOT EXISTS "ix_invoices_vendor_name_trgm" ON {prefix}"invoices" '
                        f'USING gin ("vendor_name" gin_trgm_ops);'
                    )
                )
            except Exception:
                pass

    # =========================================================================
    # 2. Tabla `invoice_lines`
    # =========================================================================
    if _has_table("invoice_lines", schema=schema) is not True:
        invoice_fk = f"{schema}.invoices.id" if schema else "invoices.id"
        catalog_fk = f"{schema}.catalog_items.id" if schema and _has_table("catalog_items", schema=schema) else (
            "catalog_items.id" if _has_table("catalog_items", schema=schema) else None
        )
        bodega_fk = f"{schema}.bodegas.id" if schema and _has_table("bodegas", schema=schema) else (
            "bodegas.id" if _has_table("bodegas", schema=schema) else None
        )

        columns = [
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
            sa.Column("invoice_id", uuid_type, sa.ForeignKey(invoice_fk, ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("line_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("raw_description", sa.Text(), nullable=False),
            sa.Column("quantity", sa.Numeric(14, 4), nullable=False, server_default="1.0000"),
            sa.Column("unit", sa.String(length=30), nullable=False, server_default="un"),
            sa.Column("unit_price", sa.Numeric(14, 4), nullable=False, server_default="0.0000"),
            sa.Column("line_total", sa.Numeric(14, 4), nullable=False, server_default="0.0000"),
            sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False, server_default="19.00"),
            sa.Column(
                "matched_catalog_item_id",
                uuid_type,
                sa.ForeignKey(catalog_fk, ondelete="SET NULL") if catalog_fk else None,
                nullable=True,
                index=True,
            ),
            sa.Column("match_status", sa.String(length=20), nullable=False, server_default="UNMATCHED"),
            sa.Column("suggested_catalog_item_id", uuid_type, nullable=True),
            sa.Column("match_confidence", sa.Numeric(5, 2), nullable=True),
            sa.Column("packaging_description", sa.String(length=100), nullable=True),
            sa.Column("packaging_factor", sa.Numeric(14, 4), nullable=False, server_default="1.0000"),
            sa.Column("calculated_stock_qty", sa.Numeric(14, 4), nullable=False, server_default="0.0000"),
            sa.Column("inventory_unit", sa.String(length=30), nullable=False, server_default="un"),
            sa.Column("inventory_unit_cost", sa.Numeric(14, 4), nullable=False, server_default="0.0000"),
            sa.Column(
                "target_bodega_id",
                sa.Integer(),
                sa.ForeignKey(bodega_fk, ondelete="SET NULL") if bodega_fk else None,
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        ]

        op.create_table("invoice_lines", *columns, schema=schema)

    # Índice Trigram GIN sobre raw_description en `invoice_lines`
    if is_pg and _has_table("invoice_lines", schema=schema) is True:
        if not _has_index("invoice_lines", "ix_invoice_lines_raw_description_trgm", schema=schema):
            try:
                op.execute(
                    sa.text(
                        f'CREATE INDEX IF NOT EXISTS "ix_invoice_lines_raw_description_trgm" ON {prefix}"invoice_lines" '
                        f'USING gin ("raw_description" gin_trgm_ops);'
                    )
                )
            except Exception:
                pass

    # =========================================================================
    # 3. Tabla `supplier_product_aliases`
    # =========================================================================
    if _has_table("supplier_product_aliases", schema=schema) is not True:
        supplier_fk = f"{schema}.suppliers.id" if schema and _has_table("suppliers", schema=schema) else (
            "suppliers.id" if _has_table("suppliers", schema=schema) else None
        )
        catalog_alias_fk = f"{schema}.catalog_items.id" if schema and _has_table("catalog_items", schema=schema) else (
            "catalog_items.id" if _has_table("catalog_items", schema=schema) else None
        )

        alias_columns = [
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
            sa.Column("tenant_id", uuid_type, nullable=False, index=True),
            sa.Column(
                "supplier_id",
                uuid_type,
                sa.ForeignKey(supplier_fk, ondelete="CASCADE") if supplier_fk else None,
                nullable=True,
                index=True,
            ),
            sa.Column("raw_vendor_product_name", sa.Text(), nullable=False),
            sa.Column(
                "catalog_item_id",
                uuid_type,
                sa.ForeignKey(catalog_alias_fk, ondelete="CASCADE") if catalog_alias_fk else None,
                nullable=False,
                index=True,
            ),
            sa.Column("default_packaging_factor", sa.Numeric(14, 4), nullable=False, server_default="1.0000"),
            sa.Column("default_inventory_unit", sa.String(length=30), nullable=False, server_default="un"),
            sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("times_used", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("last_matched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint(
                "tenant_id",
                "supplier_id",
                "raw_vendor_product_name",
                name="uq_supplier_product_aliases_tenant_supplier_name",
            ),
        ]

        op.create_table("supplier_product_aliases", *alias_columns, schema=schema)

    # Índice Trigram GIN sobre raw_vendor_product_name en `supplier_product_aliases`
    if is_pg and _has_table("supplier_product_aliases", schema=schema) is True:
        if not _has_index("supplier_product_aliases", "ix_supplier_product_aliases_vendor_name_trgm", schema=schema):
            try:
                op.execute(
                    sa.text(
                        f'CREATE INDEX IF NOT EXISTS "ix_supplier_product_aliases_vendor_name_trgm" ON {prefix}"supplier_product_aliases" '
                        f'USING gin ("raw_vendor_product_name" gin_trgm_ops);'
                    )
                )
            except Exception:
                pass

    # =========================================================================
    # 4. Tabla `invoice_audit_flags`
    # =========================================================================
    if _has_table("invoice_audit_flags", schema=schema) is not True:
        invoice_flag_fk = f"{schema}.invoices.id" if schema else "invoices.id"

        op.create_table(
            "invoice_audit_flags",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
            sa.Column(
                "invoice_id",
                uuid_type,
                sa.ForeignKey(invoice_flag_fk, ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("severity", sa.String(length=20), nullable=False),
            sa.Column("rule_code", sa.String(length=50), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            schema=schema,
        )


def _apply_tenant_downgrade_to_schema(schema: str | None) -> None:
    """Elimina en orden inverso las 4 tablas e índices creados en el esquema tenant especificado."""
    # 1. Dropear `invoice_audit_flags`
    if _has_table("invoice_audit_flags", schema=schema) is True:
        if _has_index("invoice_audit_flags", "ix_invoice_audit_flags_invoice_id", schema=schema) is True:
            op.drop_index("ix_invoice_audit_flags_invoice_id", table_name="invoice_audit_flags", schema=schema)
        op.drop_table("invoice_audit_flags", schema=schema)

    # 2. Dropear `supplier_product_aliases`
    if _has_table("supplier_product_aliases", schema=schema) is True:
        if _has_index("supplier_product_aliases", "ix_supplier_product_aliases_vendor_name_trgm", schema=schema) is True:
            op.drop_index("ix_supplier_product_aliases_vendor_name_trgm", table_name="supplier_product_aliases", schema=schema)
        if _has_index("supplier_product_aliases", "ix_supplier_product_aliases_catalog_item_id", schema=schema) is True:
            op.drop_index("ix_supplier_product_aliases_catalog_item_id", table_name="supplier_product_aliases", schema=schema)
        if _has_index("supplier_product_aliases", "ix_supplier_product_aliases_supplier_id", schema=schema) is True:
            op.drop_index("ix_supplier_product_aliases_supplier_id", table_name="supplier_product_aliases", schema=schema)
        if _has_index("supplier_product_aliases", "ix_supplier_product_aliases_tenant_id", schema=schema) is True:
            op.drop_index("ix_supplier_product_aliases_tenant_id", table_name="supplier_product_aliases", schema=schema)
        op.drop_table("supplier_product_aliases", schema=schema)

    # 3. Dropear `invoice_lines`
    if _has_table("invoice_lines", schema=schema) is True:
        if _has_index("invoice_lines", "ix_invoice_lines_raw_description_trgm", schema=schema) is True:
            op.drop_index("ix_invoice_lines_raw_description_trgm", table_name="invoice_lines", schema=schema)
        if _has_index("invoice_lines", "ix_invoice_lines_matched_catalog_item_id", schema=schema) is True:
            op.drop_index("ix_invoice_lines_matched_catalog_item_id", table_name="invoice_lines", schema=schema)
        if _has_index("invoice_lines", "ix_invoice_lines_invoice_id", schema=schema) is True:
            op.drop_index("ix_invoice_lines_invoice_id", table_name="invoice_lines", schema=schema)
        op.drop_table("invoice_lines", schema=schema)

    # 4. Dropear `invoices`
    if _has_table("invoices", schema=schema) is True:
        if _has_index("invoices", "ix_invoices_vendor_name_trgm", schema=schema) is True:
            op.drop_index("ix_invoices_vendor_name_trgm", table_name="invoices", schema=schema)
        if _has_index("invoices", "ix_invoices_status", schema=schema) is True:
            op.drop_index("ix_invoices_status", table_name="invoices", schema=schema)
        if _has_index("invoices", "ix_invoices_invoice_date", schema=schema) is True:
            op.drop_index("ix_invoices_invoice_date", table_name="invoices", schema=schema)
        if _has_index("invoices", "ix_invoices_invoice_number", schema=schema) is True:
            op.drop_index("ix_invoices_invoice_number", table_name="invoices", schema=schema)
        if _has_index("invoices", "ix_invoices_vendor_tax_id", schema=schema) is True:
            op.drop_index("ix_invoices_vendor_tax_id", table_name="invoices", schema=schema)
        if _has_index("invoices", "ix_invoices_tenant_id", schema=schema) is True:
            op.drop_index("ix_invoices_tenant_id", table_name="invoices", schema=schema)
        op.drop_table("invoices", schema=schema)


def upgrade() -> None:
    """Aplica DDL de facturas, líneas, aliases y auditoría en esquemas `tenant_*`."""
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
    """Revierte simétricamente todas las tablas e índices de facturas en esquemas `tenant_*`."""
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
