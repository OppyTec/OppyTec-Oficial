"""
0008_tenant_recipes_combos_dynamic_option_groups.py
Migración correlativa 0008 para el alcance `tenant`:
Implementa persistencia completa para Recetas, Combos y Grupos de Opciones Polimórficos
(Fase 1 - PLAN_MAESTRO_GESTION_RECETAS_COMBOS.md):
- `categorias_recetas`: Clasificación de recetas y escandallos gastronómicos.
- `categorias_combos`: Clasificación de promociones y combos.
- `recetas`: Fichas técnicas gastronómicas con campos dinámicos, rendimiento y márgenes Decimal.
- `receta_ingredientes`: Ingredientes fijos con merma técnica en Decimal(6, 2) y check de origen exclusivo.
- `grupos_opciones`: Biblioteca de modificadores/opciones dinámicas intercambiables.
- `grupo_opciones_items`: Ítems polimórficos (producto o subreceta) con recargos Decimal(14, 2).
- `receta_grupos_opciones`: Asociación Many-to-Many para recetas dinámicas.
- `combos`: Paquetes y menús gastronómicos comercializables con desglose financiero.
- `combo_items`: Componentes fijos polimórficos de combos (producto o receta).
- `combo_grupos_opciones`: Asociación Many-to-Many para combos dinámicos.
"""
from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_tenant_recipes_combos_dynamic_option_groups"
down_revision = "0007_public_system_plans_extension_and_saas_policy"
branch_labels = None
depends_on = None
migration_scope: Literal["public", "tenant"] = "tenant"


def _get_current_schema() -> str | None:
    try:
        bind = op.get_bind()
        return bind.execute(sa.text("SELECT current_schema()")).scalar()
    except Exception:
        return None


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


def _apply_upgrade_to_schema(schema: str) -> None:
    """Aplica DDL de recetas, combos y grupos de opciones en el esquema tenant especificado."""
    jsonb_type = postgresql.JSONB(astext_type=sa.Text())

    # 1. Tabla `categorias_recetas`
    if _has_table("categorias_recetas", schema=schema) is not True:
        op.create_table(
            "categorias_recetas",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("nombre", sa.String(length=180), nullable=False),
            sa.Column("color", sa.String(length=32), nullable=True, server_default="#f59e0b"),
            sa.Column("icono", sa.String(length=64), nullable=True, server_default="ChefHat"),
            sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_by", sa.Integer(), nullable=True),
            sa.Column("i18n_data", jsonb_type, nullable=False, server_default="{}"),
            sa.Column("i18n_source_hash", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema=schema,
        )

    if _has_table("categorias_recetas", schema=schema) is True:
        if _has_index("categorias_recetas", "ix_categorias_recetas_nombre", schema=schema) is not True:
            op.create_index("ix_categorias_recetas_nombre", "categorias_recetas", ["nombre"], schema=schema)
        if _has_index("categorias_recetas", "ix_categorias_recetas_is_deleted", schema=schema) is not True:
            op.create_index("ix_categorias_recetas_is_deleted", "categorias_recetas", ["is_deleted"], schema=schema)

    # 2. Tabla `categorias_combos`
    if _has_table("categorias_combos", schema=schema) is not True:
        op.create_table(
            "categorias_combos",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("nombre", sa.String(length=180), nullable=False),
            sa.Column("color", sa.String(length=32), nullable=True, server_default="#ec4899"),
            sa.Column("icono", sa.String(length=64), nullable=True, server_default="Boxes"),
            sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_by", sa.Integer(), nullable=True),
            sa.Column("i18n_data", jsonb_type, nullable=False, server_default="{}"),
            sa.Column("i18n_source_hash", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema=schema,
        )

    if _has_table("categorias_combos", schema=schema) is True:
        if _has_index("categorias_combos", "ix_categorias_combos_nombre", schema=schema) is not True:
            op.create_index("ix_categorias_combos_nombre", "categorias_combos", ["nombre"], schema=schema)
        if _has_index("categorias_combos", "ix_categorias_combos_is_deleted", schema=schema) is not True:
            op.create_index("ix_categorias_combos_is_deleted", "categorias_combos", ["is_deleted"], schema=schema)

    # 3. Tabla `recetas`
    if _has_table("recetas", schema=schema) is not True:
        op.create_table(
            "recetas",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("codigo", sa.String(length=64), nullable=False, unique=True),
            sa.Column("nombre", sa.String(length=180), nullable=False),
            sa.Column("descripcion", sa.Text(), nullable=True),
            sa.Column(
                "categoria_receta_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.categorias_recetas.id" if schema else "categorias_recetas.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("es_subreceta", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("es_dinamica", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("porciones_rendimiento", sa.Numeric(12, 4), nullable=False, server_default="1.0000"),
            sa.Column("costo_total_calculado", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("precio_venta_neto", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("precio_venta_bruto", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("iva_porcentaje", sa.Numeric(5, 2), nullable=False, server_default="19.00"),
            sa.Column("iva_incluido", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("imagen_url", sa.String(length=512), nullable=True),
            sa.Column("preparacion", sa.Text(), nullable=True),
            sa.Column("video_url", sa.String(length=512), nullable=True),
            sa.Column("documento_url", sa.String(length=512), nullable=True),
            sa.Column("tiempo_preparacion_minutos", sa.Integer(), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_by", sa.Integer(), nullable=True),
            sa.Column("i18n_data", jsonb_type, nullable=False, server_default="{}"),
            sa.Column("i18n_source_hash", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema=schema,
        )
    else:
        # Enriquecer columnas si la tabla ya existía
        if _has_column("recetas", "descripcion", schema=schema) is not True:
            op.add_column("recetas", sa.Column("descripcion", sa.Text(), nullable=True), schema=schema)
        if _has_column("recetas", "categoria_receta_id", schema=schema) is not True:
            op.add_column(
                "recetas",
                sa.Column(
                    "categoria_receta_id",
                    sa.BigInteger(),
                    sa.ForeignKey(f"{schema}.categorias_recetas.id" if schema else "categorias_recetas.id", ondelete="SET NULL"),
                    nullable=True,
                ),
                schema=schema,
            )
        if _has_column("recetas", "es_dinamica", schema=schema) is not True:
            op.add_column("recetas", sa.Column("es_dinamica", sa.Boolean(), nullable=False, server_default="false"), schema=schema)
        if _has_column("recetas", "precio_venta_neto", schema=schema) is not True:
            op.add_column("recetas", sa.Column("precio_venta_neto", sa.Numeric(14, 2), nullable=False, server_default="0.00"), schema=schema)
        if _has_column("recetas", "iva_porcentaje", schema=schema) is not True:
            op.add_column("recetas", sa.Column("iva_porcentaje", sa.Numeric(5, 2), nullable=False, server_default="19.00"), schema=schema)
        if _has_column("recetas", "iva_incluido", schema=schema) is not True:
            op.add_column("recetas", sa.Column("iva_incluido", sa.Boolean(), nullable=False, server_default="true"), schema=schema)
        if _has_column("recetas", "imagen_url", schema=schema) is not True:
            op.add_column("recetas", sa.Column("imagen_url", sa.String(length=512), nullable=True), schema=schema)
        if _has_column("recetas", "preparacion", schema=schema) is not True:
            op.add_column("recetas", sa.Column("preparacion", sa.Text(), nullable=True), schema=schema)
        if _has_column("recetas", "video_url", schema=schema) is not True:
            op.add_column("recetas", sa.Column("video_url", sa.String(length=512), nullable=True), schema=schema)
        if _has_column("recetas", "documento_url", schema=schema) is not True:
            op.add_column("recetas", sa.Column("documento_url", sa.String(length=512), nullable=True), schema=schema)
        if _has_column("recetas", "tiempo_preparacion_minutos", schema=schema) is not True:
            op.add_column("recetas", sa.Column("tiempo_preparacion_minutos", sa.Integer(), nullable=True), schema=schema)

    if _has_table("recetas", schema=schema) is True:
        if _has_index("recetas", "ix_recetas_codigo", schema=schema) is not True:
            op.create_index("ix_recetas_codigo", "recetas", ["codigo"], schema=schema)
        if _has_index("recetas", "ix_recetas_nombre", schema=schema) is not True:
            op.create_index("ix_recetas_nombre", "recetas", ["nombre"], schema=schema)
        if _has_index("recetas", "ix_recetas_categoria_receta_id", schema=schema) is not True:
            op.create_index("ix_recetas_categoria_receta_id", "recetas", ["categoria_receta_id"], schema=schema)
        if _has_index("recetas", "ix_recetas_es_dinamica", schema=schema) is not True:
            op.create_index("ix_recetas_es_dinamica", "recetas", ["es_dinamica"], schema=schema)
        if _has_index("recetas", "ix_recetas_is_deleted", schema=schema) is not True:
            op.create_index("ix_recetas_is_deleted", "recetas", ["is_deleted"], schema=schema)

    # 4. Tabla `receta_ingredientes`
    if _has_table("receta_ingredientes", schema=schema) is not True:
        op.create_table(
            "receta_ingredientes",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "receta_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.recetas.id" if schema else "recetas.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "producto_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.productos.id" if schema else "productos.id", ondelete="RESTRICT"),
                nullable=True,
            ),
            sa.Column(
                "subreceta_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.recetas.id" if schema else "recetas.id", ondelete="RESTRICT"),
                nullable=True,
            ),
            sa.Column("cantidad_receta", sa.Numeric(12, 4), nullable=False),
            sa.Column("porcentaje_merma", sa.Numeric(6, 2), nullable=False, server_default="0.00"),
            sa.Column(
                "bodega_consumo_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.bodegas.id" if schema else "bodegas.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("notas", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "((producto_id IS NOT NULL AND subreceta_id IS NULL) OR "
                "(producto_id IS NULL AND subreceta_id IS NOT NULL))",
                name="ck_receta_ingredientes_origen_exclusivo",
            ),
            schema=schema,
        )
    else:
        if _has_column("receta_ingredientes", "subreceta_id", schema=schema) is not True:
            op.add_column(
                "receta_ingredientes",
                sa.Column(
                    "subreceta_id",
                    sa.BigInteger(),
                    sa.ForeignKey(f"{schema}.recetas.id" if schema else "recetas.id", ondelete="RESTRICT"),
                    nullable=True,
                ),
                schema=schema,
            )
        if _has_column("receta_ingredientes", "bodega_consumo_id", schema=schema) is not True:
            op.add_column(
                "receta_ingredientes",
                sa.Column(
                    "bodega_consumo_id",
                    sa.BigInteger(),
                    sa.ForeignKey(f"{schema}.bodegas.id" if schema else "bodegas.id", ondelete="SET NULL"),
                    nullable=True,
                ),
                schema=schema,
            )
        if _has_column("receta_ingredientes", "notas", schema=schema) is not True:
            op.add_column("receta_ingredientes", sa.Column("notas", sa.String(length=255), nullable=True), schema=schema)

    if _has_table("receta_ingredientes", schema=schema) is True:
        if _has_index("receta_ingredientes", "ix_receta_ingredientes_receta_id", schema=schema) is not True:
            op.create_index("ix_receta_ingredientes_receta_id", "receta_ingredientes", ["receta_id"], schema=schema)
        if _has_index("receta_ingredientes", "ix_receta_ingredientes_producto_id", schema=schema) is not True:
            op.create_index("ix_receta_ingredientes_producto_id", "receta_ingredientes", ["producto_id"], schema=schema)
        if _has_index("receta_ingredientes", "ix_receta_ingredientes_subreceta_id", schema=schema) is not True:
            op.create_index("ix_receta_ingredientes_subreceta_id", "receta_ingredientes", ["subreceta_id"], schema=schema)

    # 5. Tabla `grupos_opciones`
    if _has_table("grupos_opciones", schema=schema) is not True:
        op.create_table(
            "grupos_opciones",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("nombre", sa.String(length=120), nullable=False),
            sa.Column("descripcion", sa.Text(), nullable=True),
            sa.Column("seleccion_minima", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("seleccion_maxima", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("permite_repetir", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_by", sa.Integer(), nullable=True),
            sa.Column("i18n_data", jsonb_type, nullable=False, server_default="{}"),
            sa.Column("i18n_source_hash", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "seleccion_minima >= 0 AND seleccion_maxima >= seleccion_minima",
                name="ck_grupos_opciones_rango_seleccion",
            ),
            schema=schema,
        )
    else:
        if _has_column("grupos_opciones", "descripcion", schema=schema) is not True:
            op.add_column("grupos_opciones", sa.Column("descripcion", sa.Text(), nullable=True), schema=schema)
        if _has_column("grupos_opciones", "seleccion_minima", schema=schema) is not True:
            op.add_column("grupos_opciones", sa.Column("seleccion_minima", sa.Integer(), nullable=False, server_default="1"), schema=schema)
        if _has_column("grupos_opciones", "seleccion_maxima", schema=schema) is not True:
            op.add_column("grupos_opciones", sa.Column("seleccion_maxima", sa.Integer(), nullable=False, server_default="1"), schema=schema)
        if _has_column("grupos_opciones", "permite_repetir", schema=schema) is not True:
            op.add_column("grupos_opciones", sa.Column("permite_repetir", sa.Boolean(), nullable=False, server_default="false"), schema=schema)

    if _has_table("grupos_opciones", schema=schema) is True:
        if _has_index("grupos_opciones", "ix_grupos_opciones_nombre", schema=schema) is not True:
            op.create_index("ix_grupos_opciones_nombre", "grupos_opciones", ["nombre"], schema=schema)
        if _has_index("grupos_opciones", "ix_grupos_opciones_is_deleted", schema=schema) is not True:
            op.create_index("ix_grupos_opciones_is_deleted", "grupos_opciones", ["is_deleted"], schema=schema)

    # 6. Tabla `grupo_opciones_items`
    if _has_table("grupo_opciones_items", schema=schema) is not True:
        op.create_table(
            "grupo_opciones_items",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "grupo_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.grupos_opciones.id" if schema else "grupos_opciones.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "producto_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.productos.id" if schema else "productos.id", ondelete="RESTRICT"),
                nullable=True,
            ),
            sa.Column(
                "receta_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.recetas.id" if schema else "recetas.id", ondelete="RESTRICT"),
                nullable=True,
            ),
            sa.Column("cantidad", sa.Numeric(12, 4), nullable=False, server_default="1.0000"),
            sa.Column("es_opcion_default", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("recargo_precio", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "((producto_id IS NOT NULL AND receta_id IS NULL) OR "
                "(producto_id IS NULL AND receta_id IS NOT NULL))",
                name="ck_grupo_opciones_items_origen_exclusivo",
            ),
            schema=schema,
        )
    else:
        if _has_column("grupo_opciones_items", "receta_id", schema=schema) is not True:
            op.add_column(
                "grupo_opciones_items",
                sa.Column(
                    "receta_id",
                    sa.BigInteger(),
                    sa.ForeignKey(f"{schema}.recetas.id" if schema else "recetas.id", ondelete="RESTRICT"),
                    nullable=True,
                ),
                schema=schema,
            )
        if _has_column("grupo_opciones_items", "cantidad", schema=schema) is not True:
            op.add_column("grupo_opciones_items", sa.Column("cantidad", sa.Numeric(12, 4), nullable=False, server_default="1.0000"), schema=schema)
        if _has_column("grupo_opciones_items", "es_opcion_default", schema=schema) is not True:
            op.add_column("grupo_opciones_items", sa.Column("es_opcion_default", sa.Boolean(), nullable=False, server_default="false"), schema=schema)
        if _has_column("grupo_opciones_items", "orden", schema=schema) is not True:
            op.add_column("grupo_opciones_items", sa.Column("orden", sa.Integer(), nullable=False, server_default="0"), schema=schema)

    if _has_table("grupo_opciones_items", schema=schema) is True:
        if _has_index("grupo_opciones_items", "ix_grupo_opciones_items_grupo_id", schema=schema) is not True:
            op.create_index("ix_grupo_opciones_items_grupo_id", "grupo_opciones_items", ["grupo_id"], schema=schema)
        if _has_index("grupo_opciones_items", "ix_grupo_opciones_items_producto_id", schema=schema) is not True:
            op.create_index("ix_grupo_opciones_items_producto_id", "grupo_opciones_items", ["producto_id"], schema=schema)
        if _has_index("grupo_opciones_items", "ix_grupo_opciones_items_receta_id", schema=schema) is not True:
            op.create_index("ix_grupo_opciones_items_receta_id", "grupo_opciones_items", ["receta_id"], schema=schema)

    # 7. Tabla asociativa `receta_grupos_opciones`
    if _has_table("receta_grupos_opciones", schema=schema) is not True:
        op.create_table(
            "receta_grupos_opciones",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "receta_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.recetas.id" if schema else "recetas.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "grupo_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.grupos_opciones.id" if schema else "grupos_opciones.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("es_requerido", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("receta_id", "grupo_id", name="uq_receta_grupos_opciones_receta_grupo"),
            schema=schema,
        )

    if _has_table("receta_grupos_opciones", schema=schema) is True:
        if _has_index("receta_grupos_opciones", "ix_receta_grupos_opciones_receta_id", schema=schema) is not True:
            op.create_index("ix_receta_grupos_opciones_receta_id", "receta_grupos_opciones", ["receta_id"], schema=schema)
        if _has_index("receta_grupos_opciones", "ix_receta_grupos_opciones_grupo_id", schema=schema) is not True:
            op.create_index("ix_receta_grupos_opciones_grupo_id", "receta_grupos_opciones", ["grupo_id"], schema=schema)

    # 8. Tabla `combos`
    if _has_table("combos", schema=schema) is not True:
        op.create_table(
            "combos",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("codigo", sa.String(length=64), nullable=True, unique=True),
            sa.Column("nombre", sa.String(length=180), nullable=False),
            sa.Column("descripcion", sa.Text(), nullable=True),
            sa.Column(
                "categoria_combo_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.categorias_combos.id" if schema else "categorias_combos.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("es_dinamico", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("precio_venta_neto", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("precio_venta_bruto", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("iva_porcentaje", sa.Numeric(5, 2), nullable=False, server_default="19.00"),
            sa.Column("iva_incluido", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("costo_total_calculado", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("imagen_url", sa.String(length=512), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_by", sa.Integer(), nullable=True),
            sa.Column("i18n_data", jsonb_type, nullable=False, server_default="{}"),
            sa.Column("i18n_source_hash", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema=schema,
        )
    else:
        if _has_column("combos", "codigo", schema=schema) is not True:
            op.add_column("combos", sa.Column("codigo", sa.String(length=64), nullable=True, unique=True), schema=schema)
        if _has_column("combos", "descripcion", schema=schema) is not True:
            op.add_column("combos", sa.Column("descripcion", sa.Text(), nullable=True), schema=schema)
        if _has_column("combos", "categoria_combo_id", schema=schema) is not True:
            op.add_column(
                "combos",
                sa.Column(
                    "categoria_combo_id",
                    sa.BigInteger(),
                    sa.ForeignKey(f"{schema}.categorias_combos.id" if schema else "categorias_combos.id", ondelete="SET NULL"),
                    nullable=True,
                ),
                schema=schema,
            )
        if _has_column("combos", "es_dinamico", schema=schema) is not True:
            op.add_column("combos", sa.Column("es_dinamico", sa.Boolean(), nullable=False, server_default="false"), schema=schema)
        if _has_column("combos", "precio_venta_neto", schema=schema) is not True:
            op.add_column("combos", sa.Column("precio_venta_neto", sa.Numeric(14, 2), nullable=False, server_default="0.00"), schema=schema)
        if _has_column("combos", "iva_porcentaje", schema=schema) is not True:
            op.add_column("combos", sa.Column("iva_porcentaje", sa.Numeric(5, 2), nullable=False, server_default="19.00"), schema=schema)
        if _has_column("combos", "iva_incluido", schema=schema) is not True:
            op.add_column("combos", sa.Column("iva_incluido", sa.Boolean(), nullable=False, server_default="true"), schema=schema)
        if _has_column("combos", "costo_total_calculado", schema=schema) is not True:
            op.add_column("combos", sa.Column("costo_total_calculado", sa.Numeric(14, 2), nullable=False, server_default="0.00"), schema=schema)
        if _has_column("combos", "imagen_url", schema=schema) is not True:
            op.add_column("combos", sa.Column("imagen_url", sa.String(length=512), nullable=True), schema=schema)

    if _has_table("combos", schema=schema) is True:
        if _has_index("combos", "ix_combos_codigo", schema=schema) is not True:
            op.create_index("ix_combos_codigo", "combos", ["codigo"], schema=schema)
        if _has_index("combos", "ix_combos_nombre", schema=schema) is not True:
            op.create_index("ix_combos_nombre", "combos", ["nombre"], schema=schema)
        if _has_index("combos", "ix_combos_categoria_combo_id", schema=schema) is not True:
            op.create_index("ix_combos_categoria_combo_id", "combos", ["categoria_combo_id"], schema=schema)
        if _has_index("combos", "ix_combos_es_dinamico", schema=schema) is not True:
            op.create_index("ix_combos_es_dinamico", "combos", ["es_dinamico"], schema=schema)
        if _has_index("combos", "ix_combos_is_deleted", schema=schema) is not True:
            op.create_index("ix_combos_is_deleted", "combos", ["is_deleted"], schema=schema)

    # 9. Tabla `combo_items`
    if _has_table("combo_items", schema=schema) is not True:
        op.create_table(
            "combo_items",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "combo_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.combos.id" if schema else "combos.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "producto_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.productos.id" if schema else "productos.id", ondelete="RESTRICT"),
                nullable=True,
            ),
            sa.Column(
                "receta_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.recetas.id" if schema else "recetas.id", ondelete="RESTRICT"),
                nullable=True,
            ),
            sa.Column("cantidad", sa.Numeric(12, 4), nullable=False, server_default="1.0000"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "((producto_id IS NOT NULL AND receta_id IS NULL) OR "
                "(producto_id IS NULL AND receta_id IS NOT NULL))",
                name="ck_combo_items_origen_exclusivo",
            ),
            schema=schema,
        )
    else:
        if _has_column("combo_items", "producto_id", schema=schema) is not True:
            op.add_column(
                "combo_items",
                sa.Column(
                    "producto_id",
                    sa.BigInteger(),
                    sa.ForeignKey(f"{schema}.productos.id" if schema else "productos.id", ondelete="RESTRICT"),
                    nullable=True,
                ),
                schema=schema,
            )

    if _has_table("combo_items", schema=schema) is True:
        if _has_index("combo_items", "ix_combo_items_combo_id", schema=schema) is not True:
            op.create_index("ix_combo_items_combo_id", "combo_items", ["combo_id"], schema=schema)
        if _has_index("combo_items", "ix_combo_items_producto_id", schema=schema) is not True:
            op.create_index("ix_combo_items_producto_id", "combo_items", ["producto_id"], schema=schema)
        if _has_index("combo_items", "ix_combo_items_receta_id", schema=schema) is not True:
            op.create_index("ix_combo_items_receta_id", "combo_items", ["receta_id"], schema=schema)

    # 10. Tabla asociativa `combo_grupos_opciones`
    if _has_table("combo_grupos_opciones", schema=schema) is not True:
        op.create_table(
            "combo_grupos_opciones",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "combo_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.combos.id" if schema else "combos.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "grupo_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{schema}.grupos_opciones.id" if schema else "grupos_opciones.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("es_requerido", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("combo_id", "grupo_id", name="uq_combo_grupos_opciones_combo_grupo"),
            schema=schema,
        )

    if _has_table("combo_grupos_opciones", schema=schema) is True:
        if _has_index("combo_grupos_opciones", "ix_combo_grupos_opciones_combo_id", schema=schema) is not True:
            op.create_index("ix_combo_grupos_opciones_combo_id", "combo_grupos_opciones", ["combo_id"], schema=schema)
        if _has_index("combo_grupos_opciones", "ix_combo_grupos_opciones_grupo_id", schema=schema) is not True:
            op.create_index("ix_combo_grupos_opciones_grupo_id", "combo_grupos_opciones", ["grupo_id"], schema=schema)


def _apply_downgrade_to_schema(schema: str) -> None:
    """Revierte simétricamente las tablas e índices creados en 0008."""
    # 1. Dropear `combo_grupos_opciones`
    if _has_table("combo_grupos_opciones", schema=schema) is not False:
        if _has_index("combo_grupos_opciones", "ix_combo_grupos_opciones_grupo_id", schema=schema) is not False:
            op.drop_index("ix_combo_grupos_opciones_grupo_id", table_name="combo_grupos_opciones", schema=schema)
        if _has_index("combo_grupos_opciones", "ix_combo_grupos_opciones_combo_id", schema=schema) is not False:
            op.drop_index("ix_combo_grupos_opciones_combo_id", table_name="combo_grupos_opciones", schema=schema)
        op.drop_table("combo_grupos_opciones", schema=schema)

    # 2. Dropear `combo_items`
    if _has_table("combo_items", schema=schema) is not False:
        if _has_index("combo_items", "ix_combo_items_receta_id", schema=schema) is not False:
            op.drop_index("ix_combo_items_receta_id", table_name="combo_items", schema=schema)
        if _has_index("combo_items", "ix_combo_items_producto_id", schema=schema) is not False:
            op.drop_index("ix_combo_items_producto_id", table_name="combo_items", schema=schema)
        if _has_index("combo_items", "ix_combo_items_combo_id", schema=schema) is not False:
            op.drop_index("ix_combo_items_combo_id", table_name="combo_items", schema=schema)
        op.drop_table("combo_items", schema=schema)

    # 3. Dropear `combos`
    if _has_table("combos", schema=schema) is not False:
        if _has_index("combos", "ix_combos_is_deleted", schema=schema) is not False:
            op.drop_index("ix_combos_is_deleted", table_name="combos", schema=schema)
        if _has_index("combos", "ix_combos_es_dinamico", schema=schema) is not False:
            op.drop_index("ix_combos_es_dinamico", table_name="combos", schema=schema)
        if _has_index("combos", "ix_combos_categoria_combo_id", schema=schema) is not False:
            op.drop_index("ix_combos_categoria_combo_id", table_name="combos", schema=schema)
        if _has_index("combos", "ix_combos_nombre", schema=schema) is not False:
            op.drop_index("ix_combos_nombre", table_name="combos", schema=schema)
        if _has_index("combos", "ix_combos_codigo", schema=schema) is not False:
            op.drop_index("ix_combos_codigo", table_name="combos", schema=schema)
        op.drop_table("combos", schema=schema)

    # 4. Dropear `receta_grupos_opciones`
    if _has_table("receta_grupos_opciones", schema=schema) is not False:
        if _has_index("receta_grupos_opciones", "ix_receta_grupos_opciones_grupo_id", schema=schema) is not False:
            op.drop_index("ix_receta_grupos_opciones_grupo_id", table_name="receta_grupos_opciones", schema=schema)
        if _has_index("receta_grupos_opciones", "ix_receta_grupos_opciones_receta_id", schema=schema) is not False:
            op.drop_index("ix_receta_grupos_opciones_receta_id", table_name="receta_grupos_opciones", schema=schema)
        op.drop_table("receta_grupos_opciones", schema=schema)

    # 5. Dropear `grupo_opciones_items`
    if _has_table("grupo_opciones_items", schema=schema) is not False:
        if _has_index("grupo_opciones_items", "ix_grupo_opciones_items_receta_id", schema=schema) is not False:
            op.drop_index("ix_grupo_opciones_items_receta_id", table_name="grupo_opciones_items", schema=schema)
        if _has_index("grupo_opciones_items", "ix_grupo_opciones_items_producto_id", schema=schema) is not False:
            op.drop_index("ix_grupo_opciones_items_producto_id", table_name="grupo_opciones_items", schema=schema)
        if _has_index("grupo_opciones_items", "ix_grupo_opciones_items_grupo_id", schema=schema) is not False:
            op.drop_index("ix_grupo_opciones_items_grupo_id", table_name="grupo_opciones_items", schema=schema)
        op.drop_table("grupo_opciones_items", schema=schema)

    # 6. Dropear `grupos_opciones`
    if _has_table("grupos_opciones", schema=schema) is not False:
        if _has_index("grupos_opciones", "ix_grupos_opciones_is_deleted", schema=schema) is not False:
            op.drop_index("ix_grupos_opciones_is_deleted", table_name="grupos_opciones", schema=schema)
        if _has_index("grupos_opciones", "ix_grupos_opciones_nombre", schema=schema) is not False:
            op.drop_index("ix_grupos_opciones_nombre", table_name="grupos_opciones", schema=schema)
        op.drop_table("grupos_opciones", schema=schema)

    # 7. Dropear `receta_ingredientes`
    if _has_table("receta_ingredientes", schema=schema) is not False:
        if _has_index("receta_ingredientes", "ix_receta_ingredientes_subreceta_id", schema=schema) is not False:
            op.drop_index("ix_receta_ingredientes_subreceta_id", table_name="receta_ingredientes", schema=schema)
        if _has_index("receta_ingredientes", "ix_receta_ingredientes_producto_id", schema=schema) is not False:
            op.drop_index("ix_receta_ingredientes_producto_id", table_name="receta_ingredientes", schema=schema)
        if _has_index("receta_ingredientes", "ix_receta_ingredientes_receta_id", schema=schema) is not False:
            op.drop_index("ix_receta_ingredientes_receta_id", table_name="receta_ingredientes", schema=schema)
        op.drop_table("receta_ingredientes", schema=schema)

    # 8. Dropear `recetas`
    if _has_table("recetas", schema=schema) is not False:
        if _has_index("recetas", "ix_recetas_is_deleted", schema=schema) is not False:
            op.drop_index("ix_recetas_is_deleted", table_name="recetas", schema=schema)
        if _has_index("recetas", "ix_recetas_es_dinamica", schema=schema) is not False:
            op.drop_index("ix_recetas_es_dinamica", table_name="recetas", schema=schema)
        if _has_index("recetas", "ix_recetas_categoria_receta_id", schema=schema) is not False:
            op.drop_index("ix_recetas_categoria_receta_id", table_name="recetas", schema=schema)
        if _has_index("recetas", "ix_recetas_nombre", schema=schema) is not False:
            op.drop_index("ix_recetas_nombre", table_name="recetas", schema=schema)
        if _has_index("recetas", "ix_recetas_codigo", schema=schema) is not False:
            op.drop_index("ix_recetas_codigo", table_name="recetas", schema=schema)
        op.drop_table("recetas", schema=schema)

    # 9. Dropear `categorias_combos`
    if _has_table("categorias_combos", schema=schema) is not False:
        if _has_index("categorias_combos", "ix_categorias_combos_is_deleted", schema=schema) is not False:
            op.drop_index("ix_categorias_combos_is_deleted", table_name="categorias_combos", schema=schema)
        if _has_index("categorias_combos", "ix_categorias_combos_nombre", schema=schema) is not False:
            op.drop_index("ix_categorias_combos_nombre", table_name="categorias_combos", schema=schema)
        op.drop_table("categorias_combos", schema=schema)

    # 10. Dropear `categorias_recetas`
    if _has_table("categorias_recetas", schema=schema) is not False:
        if _has_index("categorias_recetas", "ix_categorias_recetas_is_deleted", schema=schema) is not False:
            op.drop_index("ix_categorias_recetas_is_deleted", table_name="categorias_recetas", schema=schema)
        if _has_index("categorias_recetas", "ix_categorias_recetas_nombre", schema=schema) is not False:
            op.drop_index("ix_categorias_recetas_nombre", table_name="categorias_recetas", schema=schema)
        op.drop_table("categorias_recetas", schema=schema)


def upgrade() -> None:
    """Aplica DDL de recetas, combos y opciones dinámicas en esquemas `tenant_*`."""
    current_schema = _get_current_schema()
    bind = op.get_bind()

    if current_schema and current_schema.startswith("tenant_"):
        target_schemas = [current_schema]
    elif current_schema == "public":
        target_schemas = _get_tenant_schemas(bind)
    else:
        target_schemas = [current_schema] if current_schema else []

    for schema in target_schemas:
        _apply_upgrade_to_schema(schema)


def downgrade() -> None:
    """Revierte simétricamente todas las tablas e índices de recetas y combos en esquemas `tenant_*`."""
    current_schema = _get_current_schema()
    bind = op.get_bind()

    if current_schema and current_schema.startswith("tenant_"):
        target_schemas = [current_schema]
    elif current_schema == "public":
        target_schemas = _get_tenant_schemas(bind)
    else:
        target_schemas = [current_schema] if current_schema else []

    for schema in target_schemas:
        _apply_downgrade_to_schema(schema)
