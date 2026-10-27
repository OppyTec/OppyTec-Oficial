"""
0010_tenant_oppyfy_custom_rbac_and_credit_wallets.py
Migración correlativa 0010 para el alcance `tenant` y soporte complementario en `public`:
Implementa la persistencia de la Fase 1 del PLAN_MAESTRO_OPPYFY_AI.md:
- Tablas operativas en esquemas `tenant_*`:
  * `oppyfy_domains`: Árbol de dominios cognitivos editable por el local.
  * `oppyfy_subdomains`: Subdominios vinculados a herramientas operativas y documentos.
  * `oppyfy_permission_grants`: Permisos granulares con triple control de caducidad.
  * `oppyfy_worker_credit_wallets`: Billetera y techos de créditos asignados por trabajador.
  * `oppyfy_prompt_audit_log`: Bitácora inmutable Append-Only de prompts enviados a OppyFy.
  * `oppyfy_rbac_audit_log`: Auditoría de modificaciones y asignaciones RBAC en OppyFy.
- Tablas y columnas complementarias en esquema `public`:
  * `public.ai_credit_packs`: Paquetes de créditos IA independientes para compra Add-On.
  * `public.ai_model_configs`: Columnas `cached_cost_per_1m_usd` y `embedding_cost_per_1m_usd`.
  * `public.spec_chunks`: Columna `token_count`.
"""
from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_tenant_oppyfy_custom_rbac_and_credit_wallets"
down_revision = "0009_tenant_procurement_purchases_and_suppliers"
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
    """Descubre todos los esquemas tenant_* registrados en PostgreSQL."""
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
    """Aplica tablas y columnas complementarias de IA en el esquema `public`."""
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    # 1. Tabla `public.ai_credit_packs`
    if _has_table("ai_credit_packs", schema="public") is not True:
        op.create_table(
            "ai_credit_packs",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("pack_name", sa.String(length=120), nullable=False),
            sa.Column("credits_amount", sa.Numeric(14, 2), nullable=False),
            sa.Column("price_clp", sa.Numeric(14, 2), nullable=False),
            sa.Column("price_usd", sa.Numeric(14, 2), nullable=False),
            sa.Column("is_popular", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            schema="public",
        )

    if _has_table("ai_credit_packs", schema="public") is True:
        if _has_index("ai_credit_packs", "ix_ai_credit_packs_is_active", schema="public") is not True:
            op.create_index("ix_ai_credit_packs_is_active", "ai_credit_packs", ["is_active"], schema="public")
        if _has_index("ai_credit_packs", "ix_ai_credit_packs_sort_order", schema="public") is not True:
            op.create_index("ix_ai_credit_packs_sort_order", "ai_credit_packs", ["sort_order"], schema="public")

    # 2. Extensión de `public.ai_model_configs`
    if _has_table("ai_model_configs", schema="public") is True:
        if _has_column("ai_model_configs", "cached_cost_per_1m_usd", schema="public") is not True:
            op.add_column(
                "ai_model_configs",
                sa.Column("cached_cost_per_1m_usd", sa.Numeric(12, 6), nullable=False, server_default=sa.text("0.000000")),
                schema="public",
            )
        if _has_column("ai_model_configs", "embedding_cost_per_1m_usd", schema="public") is not True:
            op.add_column(
                "ai_model_configs",
                sa.Column("embedding_cost_per_1m_usd", sa.Numeric(12, 6), nullable=False, server_default=sa.text("0.000000")),
                schema="public",
            )

    # 3. Extensión de `public.spec_chunks`
    if _has_table("spec_chunks", schema="public") is True:
        if _has_column("spec_chunks", "token_count", schema="public") is not True:
            op.add_column(
                "spec_chunks",
                sa.Column("token_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
                schema="public",
            )


def _apply_public_downgrades() -> None:
    """Revierte simétricamente los cambios en `public`."""
    if _has_table("ai_credit_packs", schema="public") is True:
        if _has_index("ai_credit_packs", "ix_ai_credit_packs_sort_order", schema="public") is True:
            op.drop_index("ix_ai_credit_packs_sort_order", table_name="ai_credit_packs", schema="public")
        if _has_index("ai_credit_packs", "ix_ai_credit_packs_is_active", schema="public") is True:
            op.drop_index("ix_ai_credit_packs_is_active", table_name="ai_credit_packs", schema="public")
        op.drop_table("ai_credit_packs", schema="public")

    if _has_table("ai_model_configs", schema="public") is True:
        if _has_column("ai_model_configs", "embedding_cost_per_1m_usd", schema="public") is True:
            op.drop_column("ai_model_configs", "embedding_cost_per_1m_usd", schema="public")
        if _has_column("ai_model_configs", "cached_cost_per_1m_usd", schema="public") is True:
            op.drop_column("ai_model_configs", "cached_cost_per_1m_usd", schema="public")

    if _has_table("spec_chunks", schema="public") is True:
        if _has_column("spec_chunks", "token_count", schema="public") is True:
            op.drop_column("spec_chunks", "token_count", schema="public")


def _apply_tenant_upgrade_to_schema(schema: str) -> None:
    """Aplica DDL de OppyFy RBAC y Billeteras en el esquema tenant especificado."""
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    bind = op.get_bind()

    # ---------------------------------------------------------
    # 1. Tabla `oppyfy_domains`
    # ---------------------------------------------------------
    if _has_table("oppyfy_domains", schema=schema) is not True:
        op.create_table(
            "oppyfy_domains",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("domain_key", sa.String(length=100), nullable=False),
            sa.Column("name_es", sa.String(length=150), nullable=False),
            sa.Column("name_en", sa.String(length=150), nullable=False, server_default=""),
            sa.Column("icon", sa.String(length=50), nullable=False, server_default="BrainCircuit"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            schema=schema,
        )
    else:
        # Enriquecimiento idempotente si la tabla ya existía
        if _has_column("oppyfy_domains", "domain_key", schema=schema) is not True:
            op.add_column("oppyfy_domains", sa.Column("domain_key", sa.String(length=100), nullable=True), schema=schema)
            if _has_column("oppyfy_domains", "slug", schema=schema) is True:
                bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_domains SET domain_key = slug WHERE domain_key IS NULL'))
            bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_domains SET domain_key = \'domain_\' || id WHERE domain_key IS NULL'))
            op.alter_column("oppyfy_domains", "domain_key", nullable=False, schema=schema)

        if _has_column("oppyfy_domains", "name_es", schema=schema) is not True:
            op.add_column("oppyfy_domains", sa.Column("name_es", sa.String(length=150), nullable=True), schema=schema)
            if _has_column("oppyfy_domains", "name", schema=schema) is True:
                bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_domains SET name_es = name WHERE name_es IS NULL'))
            bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_domains SET name_es = \'Dominio \' || id WHERE name_es IS NULL'))
            op.alter_column("oppyfy_domains", "name_es", nullable=False, schema=schema)

        if _has_column("oppyfy_domains", "name_en", schema=schema) is not True:
            op.add_column("oppyfy_domains", sa.Column("name_en", sa.String(length=150), nullable=False, server_default=""), schema=schema)
            if _has_column("oppyfy_domains", "name", schema=schema) is True:
                bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_domains SET name_en = name WHERE name_en = \'\' OR name_en IS NULL'))

        if _has_column("oppyfy_domains", "icon", schema=schema) is not True:
            op.add_column("oppyfy_domains", sa.Column("icon", sa.String(length=50), nullable=False, server_default="BrainCircuit"), schema=schema)

        if _has_column("oppyfy_domains", "is_active", schema=schema) is not True:
            op.add_column("oppyfy_domains", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")), schema=schema)
            if _has_column("oppyfy_domains", "is_enabled", schema=schema) is True:
                bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_domains SET is_active = is_enabled WHERE is_active IS NULL'))

        if _has_column("oppyfy_domains", "sort_order", schema=schema) is not True:
            op.add_column("oppyfy_domains", sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")), schema=schema)

    if _has_table("oppyfy_domains", schema=schema) is True:
        if _has_index("oppyfy_domains", "ix_oppyfy_domains_domain_key", schema=schema) is not True:
            op.create_index("ix_oppyfy_domains_domain_key", "oppyfy_domains", ["domain_key"], unique=True, schema=schema)
        if _has_index("oppyfy_domains", "ix_oppyfy_domains_is_active", schema=schema) is not True:
            op.create_index("ix_oppyfy_domains_is_active", "oppyfy_domains", ["is_active"], schema=schema)
        if _has_index("oppyfy_domains", "ix_oppyfy_domains_sort_order", schema=schema) is not True:
            op.create_index("ix_oppyfy_domains_sort_order", "oppyfy_domains", ["sort_order"], schema=schema)

    # ---------------------------------------------------------
    # 2. Tabla `oppyfy_subdomains`
    # ---------------------------------------------------------
    domain_fk_target = f"{schema}.oppyfy_domains.id" if schema else "oppyfy_domains.id"
    if _has_table("oppyfy_subdomains", schema=schema) is not True:
        op.create_table(
            "oppyfy_subdomains",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("domain_id", sa.BigInteger(), sa.ForeignKey(domain_fk_target, ondelete="CASCADE"), nullable=False),
            sa.Column("subdomain_key", sa.String(length=100), nullable=False),
            sa.Column("name_es", sa.String(length=150), nullable=False),
            sa.Column("name_en", sa.String(length=150), nullable=False, server_default=""),
            sa.Column("module_slug", sa.String(length=100), nullable=False, server_default="oppy_ai"),
            sa.Column("allowed_tool_functions", json_type, nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("can_view_costs_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            schema=schema,
        )
    else:
        # Enriquecimiento idempotente si la tabla ya existía
        if _has_column("oppyfy_subdomains", "subdomain_key", schema=schema) is not True:
            op.add_column("oppyfy_subdomains", sa.Column("subdomain_key", sa.String(length=100), nullable=True), schema=schema)
            if _has_column("oppyfy_subdomains", "slug", schema=schema) is True:
                bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_subdomains SET subdomain_key = slug WHERE subdomain_key IS NULL'))
            bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_subdomains SET subdomain_key = \'sub_\' || id WHERE subdomain_key IS NULL'))
            op.alter_column("oppyfy_subdomains", "subdomain_key", nullable=False, schema=schema)

        if _has_column("oppyfy_subdomains", "name_es", schema=schema) is not True:
            op.add_column("oppyfy_subdomains", sa.Column("name_es", sa.String(length=150), nullable=True), schema=schema)
            if _has_column("oppyfy_subdomains", "name", schema=schema) is True:
                bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_subdomains SET name_es = name WHERE name_es IS NULL'))
            bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_subdomains SET name_es = \'Subdominio \' || id WHERE name_es IS NULL'))
            op.alter_column("oppyfy_subdomains", "name_es", nullable=False, schema=schema)

        if _has_column("oppyfy_subdomains", "name_en", schema=schema) is not True:
            op.add_column("oppyfy_subdomains", sa.Column("name_en", sa.String(length=150), nullable=False, server_default=""), schema=schema)
            if _has_column("oppyfy_subdomains", "name", schema=schema) is True:
                bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_subdomains SET name_en = name WHERE name_en = \'\' OR name_en IS NULL'))

        if _has_column("oppyfy_subdomains", "module_slug", schema=schema) is not True:
            op.add_column("oppyfy_subdomains", sa.Column("module_slug", sa.String(length=100), nullable=False, server_default="oppy_ai"), schema=schema)

        if _has_column("oppyfy_subdomains", "allowed_tool_functions", schema=schema) is not True:
            op.add_column("oppyfy_subdomains", sa.Column("allowed_tool_functions", json_type, nullable=False, server_default=sa.text("'[]'::jsonb")), schema=schema)
            if _has_column("oppyfy_subdomains", "bound_tool_codes", schema=schema) is True:
                bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_subdomains SET allowed_tool_functions = bound_tool_codes WHERE allowed_tool_functions IS NULL'))

        if _has_column("oppyfy_subdomains", "can_view_costs_default", schema=schema) is not True:
            op.add_column("oppyfy_subdomains", sa.Column("can_view_costs_default", sa.Boolean(), nullable=False, server_default=sa.text("false")), schema=schema)

        if _has_column("oppyfy_subdomains", "sort_order", schema=schema) is not True:
            op.add_column("oppyfy_subdomains", sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")), schema=schema)

        if _has_column("oppyfy_subdomains", "is_active", schema=schema) is not True:
            op.add_column("oppyfy_subdomains", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")), schema=schema)

    if _has_table("oppyfy_subdomains", schema=schema) is True:
        if _has_index("oppyfy_subdomains", "ix_oppyfy_subdomains_subdomain_key", schema=schema) is not True:
            op.create_index("ix_oppyfy_subdomains_subdomain_key", "oppyfy_subdomains", ["subdomain_key"], unique=True, schema=schema)
        if _has_index("oppyfy_subdomains", "ix_oppyfy_subdomains_domain_id", schema=schema) is not True:
            op.create_index("ix_oppyfy_subdomains_domain_id", "oppyfy_subdomains", ["domain_id"], schema=schema)
        if _has_index("oppyfy_subdomains", "ix_oppyfy_subdomains_module_slug", schema=schema) is not True:
            op.create_index("ix_oppyfy_subdomains_module_slug", "oppyfy_subdomains", ["module_slug"], schema=schema)

    # ---------------------------------------------------------
    # 3. Tabla `oppyfy_permission_grants`
    # ---------------------------------------------------------
    subdomain_fk_target = f"{schema}.oppyfy_subdomains.id" if schema else "oppyfy_subdomains.id"
    if _has_table("oppyfy_permission_grants", schema=schema) is not True:
        op.create_table(
            "oppyfy_permission_grants",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("subdomain_id", sa.BigInteger(), sa.ForeignKey(subdomain_fk_target, ondelete="CASCADE"), nullable=False),
            sa.Column("role_id", sa.Integer(), nullable=True),
            sa.Column("effect", sa.String(length=16), nullable=False, server_default="ALLOW"),
            sa.Column("can_query", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("can_view_costs", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("max_prompts", sa.Integer(), nullable=True),
            sa.Column("prompts_used", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("temp_credit_ceiling", sa.Numeric(12, 2), nullable=True),
            sa.Column("temp_credits_used", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            schema=schema,
        )
    else:
        if _has_column("oppyfy_permission_grants", "can_query", schema=schema) is not True:
            op.add_column("oppyfy_permission_grants", sa.Column("can_query", sa.Boolean(), nullable=False, server_default=sa.text("true")), schema=schema)
        if _has_column("oppyfy_permission_grants", "prompts_used", schema=schema) is not True:
            op.add_column("oppyfy_permission_grants", sa.Column("prompts_used", sa.Integer(), nullable=False, server_default=sa.text("0")), schema=schema)
            if _has_column("oppyfy_permission_grants", "used_prompts", schema=schema) is True:
                bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_permission_grants SET prompts_used = used_prompts WHERE prompts_used = 0'))
        if _has_column("oppyfy_permission_grants", "temp_credits_used", schema=schema) is not True:
            op.add_column("oppyfy_permission_grants", sa.Column("temp_credits_used", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")), schema=schema)

    if _has_table("oppyfy_permission_grants", schema=schema) is True:
        if _has_index("oppyfy_permission_grants", "ix_oppyfy_permission_grants_user_id", schema=schema) is not True:
            op.create_index("ix_oppyfy_permission_grants_user_id", "oppyfy_permission_grants", ["user_id"], schema=schema)
        if _has_index("oppyfy_permission_grants", "ix_oppyfy_permission_grants_subdomain_id", schema=schema) is not True:
            op.create_index("ix_oppyfy_permission_grants_subdomain_id", "oppyfy_permission_grants", ["subdomain_id"], schema=schema)

    # ---------------------------------------------------------
    # 4. Tabla `oppyfy_worker_credit_wallets`
    # ---------------------------------------------------------
    if _has_table("oppyfy_worker_credit_wallets", schema=schema) is not True:
        op.create_table(
            "oppyfy_worker_credit_wallets",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("is_oppyfy_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("assigned_credit_ceiling", sa.Numeric(12, 2), nullable=True, server_default=sa.text("0.00")),
            sa.Column("credits_spent_total", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")),
            sa.Column("balance_override", sa.Numeric(12, 2), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            schema=schema,
        )
    else:
        if _has_column("oppyfy_worker_credit_wallets", "assigned_credit_ceiling", schema=schema) is not True:
            op.add_column("oppyfy_worker_credit_wallets", sa.Column("assigned_credit_ceiling", sa.Numeric(12, 2), nullable=True, server_default=sa.text("0.00")), schema=schema)
            if _has_column("oppyfy_worker_credit_wallets", "allocated_credits", schema=schema) is True:
                bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_worker_credit_wallets SET assigned_credit_ceiling = allocated_credits WHERE assigned_credit_ceiling IS NULL OR assigned_credit_ceiling = 0.00'))
        if _has_column("oppyfy_worker_credit_wallets", "credits_spent_total", schema=schema) is not True:
            op.add_column("oppyfy_worker_credit_wallets", sa.Column("credits_spent_total", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")), schema=schema)
            if _has_column("oppyfy_worker_credit_wallets", "consumed_credits", schema=schema) is True:
                bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_worker_credit_wallets SET credits_spent_total = consumed_credits WHERE credits_spent_total = 0.00'))
        if _has_column("oppyfy_worker_credit_wallets", "balance_override", schema=schema) is not True:
            op.add_column("oppyfy_worker_credit_wallets", sa.Column("balance_override", sa.Numeric(12, 2), nullable=True), schema=schema)

    if _has_table("oppyfy_worker_credit_wallets", schema=schema) is True:
        if _has_index("oppyfy_worker_credit_wallets", "ix_oppyfy_worker_credit_wallets_user_id", schema=schema) is not True:
            op.create_index("ix_oppyfy_worker_credit_wallets_user_id", "oppyfy_worker_credit_wallets", ["user_id"], unique=True, schema=schema)

    # ---------------------------------------------------------
    # 5. Tabla `oppyfy_prompt_audit_log`
    # ---------------------------------------------------------
    if _has_table("oppyfy_prompt_audit_log", schema=schema) is not True:
        op.create_table(
            "oppyfy_prompt_audit_log",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("prompt_text", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="ALLOWED"),
            sa.Column("resolved_domain", sa.String(length=100), nullable=True),
            sa.Column("resolved_tools", json_type, nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("tokens_spent", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("credits_deducted", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            schema=schema,
        )
    else:
        if _has_column("oppyfy_prompt_audit_log", "status", schema=schema) is not True:
            op.add_column("oppyfy_prompt_audit_log", sa.Column("status", sa.String(length=50), nullable=False, server_default="ALLOWED"), schema=schema)
            if _has_column("oppyfy_prompt_audit_log", "decision_status", schema=schema) is True:
                bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_prompt_audit_log SET status = decision_status WHERE status IS NULL OR status = \'ALLOWED\''))
        if _has_column("oppyfy_prompt_audit_log", "resolved_domain", schema=schema) is not True:
            op.add_column("oppyfy_prompt_audit_log", sa.Column("resolved_domain", sa.String(length=100), nullable=True), schema=schema)
            if _has_column("oppyfy_prompt_audit_log", "subdomain_slug", schema=schema) is True:
                bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_prompt_audit_log SET resolved_domain = subdomain_slug WHERE resolved_domain IS NULL'))
        if _has_column("oppyfy_prompt_audit_log", "resolved_tools", schema=schema) is not True:
            op.add_column("oppyfy_prompt_audit_log", sa.Column("resolved_tools", json_type, nullable=False, server_default=sa.text("'[]'::jsonb")), schema=schema)
        if _has_column("oppyfy_prompt_audit_log", "tokens_spent", schema=schema) is not True:
            op.add_column("oppyfy_prompt_audit_log", sa.Column("tokens_spent", sa.Integer(), nullable=False, server_default=sa.text("0")), schema=schema)
        if _has_column("oppyfy_prompt_audit_log", "credits_deducted", schema=schema) is not True:
            op.add_column("oppyfy_prompt_audit_log", sa.Column("credits_deducted", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")), schema=schema)
            if _has_column("oppyfy_prompt_audit_log", "credits_consumed", schema=schema) is True:
                bind.execute(sa.text(f'UPDATE "{schema}".oppyfy_prompt_audit_log SET credits_deducted = credits_consumed WHERE credits_deducted = 0.00'))

    if _has_table("oppyfy_prompt_audit_log", schema=schema) is True:
        if _has_index("oppyfy_prompt_audit_log", "ix_oppyfy_prompt_audit_log_user_id", schema=schema) is not True:
            op.create_index("ix_oppyfy_prompt_audit_log_user_id", "oppyfy_prompt_audit_log", ["user_id"], schema=schema)
        if _has_index("oppyfy_prompt_audit_log", "ix_oppyfy_prompt_audit_log_status", schema=schema) is not True:
            op.create_index("ix_oppyfy_prompt_audit_log_status", "oppyfy_prompt_audit_log", ["status"], schema=schema)
        if _has_index("oppyfy_prompt_audit_log", "ix_oppyfy_prompt_audit_log_created_at", schema=schema) is not True:
            op.create_index("ix_oppyfy_prompt_audit_log_created_at", "oppyfy_prompt_audit_log", ["created_at"], schema=schema)

    # ---------------------------------------------------------
    # 6. Tabla `oppyfy_rbac_audit_log`
    # ---------------------------------------------------------
    if _has_table("oppyfy_rbac_audit_log", schema=schema) is not True:
        op.create_table(
            "oppyfy_rbac_audit_log",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("actor_user_id", sa.Integer(), nullable=False),
            sa.Column("target_user_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column("details", json_type, nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            schema=schema,
        )

    if _has_table("oppyfy_rbac_audit_log", schema=schema) is True:
        if _has_index("oppyfy_rbac_audit_log", "ix_oppyfy_rbac_audit_log_actor_user_id", schema=schema) is not True:
            op.create_index("ix_oppyfy_rbac_audit_log_actor_user_id", "oppyfy_rbac_audit_log", ["actor_user_id"], schema=schema)
        if _has_index("oppyfy_rbac_audit_log", "ix_oppyfy_rbac_audit_log_target_user_id", schema=schema) is not True:
            op.create_index("ix_oppyfy_rbac_audit_log_target_user_id", "oppyfy_rbac_audit_log", ["target_user_id"], schema=schema)
        if _has_index("oppyfy_rbac_audit_log", "ix_oppyfy_rbac_audit_log_action", schema=schema) is not True:
            op.create_index("ix_oppyfy_rbac_audit_log_action", "oppyfy_rbac_audit_log", ["action"], schema=schema)
        if _has_index("oppyfy_rbac_audit_log", "ix_oppyfy_rbac_audit_log_created_at", schema=schema) is not True:
            op.create_index("ix_oppyfy_rbac_audit_log_created_at", "oppyfy_rbac_audit_log", ["created_at"], schema=schema)


def _apply_tenant_downgrade_to_schema(schema: str) -> None:
    """Revierte simétricamente todas las tablas e índices en el esquema tenant especificado."""
    # 6. `oppyfy_rbac_audit_log`
    if _has_table("oppyfy_rbac_audit_log", schema=schema) is True:
        if _has_index("oppyfy_rbac_audit_log", "ix_oppyfy_rbac_audit_log_created_at", schema=schema) is True:
            op.drop_index("ix_oppyfy_rbac_audit_log_created_at", table_name="oppyfy_rbac_audit_log", schema=schema)
        if _has_index("oppyfy_rbac_audit_log", "ix_oppyfy_rbac_audit_log_action", schema=schema) is True:
            op.drop_index("ix_oppyfy_rbac_audit_log_action", table_name="oppyfy_rbac_audit_log", schema=schema)
        if _has_index("oppyfy_rbac_audit_log", "ix_oppyfy_rbac_audit_log_target_user_id", schema=schema) is True:
            op.drop_index("ix_oppyfy_rbac_audit_log_target_user_id", table_name="oppyfy_rbac_audit_log", schema=schema)
        if _has_index("oppyfy_rbac_audit_log", "ix_oppyfy_rbac_audit_log_actor_user_id", schema=schema) is True:
            op.drop_index("ix_oppyfy_rbac_audit_log_actor_user_id", table_name="oppyfy_rbac_audit_log", schema=schema)
        op.drop_table("oppyfy_rbac_audit_log", schema=schema)

    # 5. `oppyfy_prompt_audit_log`
    if _has_table("oppyfy_prompt_audit_log", schema=schema) is True:
        if _has_index("oppyfy_prompt_audit_log", "ix_oppyfy_prompt_audit_log_created_at", schema=schema) is True:
            op.drop_index("ix_oppyfy_prompt_audit_log_created_at", table_name="oppyfy_prompt_audit_log", schema=schema)
        if _has_index("oppyfy_prompt_audit_log", "ix_oppyfy_prompt_audit_log_status", schema=schema) is True:
            op.drop_index("ix_oppyfy_prompt_audit_log_status", table_name="oppyfy_prompt_audit_log", schema=schema)
        if _has_index("oppyfy_prompt_audit_log", "ix_oppyfy_prompt_audit_log_user_id", schema=schema) is True:
            op.drop_index("ix_oppyfy_prompt_audit_log_user_id", table_name="oppyfy_prompt_audit_log", schema=schema)
        op.drop_table("oppyfy_prompt_audit_log", schema=schema)

    # 4. `oppyfy_worker_credit_wallets`
    if _has_table("oppyfy_worker_credit_wallets", schema=schema) is True:
        if _has_index("oppyfy_worker_credit_wallets", "ix_oppyfy_worker_credit_wallets_user_id", schema=schema) is True:
            op.drop_index("ix_oppyfy_worker_credit_wallets_user_id", table_name="oppyfy_worker_credit_wallets", schema=schema)
        op.drop_table("oppyfy_worker_credit_wallets", schema=schema)

    # 3. `oppyfy_permission_grants`
    if _has_table("oppyfy_permission_grants", schema=schema) is True:
        if _has_index("oppyfy_permission_grants", "ix_oppyfy_permission_grants_subdomain_id", schema=schema) is True:
            op.drop_index("ix_oppyfy_permission_grants_subdomain_id", table_name="oppyfy_permission_grants", schema=schema)
        if _has_index("oppyfy_permission_grants", "ix_oppyfy_permission_grants_user_id", schema=schema) is True:
            op.drop_index("ix_oppyfy_permission_grants_user_id", table_name="oppyfy_permission_grants", schema=schema)
        op.drop_table("oppyfy_permission_grants", schema=schema)

    # 2. `oppyfy_subdomains`
    if _has_table("oppyfy_subdomains", schema=schema) is True:
        if _has_index("oppyfy_subdomains", "ix_oppyfy_subdomains_module_slug", schema=schema) is True:
            op.drop_index("ix_oppyfy_subdomains_module_slug", table_name="oppyfy_subdomains", schema=schema)
        if _has_index("oppyfy_subdomains", "ix_oppyfy_subdomains_domain_id", schema=schema) is True:
            op.drop_index("ix_oppyfy_subdomains_domain_id", table_name="oppyfy_subdomains", schema=schema)
        if _has_index("oppyfy_subdomains", "ix_oppyfy_subdomains_subdomain_key", schema=schema) is True:
            op.drop_index("ix_oppyfy_subdomains_subdomain_key", table_name="oppyfy_subdomains", schema=schema)
        op.drop_table("oppyfy_subdomains", schema=schema)

    # 1. `oppyfy_domains`
    if _has_table("oppyfy_domains", schema=schema) is True:
        if _has_index("oppyfy_domains", "ix_oppyfy_domains_sort_order", schema=schema) is True:
            op.drop_index("ix_oppyfy_domains_sort_order", table_name="oppyfy_domains", schema=schema)
        if _has_index("oppyfy_domains", "ix_oppyfy_domains_is_active", schema=schema) is True:
            op.drop_index("ix_oppyfy_domains_is_active", table_name="oppyfy_domains", schema=schema)
        if _has_index("oppyfy_domains", "ix_oppyfy_domains_domain_key", schema=schema) is True:
            op.drop_index("ix_oppyfy_domains_domain_key", table_name="oppyfy_domains", schema=schema)
        op.drop_table("oppyfy_domains", schema=schema)


def upgrade() -> None:
    """Aplica DDL de OppyFy en el esquema activo (public o tenant_*)."""
    current_schema = _get_current_schema()
    bind = op.get_bind()

    # Siempre asegura que las tablas y columnas de `public` existan
    _apply_public_upgrades()

    if current_schema and current_schema.startswith("tenant_"):
        target_schemas = [current_schema]
    elif current_schema == "public":
        target_schemas = _get_tenant_schemas(bind)
    else:
        target_schemas = [current_schema] if current_schema else []

    for schema in target_schemas:
        _apply_tenant_upgrade_to_schema(schema)


def downgrade() -> None:
    """Revierte simétricamente todas las tablas e índices creados en 0010."""
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

    _apply_public_downgrades()
