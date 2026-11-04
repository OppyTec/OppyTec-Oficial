"""
0015_tenant_actividades_triada_enriquecida.py
Migración correlativa 0015 para el alcance `tenant`:
Implementa la Fase 1 del Plan Maestro del Panel de Actividades (Notas, Tareas y Horarios):
- `turnos_horarios`: Enriquecimiento con usuario_id, area_id, fecha_inicio, fecha_fin, hora_inicio, hora_fin, nota, color, creado_por.
- `notas_personales`: Enriquecimiento con area_id y fecha.
- `notas_equipo`: Enriquecimiento con area_id, categoria, fecha, insumo_id, receta_id, foto_url.
- `nota_equipo_menciones`: Menciones de colaboradores vinculadas a notas de equipo con constraints CASCADE.
- `nota_equipo_lecturas`: Registro y auditoría de lecturas / vistos de notas de equipo.
- `plantillas_rutinas`: Catálogo de rutinas operativas (apertura, cierre, limpieza) con items estructurados.
- `tareas`: Enriquecimiento con creador_user_id, area_id, descripcion, estado, urgencia, fecha_limite, nota_incompleta, compra_id, foto_evidencia_url, plantilla_id.
"""
from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015_tenant_actividades_triada_enriquecida"
down_revision = "0014_tenant_projection_snapshots_and_consumption_rates"
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
    """Aplica las extensiones de la tríada de actividades e índices en un esquema tenant_*."""
    bind = op.get_bind()
    is_pg = _is_postgresql()
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    json_empty_array = sa.text("'[]'::jsonb") if is_pg else sa.text("'[]'")

    prefix = f'"{schema}".' if schema else ""
    notas_equipo_fk = f"{schema}.notas_equipo.id" if schema else "notas_equipo.id"
    plantillas_rutinas_fk = f"{schema}.plantillas_rutinas.id" if schema else "plantillas_rutinas.id"

    # =========================================================================
    # 1. Enriquecer `turnos_horarios`
    # =========================================================================
    if _has_table("turnos_horarios", schema=schema) is True:
        if _has_column("turnos_horarios", "usuario_id", schema=schema) is not True:
            op.add_column("turnos_horarios", sa.Column("usuario_id", sa.Integer(), nullable=True), schema=schema)
        if _has_column("turnos_horarios", "area_id", schema=schema) is not True:
            op.add_column("turnos_horarios", sa.Column("area_id", sa.String(length=64), nullable=True), schema=schema)
        if _has_column("turnos_horarios", "fecha_inicio", schema=schema) is not True:
            op.add_column("turnos_horarios", sa.Column("fecha_inicio", sa.Date(), nullable=True), schema=schema)
        if _has_column("turnos_horarios", "fecha_fin", schema=schema) is not True:
            op.add_column("turnos_horarios", sa.Column("fecha_fin", sa.Date(), nullable=True), schema=schema)
        if _has_column("turnos_horarios", "hora_inicio", schema=schema) is not True:
            op.add_column("turnos_horarios", sa.Column("hora_inicio", sa.Time(), nullable=True), schema=schema)
        if _has_column("turnos_horarios", "hora_fin", schema=schema) is not True:
            op.add_column("turnos_horarios", sa.Column("hora_fin", sa.Time(), nullable=True), schema=schema)
        if _has_column("turnos_horarios", "nota", schema=schema) is not True:
            op.add_column("turnos_horarios", sa.Column("nota", sa.String(length=500), nullable=True), schema=schema)
        if _has_column("turnos_horarios", "color", schema=schema) is not True:
            op.add_column("turnos_horarios", sa.Column("color", sa.String(length=20), nullable=True), schema=schema)
        if _has_column("turnos_horarios", "creado_por", schema=schema) is not True:
            op.add_column("turnos_horarios", sa.Column("creado_por", sa.Integer(), nullable=True), schema=schema)

        # Flexibilizar inicio_turno y fin_turno a nullable
        try:
            op.alter_column("turnos_horarios", "inicio_turno", nullable=True, schema=schema)
            op.alter_column("turnos_horarios", "fin_turno", nullable=True, schema=schema)
        except Exception:
            pass

        # Índices
        if _has_index("turnos_horarios", "ix_turnos_horarios_usuario_id", schema=schema) is not True:
            op.create_index("ix_turnos_horarios_usuario_id", "turnos_horarios", ["usuario_id"], schema=schema)
        if _has_index("turnos_horarios", "ix_turnos_horarios_area_id", schema=schema) is not True:
            op.create_index("ix_turnos_horarios_area_id", "turnos_horarios", ["area_id"], schema=schema)
        if _has_index("turnos_horarios", "ix_turnos_horarios_fecha_inicio", schema=schema) is not True:
            op.create_index("ix_turnos_horarios_fecha_inicio", "turnos_horarios", ["fecha_inicio"], schema=schema)
        if _has_index("turnos_horarios", "ix_turnos_horarios_fecha_fin", schema=schema) is not True:
            op.create_index("ix_turnos_horarios_fecha_fin", "turnos_horarios", ["fecha_fin"], schema=schema)
        if _has_index("turnos_horarios", "ix_turnos_horarios_creado_por", schema=schema) is not True:
            op.create_index("ix_turnos_horarios_creado_por", "turnos_horarios", ["creado_por"], schema=schema)

        # Backfill de datos existentes
        try:
            bind.execute(sa.text(f"UPDATE {prefix}turnos_horarios SET usuario_id = user_id WHERE usuario_id IS NULL AND user_id IS NOT NULL"))
        except Exception:
            pass

    # =========================================================================
    # 2. Enriquecer `notas_personales`
    # =========================================================================
    if _has_table("notas_personales", schema=schema) is True:
        if _has_column("notas_personales", "area_id", schema=schema) is not True:
            op.add_column("notas_personales", sa.Column("area_id", sa.String(length=64), nullable=True), schema=schema)
        if _has_column("notas_personales", "fecha", schema=schema) is not True:
            op.add_column("notas_personales", sa.Column("fecha", sa.DateTime(timezone=True), nullable=True), schema=schema)

        if _has_index("notas_personales", "ix_notas_personales_area_id", schema=schema) is not True:
            op.create_index("ix_notas_personales_area_id", "notas_personales", ["area_id"], schema=schema)

    # =========================================================================
    # 3. Enriquecer `notas_equipo`
    # =========================================================================
    if _has_table("notas_equipo", schema=schema) is True:
        if _has_column("notas_equipo", "area_id", schema=schema) is not True:
            op.add_column("notas_equipo", sa.Column("area_id", sa.String(length=64), nullable=True), schema=schema)
        if _has_column("notas_equipo", "categoria", schema=schema) is not True:
            op.add_column(
                "notas_equipo",
                sa.Column("categoria", sa.String(length=40), nullable=False, server_default="general"),
                schema=schema,
            )
        if _has_column("notas_equipo", "fecha", schema=schema) is not True:
            op.add_column("notas_equipo", sa.Column("fecha", sa.DateTime(timezone=True), nullable=True), schema=schema)
        if _has_column("notas_equipo", "insumo_id", schema=schema) is not True:
            op.add_column("notas_equipo", sa.Column("insumo_id", sa.String(length=64), nullable=True), schema=schema)
        if _has_column("notas_equipo", "receta_id", schema=schema) is not True:
            op.add_column("notas_equipo", sa.Column("receta_id", sa.Integer(), nullable=True), schema=schema)
        if _has_column("notas_equipo", "foto_url", schema=schema) is not True:
            op.add_column("notas_equipo", sa.Column("foto_url", sa.String(length=500), nullable=True), schema=schema)

        # Índices
        if _has_index("notas_equipo", "ix_notas_equipo_area_id", schema=schema) is not True:
            op.create_index("ix_notas_equipo_area_id", "notas_equipo", ["area_id"], schema=schema)
        if _has_index("notas_equipo", "ix_notas_equipo_categoria", schema=schema) is not True:
            op.create_index("ix_notas_equipo_categoria", "notas_equipo", ["categoria"], schema=schema)
        if _has_index("notas_equipo", "ix_notas_equipo_insumo_id", schema=schema) is not True:
            op.create_index("ix_notas_equipo_insumo_id", "notas_equipo", ["insumo_id"], schema=schema)
        if _has_index("notas_equipo", "ix_notas_equipo_receta_id", schema=schema) is not True:
            op.create_index("ix_notas_equipo_receta_id", "notas_equipo", ["receta_id"], schema=schema)

        # Backfill fecha = created_at
        try:
            bind.execute(sa.text(f"UPDATE {prefix}notas_equipo SET fecha = created_at WHERE fecha IS NULL AND created_at IS NOT NULL"))
        except Exception:
            pass

    # =========================================================================
    # 4. Tabla `nota_equipo_menciones`
    # =========================================================================
    if _has_table("nota_equipo_menciones", schema=schema) is not True:
        op.create_table(
            "nota_equipo_menciones",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "nota_id",
                sa.Integer(),
                sa.ForeignKey(notas_equipo_fk, ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("user_id", sa.Integer(), nullable=False),
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
            sa.UniqueConstraint("nota_id", "user_id", name="uq_nota_equipo_menciones_nota_user"),
            schema=schema,
        )

    if _has_table("nota_equipo_menciones", schema=schema) is True:
        if _has_index("nota_equipo_menciones", "ix_nota_equipo_menciones_nota_id", schema=schema) is not True:
            op.create_index("ix_nota_equipo_menciones_nota_id", "nota_equipo_menciones", ["nota_id"], schema=schema)
        if _has_index("nota_equipo_menciones", "ix_nota_equipo_menciones_user_id", schema=schema) is not True:
            op.create_index("ix_nota_equipo_menciones_user_id", "nota_equipo_menciones", ["user_id"], schema=schema)

    # =========================================================================
    # 5. Tabla `nota_equipo_lecturas`
    # =========================================================================
    if _has_table("nota_equipo_lecturas", schema=schema) is not True:
        op.create_table(
            "nota_equipo_lecturas",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "nota_id",
                sa.Integer(),
                sa.ForeignKey(notas_equipo_fk, ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column(
                "read_at",
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
            sa.UniqueConstraint("nota_id", "user_id", name="uq_nota_equipo_lecturas_nota_user"),
            schema=schema,
        )

    if _has_table("nota_equipo_lecturas", schema=schema) is True:
        if _has_index("nota_equipo_lecturas", "ix_nota_equipo_lecturas_nota_id", schema=schema) is not True:
            op.create_index("ix_nota_equipo_lecturas_nota_id", "nota_equipo_lecturas", ["nota_id"], schema=schema)
        if _has_index("nota_equipo_lecturas", "ix_nota_equipo_lecturas_user_id", schema=schema) is not True:
            op.create_index("ix_nota_equipo_lecturas_user_id", "nota_equipo_lecturas", ["user_id"], schema=schema)

    # =========================================================================
    # 6. Tabla `plantillas_rutinas`
    # =========================================================================
    if _has_table("plantillas_rutinas", schema=schema) is not True:
        op.create_table(
            "plantillas_rutinas",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("nombre", sa.String(length=160), nullable=False),
            sa.Column("descripcion", sa.Text(), nullable=True),
            sa.Column("area_id", sa.String(length=64), nullable=True),
            sa.Column(
                "tipo_rutina",
                sa.String(length=40),
                nullable=False,
                server_default="APERTURA",
            ),
            sa.Column(
                "frecuencia",
                sa.String(length=30),
                nullable=False,
                server_default="DIARIA",
            ),
            sa.Column(
                "items_json",
                json_type,
                nullable=False,
                server_default=json_empty_array,
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column("usuario_creador_id", sa.Integer(), nullable=True),
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
            schema=schema,
        )

    if _has_table("plantillas_rutinas", schema=schema) is True:
        if _has_index("plantillas_rutinas", "ix_plantillas_rutinas_nombre", schema=schema) is not True:
            op.create_index("ix_plantillas_rutinas_nombre", "plantillas_rutinas", ["nombre"], schema=schema)
        if _has_index("plantillas_rutinas", "ix_plantillas_rutinas_area_id", schema=schema) is not True:
            op.create_index("ix_plantillas_rutinas_area_id", "plantillas_rutinas", ["area_id"], schema=schema)
        if _has_index("plantillas_rutinas", "ix_plantillas_rutinas_tipo_rutina", schema=schema) is not True:
            op.create_index("ix_plantillas_rutinas_tipo_rutina", "plantillas_rutinas", ["tipo_rutina"], schema=schema)
        if _has_index("plantillas_rutinas", "ix_plantillas_rutinas_usuario_creador_id", schema=schema) is not True:
            op.create_index("ix_plantillas_rutinas_usuario_creador_id", "plantillas_rutinas", ["usuario_creador_id"], schema=schema)

    # =========================================================================
    # 7. Enriquecer `tareas`
    # =========================================================================
    if _has_table("tareas", schema=schema) is True:
        if _has_column("tareas", "creador_user_id", schema=schema) is not True:
            op.add_column("tareas", sa.Column("creador_user_id", sa.Integer(), nullable=True), schema=schema)
        if _has_column("tareas", "area_id", schema=schema) is not True:
            op.add_column("tareas", sa.Column("area_id", sa.String(length=64), nullable=True), schema=schema)
        if _has_column("tareas", "descripcion", schema=schema) is not True:
            op.add_column("tareas", sa.Column("descripcion", sa.Text(), nullable=True), schema=schema)
        if _has_column("tareas", "estado", schema=schema) is not True:
            op.add_column(
                "tareas",
                sa.Column("estado", sa.String(length=30), nullable=False, server_default="pendiente"),
                schema=schema,
            )
        if _has_column("tareas", "urgencia", schema=schema) is not True:
            op.add_column(
                "tareas",
                sa.Column("urgencia", sa.String(length=20), nullable=False, server_default="media"),
                schema=schema,
            )
        if _has_column("tareas", "fecha_limite", schema=schema) is not True:
            op.add_column("tareas", sa.Column("fecha_limite", sa.DateTime(timezone=True), nullable=True), schema=schema)
        if _has_column("tareas", "nota_incompleta", schema=schema) is not True:
            op.add_column("tareas", sa.Column("nota_incompleta", sa.Text(), nullable=True), schema=schema)
        if _has_column("tareas", "compra_id", schema=schema) is not True:
            op.add_column("tareas", sa.Column("compra_id", sa.String(length=64), nullable=True), schema=schema)
        if _has_column("tareas", "foto_evidencia_url", schema=schema) is not True:
            op.add_column("tareas", sa.Column("foto_evidencia_url", sa.String(length=500), nullable=True), schema=schema)
        if _has_column("tareas", "plantilla_id", schema=schema) is not True:
            op.add_column(
                "tareas",
                sa.Column(
                    "plantilla_id",
                    sa.Integer(),
                    sa.ForeignKey(plantillas_rutinas_fk, ondelete="SET NULL"),
                    nullable=True,
                ),
                schema=schema,
            )

        # Índices
        if _has_index("tareas", "ix_tareas_creador_user_id", schema=schema) is not True:
            op.create_index("ix_tareas_creador_user_id", "tareas", ["creador_user_id"], schema=schema)
        if _has_index("tareas", "ix_tareas_area_id", schema=schema) is not True:
            op.create_index("ix_tareas_area_id", "tareas", ["area_id"], schema=schema)
        if _has_index("tareas", "ix_tareas_estado", schema=schema) is not True:
            op.create_index("ix_tareas_estado", "tareas", ["estado"], schema=schema)
        if _has_index("tareas", "ix_tareas_urgencia", schema=schema) is not True:
            op.create_index("ix_tareas_urgencia", "tareas", ["urgencia"], schema=schema)
        if _has_index("tareas", "ix_tareas_compra_id", schema=schema) is not True:
            op.create_index("ix_tareas_compra_id", "tareas", ["compra_id"], schema=schema)
        if _has_index("tareas", "ix_tareas_plantilla_id", schema=schema) is not True:
            op.create_index("ix_tareas_plantilla_id", "tareas", ["plantilla_id"], schema=schema)

        # Sincronización de compatibilidad de estado y completada
        try:
            bind.execute(sa.text(f"UPDATE {prefix}tareas SET estado = 'completada' WHERE completada = true AND estado = 'pendiente'"))
        except Exception:
            pass


def _apply_tenant_downgrade_to_schema(schema: str | None) -> None:
    """Revierte simétricamente todas las tablas, columnas e índices creados en 0015."""
    # 1. Revertir `tareas`
    if _has_table("tareas", schema=schema) is True:
        for idx in [
            "ix_tareas_plantilla_id",
            "ix_tareas_compra_id",
            "ix_tareas_urgencia",
            "ix_tareas_estado",
            "ix_tareas_area_id",
            "ix_tareas_creador_user_id",
        ]:
            if _has_index("tareas", idx, schema=schema) is True:
                op.drop_index(idx, table_name="tareas", schema=schema)

        for col in [
            "plantilla_id",
            "foto_evidencia_url",
            "compra_id",
            "nota_incompleta",
            "fecha_limite",
            "urgencia",
            "estado",
            "descripcion",
            "area_id",
            "creador_user_id",
        ]:
            if _has_column("tareas", col, schema=schema) is True:
                op.drop_column("tareas", col, schema=schema)

    # 2. Dropear `plantillas_rutinas`
    if _has_table("plantillas_rutinas", schema=schema) is True:
        for idx in [
            "ix_plantillas_rutinas_usuario_creador_id",
            "ix_plantillas_rutinas_tipo_rutina",
            "ix_plantillas_rutinas_area_id",
            "ix_plantillas_rutinas_nombre",
        ]:
            if _has_index("plantillas_rutinas", idx, schema=schema) is True:
                op.drop_index(idx, table_name="plantillas_rutinas", schema=schema)
        op.drop_table("plantillas_rutinas", schema=schema)

    # 3. Dropear `nota_equipo_lecturas`
    if _has_table("nota_equipo_lecturas", schema=schema) is True:
        for idx in [
            "ix_nota_equipo_lecturas_user_id",
            "ix_nota_equipo_lecturas_nota_id",
        ]:
            if _has_index("nota_equipo_lecturas", idx, schema=schema) is True:
                op.drop_index(idx, table_name="nota_equipo_lecturas", schema=schema)
        op.drop_table("nota_equipo_lecturas", schema=schema)

    # 4. Dropear `nota_equipo_menciones`
    if _has_table("nota_equipo_menciones", schema=schema) is True:
        for idx in [
            "ix_nota_equipo_menciones_user_id",
            "ix_nota_equipo_menciones_nota_id",
        ]:
            if _has_index("nota_equipo_menciones", idx, schema=schema) is True:
                op.drop_index(idx, table_name="nota_equipo_menciones", schema=schema)
        op.drop_table("nota_equipo_menciones", schema=schema)

    # 5. Revertir `notas_equipo`
    if _has_table("notas_equipo", schema=schema) is True:
        for idx in [
            "ix_notas_equipo_receta_id",
            "ix_notas_equipo_insumo_id",
            "ix_notas_equipo_categoria",
            "ix_notas_equipo_area_id",
        ]:
            if _has_index("notas_equipo", idx, schema=schema) is True:
                op.drop_index(idx, table_name="notas_equipo", schema=schema)

        for col in [
            "foto_url",
            "receta_id",
            "insumo_id",
            "fecha",
            "categoria",
            "area_id",
        ]:
            if _has_column("notas_equipo", col, schema=schema) is True:
                op.drop_column("notas_equipo", col, schema=schema)

    # 6. Revertir `notas_personales`
    if _has_table("notas_personales", schema=schema) is True:
        if _has_index("notas_personales", "ix_notas_personales_area_id", schema=schema) is True:
            op.drop_index("ix_notas_personales_area_id", table_name="notas_personales", schema=schema)
        for col in ["fecha", "area_id"]:
            if _has_column("notas_personales", col, schema=schema) is True:
                op.drop_column("notas_personales", col, schema=schema)

    # 7. Revertir `turnos_horarios`
    if _has_table("turnos_horarios", schema=schema) is True:
        for idx in [
            "ix_turnos_horarios_creado_por",
            "ix_turnos_horarios_fecha_fin",
            "ix_turnos_horarios_fecha_inicio",
            "ix_turnos_horarios_area_id",
            "ix_turnos_horarios_usuario_id",
        ]:
            if _has_index("turnos_horarios", idx, schema=schema) is True:
                op.drop_index(idx, table_name="turnos_horarios", schema=schema)

        for col in [
            "creado_por",
            "color",
            "nota",
            "hora_fin",
            "hora_inicio",
            "fecha_fin",
            "fecha_inicio",
            "area_id",
            "usuario_id",
        ]:
            if _has_column("turnos_horarios", col, schema=schema) is True:
                op.drop_column("turnos_horarios", col, schema=schema)


def upgrade() -> None:
    """Aplica DDL de enriquecimiento de actividades (notas, tareas, horarios) en esquemas `tenant_*`."""
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
    """Revierte simétricamente todas las tablas, columnas e índices de actividades en esquemas `tenant_*`."""
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
