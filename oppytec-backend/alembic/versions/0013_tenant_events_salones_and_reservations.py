"""
0013_tenant_events_salones_and_reservations.py
Migración correlativa 0013 para el alcance `tenant`:
Implementa la Fase 1 del PLAN_MAESTRO_EVENTOS.md:
- `salones`: Espacios físicos y salones de banquetes con tarificación neta/bruta, IVA, capacidad y estado higiénico/operativo.
- `salon_areas_operativas`: Tabla pivote Many-to-Many entre salones y áreas operativas.
- `eventos`: Cabecera de reservas, banquetes y eventos agendados con control anti-overbooking y auditoría de ejecución.
- `evento_items`: Insumos y materias primas directas asignadas al evento desde bodegas específicas.
- `evento_recetas`: Fichas técnicas gastronómicas y recetas asignadas al menú del evento.
- `evento_combos`: Paquetes y menús de combos asignados al evento.
- `evento_trabajadores`: Brigada y equipo asignado al evento (mozos, cocineros, bartenders, jefes de sala).
- `evento_consumos_kardex`: Trazabilidad inmutable de rebajas de inventario en Kardex tras ejecución del evento.
"""
from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_tenant_events_salones_and_reservations"
down_revision = "0012_public_ai_model_configs_catalog_extension"
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
    """Descubre todos los esquemas tenant_* registrados dinámicamente en PostgreSQL."""
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


def _apply_upgrade_to_schema(schema: str) -> None:
    """Aplica DDL de salones, eventos y reservaciones en el esquema tenant especificado."""
    is_pg = _is_postgresql()
    uuid_type = postgresql.UUID(as_uuid=True) if is_pg else sa.String(36)
    uuid_default = sa.text("gen_random_uuid()") if is_pg else None
    jsonb_type = postgresql.JSONB(astext_type=sa.Text()) if is_pg else sa.JSON()

    # -------------------------------------------------------------------------
    # 1. Tabla `salones`
    # -------------------------------------------------------------------------
    if _has_table("salones", schema=schema) is not True:
        op.create_table(
            "salones",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
            sa.Column("nombre", sa.String(length=200), nullable=False),
            sa.Column("capacidad_personas", sa.Integer(), nullable=True),
            sa.Column("precio_neto", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("iva_porcentaje", sa.Numeric(5, 2), nullable=False, server_default="19.00"),
            sa.Column("precio_bruto", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column("estado", sa.String(length=32), nullable=False, server_default="activo"),
            sa.Column("color", sa.String(length=32), nullable=False, server_default="#ec4899"),
            sa.Column(
                "areas_operativas_ids",
                jsonb_type,
                nullable=False,
                server_default=sa.text("'[]'::jsonb" if is_pg else "'[]'"),
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_by", sa.Integer(), nullable=True),
            sa.Column("i18n_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("i18n_source_hash", sa.String(length=64), nullable=True),
            schema=schema,
        )

    if _has_table("salones", schema=schema) is True:
        if _has_index("salones", "ix_salones_nombre", schema=schema) is not True:
            op.create_index("ix_salones_nombre", "salones", ["nombre"], schema=schema)
        if _has_index("salones", "ix_salones_estado", schema=schema) is not True:
            op.create_index("ix_salones_estado", "salones", ["estado"], schema=schema)
        if _has_index("salones", "ix_salones_is_deleted", schema=schema) is not True:
            op.create_index("ix_salones_is_deleted", "salones", ["is_deleted"], schema=schema)

    # -------------------------------------------------------------------------
    # 2. Tabla `salon_areas_operativas` (relación Many-to-Many física)
    # -------------------------------------------------------------------------
    if _has_table("salon_areas_operativas", schema=schema) is not True:
        op.create_table(
            "salon_areas_operativas",
            sa.Column(
                "salon_id",
                uuid_type,
                sa.ForeignKey(f"{schema}.salones.id" if schema else "salones.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("area_operativa_id", sa.BigInteger(), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema=schema,
        )

    # -------------------------------------------------------------------------
    # 3. Tabla `eventos`
    # -------------------------------------------------------------------------
    if _has_table("eventos", schema=schema) is not True:
        op.create_table(
            "eventos",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
            sa.Column("nombre", sa.String(length=255), nullable=False),
            sa.Column("tipo_evento", sa.String(length=64), nullable=False, server_default="banquete"),
            sa.Column("titular", sa.String(length=255), nullable=True),
            sa.Column(
                "salon_id",
                uuid_type,
                sa.ForeignKey(f"{schema}.salones.id" if schema else "salones.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("lugar", sa.String(length=255), nullable=True),
            sa.Column("fecha", sa.Date(), nullable=False),
            sa.Column("hora_inicio", sa.Time(), nullable=False, server_default="00:00:00"),
            sa.Column("hora_fin", sa.Time(), nullable=False, server_default="23:59:59"),
            sa.Column("cantidad_personas", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("cantidad_invitados", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("estado", sa.String(length=32), nullable=False, server_default="AGENDADO"),
            sa.Column("color", sa.String(length=32), nullable=False, server_default="#ec4899"),
            sa.Column("ejecutado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("cancelado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("ejecutado_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancelado_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("motivo_cancelacion", sa.Text(), nullable=True),
            sa.Column("encargado_id", sa.Integer(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("valor_publico", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column("nota_personal", sa.Text(), nullable=True),
            sa.Column("nota_equipo", sa.Text(), nullable=True),
            sa.Column("nota_visible", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_by", sa.Integer(), nullable=True),
            sa.Column("i18n_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("i18n_source_hash", sa.String(length=64), nullable=True),
            schema=schema,
        )

    if _has_table("eventos", schema=schema) is True:
        if _has_index("eventos", "ix_eventos_fecha", schema=schema) is not True:
            op.create_index("ix_eventos_fecha", "eventos", ["fecha"], schema=schema)
        if _has_index("eventos", "ix_eventos_salon_id_fecha", schema=schema) is not True:
            op.create_index("ix_eventos_salon_id_fecha", "eventos", ["salon_id", "fecha"], schema=schema)
        if _has_index("eventos", "ix_eventos_fecha_cancelado_ejecutado", schema=schema) is not True:
            op.create_index("ix_eventos_fecha_cancelado_ejecutado", "eventos", ["fecha", "cancelado", "ejecutado"], schema=schema)
        if _has_index("eventos", "ix_eventos_estado", schema=schema) is not True:
            op.create_index("ix_eventos_estado", "eventos", ["estado"], schema=schema)
        if _has_index("eventos", "ix_eventos_is_deleted", schema=schema) is not True:
            op.create_index("ix_eventos_is_deleted", "eventos", ["is_deleted"], schema=schema)
        if _has_index("eventos", "ix_eventos_encargado_id", schema=schema) is not True:
            op.create_index("ix_eventos_encargado_id", "eventos", ["encargado_id"], schema=schema)

    # -------------------------------------------------------------------------
    # 4. Tabla `evento_items` (Insumos directos de inventario)
    # -------------------------------------------------------------------------
    if _has_table("evento_items", schema=schema) is not True:
        op.create_table(
            "evento_items",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "evento_id",
                uuid_type,
                sa.ForeignKey(f"{schema}.eventos.id" if schema else "eventos.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("producto_id", sa.BigInteger(), nullable=False),
            sa.Column("bodega_id", sa.BigInteger(), nullable=False),
            sa.Column("cantidad", sa.Numeric(12, 4), nullable=False),
            sa.Column("costo_unitario_estimado", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.UniqueConstraint("evento_id", "producto_id", "bodega_id", name="uq_evento_items_evento_producto_bodega"),
            schema=schema,
        )

    if _has_table("evento_items", schema=schema) is True:
        if _has_index("evento_items", "ix_evento_items_evento_id", schema=schema) is not True:
            op.create_index("ix_evento_items_evento_id", "evento_items", ["evento_id"], schema=schema)
        if _has_index("evento_items", "ix_evento_items_producto_id", schema=schema) is not True:
            op.create_index("ix_evento_items_producto_id", "evento_items", ["producto_id"], schema=schema)
        if _has_index("evento_items", "ix_evento_items_bodega_id", schema=schema) is not True:
            op.create_index("ix_evento_items_bodega_id", "evento_items", ["bodega_id"], schema=schema)

    # -------------------------------------------------------------------------
    # 5. Tabla `evento_recetas` (Fichas gastronómicas)
    # -------------------------------------------------------------------------
    if _has_table("evento_recetas", schema=schema) is not True:
        op.create_table(
            "evento_recetas",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "evento_id",
                uuid_type,
                sa.ForeignKey(f"{schema}.eventos.id" if schema else "eventos.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("receta_id", sa.BigInteger(), nullable=False),
            sa.Column("bodega_id", sa.BigInteger(), nullable=False),
            sa.Column("porciones", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("cantidad", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.UniqueConstraint("evento_id", "receta_id", name="uq_evento_recetas_evento_receta"),
            schema=schema,
        )

    if _has_table("evento_recetas", schema=schema) is True:
        if _has_index("evento_recetas", "ix_evento_recetas_evento_id", schema=schema) is not True:
            op.create_index("ix_evento_recetas_evento_id", "evento_recetas", ["evento_id"], schema=schema)
        if _has_index("evento_recetas", "ix_evento_recetas_receta_id", schema=schema) is not True:
            op.create_index("ix_evento_recetas_receta_id", "evento_recetas", ["receta_id"], schema=schema)
        if _has_index("evento_recetas", "ix_evento_recetas_bodega_id", schema=schema) is not True:
            op.create_index("ix_evento_recetas_bodega_id", "evento_recetas", ["bodega_id"], schema=schema)

    # -------------------------------------------------------------------------
    # 6. Tabla `evento_combos` (Paquetes y combos)
    # -------------------------------------------------------------------------
    if _has_table("evento_combos", schema=schema) is not True:
        op.create_table(
            "evento_combos",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "evento_id",
                uuid_type,
                sa.ForeignKey(f"{schema}.eventos.id" if schema else "eventos.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("combo_id", sa.BigInteger(), nullable=False),
            sa.Column("bodega_id", sa.BigInteger(), nullable=False),
            sa.Column("cantidad", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.UniqueConstraint("evento_id", "combo_id", name="uq_evento_combos_evento_combo"),
            schema=schema,
        )

    if _has_table("evento_combos", schema=schema) is True:
        if _has_index("evento_combos", "ix_evento_combos_evento_id", schema=schema) is not True:
            op.create_index("ix_evento_combos_evento_id", "evento_combos", ["evento_id"], schema=schema)
        if _has_index("evento_combos", "ix_evento_combos_combo_id", schema=schema) is not True:
            op.create_index("ix_evento_combos_combo_id", "evento_combos", ["combo_id"], schema=schema)
        if _has_index("evento_combos", "ix_evento_combos_bodega_id", schema=schema) is not True:
            op.create_index("ix_evento_combos_bodega_id", "evento_combos", ["bodega_id"], schema=schema)

    # -------------------------------------------------------------------------
    # 7. Tabla `evento_trabajadores` (Brigada y personal)
    # -------------------------------------------------------------------------
    if _has_table("evento_trabajadores", schema=schema) is not True:
        op.create_table(
            "evento_trabajadores",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "evento_id",
                uuid_type,
                sa.ForeignKey(f"{schema}.eventos.id" if schema else "eventos.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("usuario_id", sa.Integer(), nullable=False),
            sa.Column("rol_evento", sa.String(length=64), nullable=True),
            sa.Column("horas_asignadas", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.UniqueConstraint("evento_id", "usuario_id", name="uq_evento_trabajadores_evento_usuario"),
            schema=schema,
        )

    if _has_table("evento_trabajadores", schema=schema) is True:
        if _has_index("evento_trabajadores", "ix_evento_trabajadores_evento_id", schema=schema) is not True:
            op.create_index("ix_evento_trabajadores_evento_id", "evento_trabajadores", ["evento_id"], schema=schema)
        if _has_index("evento_trabajadores", "ix_evento_trabajadores_usuario_id", schema=schema) is not True:
            op.create_index("ix_evento_trabajadores_usuario_id", "evento_trabajadores", ["usuario_id"], schema=schema)

    # -------------------------------------------------------------------------
    # 8. Tabla `evento_consumos_kardex` (Trazabilidad en inventario)
    # -------------------------------------------------------------------------
    if _has_table("evento_consumos_kardex", schema=schema) is not True:
        op.create_table(
            "evento_consumos_kardex",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "evento_id",
                uuid_type,
                sa.ForeignKey(f"{schema}.eventos.id" if schema else "eventos.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("kardex_movement_id", sa.BigInteger(), nullable=True),
            sa.Column("producto_id", sa.BigInteger(), nullable=False),
            sa.Column("bodega_id", sa.BigInteger(), nullable=False),
            sa.Column("cantidad_consumida", sa.Numeric(12, 4), nullable=False),
            sa.Column("costo_unitario_ppp", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("origen_tipo", sa.String(length=30), nullable=False, server_default="DIRECTO"),
            sa.Column("origen_id", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema=schema,
        )

    if _has_table("evento_consumos_kardex", schema=schema) is True:
        if _has_index("evento_consumos_kardex", "ix_evento_consumos_evento_id", schema=schema) is not True:
            op.create_index("ix_evento_consumos_evento_id", "evento_consumos_kardex", ["evento_id"], schema=schema)
        if _has_index("evento_consumos_kardex", "ix_evento_consumos_kardex_id", schema=schema) is not True:
            op.create_index("ix_evento_consumos_kardex_id", "evento_consumos_kardex", ["kardex_movement_id"], schema=schema)


def _apply_downgrade_to_schema(schema: str) -> None:
    """Elimina en orden inverso de dependencias las tablas e índices de eventos y salones."""
    # 8. Dropear `evento_consumos_kardex`
    if _has_table("evento_consumos_kardex", schema=schema) is not False:
        if _has_index("evento_consumos_kardex", "ix_evento_consumos_kardex_id", schema=schema) is not False:
            op.drop_index("ix_evento_consumos_kardex_id", table_name="evento_consumos_kardex", schema=schema)
        if _has_index("evento_consumos_kardex", "ix_evento_consumos_evento_id", schema=schema) is not False:
            op.drop_index("ix_evento_consumos_evento_id", table_name="evento_consumos_kardex", schema=schema)
        op.drop_table("evento_consumos_kardex", schema=schema)

    # 7. Dropear `evento_trabajadores`
    if _has_table("evento_trabajadores", schema=schema) is not False:
        if _has_index("evento_trabajadores", "ix_evento_trabajadores_usuario_id", schema=schema) is not False:
            op.drop_index("ix_evento_trabajadores_usuario_id", table_name="evento_trabajadores", schema=schema)
        if _has_index("evento_trabajadores", "ix_evento_trabajadores_evento_id", schema=schema) is not False:
            op.drop_index("ix_evento_trabajadores_evento_id", table_name="evento_trabajadores", schema=schema)
        op.drop_table("evento_trabajadores", schema=schema)

    # 6. Dropear `evento_combos`
    if _has_table("evento_combos", schema=schema) is not False:
        if _has_index("evento_combos", "ix_evento_combos_bodega_id", schema=schema) is not False:
            op.drop_index("ix_evento_combos_bodega_id", table_name="evento_combos", schema=schema)
        if _has_index("evento_combos", "ix_evento_combos_combo_id", schema=schema) is not False:
            op.drop_index("ix_evento_combos_combo_id", table_name="evento_combos", schema=schema)
        if _has_index("evento_combos", "ix_evento_combos_evento_id", schema=schema) is not False:
            op.drop_index("ix_evento_combos_evento_id", table_name="evento_combos", schema=schema)
        op.drop_table("evento_combos", schema=schema)

    # 5. Dropear `evento_recetas`
    if _has_table("evento_recetas", schema=schema) is not False:
        if _has_index("evento_recetas", "ix_evento_recetas_bodega_id", schema=schema) is not False:
            op.drop_index("ix_evento_recetas_bodega_id", table_name="evento_recetas", schema=schema)
        if _has_index("evento_recetas", "ix_evento_recetas_receta_id", schema=schema) is not False:
            op.drop_index("ix_evento_recetas_receta_id", table_name="evento_recetas", schema=schema)
        if _has_index("evento_recetas", "ix_evento_recetas_evento_id", schema=schema) is not False:
            op.drop_index("ix_evento_recetas_evento_id", table_name="evento_recetas", schema=schema)
        op.drop_table("evento_recetas", schema=schema)

    # 4. Dropear `evento_items`
    if _has_table("evento_items", schema=schema) is not False:
        if _has_index("evento_items", "ix_evento_items_bodega_id", schema=schema) is not False:
            op.drop_index("ix_evento_items_bodega_id", table_name="evento_items", schema=schema)
        if _has_index("evento_items", "ix_evento_items_producto_id", schema=schema) is not False:
            op.drop_index("ix_evento_items_producto_id", table_name="evento_items", schema=schema)
        if _has_index("evento_items", "ix_evento_items_evento_id", schema=schema) is not False:
            op.drop_index("ix_evento_items_evento_id", table_name="evento_items", schema=schema)
        op.drop_table("evento_items", schema=schema)

    # 3. Dropear `eventos`
    if _has_table("eventos", schema=schema) is not False:
        if _has_index("eventos", "ix_eventos_encargado_id", schema=schema) is not False:
            op.drop_index("ix_eventos_encargado_id", table_name="eventos", schema=schema)
        if _has_index("eventos", "ix_eventos_is_deleted", schema=schema) is not False:
            op.drop_index("ix_eventos_is_deleted", table_name="eventos", schema=schema)
        if _has_index("eventos", "ix_eventos_estado", schema=schema) is not False:
            op.drop_index("ix_eventos_estado", table_name="eventos", schema=schema)
        if _has_index("eventos", "ix_eventos_fecha_cancelado_ejecutado", schema=schema) is not False:
            op.drop_index("ix_eventos_fecha_cancelado_ejecutado", table_name="eventos", schema=schema)
        if _has_index("eventos", "ix_eventos_salon_id_fecha", schema=schema) is not False:
            op.drop_index("ix_eventos_salon_id_fecha", table_name="eventos", schema=schema)
        if _has_index("eventos", "ix_eventos_fecha", schema=schema) is not False:
            op.drop_index("ix_eventos_fecha", table_name="eventos", schema=schema)
        op.drop_table("eventos", schema=schema)

    # 2. Dropear `salon_areas_operativas`
    if _has_table("salon_areas_operativas", schema=schema) is not False:
        op.drop_table("salon_areas_operativas", schema=schema)

    # 1. Dropear `salones`
    if _has_table("salones", schema=schema) is not False:
        if _has_index("salones", "ix_salones_is_deleted", schema=schema) is not False:
            op.drop_index("ix_salones_is_deleted", table_name="salones", schema=schema)
        if _has_index("salones", "ix_salones_estado", schema=schema) is not False:
            op.drop_index("ix_salones_estado", table_name="salones", schema=schema)
        if _has_index("salones", "ix_salones_nombre", schema=schema) is not False:
            op.drop_index("ix_salones_nombre", table_name="salones", schema=schema)
        op.drop_table("salones", schema=schema)


def upgrade() -> None:
    """Aplica DDL de salones y eventos en esquemas `tenant_*`."""
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
    """Revierte simétricamente todas las tablas e índices de eventos y salones en esquemas `tenant_*`."""
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
