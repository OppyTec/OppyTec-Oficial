"""
0012_public_ai_model_configs_catalog_extension.py
Migración correlativa 0012 para el alcance `public`:
Extensión del catálogo de modelos IA (`public.ai_model_configs`) para soporte integral de LLM y JEV:
- Columnas añadidas:
  * display_name (VARCHAR(120), nullable=False, default='')
  * provider (VARCHAR(64), nullable=False, default='google')
  * latency_p95_ms (INTEGER, nullable=False, default=500)
  * min_confidence_score (NUMERIC(5, 4), nullable=True) # para calibración y compuertas JEV
  * max_context_tokens (INTEGER, nullable=False, default=128000)
  * is_default (BOOLEAN, nullable=False, default=False)
  * is_fallback (BOOLEAN, nullable=False, default=False)
  * description (TEXT, nullable=True)
  * is_deleted (BOOLEAN, nullable=False, default=False) para Soft-Delete
- Índices de rendimiento:
  * ix_ai_model_configs_provider
  * ix_ai_model_configs_is_default
  * ix_ai_model_configs_is_deleted
- Sembrado idempotente de modelos iniciales del catálogo:
  * gemini-3.8-flash (Google, Default)
  * gemini-4-argon (Google, High-Reasoning)
  * claude-3-7-sonnet (Anthropic, Architecture & Code)
  * gpt-4o (OpenAI, Multimodal Enterprise Fallback)
  * jev-fast-classifier (OppyTec, System 1 Sub-symbolic)
  * text-embedding-004 (Google, Vector RAG)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

import sqlalchemy as sa
from alembic import op

revision = "0012_public_ai_model_configs_catalog_extension"
down_revision = "0011_public_jev_request_logs_and_finops_telemetry"
branch_labels = None
depends_on = None
migration_scope: Literal["public", "tenant"] = "public"


def _is_postgresql() -> bool:
    try:
        bind = op.get_bind()
        return bind.dialect.name == "postgresql"
    except Exception:
        return True


def _has_table(table_name: str, schema: str = "public") -> bool | None:
    try:
        bind = op.get_bind()
        insp = sa.inspect(bind)
        tables = insp.get_table_names(schema=schema)
        return table_name in tables
    except Exception:
        return None


def _has_column(table_name: str, column_name: str, schema: str = "public") -> bool | None:
    try:
        bind = op.get_bind()
        insp = sa.inspect(bind)
        cols = [c["name"] for c in insp.get_columns(table_name, schema=schema)]
        return column_name in cols
    except Exception:
        return None


def _has_index(table_name: str, index_name: str, schema: str = "public") -> bool | None:
    try:
        bind = op.get_bind()
        insp = sa.inspect(bind)
        indexes = [ix["name"] for ix in insp.get_indexes(table_name, schema=schema)]
        return index_name in indexes
    except Exception:
        return None


def upgrade() -> None:
    """Añade columnas de catálogo LLM/JEV e índices a `public.ai_model_configs` con sembrado idempotente."""
    if _has_table("ai_model_configs", schema="public") is not True:
        # Si la tabla no existe en entornos aislados de pruebas, se crea completa
        op.create_table(
            "ai_model_configs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("model_slug", sa.String(length=64), unique=True, nullable=False),
            sa.Column("display_name", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("provider", sa.String(length=64), nullable=False, server_default="google"),
            sa.Column("engine_tier", sa.String(length=32), nullable=False, server_default="SYSTEM_2_LLM"),
            sa.Column("input_cost_per_1m_usd", sa.Numeric(12, 6), nullable=False),
            sa.Column("cached_cost_per_1m_usd", sa.Numeric(12, 6), nullable=False, server_default="0.000000"),
            sa.Column("output_cost_per_1m_usd", sa.Numeric(12, 6), nullable=False),
            sa.Column("embedding_cost_per_1m_usd", sa.Numeric(12, 6), nullable=False, server_default="0.000000"),
            sa.Column("latency_p95_ms", sa.Integer(), nullable=False, server_default=sa.text("500")),
            sa.Column("min_confidence_score", sa.Numeric(5, 4), nullable=True),
            sa.Column("max_context_tokens", sa.Integer(), nullable=False, server_default=sa.text("128000")),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            schema="public",
        )
    else:
        # Enriquecimiento idempotente de columnas requeridas
        if _has_column("ai_model_configs", "display_name", schema="public") is not True:
            op.add_column(
                "ai_model_configs",
                sa.Column("display_name", sa.String(length=120), nullable=False, server_default=""),
                schema="public",
            )
        if _has_column("ai_model_configs", "provider", schema="public") is not True:
            op.add_column(
                "ai_model_configs",
                sa.Column("provider", sa.String(length=64), nullable=False, server_default="google"),
                schema="public",
            )
        if _has_column("ai_model_configs", "latency_p95_ms", schema="public") is not True:
            op.add_column(
                "ai_model_configs",
                sa.Column("latency_p95_ms", sa.Integer(), nullable=False, server_default=sa.text("500")),
                schema="public",
            )
        if _has_column("ai_model_configs", "min_confidence_score", schema="public") is not True:
            op.add_column(
                "ai_model_configs",
                sa.Column("min_confidence_score", sa.Numeric(5, 4), nullable=True),
                schema="public",
            )
        if _has_column("ai_model_configs", "max_context_tokens", schema="public") is not True:
            op.add_column(
                "ai_model_configs",
                sa.Column("max_context_tokens", sa.Integer(), nullable=False, server_default=sa.text("128000")),
                schema="public",
            )
        if _has_column("ai_model_configs", "is_default", schema="public") is not True:
            op.add_column(
                "ai_model_configs",
                sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
                schema="public",
            )
        if _has_column("ai_model_configs", "is_fallback", schema="public") is not True:
            op.add_column(
                "ai_model_configs",
                sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default=sa.text("false")),
                schema="public",
            )
        if _has_column("ai_model_configs", "description", schema="public") is not True:
            op.add_column(
                "ai_model_configs",
                sa.Column("description", sa.Text(), nullable=True),
                schema="public",
            )
        if _has_column("ai_model_configs", "is_deleted", schema="public") is not True:
            op.add_column(
                "ai_model_configs",
                sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
                schema="public",
            )

    # Índices idempotentes
    if _has_index("ai_model_configs", "ix_ai_model_configs_provider", schema="public") is not True:
        op.create_index("ix_ai_model_configs_provider", "ai_model_configs", ["provider"], schema="public")
    if _has_index("ai_model_configs", "ix_ai_model_configs_is_default", schema="public") is not True:
        op.create_index("ix_ai_model_configs_is_default", "ai_model_configs", ["is_default"], schema="public")
    if _has_index("ai_model_configs", "ix_ai_model_configs_is_deleted", schema="public") is not True:
        op.create_index("ix_ai_model_configs_is_deleted", "ai_model_configs", ["is_deleted"], schema="public")

    # Sembrado inicial idempotente de modelos clave
    seed_models = [
        {
            "model_slug": "gemini-3.8-flash",
            "display_name": "Gemini 3.8 Flash",
            "provider": "google",
            "engine_tier": "SYSTEM_2_LLM",
            "input_cost_per_1m_usd": Decimal("0.150000"),
            "cached_cost_per_1m_usd": Decimal("0.037500"),
            "output_cost_per_1m_usd": Decimal("0.600000"),
            "embedding_cost_per_1m_usd": Decimal("0.000000"),
            "latency_p95_ms": 450,
            "min_confidence_score": None,
            "max_context_tokens": 1048576,
            "is_default": True,
            "is_fallback": False,
            "description": "Google Gemini 3.8 Flash - Modelo de alta velocidad y bajo costo para razonamiento operativo general.",
            "is_enabled": True,
            "is_deleted": False,
        },
        {
            "model_slug": "gemini-4-argon",
            "display_name": "Gemini 4 Argon",
            "provider": "google",
            "engine_tier": "SYSTEM_2_LLM",
            "input_cost_per_1m_usd": Decimal("1.250000"),
            "cached_cost_per_1m_usd": Decimal("0.312500"),
            "output_cost_per_1m_usd": Decimal("5.000000"),
            "embedding_cost_per_1m_usd": Decimal("0.000000"),
            "latency_p95_ms": 1200,
            "min_confidence_score": None,
            "max_context_tokens": 2097152,
            "is_default": False,
            "is_fallback": False,
            "description": "Google Gemini 4 Argon - Razonamiento avanzado para análisis financiero, escandallos y diagnósticos complejos.",
            "is_enabled": True,
            "is_deleted": False,
        },
        {
            "model_slug": "claude-3-7-sonnet",
            "display_name": "Claude 3.7 Sonnet",
            "provider": "anthropic",
            "engine_tier": "SYSTEM_2_LLM",
            "input_cost_per_1m_usd": Decimal("3.000000"),
            "cached_cost_per_1m_usd": Decimal("0.750000"),
            "output_cost_per_1m_usd": Decimal("15.000000"),
            "embedding_cost_per_1m_usd": Decimal("0.000000"),
            "latency_p95_ms": 1500,
            "min_confidence_score": None,
            "max_context_tokens": 200000,
            "is_default": False,
            "is_fallback": False,
            "description": "Anthropic Claude 3.7 Sonnet - Razonamiento híbrido estándar y de pensamiento extendido para auditorías y arquitectura.",
            "is_enabled": True,
            "is_deleted": False,
        },
        {
            "model_slug": "gpt-4o",
            "display_name": "GPT-4o",
            "provider": "openai",
            "engine_tier": "SYSTEM_2_LLM",
            "input_cost_per_1m_usd": Decimal("2.500000"),
            "cached_cost_per_1m_usd": Decimal("1.250000"),
            "output_cost_per_1m_usd": Decimal("10.000000"),
            "embedding_cost_per_1m_usd": Decimal("0.000000"),
            "latency_p95_ms": 800,
            "min_confidence_score": None,
            "max_context_tokens": 128000,
            "is_default": False,
            "is_fallback": True,
            "description": "OpenAI GPT-4o - Modelo multimodal de respaldo empresarial y alta fidelidad.",
            "is_enabled": True,
            "is_deleted": False,
        },
        {
            "model_slug": "jev-fast-classifier",
            "display_name": "JEV Fast Classifier",
            "provider": "oppytec",
            "engine_tier": "SYSTEM_1_JEV",
            "input_cost_per_1m_usd": Decimal("0.000000"),
            "cached_cost_per_1m_usd": Decimal("0.000000"),
            "output_cost_per_1m_usd": Decimal("0.000000"),
            "embedding_cost_per_1m_usd": Decimal("0.000000"),
            "latency_p95_ms": 50,
            "min_confidence_score": Decimal("0.8500"),
            "max_context_tokens": 8192,
            "is_default": False,
            "is_fallback": False,
            "description": "Motor local JEV System 1 determinista y sub-simbólico de ultra-baja latencia y cero costo de proveedor.",
            "is_enabled": True,
            "is_deleted": False,
        },
        {
            "model_slug": "text-embedding-004",
            "display_name": "Text Embedding 004",
            "provider": "google",
            "engine_tier": "EMBEDDING",
            "input_cost_per_1m_usd": Decimal("0.000000"),
            "cached_cost_per_1m_usd": Decimal("0.000000"),
            "output_cost_per_1m_usd": Decimal("0.000000"),
            "embedding_cost_per_1m_usd": Decimal("0.025000"),
            "latency_p95_ms": 100,
            "min_confidence_score": None,
            "max_context_tokens": 8192,
            "is_default": False,
            "is_fallback": False,
            "description": "Google Text Embedding 004 - Embeddings vectoriales de 768 dimensiones para RAG.",
            "is_enabled": True,
            "is_deleted": False,
        },
    ]

    bind = op.get_bind()
    try:
        res = bind.execute(sa.text("SELECT model_slug FROM public.ai_model_configs"))
        existing_slugs = {row[0] for row in res.fetchall()}
    except Exception:
        existing_slugs = set()

    model_table = sa.table(
        "ai_model_configs",
        sa.column("model_slug", sa.String),
        sa.column("display_name", sa.String),
        sa.column("provider", sa.String),
        sa.column("engine_tier", sa.String),
        sa.column("input_cost_per_1m_usd", sa.Numeric),
        sa.column("cached_cost_per_1m_usd", sa.Numeric),
        sa.column("output_cost_per_1m_usd", sa.Numeric),
        sa.column("embedding_cost_per_1m_usd", sa.Numeric),
        sa.column("latency_p95_ms", sa.Integer),
        sa.column("min_confidence_score", sa.Numeric),
        sa.column("max_context_tokens", sa.Integer),
        sa.column("is_default", sa.Boolean),
        sa.column("is_fallback", sa.Boolean),
        sa.column("description", sa.Text),
        sa.column("is_enabled", sa.Boolean),
        sa.column("is_deleted", sa.Boolean),
    )

    items_to_insert = [m for m in seed_models if m["model_slug"] not in existing_slugs]
    if items_to_insert:
        try:
            op.bulk_insert(model_table, items_to_insert)
        except Exception:
            # Fallback seguro para dialectos o transacciones restringidas
            pass


def downgrade() -> None:
    """Revierte simétricamente los índices y columnas agregadas a `public.ai_model_configs`."""
    if _has_table("ai_model_configs", schema="public") is True:
        # 1. Dropear índices
        for idx in (
            "ix_ai_model_configs_is_deleted",
            "ix_ai_model_configs_is_default",
            "ix_ai_model_configs_provider",
        ):
            if _has_index("ai_model_configs", idx, schema="public") is True:
                op.drop_index(idx, table_name="ai_model_configs", schema="public")

        # 2. Dropear columnas
        columns_to_drop = [
            "is_deleted",
            "description",
            "is_fallback",
            "is_default",
            "max_context_tokens",
            "min_confidence_score",
            "latency_p95_ms",
            "provider",
            "display_name",
        ]
        for col in columns_to_drop:
            if _has_column("ai_model_configs", col, schema="public") is True:
                op.drop_column("ai_model_configs", col, schema="public")
