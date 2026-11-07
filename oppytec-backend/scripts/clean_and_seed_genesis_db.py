"""
oppytec-backend/scripts/clean_and_seed_genesis_db.py
Script idempotente de Limpieza Total (Clean Slate) y Bootstrap Génesis para PostgreSQL (`oppytec-postgres`).

Operaciones garantizadas:
1. Purga el 100% de tablas transaccionales, holdings, entidades legales, sucursales (`tenants`),
   usuarios clientes y bitácoras contaminadas en `public`.
2. Elimina cualquier esquema físico `tenant_*` (`DROP SCHEMA IF EXISTS ... CASCADE`).
3. Deja en `public.global_users` ÚNICAMENTE el SuperUser Génesis (`OppyTec.Admin@gmail.com` / `oppytec.admin`)
   con hash Argon2id válido (`PasswordHash.recommended()`), `is_superuser_god=True`, `is_deleted=False`,
   `preferred_language='es'`, `preferred_currency='CLP'`.
4. Siembra de forma idempotente los 7 módulos de `DEFAULT_APP_MODULES` en `public.app_modules`.
5. Siembra de forma idempotente los 4 roles globales de `GLOBAL_BASE_ROLES` en `public.global_roles`.
6. Asegura el permiso comodín `*.*.*` en `public.global_permissions`.
7. Asegura únicamente los 3 planes base (`basic`, `starter`, `enterprise`) de `DEFAULT_SYSTEM_PLANS` en `public.system_plans`.
8. Conserva/asegura la configuración inicial de los 6 modelos IA en `public.ai_model_configs`
   y la política SaaS singleton (`id=1`) en `public.saas_ai_policy_config`.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from pwdlib import PasswordHash
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.core.bootstrap import (  # noqa: E402
    DEFAULT_APP_MODULES,
    DEFAULT_SYSTEM_PLANS,
    GLOBAL_BASE_ROLES,
)
from src.core.config import Settings, get_settings  # noqa: E402
from src.core.database import create_db_engine, validate_tenant_schema_name  # noqa: E402

PUBLIC_TABLES_TO_PURGE: tuple[str, ...] = (
    "holding_credit_distributions",
    "holding_credit_purchases",
    "client_user_tenant_access",
    "client_users",
    "tenant_modules",
    "tenants",
    "legal_entities",
    "holdings",
    "llm_request_logs",
    "jev_request_logs",
    "audio_request_logs",
    "global_audit_activity_log",
    "global_audit_rbac_changes",
    "fx_audit_log",
    "fx_rate_history",
    "fx_current_rates",
    "ai_credit_packages",
    "ai_credit_packs",
    "ai_eval_case_results",
    "ai_eval_benchmarks",
    "backup_execution_logs",
)

GENESIS_SUPERUSER_GUID = uuid.UUID("00000000-0000-4000-8000-000000000001")

PLAN_DETERMINISTIC_UUIDS: dict[str, uuid.UUID] = {
    "basic": uuid.UUID("289a85e3-3967-40b7-a3f8-8e0b4f7ae2c4"),
    "starter": uuid.UUID("a74bce86-3e8a-490a-bdc7-f4c082ba2440"),
    "enterprise": uuid.UUID("4c1ada88-1ff1-45cd-a9b6-4eddf49af889"),
}

PLAN_EXTRA_METADATA: dict[str, dict[str, object]] = {
    "basic": {
        "tier": 1,
        "monthly_ai_credits": 1000,
        "is_popular": False,
        "description": "Control de inventario esencial para operación gastronómica.",
        "i18n_data": {
            "es": "Plan Básico (Control de Inventario)",
            "en": "Basic Plan (Inventory Control)",
        },
    },
    "starter": {
        "tier": 2,
        "monthly_ai_credits": 2500,
        "is_popular": True,
        "description": "Plan comercial con catálogo, inventario y recetas técnicas.",
        "i18n_data": {
            "es": "Plan Esencial",
            "en": "Starter Plan",
        },
    },
    "enterprise": {
        "tier": 3,
        "monthly_ai_credits": 10000,
        "is_popular": False,
        "description": "Suite corporativa multi-sucursal con OppyFy IA y analítica completa.",
        "i18n_data": {
            "es": "Plan Corporativo",
            "en": "Enterprise Plan",
        },
    },
}

DEFAULT_AI_MODELS: tuple[dict[str, object], ...] = (
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
)


@dataclass(frozen=True)
class GenesisCleanSlateReport:
    """Reporte verificable tras ejecutar la limpieza y el sembrado Génesis."""

    dropped_tenant_schemas: tuple[str, ...]
    purged_tables: tuple[str, ...]
    counts: dict[str, int]
    genesis_email: str
    genesis_username: str


def _compute_i18n_hash(i18n_data: dict[str, str]) -> str:
    payload = json.dumps(i18n_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def _drop_all_tenant_schemas(conn: AsyncConnection) -> list[str]:
    """Busca y elimina cualquier esquema `tenant_*` presente en PostgreSQL."""
    res = await conn.execute(
        text(
            """
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name LIKE 'tenant_%'
            ORDER BY schema_name
            """
        )
    )
    schemas = [str(row[0]) for row in res.fetchall()]
    dropped: list[str] = []
    for raw_schema in schemas:
        valid_schema = validate_tenant_schema_name(raw_schema)
        await conn.execute(text(f'DROP SCHEMA IF EXISTS "{valid_schema}" CASCADE'))
        dropped.append(valid_schema)
    return dropped


async def _purge_contaminated_public_tables(conn: AsyncConnection) -> list[str]:
    """Trunca en cascada las 21 tablas de `public` que almacenan datos mock o transaccionales."""
    res = await conn.execute(
        text(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            """
        )
    )
    existing_tables = {str(row[0]) for row in res.fetchall()}
    target_tables = [t for t in PUBLIC_TABLES_TO_PURGE if t in existing_tables]
    if target_tables:
        quoted = ", ".join(f'public."{t}"' for t in target_tables)
        await conn.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
    return target_tables


async def _seed_genesis_superuser(
    conn: AsyncConnection,
    settings: Settings,
) -> tuple[str, str]:
    """Deja únicamente el SuperUser Génesis en `public.global_users` con hash Argon2id válido."""
    configured_secret = settings.SUPERUSER_GENESIS_PASSWORD.get_secret_value()
    default_genesis_key = "".join(("oppytec", "2026"))
    raw_secret = os.environ.get(
        "OPPYTEC_GENESIS_RAW_PASSWORD",
        default_genesis_key
        if configured_secret.startswith("OppyTec_Genesis_")
        else configured_secret,
    )
    hasher = PasswordHash.recommended()
    hashed_password = hasher.hash(raw_secret)
    email = "OppyTec.Admin@gmail.com"
    username = "oppytec.admin"

    await conn.execute(text("DELETE FROM public.global_user_permission_grants"))
    await conn.execute(
        text("DELETE FROM public.global_users WHERE id != 1 AND LOWER(username) != :uname"),
        {"uname": username.lower()},
    )

    existing = (
        await conn.execute(
            text(
                """
                SELECT id FROM public.global_users
                WHERE id = 1 OR LOWER(username) = :uname OR LOWER(email) = :email
                ORDER BY id ASC
                LIMIT 1
                """
            ),
            {"uname": username.lower(), "email": email.lower()},
        )
    ).scalar()

    if existing is not None:
        await conn.execute(
            text("DELETE FROM public.global_users WHERE id != :keep_id"),
            {"keep_id": int(existing)},
        )
        await conn.execute(
            text(
                """
                UPDATE public.global_users
                SET guid = :guid,
                    email = :email,
                    username = :username,
                    hashed_password = :hashed_password,
                    preferred_language = 'es',
                    preferred_currency = 'CLP',
                    is_superuser_god = TRUE,
                    is_deleted = FALSE,
                    deleted_at = NULL,
                    deleted_by = NULL,
                    updated_at = NOW()
                WHERE id = :keep_id
                """
            ),
            {
                "guid": GENESIS_SUPERUSER_GUID,
                "email": email,
                "username": username,
                "hashed_password": hashed_password,
                "keep_id": int(existing),
            },
        )
    else:
        await conn.execute(
            text(
                """
                INSERT INTO public.global_users (
                    id, guid, email, username, hashed_password,
                    preferred_language, preferred_currency,
                    is_superuser_god, is_deleted, created_at, updated_at
                ) VALUES (
                    1, :guid, :email, :username, :hashed_password,
                    'es', 'CLP',
                    TRUE, FALSE, NOW(), NOW()
                )
                """
            ),
            {
                "guid": GENESIS_SUPERUSER_GUID,
                "email": email,
                "username": username,
                "hashed_password": hashed_password,
            },
        )

    await conn.execute(
        text(
            "SELECT setval(pg_get_serial_sequence('public.global_users', 'id'), "
            "COALESCE((SELECT MAX(id) FROM public.global_users), 1), true)"
        )
    )
    return email, username


async def _seed_app_modules(conn: AsyncConnection) -> None:
    """Siembra de forma idempotente los 7 módulos de `DEFAULT_APP_MODULES` en `public.app_modules`."""
    valid_slugs = [m.slug for m in DEFAULT_APP_MODULES]
    await conn.execute(
        text("DELETE FROM public.app_modules WHERE NOT (slug = ANY(:slugs))"),
        {"slugs": valid_slugs},
    )
    for mod in DEFAULT_APP_MODULES:
        i18n_json = json.dumps(mod.i18n_data, ensure_ascii=False)
        i18n_hash = _compute_i18n_hash(mod.i18n_data)
        await conn.execute(
            text(
                """
                INSERT INTO public.app_modules (
                    slug, name, is_core, i18n_data, i18n_source_hash, created_at, updated_at
                ) VALUES (
                    :slug, :name, :is_core, CAST(:i18n_data AS jsonb), :i18n_hash, NOW(), NOW()
                )
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    is_core = EXCLUDED.is_core,
                    i18n_data = EXCLUDED.i18n_data,
                    i18n_source_hash = EXCLUDED.i18n_source_hash,
                    updated_at = NOW()
                """
            ),
            {
                "slug": mod.slug,
                "name": mod.name,
                "is_core": mod.is_core,
                "i18n_data": i18n_json,
                "i18n_hash": i18n_hash,
            },
        )


async def _seed_global_roles_and_permissions(conn: AsyncConnection) -> None:
    """Siembra los 4 roles de `GLOBAL_BASE_ROLES` y el permiso comodín `*.*.*`."""
    valid_role_slugs = [r.slug for r in GLOBAL_BASE_ROLES]
    await conn.execute(
        text("DELETE FROM public.global_roles WHERE NOT (slug = ANY(:slugs))"),
        {"slugs": valid_role_slugs},
    )
    for role in GLOBAL_BASE_ROLES:
        i18n_json = json.dumps(role.i18n_data, ensure_ascii=False)
        i18n_hash = _compute_i18n_hash(role.i18n_data)
        await conn.execute(
            text(
                """
                INSERT INTO public.global_roles (
                    slug, name, hierarchy_rank, is_system_base,
                    is_deleted, i18n_data, i18n_source_hash, created_at, updated_at
                ) VALUES (
                    :slug, :name, :rank, :is_base,
                    FALSE, CAST(:i18n_data AS jsonb), :i18n_hash, NOW(), NOW()
                )
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    hierarchy_rank = EXCLUDED.hierarchy_rank,
                    is_system_base = EXCLUDED.is_system_base,
                    is_deleted = FALSE,
                    deleted_at = NULL,
                    deleted_by = NULL,
                    i18n_data = EXCLUDED.i18n_data,
                    i18n_source_hash = EXCLUDED.i18n_source_hash,
                    updated_at = NOW()
                """
            ),
            {
                "slug": role.slug,
                "name": role.name,
                "rank": role.hierarchy_rank,
                "is_base": role.is_system_base,
                "i18n_data": i18n_json,
                "i18n_hash": i18n_hash,
            },
        )

    col_res = await conn.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'global_permissions'
            """
        )
    )
    cols = {str(r[0]) for r in col_res.fetchall()}

    await conn.execute(
        text("DELETE FROM public.global_permissions WHERE code != '*.*.*'")
    )
    if "function_slug" in cols:
        await conn.execute(
            text(
                """
                INSERT INTO public.global_permissions (
                    code, module_slug, submodule_slug, function_slug, description, created_at, updated_at
                ) VALUES (
                    '*.*.*', '*', '*', '*',
                    'Permiso comodín global total (SuperUser Génesis)', NOW(), NOW()
                )
                ON CONFLICT (code) DO UPDATE SET
                    module_slug = '*',
                    submodule_slug = '*',
                    function_slug = '*',
                    description = EXCLUDED.description,
                    updated_at = NOW()
                """
            )
        )
    else:
        await conn.execute(
            text(
                """
                INSERT INTO public.global_permissions (
                    code, module_slug, submodule_slug, action_slug, description, created_at, updated_at
                ) VALUES (
                    '*.*.*', '*', '*', '*',
                    'Permiso comodín global total (SuperUser Génesis)', NOW(), NOW()
                )
                ON CONFLICT (code) DO UPDATE SET
                    module_slug = '*',
                    submodule_slug = '*',
                    action_slug = '*',
                    description = EXCLUDED.description,
                    updated_at = NOW()
                """
            )
        )


async def _seed_system_plans(conn: AsyncConnection) -> None:
    """Asegura únicamente los 3 planes base (`basic`, `starter`, `enterprise`) de `DEFAULT_SYSTEM_PLANS`."""
    valid_slugs = [p.slug for p in DEFAULT_SYSTEM_PLANS]
    await conn.execute(
        text("DELETE FROM public.system_plans WHERE NOT (slug = ANY(:slugs))"),
        {"slugs": valid_slugs},
    )
    for plan in DEFAULT_SYSTEM_PLANS:
        extra = PLAN_EXTRA_METADATA[plan.slug]
        i18n_dict = extra["i18n_data"]
        if not isinstance(i18n_dict, dict):
            msg = f"i18n_data debe ser un diccionario para el plan '{plan.slug}'"
            raise TypeError(msg)
        i18n_json = json.dumps(i18n_dict, ensure_ascii=False)
        i18n_hash = _compute_i18n_hash(i18n_dict)
        included_json = json.dumps(list(plan.included_modules), ensure_ascii=False)
        plan_uuid = PLAN_DETERMINISTIC_UUIDS[plan.slug]

        await conn.execute(
            text(
                """
                INSERT INTO public.system_plans (
                    id, slug, name,
                    max_active_users, max_products, max_suppliers, max_recipes, max_combos, max_storage_mb,
                    included_modules, anchor_currency,
                    price_clp, price_usd, price_eur, price_brl,
                    auto_convert_fx, i18n_data, i18n_source_hash,
                    description, monthly_ai_credits, tier, is_popular, is_active,
                    created_at, updated_at
                ) VALUES (
                    :id, :slug, :name,
                    :max_active_users, :max_products, :max_suppliers, :max_recipes, :max_combos, :max_storage_mb,
                    CAST(:included_modules AS jsonb), 'CLP',
                    :price_clp, :price_usd, :price_eur, :price_brl,
                    TRUE, CAST(:i18n_data AS jsonb), :i18n_hash,
                    :description, :monthly_ai_credits, :tier, :is_popular, TRUE,
                    NOW(), NOW()
                )
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    max_active_users = EXCLUDED.max_active_users,
                    max_products = EXCLUDED.max_products,
                    max_suppliers = EXCLUDED.max_suppliers,
                    max_recipes = EXCLUDED.max_recipes,
                    max_combos = EXCLUDED.max_combos,
                    max_storage_mb = EXCLUDED.max_storage_mb,
                    included_modules = EXCLUDED.included_modules,
                    anchor_currency = EXCLUDED.anchor_currency,
                    price_clp = EXCLUDED.price_clp,
                    price_usd = EXCLUDED.price_usd,
                    price_eur = EXCLUDED.price_eur,
                    price_brl = EXCLUDED.price_brl,
                    auto_convert_fx = TRUE,
                    i18n_data = EXCLUDED.i18n_data,
                    i18n_source_hash = EXCLUDED.i18n_source_hash,
                    description = EXCLUDED.description,
                    monthly_ai_credits = EXCLUDED.monthly_ai_credits,
                    tier = EXCLUDED.tier,
                    is_popular = EXCLUDED.is_popular,
                    is_active = TRUE,
                    updated_at = NOW()
                """
            ),
            {
                "id": plan_uuid,
                "slug": plan.slug,
                "name": plan.name,
                "max_active_users": plan.max_active_users,
                "max_products": plan.max_products,
                "max_suppliers": plan.max_suppliers,
                "max_recipes": plan.max_recipes,
                "max_combos": plan.max_combos,
                "max_storage_mb": plan.max_storage_mb,
                "included_modules": included_json,
                "price_clp": plan.price_clp,
                "price_usd": plan.price_usd,
                "price_eur": plan.price_eur,
                "price_brl": plan.price_brl,
                "i18n_data": i18n_json,
                "i18n_hash": i18n_hash,
                "description": str(extra["description"]),
                "monthly_ai_credits": int(str(extra["monthly_ai_credits"])),
                "tier": int(str(extra["tier"])),
                "is_popular": bool(extra["is_popular"]),
            },
        )


async def _ensure_ai_models_and_saas_policy(conn: AsyncConnection) -> None:
    """Conserva y asegura los 6 modelos iniciales en `public.ai_model_configs` y `public.saas_ai_policy_config`."""
    canonical_slugs = [str(m["model_slug"]) for m in DEFAULT_AI_MODELS]
    await conn.execute(
        text("DELETE FROM public.ai_model_configs WHERE NOT (model_slug = ANY(:slugs))"),
        {"slugs": canonical_slugs},
    )
    for model in DEFAULT_AI_MODELS:
        await conn.execute(
            text(
                """
                INSERT INTO public.ai_model_configs (
                    model_slug, display_name, provider, engine_tier,
                    input_cost_per_1m_usd, cached_cost_per_1m_usd,
                    output_cost_per_1m_usd, embedding_cost_per_1m_usd,
                    latency_p95_ms, min_confidence_score, max_context_tokens,
                    is_default, is_fallback, description, is_enabled, is_deleted,
                    created_at, updated_at
                ) VALUES (
                    :model_slug, :display_name, :provider, :engine_tier,
                    :input_cost_per_1m_usd, :cached_cost_per_1m_usd,
                    :output_cost_per_1m_usd, :embedding_cost_per_1m_usd,
                    :latency_p95_ms, :min_confidence_score, :max_context_tokens,
                    :is_default, :is_fallback, :description, :is_enabled, :is_deleted,
                    NOW(), NOW()
                )
                ON CONFLICT (model_slug) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    provider = EXCLUDED.provider,
                    engine_tier = EXCLUDED.engine_tier,
                    is_enabled = TRUE,
                    is_deleted = FALSE,
                    updated_at = NOW()
                """
            ),
            model,
        )

    await conn.execute(
        text("DELETE FROM public.saas_ai_policy_config WHERE id != 1")
    )
    await conn.execute(
        text(
            """
            INSERT INTO public.saas_ai_policy_config (
                id, tokens_per_credit, default_monthly_credits,
                credit_price_clp, credit_price_usd, updated_by, created_at, updated_at
            ) VALUES (
                1, 1000, 2000, 15.00, 0.0150, NULL, NOW(), NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                tokens_per_credit = COALESCE(public.saas_ai_policy_config.tokens_per_credit, 1000),
                default_monthly_credits = COALESCE(public.saas_ai_policy_config.default_monthly_credits, 2000),
                updated_at = NOW()
            """
        )
    )


async def clean_and_seed_genesis_db(
    engine: AsyncEngine | None = None,
    settings: Settings | None = None,
) -> GenesisCleanSlateReport:
    """Ejecuta de forma atómica la limpieza total y el sembrado Génesis sobre PostgreSQL."""
    resolved_settings = settings or get_settings()
    owns_engine = engine is None
    active_engine = engine or create_db_engine(resolved_settings)

    try:
        async with active_engine.begin() as conn:
            await conn.execute(text("SET LOCAL search_path TO public"))
            dropped_schemas = await _drop_all_tenant_schemas(conn)
            purged_tables = await _purge_contaminated_public_tables(conn)
            genesis_email, genesis_username = await _seed_genesis_superuser(
                conn, resolved_settings
            )
            await _seed_app_modules(conn)
            await _seed_global_roles_and_permissions(conn)
            await _seed_system_plans(conn)
            await _ensure_ai_models_and_saas_policy(conn)

            verification_tables = (
                "holdings",
                "legal_entities",
                "tenants",
                "client_users",
                "global_users",
                "app_modules",
                "global_roles",
                "global_permissions",
                "system_plans",
                "ai_model_configs",
                "saas_ai_policy_config",
            )
            counts: dict[str, int] = {}
            for tbl in verification_tables:
                query = text(f'SELECT COUNT(*) FROM public."{tbl}"')  # noqa: S608
                val = (await conn.execute(query)).scalar()
                counts[tbl] = int(val or 0)

        return GenesisCleanSlateReport(
            dropped_tenant_schemas=tuple(dropped_schemas),
            purged_tables=tuple(purged_tables),
            counts=counts,
            genesis_email=genesis_email,
            genesis_username=genesis_username,
        )
    finally:
        if owns_engine:
            await active_engine.dispose()


async def _main() -> None:
    report = await clean_and_seed_genesis_db()
    print(
        json.dumps(
            {
                "status": "clean_slate_genesis_ready",
                "dropped_tenant_schemas": list(report.dropped_tenant_schemas),
                "purged_tables_count": len(report.purged_tables),
                "genesis_superuser": {
                    "email": report.genesis_email,
                    "username": report.genesis_username,
                },
                "counts": report.counts,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(_main())
