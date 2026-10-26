"""
0005_tenant_consumption_buffet_and_voice_tables.py
Migración correlativa 0005 para el alcance `tenant`:
Implementa persistencia para el Módulo de Consumo, Manos Libres y Buffet Inteligente (Fase 1 - PLAN_MAESTRO_CONSUMO):
- `consumption_records`: cabecera transaccional de consumo directo y personal.
- `consumption_record_items`: detalle de insumos/productos/recetas/combos consumidos.
- `consumption_templates`: plantillas personalizables de consumo para agilizar turnos.
- `buffet_session_items`: detalle de consumo, reposición y mermas por estación en sesiones de buffet.
- `buffet_templates`: enriquecimiento con descripción, estaciones_json, is_system, is_public.
- `buffet_sessions`: enriquecimiento con área, bodega, creador, tipo_servicio, pax, costos y mermas.
- `buffet_stations`: ordenamiento numérico de estaciones.
- `voice_stations`: estaciones de cocina/barra para captura fonética manos libres.
- `voice_order_logs`: bitácora de transcripción y parsing IA de órdenes por voz.
- Vistas de compatibilidad en español: `registros_consumo`, `registro_consumo_items`, `plantillas_consumo`.
"""
from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_tenant_consumption_buffet_and_voice_tables"
down_revision = "0004_tenant_inventory_kardex_and_physical_counts"
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
    """Aplica DDL completo de consumo, buffet y comandos de voz en el esquema `tenant_*` especificado."""
    bind = op.get_bind()
    jsonb_type = postgresql.JSONB(astext_type=sa.Text())

    # 1. Tabla `consumption_records`
    if _has_table("consumption_records", schema=schema) is not True:
        op.create_table(
            "consumption_records",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("codigo_folio", sa.String(length=64), nullable=False, unique=True),
            sa.Column("folio_ticket", sa.String(length=64), nullable=True),
            sa.Column(
                "area_operativa_id",
                sa.Integer(),
                sa.ForeignKey("areas_operativas.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "bodega_id",
                sa.Integer(),
                sa.ForeignKey("bodegas.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("usuario_id", sa.Integer(), nullable=False),
            sa.Column("tipo_origen", sa.String(length=32), nullable=False, server_default="MANUAL_TERMINAL"),
            sa.Column("costo_total", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema=schema,
        )

    if _has_table("consumption_records", schema=schema) is True:
        if _has_index("consumption_records", "ix_consumption_records_codigo_folio", schema=schema) is not True:
            op.create_index(
                "ix_consumption_records_codigo_folio",
                "consumption_records",
                ["codigo_folio"],
                schema=schema,
            )
        if _has_index("consumption_records", "ix_consumption_records_folio_ticket", schema=schema) is not True:
            op.create_index(
                "ix_consumption_records_folio_ticket",
                "consumption_records",
                ["folio_ticket"],
                schema=schema,
            )
        if _has_index("consumption_records", "ix_consumption_records_area_operativa_id", schema=schema) is not True:
            op.create_index(
                "ix_consumption_records_area_operativa_id",
                "consumption_records",
                ["area_operativa_id"],
                schema=schema,
            )
        if _has_index("consumption_records", "ix_consumption_records_bodega_id", schema=schema) is not True:
            op.create_index(
                "ix_consumption_records_bodega_id",
                "consumption_records",
                ["bodega_id"],
                schema=schema,
            )
        if _has_index("consumption_records", "ix_consumption_records_usuario_id", schema=schema) is not True:
            op.create_index(
                "ix_consumption_records_usuario_id",
                "consumption_records",
                ["usuario_id"],
                schema=schema,
            )
        if _has_index("consumption_records", "ix_consumption_records_tipo_origen", schema=schema) is not True:
            op.create_index(
                "ix_consumption_records_tipo_origen",
                "consumption_records",
                ["tipo_origen"],
                schema=schema,
            )
        if _has_index("consumption_records", "ix_consumption_records_created_at", schema=schema) is not True:
            op.create_index(
                "ix_consumption_records_created_at",
                "consumption_records",
                ["created_at"],
                schema=schema,
            )

    # 2. Tabla `consumption_record_items`
    if _has_table("consumption_record_items", schema=schema) is not True:
        op.create_table(
            "consumption_record_items",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "consumption_record_id",
                sa.BigInteger(),
                sa.ForeignKey("consumption_records.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("tipo_item", sa.String(length=20), nullable=False),
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("cantidad", sa.Numeric(12, 4), nullable=False, server_default="0.0000"),
            sa.Column("unidad_medida", sa.String(length=20), nullable=False, server_default="UN"),
            sa.Column("costo_unitario_ppp", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("costo_total", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("lote_codigo", sa.String(length=64), nullable=True),
            sa.Column("fecha_vencimiento_lote", sa.Date(), nullable=True),
            sa.Column(
                "kardex_movement_id",
                sa.BigInteger(),
                sa.ForeignKey("registro_stock.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("opciones_seleccionadas", jsonb_type, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema=schema,
        )

    if _has_table("consumption_record_items", schema=schema) is True:
        if _has_index("consumption_record_items", "ix_consumption_record_items_record_id", schema=schema) is not True:
            op.create_index(
                "ix_consumption_record_items_record_id",
                "consumption_record_items",
                ["consumption_record_id"],
                schema=schema,
            )
        if _has_index("consumption_record_items", "ix_consumption_record_items_item_id", schema=schema) is not True:
            op.create_index(
                "ix_consumption_record_items_item_id",
                "consumption_record_items",
                ["item_id"],
                schema=schema,
            )
        if _has_index("consumption_record_items", "ix_consumption_record_items_tipo_item", schema=schema) is not True:
            op.create_index(
                "ix_consumption_record_items_tipo_item",
                "consumption_record_items",
                ["tipo_item"],
                schema=schema,
            )
        if _has_index("consumption_record_items", "ix_consumption_record_items_kardex_id", schema=schema) is not True:
            op.create_index(
                "ix_consumption_record_items_kardex_id",
                "consumption_record_items",
                ["kardex_movement_id"],
                schema=schema,
            )

    # 3. Tabla `consumption_templates`
    if _has_table("consumption_templates", schema=schema) is not True:
        op.create_table(
            "consumption_templates",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("slug", sa.String(length=64), nullable=False, unique=True),
            sa.Column("nombre", sa.String(length=128), nullable=False),
            sa.Column("descripcion", sa.Text(), nullable=True),
            sa.Column("usuario_creador_id", sa.Integer(), nullable=False),
            sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("columnas_count", sa.Integer(), nullable=False, server_default="8"),
            sa.Column("sort_mode", sa.String(length=32), nullable=False, server_default="alpha_asc"),
            sa.Column("product_ids", jsonb_type, nullable=False, server_default="[]"),
            sa.Column("custom_product_order", jsonb_type, nullable=True),
            sa.Column("i18n_data", jsonb_type, nullable=False, server_default="{}"),
            sa.Column("i18n_source_hash", sa.String(length=64), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema=schema,
        )

    if _has_table("consumption_templates", schema=schema) is True:
        if _has_index("consumption_templates", "ix_consumption_templates_slug", schema=schema) is not True:
            op.create_index(
                "ix_consumption_templates_slug",
                "consumption_templates",
                ["slug"],
                schema=schema,
            )
        if _has_index("consumption_templates", "ix_consumption_templates_nombre", schema=schema) is not True:
            op.create_index(
                "ix_consumption_templates_nombre",
                "consumption_templates",
                ["nombre"],
                schema=schema,
            )
        if _has_index("consumption_templates", "ix_consumption_templates_creador_id", schema=schema) is not True:
            op.create_index(
                "ix_consumption_templates_creador_id",
                "consumption_templates",
                ["usuario_creador_id"],
                schema=schema,
            )

    # 4. Enriquecimiento de `buffet_templates`
    if _has_table("buffet_templates", schema=schema) is True:
        if _has_column("buffet_templates", "descripcion", schema=schema) is not True:
            op.add_column(
                "buffet_templates",
                sa.Column("descripcion", sa.Text(), nullable=True),
                schema=schema,
            )
        if _has_column("buffet_templates", "estaciones_json", schema=schema) is not True:
            op.add_column(
                "buffet_templates",
                sa.Column("estaciones_json", jsonb_type, nullable=True, server_default="[]"),
                schema=schema,
            )
        if _has_column("buffet_templates", "is_system", schema=schema) is not True:
            op.add_column(
                "buffet_templates",
                sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
                schema=schema,
            )
        if _has_column("buffet_templates", "is_public", schema=schema) is not True:
            op.add_column(
                "buffet_templates",
                sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
                schema=schema,
            )

    # 5. Enriquecimiento de `buffet_sessions`
    if _has_table("buffet_sessions", schema=schema) is True:
        if _has_column("buffet_sessions", "area_operativa_id", schema=schema) is not True:
            op.add_column(
                "buffet_sessions",
                sa.Column(
                    "area_operativa_id",
                    sa.Integer(),
                    sa.ForeignKey("areas_operativas.id", ondelete="SET NULL"),
                    nullable=True,
                ),
                schema=schema,
            )
        if _has_column("buffet_sessions", "bodega_id", schema=schema) is not True:
            op.add_column(
                "buffet_sessions",
                sa.Column(
                    "bodega_id",
                    sa.Integer(),
                    sa.ForeignKey("bodegas.id", ondelete="SET NULL"),
                    nullable=True,
                ),
                schema=schema,
            )
        if _has_column("buffet_sessions", "usuario_creador_id", schema=schema) is not True:
            op.add_column(
                "buffet_sessions",
                sa.Column("usuario_creador_id", sa.Integer(), nullable=True),
                schema=schema,
            )
        if _has_column("buffet_sessions", "tipo_servicio", schema=schema) is not True:
            op.add_column(
                "buffet_sessions",
                sa.Column("tipo_servicio", sa.String(length=64), nullable=False, server_default="DESAYUNO"),
                schema=schema,
            )
        if _has_column("buffet_sessions", "pax_comensales", schema=schema) is not True:
            op.add_column(
                "buffet_sessions",
                sa.Column("pax_comensales", sa.Integer(), nullable=False, server_default="0"),
                schema=schema,
            )
        if _has_column("buffet_sessions", "costo_total_montaje", schema=schema) is not True:
            op.add_column(
                "buffet_sessions",
                sa.Column("costo_total_montaje", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
                schema=schema,
            )
        if _has_column("buffet_sessions", "valor_sobrante_reutilizable", schema=schema) is not True:
            op.add_column(
                "buffet_sessions",
                sa.Column("valor_sobrante_reutilizable", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
                schema=schema,
            )
        if _has_column("buffet_sessions", "costo_neto_pax", schema=schema) is not True:
            op.add_column(
                "buffet_sessions",
                sa.Column("costo_neto_pax", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
                schema=schema,
            )

        if _has_index("buffet_sessions", "ix_buffet_sessions_area_operativa_id", schema=schema) is not True:
            op.create_index(
                "ix_buffet_sessions_area_operativa_id",
                "buffet_sessions",
                ["area_operativa_id"],
                schema=schema,
            )
        if _has_index("buffet_sessions", "ix_buffet_sessions_bodega_id", schema=schema) is not True:
            op.create_index(
                "ix_buffet_sessions_bodega_id",
                "buffet_sessions",
                ["bodega_id"],
                schema=schema,
            )
        if _has_index("buffet_sessions", "ix_buffet_sessions_usuario_creador_id", schema=schema) is not True:
            op.create_index(
                "ix_buffet_sessions_usuario_creador_id",
                "buffet_sessions",
                ["usuario_creador_id"],
                schema=schema,
            )

    # 6. Enriquecimiento de `buffet_stations`
    if (
        _has_table("buffet_stations", schema=schema) is True
        and _has_column("buffet_stations", "orden", schema=schema) is not True
    ):
        op.add_column(
            "buffet_stations",
            sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
            schema=schema,
        )

    # 7. Tabla `buffet_session_items`
    if _has_table("buffet_session_items", schema=schema) is not True:
        op.create_table(
            "buffet_session_items",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "session_id",
                sa.Integer(),
                sa.ForeignKey("buffet_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "station_id",
                sa.Integer(),
                sa.ForeignKey("buffet_stations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("tipo_item", sa.String(length=20), nullable=False, server_default="PRODUCTO"),
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("cantidad_montada", sa.Numeric(12, 4), nullable=False, server_default="0.0000"),
            sa.Column("cantidad_sobrante", sa.Numeric(12, 4), nullable=False, server_default="0.0000"),
            sa.Column("cantidad_merma", sa.Numeric(12, 4), nullable=False, server_default="0.0000"),
            sa.Column("cantidad_neta_consumida", sa.Numeric(12, 4), nullable=False, server_default="0.0000"),
            sa.Column("costo_unitario_ppp", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("costo_total", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema=schema,
        )

    if _has_table("buffet_session_items", schema=schema) is True:
        if _has_index("buffet_session_items", "ix_buffet_session_items_session_id", schema=schema) is not True:
            op.create_index(
                "ix_buffet_session_items_session_id",
                "buffet_session_items",
                ["session_id"],
                schema=schema,
            )
        if _has_index("buffet_session_items", "ix_buffet_session_items_station_id", schema=schema) is not True:
            op.create_index(
                "ix_buffet_session_items_station_id",
                "buffet_session_items",
                ["station_id"],
                schema=schema,
            )
        if _has_index("buffet_session_items", "ix_buffet_session_items_item_id", schema=schema) is not True:
            op.create_index(
                "ix_buffet_session_items_item_id",
                "buffet_session_items",
                ["item_id"],
                schema=schema,
            )
        if _has_index("buffet_session_items", "ix_buffet_session_items_tipo_item", schema=schema) is not True:
            op.create_index(
                "ix_buffet_session_items_tipo_item",
                "buffet_session_items",
                ["tipo_item"],
                schema=schema,
            )

    # 8. Tabla `voice_stations`
    if _has_table("voice_stations", schema=schema) is not True:
        op.create_table(
            "voice_stations",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "area_operativa_id",
                sa.Integer(),
                sa.ForeignKey("areas_operativas.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("nombre_estacion", sa.String(length=64), nullable=False),
            sa.Column("voice_command", sa.String(length=64), nullable=False),
            sa.Column("usuario_asignado_id", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema=schema,
        )

    if _has_table("voice_stations", schema=schema) is True:
        if _has_index("voice_stations", "ix_voice_stations_nombre_estacion", schema=schema) is not True:
            op.create_index(
                "ix_voice_stations_nombre_estacion",
                "voice_stations",
                ["nombre_estacion"],
                schema=schema,
            )
        if _has_index("voice_stations", "ix_voice_stations_area_id", schema=schema) is not True:
            op.create_index(
                "ix_voice_stations_area_id",
                "voice_stations",
                ["area_operativa_id"],
                schema=schema,
            )
        if _has_index("voice_stations", "ix_voice_stations_usuario_id", schema=schema) is not True:
            op.create_index(
                "ix_voice_stations_usuario_id",
                "voice_stations",
                ["usuario_asignado_id"],
                schema=schema,
            )

    # 9. Tabla `voice_order_logs`
    if _has_table("voice_order_logs", schema=schema) is not True:
        op.create_table(
            "voice_order_logs",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "station_id",
                sa.BigInteger(),
                sa.ForeignKey("voice_stations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("texto_transcrito", sa.Text(), nullable=False),
            sa.Column("accion_detectada", sa.String(length=32), nullable=False, server_default="CONSUMO"),
            sa.Column("confianza_ia", sa.Numeric(5, 4), nullable=False, server_default="0.0000"),
            sa.Column("items_interpretados_json", jsonb_type, nullable=True, server_default="[]"),
            sa.Column("estado", sa.String(length=32), nullable=False, server_default="PENDIENTE"),
            sa.Column(
                "consumption_record_id",
                sa.BigInteger(),
                sa.ForeignKey("consumption_records.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            schema=schema,
        )

    if _has_table("voice_order_logs", schema=schema) is True:
        if _has_index("voice_order_logs", "ix_voice_order_logs_station_id", schema=schema) is not True:
            op.create_index(
                "ix_voice_order_logs_station_id",
                "voice_order_logs",
                ["station_id"],
                schema=schema,
            )
        if _has_index("voice_order_logs", "ix_voice_order_logs_accion", schema=schema) is not True:
            op.create_index(
                "ix_voice_order_logs_accion",
                "voice_order_logs",
                ["accion_detectada"],
                schema=schema,
            )
        if _has_index("voice_order_logs", "ix_voice_order_logs_estado", schema=schema) is not True:
            op.create_index(
                "ix_voice_order_logs_estado",
                "voice_order_logs",
                ["estado"],
                schema=schema,
            )
        if _has_index("voice_order_logs", "ix_voice_order_logs_consumption_id", schema=schema) is not True:
            op.create_index(
                "ix_voice_order_logs_consumption_id",
                "voice_order_logs",
                ["consumption_record_id"],
                schema=schema,
            )

    # 10. Vistas de compatibilidad en español
    try:
        bind.execute(
            sa.text(
                f'CREATE OR REPLACE VIEW "{schema}".registros_consumo AS '  # noqa: S608
                f'SELECT * FROM "{schema}".consumption_records;'
            )
        )
        bind.execute(
            sa.text(
                f'CREATE OR REPLACE VIEW "{schema}".registro_consumo_items AS '  # noqa: S608
                f'SELECT * FROM "{schema}".consumption_record_items;'
            )
        )
        bind.execute(
            sa.text(
                f'CREATE OR REPLACE VIEW "{schema}".plantillas_consumo AS '  # noqa: S608
                f'SELECT * FROM "{schema}".consumption_templates;'
            )
        )
    except Exception:  # noqa: S110
        pass


def _apply_downgrade_to_schema(schema: str) -> None:
    """Revierte simétricamente todas las tablas, columnas, índices y vistas creadas en `0005`."""
    bind = op.get_bind()

    # 1. Dropear vistas de compatibilidad
    try:
        bind.execute(sa.text(f'DROP VIEW IF EXISTS "{schema}".plantillas_consumo CASCADE;'))
        bind.execute(sa.text(f'DROP VIEW IF EXISTS "{schema}".registro_consumo_items CASCADE;'))
        bind.execute(sa.text(f'DROP VIEW IF EXISTS "{schema}".registros_consumo CASCADE;'))
    except Exception:  # noqa: S110
        pass

    # 2. Dropear `voice_order_logs`
    if _has_table("voice_order_logs", schema=schema) is not False:
        if _has_index("voice_order_logs", "ix_voice_order_logs_consumption_id", schema=schema) is not False:
            op.drop_index("ix_voice_order_logs_consumption_id", table_name="voice_order_logs", schema=schema)
        if _has_index("voice_order_logs", "ix_voice_order_logs_estado", schema=schema) is not False:
            op.drop_index("ix_voice_order_logs_estado", table_name="voice_order_logs", schema=schema)
        if _has_index("voice_order_logs", "ix_voice_order_logs_accion", schema=schema) is not False:
            op.drop_index("ix_voice_order_logs_accion", table_name="voice_order_logs", schema=schema)
        if _has_index("voice_order_logs", "ix_voice_order_logs_station_id", schema=schema) is not False:
            op.drop_index("ix_voice_order_logs_station_id", table_name="voice_order_logs", schema=schema)
        op.drop_table("voice_order_logs", schema=schema)

    # 3. Dropear `voice_stations`
    if _has_table("voice_stations", schema=schema) is not False:
        if _has_index("voice_stations", "ix_voice_stations_usuario_id", schema=schema) is not False:
            op.drop_index("ix_voice_stations_usuario_id", table_name="voice_stations", schema=schema)
        if _has_index("voice_stations", "ix_voice_stations_area_id", schema=schema) is not False:
            op.drop_index("ix_voice_stations_area_id", table_name="voice_stations", schema=schema)
        if _has_index("voice_stations", "ix_voice_stations_nombre_estacion", schema=schema) is not False:
            op.drop_index("ix_voice_stations_nombre_estacion", table_name="voice_stations", schema=schema)
        op.drop_table("voice_stations", schema=schema)

    # 4. Dropear `buffet_session_items`
    if _has_table("buffet_session_items", schema=schema) is not False:
        if _has_index("buffet_session_items", "ix_buffet_session_items_tipo_item", schema=schema) is not False:
            op.drop_index("ix_buffet_session_items_tipo_item", table_name="buffet_session_items", schema=schema)
        if _has_index("buffet_session_items", "ix_buffet_session_items_item_id", schema=schema) is not False:
            op.drop_index("ix_buffet_session_items_item_id", table_name="buffet_session_items", schema=schema)
        if _has_index("buffet_session_items", "ix_buffet_session_items_station_id", schema=schema) is not False:
            op.drop_index("ix_buffet_session_items_station_id", table_name="buffet_session_items", schema=schema)
        if _has_index("buffet_session_items", "ix_buffet_session_items_session_id", schema=schema) is not False:
            op.drop_index("ix_buffet_session_items_session_id", table_name="buffet_session_items", schema=schema)
        op.drop_table("buffet_session_items", schema=schema)

    # 5. Revertir `buffet_stations`
    if (
        _has_table("buffet_stations", schema=schema) is True
        and _has_column("buffet_stations", "orden", schema=schema) is not False
    ):
        op.drop_column("buffet_stations", "orden", schema=schema)

    # 6. Revertir `buffet_sessions`
    if _has_table("buffet_sessions", schema=schema) is True:
        if _has_index("buffet_sessions", "ix_buffet_sessions_usuario_creador_id", schema=schema) is not False:
            op.drop_index("ix_buffet_sessions_usuario_creador_id", table_name="buffet_sessions", schema=schema)
        if _has_index("buffet_sessions", "ix_buffet_sessions_bodega_id", schema=schema) is not False:
            op.drop_index("ix_buffet_sessions_bodega_id", table_name="buffet_sessions", schema=schema)
        if _has_index("buffet_sessions", "ix_buffet_sessions_area_operativa_id", schema=schema) is not False:
            op.drop_index("ix_buffet_sessions_area_operativa_id", table_name="buffet_sessions", schema=schema)

        if _has_column("buffet_sessions", "costo_neto_pax", schema=schema) is not False:
            op.drop_column("buffet_sessions", "costo_neto_pax", schema=schema)
        if _has_column("buffet_sessions", "valor_sobrante_reutilizable", schema=schema) is not False:
            op.drop_column("buffet_sessions", "valor_sobrante_reutilizable", schema=schema)
        if _has_column("buffet_sessions", "costo_total_montaje", schema=schema) is not False:
            op.drop_column("buffet_sessions", "costo_total_montaje", schema=schema)
        if _has_column("buffet_sessions", "pax_comensales", schema=schema) is not False:
            op.drop_column("buffet_sessions", "pax_comensales", schema=schema)
        if _has_column("buffet_sessions", "tipo_servicio", schema=schema) is not False:
            op.drop_column("buffet_sessions", "tipo_servicio", schema=schema)
        if _has_column("buffet_sessions", "usuario_creador_id", schema=schema) is not False:
            op.drop_column("buffet_sessions", "usuario_creador_id", schema=schema)
        if _has_column("buffet_sessions", "bodega_id", schema=schema) is not False:
            op.drop_column("buffet_sessions", "bodega_id", schema=schema)
        if _has_column("buffet_sessions", "area_operativa_id", schema=schema) is not False:
            op.drop_column("buffet_sessions", "area_operativa_id", schema=schema)

    # 7. Revertir `buffet_templates`
    if _has_table("buffet_templates", schema=schema) is True:
        if _has_column("buffet_templates", "is_public", schema=schema) is not False:
            op.drop_column("buffet_templates", "is_public", schema=schema)
        if _has_column("buffet_templates", "is_system", schema=schema) is not False:
            op.drop_column("buffet_templates", "is_system", schema=schema)
        if _has_column("buffet_templates", "estaciones_json", schema=schema) is not False:
            op.drop_column("buffet_templates", "estaciones_json", schema=schema)
        if _has_column("buffet_templates", "descripcion", schema=schema) is not False:
            op.drop_column("buffet_templates", "descripcion", schema=schema)

    # 8. Dropear `consumption_templates`
    if _has_table("consumption_templates", schema=schema) is not False:
        if _has_index("consumption_templates", "ix_consumption_templates_creador_id", schema=schema) is not False:
            op.drop_index("ix_consumption_templates_creador_id", table_name="consumption_templates", schema=schema)
        if _has_index("consumption_templates", "ix_consumption_templates_nombre", schema=schema) is not False:
            op.drop_index("ix_consumption_templates_nombre", table_name="consumption_templates", schema=schema)
        if _has_index("consumption_templates", "ix_consumption_templates_slug", schema=schema) is not False:
            op.drop_index("ix_consumption_templates_slug", table_name="consumption_templates", schema=schema)
        op.drop_table("consumption_templates", schema=schema)

    # 9. Dropear `consumption_record_items`
    if _has_table("consumption_record_items", schema=schema) is not False:
        if _has_index("consumption_record_items", "ix_consumption_record_items_kardex_id", schema=schema) is not False:
            op.drop_index("ix_consumption_record_items_kardex_id", table_name="consumption_record_items", schema=schema)
        if _has_index("consumption_record_items", "ix_consumption_record_items_tipo_item", schema=schema) is not False:
            op.drop_index("ix_consumption_record_items_tipo_item", table_name="consumption_record_items", schema=schema)
        if _has_index("consumption_record_items", "ix_consumption_record_items_item_id", schema=schema) is not False:
            op.drop_index("ix_consumption_record_items_item_id", table_name="consumption_record_items", schema=schema)
        if _has_index("consumption_record_items", "ix_consumption_record_items_record_id", schema=schema) is not False:
            op.drop_index("ix_consumption_record_items_record_id", table_name="consumption_record_items", schema=schema)
        op.drop_table("consumption_record_items", schema=schema)

    # 10. Dropear `consumption_records`
    if _has_table("consumption_records", schema=schema) is not False:
        if _has_index("consumption_records", "ix_consumption_records_created_at", schema=schema) is not False:
            op.drop_index("ix_consumption_records_created_at", table_name="consumption_records", schema=schema)
        if _has_index("consumption_records", "ix_consumption_records_tipo_origen", schema=schema) is not False:
            op.drop_index("ix_consumption_records_tipo_origen", table_name="consumption_records", schema=schema)
        if _has_index("consumption_records", "ix_consumption_records_usuario_id", schema=schema) is not False:
            op.drop_index("ix_consumption_records_usuario_id", table_name="consumption_records", schema=schema)
        if _has_index("consumption_records", "ix_consumption_records_bodega_id", schema=schema) is not False:
            op.drop_index("ix_consumption_records_bodega_id", table_name="consumption_records", schema=schema)
        if _has_index("consumption_records", "ix_consumption_records_area_operativa_id", schema=schema) is not False:
            op.drop_index("ix_consumption_records_area_operativa_id", table_name="consumption_records", schema=schema)
        if _has_index("consumption_records", "ix_consumption_records_folio_ticket", schema=schema) is not False:
            op.drop_index("ix_consumption_records_folio_ticket", table_name="consumption_records", schema=schema)
        if _has_index("consumption_records", "ix_consumption_records_codigo_folio", schema=schema) is not False:
            op.drop_index("ix_consumption_records_codigo_folio", table_name="consumption_records", schema=schema)
        op.drop_table("consumption_records", schema=schema)


def upgrade() -> None:
    """Aplica DDL de consumo, buffet enriquecido y voz/manos libres en esquemas `tenant_*`."""
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
    """Revierte simétricamente los cambios DDL de consumo, buffet y voz en los esquemas `tenant_*` activos."""
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
