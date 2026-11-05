"""
0017_public_ai_benchmarks_and_tenant_feedback.py
Migración correlativa 0017 para el alcance `public` y persistencia en esquemas dinámicos `tenant_*`:
Implementa la Etapa 1 del Plan Maestro Oficial de Evals y Observabilidad LLM (Langfuse + DeepEval):
- Esquema `public`:
  * `ai_eval_benchmarks`: Historial agregado de corridas de evaluación sistemática con métricas Numeric(5, 4).
  * `ai_eval_case_results`: Detalle granular por caso de prueba del Golden Dataset vinculado a benchmark.
- Esquemas dinámicos `tenant_*`:
  * `ai_chat_feedbacks`: Retroalimentación humana RLHF vinculada a mensajes y trace_id de Langfuse.
"""
from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0017_public_ai_benchmarks_and_tenant_feedback"
down_revision = "0016_tenant_invoices_dte_and_supplier_aliases"
branch_labels = None
depends_on = None
migration_scope: Literal["public", "tenant"] = "public"


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


def _apply_public_upgrades() -> None:
    """Crea las tablas de benchmarks y case results en el esquema `public`."""
    is_pg = _is_postgresql()
    uuid_type = postgresql.UUID(as_uuid=True) if is_pg else sa.Uuid()
    uuid_default = sa.text("gen_random_uuid()") if is_pg else None

    # 1. Tabla `public.ai_eval_benchmarks`
    if _has_table("ai_eval_benchmarks", schema="public") is not True:
        op.create_table(
            "ai_eval_benchmarks",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
            sa.Column("suite_name", sa.String(120), nullable=False, index=True),
            sa.Column("model_name", sa.String(100), nullable=False, index=True),
            sa.Column("total_cases", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("passed_cases", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("avg_faithfulness", sa.Numeric(5, 4), nullable=False, server_default=sa.text("0.0000")),
            sa.Column("avg_relevance", sa.Numeric(5, 4), nullable=False, server_default=sa.text("0.0000")),
            sa.Column("avg_context_precision", sa.Numeric(5, 4), nullable=False, server_default=sa.text("0.0000")),
            sa.Column("avg_hallucination_rate", sa.Numeric(5, 4), nullable=False, server_default=sa.text("0.0000")),
            sa.Column("passed_thresholds", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
            schema="public",
        )

    # 2. Tabla `public.ai_eval_case_results`
    if _has_table("ai_eval_case_results", schema="public") is not True:
        op.create_table(
            "ai_eval_case_results",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
            sa.Column(
                "benchmark_id",
                uuid_type,
                sa.ForeignKey("public.ai_eval_benchmarks.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("case_id", sa.String(100), nullable=False, index=True),
            sa.Column("category", sa.String(100), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("expected_output", sa.Text(), nullable=False),
            sa.Column("actual_output", sa.Text(), nullable=False),
            sa.Column("retrieved_context", sa.Text(), nullable=True),
            sa.Column("faithfulness", sa.Numeric(5, 4), nullable=False, server_default=sa.text("0.0000")),
            sa.Column("relevance", sa.Numeric(5, 4), nullable=False, server_default=sa.text("0.0000")),
            sa.Column("hallucination_detected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("latency_ms", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            schema="public",
        )


def _apply_tenant_upgrade_to_schema(schema: str | None) -> None:
    """Crea la tabla `ai_chat_feedbacks` en un esquema dinámico `tenant_*`."""
    is_pg = _is_postgresql()
    uuid_type = postgresql.UUID(as_uuid=True) if is_pg else sa.Uuid()
    uuid_default = sa.text("gen_random_uuid()") if is_pg else None

    if _has_table("ai_chat_feedbacks", schema=schema) is not True:
        message_fk = (
            f"{schema}.ai_chat_messages.id"
            if schema and _has_table("ai_chat_messages", schema=schema)
            else ("ai_chat_messages.id" if _has_table("ai_chat_messages", schema=schema) else None)
        )
        msg_col = (
            sa.Column("message_id", uuid_type, sa.ForeignKey(message_fk, ondelete="SET NULL"), nullable=True, index=True)
            if message_fk
            else sa.Column("message_id", uuid_type, nullable=True, index=True)
        )

        op.create_table(
            "ai_chat_feedbacks",
            sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
            sa.Column("tenant_id", uuid_type, nullable=False, index=True),
            sa.Column("user_id", uuid_type, nullable=True, index=True),
            msg_col,
            sa.Column("trace_id", sa.String(64), nullable=False, index=True),
            sa.Column("feedback_type", sa.String(20), nullable=False),
            sa.Column("failure_category", sa.String(50), nullable=True),
            sa.Column("user_correction", sa.Text(), nullable=True),
            sa.Column("rating", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            schema=schema,
        )


def _apply_tenant_downgrade_to_schema(schema: str | None) -> None:
    """Revierte la tabla `ai_chat_feedbacks` en un esquema dinámico `tenant_*`."""
    if _has_table("ai_chat_feedbacks", schema=schema) is True:
        if _has_index("ai_chat_feedbacks", "ix_ai_chat_feedbacks_trace_id", schema=schema) is True:
            op.drop_index("ix_ai_chat_feedbacks_trace_id", table_name="ai_chat_feedbacks", schema=schema)
        if _has_index("ai_chat_feedbacks", "ix_ai_chat_feedbacks_message_id", schema=schema) is True:
            op.drop_index("ix_ai_chat_feedbacks_message_id", table_name="ai_chat_feedbacks", schema=schema)
        if _has_index("ai_chat_feedbacks", "ix_ai_chat_feedbacks_user_id", schema=schema) is True:
            op.drop_index("ix_ai_chat_feedbacks_user_id", table_name="ai_chat_feedbacks", schema=schema)
        if _has_index("ai_chat_feedbacks", "ix_ai_chat_feedbacks_tenant_id", schema=schema) is True:
            op.drop_index("ix_ai_chat_feedbacks_tenant_id", table_name="ai_chat_feedbacks", schema=schema)
        op.drop_table("ai_chat_feedbacks", schema=schema)


def _apply_public_downgrades() -> None:
    """Revierte simétricamente las tablas de evaluación en el esquema `public`."""
    if _has_table("ai_eval_case_results", schema="public") is True:
        if _has_index("ai_eval_case_results", "ix_ai_eval_case_results_case_id", schema="public") is True:
            op.drop_index("ix_ai_eval_case_results_case_id", table_name="ai_eval_case_results", schema="public")
        if _has_index("ai_eval_case_results", "ix_ai_eval_case_results_benchmark_id", schema="public") is True:
            op.drop_index("ix_ai_eval_case_results_benchmark_id", table_name="ai_eval_case_results", schema="public")
        op.drop_table("ai_eval_case_results", schema="public")

    if _has_table("ai_eval_benchmarks", schema="public") is True:
        if _has_index("ai_eval_benchmarks", "ix_ai_eval_benchmarks_created_at", schema="public") is True:
            op.drop_index("ix_ai_eval_benchmarks_created_at", table_name="ai_eval_benchmarks", schema="public")
        if _has_index("ai_eval_benchmarks", "ix_ai_eval_benchmarks_model_name", schema="public") is True:
            op.drop_index("ix_ai_eval_benchmarks_model_name", table_name="ai_eval_benchmarks", schema="public")
        if _has_index("ai_eval_benchmarks", "ix_ai_eval_benchmarks_suite_name", schema="public") is True:
            op.drop_index("ix_ai_eval_benchmarks_suite_name", table_name="ai_eval_benchmarks", schema="public")
        op.drop_table("ai_eval_benchmarks", schema="public")


def upgrade() -> None:
    """Aplica creación de benchmarks y case results en `public`, y feedback en esquemas `tenant_*`."""
    _apply_public_upgrades()

    current_schema = _get_current_schema()
    bind = op.get_bind()

    if current_schema and current_schema.startswith("tenant_"):
        target_schemas = [current_schema]
    else:
        target_schemas = _get_tenant_schemas(bind)

    for schema in target_schemas:
        _apply_tenant_upgrade_to_schema(schema)


def downgrade() -> None:
    """Revierte simétricamente feedback en esquemas `tenant_*` y benchmarks en `public`."""
    current_schema = _get_current_schema()
    bind = op.get_bind()

    if current_schema and current_schema.startswith("tenant_"):
        target_schemas = [current_schema]
    else:
        target_schemas = _get_tenant_schemas(bind)

    for schema in target_schemas:
        _apply_tenant_downgrade_to_schema(schema)

    _apply_public_downgrades()
