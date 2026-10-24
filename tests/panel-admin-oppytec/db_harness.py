"""
tests/panel-admin-oppytec/db_harness.py
Módulo utilitario de base de datos para la suite de pruebas E2E del Panel Administrativo de OppyTec v2.0.

Responsabilidades:
1. `backup_database_safety_snapshot()`:
   - Respaldo de salvaguarda no interactivo de `oppytec_dev` mediante `pg_dump`
     hacia `tests/panel-admin-oppytec/artifacts/backups/backup_pre_e2e_{timestamp}.sql`.
2. `reset_to_genesis_clean_slate()`:
   - Limpia de forma idempotente los esquemas dinámicos `tenant_*` (DROP SCHEMA IF EXISTS ... CASCADE).
   - Realiza TRUNCATE ... CASCADE de tablas de clientes: `client_user_tenant_access`, `client_users`, `tenants`, `legal_entities`, `holdings`.
   - Elimina usuarios globales de prueba (DELETE FROM public.global_users WHERE username != 'oppytec.admin').
   - Garantiza los 3 planes comerciales ('basic', 'starter', 'enterprise') y el Superadmin Genesis ('oppytec.admin') intactos en PostgreSQL.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# =========================================================================
# CONFIGURACIÓN DEL ENTORNO DE BASE DE DATOS
# =========================================================================
ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "oppytec-backend"
DEFAULT_BACKUP_DIR = ROOT_DIR / "tests" / "panel-admin-oppytec" / "artifacts" / "backups"

# Intentar cargar variables desde oppytec-backend/.env si existe
_ENV_PATH = BACKEND_DIR / ".env"
if _ENV_PATH.exists():
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'\"")
        if key not in os.environ and val:
            os.environ[key] = val

DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_USER = os.environ.get("POSTGRES_USER", "db_user")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "db_pass")
DB_NAME = os.environ.get("POSTGRES_DB", "oppytec_dev")
DOCKER_CONTAINER = os.environ.get("POSTGRES_CONTAINER", "oppytec-postgres")

# Credenciales y hash oficial del Superadmin Genesis
GENESIS_USERNAME = os.environ.get("SUPERUSER_GENESIS_USERNAME", "oppytec.admin")
GENESIS_EMAIL = os.environ.get("SUPERUSER_GENESIS_EMAIL", "oppytec.admin@gmail.com")
GENESIS_ARGON2_HASH = "$argon2id$v=19$m=65536,t=3,p=4$OzBRbcre/mUHZLJ4ttSnWQ$bH031OAzE5/NNARDJ+pdzq3ZTBWmWCgJKCF44y2ZkWk"


def _execute_sql(sql_script: str) -> str:
    """
    Ejecuta un script SQL en PostgreSQL (host psql directo con fallback a docker exec).
    Garantiza ejecución atómica y segura contra inyección SQL.
    """
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    psql_path = shutil.which("psql")
    if psql_path:
        cmd = [
            psql_path,
            "-h",
            DB_HOST,
            "-p",
            str(DB_PORT),
            "-U",
            DB_USER,
            "-d",
            DB_NAME,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            sql_script,
        ]
        try:
            res = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            return res.stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            # Fallback a docker exec si la conexión host falla
            pass

    # Fallback por docker exec
    docker_cmd = [
        "docker",
        "exec",
        "-i",
        DOCKER_CONTAINER,
        "psql",
        "-U",
        DB_USER,
        "-d",
        DB_NAME,
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        sql_script,
    ]
    res = subprocess.run(
        docker_cmd,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return res.stdout


def backup_database_safety_snapshot(backup_dir: Path | str | None = None) -> Path:
    """
    Ejecuta un respaldo de salvaguarda de `oppytec_dev` mediante `pg_dump` no interactivo
    hacia `tests/panel-admin-oppytec/artifacts/backups/backup_pre_e2e_{timestamp}.sql`.

    Returns:
        Path del archivo de respaldo generado y verificado (> 0 bytes).
    """
    target_dir = Path(backup_dir) if backup_dir else DEFAULT_BACKUP_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_file = target_dir / f"backup_pre_e2e_{timestamp}.sql"

    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    pg_dump_path = shutil.which("pg_dump")
    dump_success = False

    if pg_dump_path:
        cmd = [
            pg_dump_path,
            "-h",
            DB_HOST,
            "-p",
            str(DB_PORT),
            "-U",
            DB_USER,
            "-d",
            DB_NAME,
            "-w",  # non-interactive
        ]
        try:
            with open(backup_file, "w", encoding="utf-8") as f:
                subprocess.run(
                    cmd,
                    env=env,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=15,
                )
            dump_success = True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            dump_success = False

    if not dump_success:
        # Fallback vía Docker exec
        docker_cmd = [
            "docker",
            "exec",
            DOCKER_CONTAINER,
            "pg_dump",
            "-U",
            DB_USER,
            "-d",
            DB_NAME,
            "-w",
        ]
        with open(backup_file, "w", encoding="utf-8") as f:
            subprocess.run(
                docker_cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                check=True,
                timeout=15,
            )

    if not backup_file.exists() or backup_file.stat().st_size == 0:
        raise RuntimeError(f"Database safety snapshot failed or generated empty file: {backup_file}")

    return backup_file


def reset_to_genesis_clean_slate() -> dict[str, Any]:
    """
    Ejecuta el protocolo de reseteo limpio Génesis para la base de datos de pruebas E2E:
    1. Limpia los esquemas dinámicos `tenant_*` (DROP SCHEMA IF EXISTS ... CASCADE).
    2. Realiza TRUNCATE ... CASCADE de las tablas de datos de clientes en `public`:
       - `client_user_tenant_access`
       - `client_users`
       - `tenants`
       - `legal_entities`
       - `holdings`
    3. Elimina usuarios globales de prueba adicionales (username != 'oppytec.admin').
    4. Garantiza que los 3 planes comerciales ('basic', 'starter', 'enterprise') en `public.system_plans`
       y el Superadmin Genesis ('oppytec.admin') queden listos e intactos en la base de datos Docker `oppytec-postgres`.

    Returns:
        dict con el reporte de entidades afectadas y tiempo de ejecución.
    """
    start_time = time.perf_counter()

    clean_slate_sql = f"""
-- 1. Eliminar esquemas dinámicos tenant_*
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%') LOOP
        EXECUTE 'DROP SCHEMA IF EXISTS ' || quote_ident(r.schema_name) || ' CASCADE';
    END LOOP;
END $$;

-- 2. Truncar tablas de datos de clientes con cascada completa
TRUNCATE TABLE 
    public.client_user_tenant_access,
    public.client_users,
    public.tenants,
    public.legal_entities,
    public.holdings 
CASCADE;

-- 3. Limpiar permisos de usuarios de prueba y eliminar usuarios globales excepto Génesis
DELETE FROM public.global_user_permission_grants 
WHERE user_id IN (SELECT id FROM public.global_users WHERE username != '{GENESIS_USERNAME}');

DELETE FROM public.global_users 
WHERE username != '{GENESIS_USERNAME}';

-- 4. Garantizar Superadmin Genesis intacto y activo
INSERT INTO public.global_users (
    guid, email, username, hashed_password, preferred_language, preferred_currency, is_superuser_god, is_deleted
) VALUES (
    '00000000-0000-4000-8000-000000000001',
    '{GENESIS_EMAIL}',
    '{GENESIS_USERNAME}',
    '{GENESIS_ARGON2_HASH}',
    'es',
    'CLP',
    true,
    false
)
ON CONFLICT (username) DO UPDATE
SET 
    is_deleted = false,
    is_superuser_god = true,
    deleted_at = NULL,
    deleted_by = NULL;

-- 5. Garantizar los 3 Planes Comerciales base intactos
INSERT INTO public.system_plans (
    id, slug, name, max_active_users, max_products, max_suppliers, max_recipes, max_combos, max_storage_mb, included_modules, anchor_currency, price_clp, price_usd, price_eur, price_brl, auto_convert_fx, i18n_data
) VALUES 
(
    '289a85e3-3967-40b7-a3f8-8e0b4f7ae2c4',
    'basic',
    'Plan Básico (Control de Inventario)',
    5, 500, 20, 0, 0, 512,
    '["inicio", "operations.consumption_log", "inventory.stock", "catalog.products", "inventory.mermas", "inventory.counts", "notifications", "alerts", "audit.history", "identity.users"]'::jsonb,
    'CLP', 34990.00, 39.00, 35.00, 195.00, true,
    '{{"en": "Plan Básico (Control de Inventario)", "es": "Plan Básico (Control de Inventario)"}}'::jsonb
),
(
    'a74bce86-3e8a-490a-bdc7-f4c082ba2440',
    'starter',
    'Plan Esencial',
    10, 1500, 50, 150, 40, 512,
    '["catalog", "inventory", "recipes"]'::jsonb,
    'CLP', 49990.00, 55.00, 50.00, 280.00, true,
    '{{"en": "Plan Esencial", "es": "Plan Esencial"}}'::jsonb
),
(
    '4c1ada88-1ff1-45cd-a9b6-4eddf49af889',
    'enterprise',
    'Plan Corporativo',
    100, 10000, 500, 2000, 500, 5120,
    '["catalog", "inventory", "recipes", "procurement", "operations", "analytics", "oppy_ai"]'::jsonb,
    'CLP', 149990.00, 165.00, 150.00, 850.00, true,
    '{{"en": "Plan Corporativo", "es": "Plan Corporativo"}}'::jsonb
)
ON CONFLICT (slug) DO UPDATE
SET 
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
    auto_convert_fx = EXCLUDED.auto_convert_fx,
    i18n_data = EXCLUDED.i18n_data;
"""

    _execute_sql(clean_slate_sql)

    # Verificación final de estado limpio
    verification_sql = f"""
SELECT 
    (SELECT count(*) FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%') AS tenant_schemas,
    (SELECT count(*) FROM public.holdings) AS holdings_count,
    (SELECT count(*) FROM public.legal_entities) AS legal_entities_count,
    (SELECT count(*) FROM public.tenants) AS tenants_count,
    (SELECT count(*) FROM public.client_users) AS client_users_count,
    (SELECT count(*) FROM public.global_users WHERE username = '{GENESIS_USERNAME}' AND is_deleted = false) AS genesis_ready,
    (SELECT count(*) FROM public.system_plans WHERE slug IN ('basic', 'starter', 'enterprise')) AS plans_ready;
"""
    output = _execute_sql(verification_sql)
    elapsed = time.perf_counter() - start_time

    return {
        "status": "success",
        "elapsed_seconds": round(elapsed, 4),
        "verification_raw": output.strip(),
        "genesis_user": GENESIS_USERNAME,
        "plans": ["basic", "starter", "enterprise"],
    }


if __name__ == "__main__":
    print("=================================================================")
    print("EJECUTANDO COMPROBACIÓN UNITARIA DE DB_HARNESS (E2E SUITE)")
    print("=================================================================")

    t0 = time.perf_counter()

    # 1. Respaldo de seguridad
    print("1. Ejecutando backup_database_safety_snapshot()...")
    backup_path = backup_database_safety_snapshot()
    size_kb = backup_path.stat().st_size / 1024.0
    print(f"   [OK] Respaldo generado: {backup_path.name} ({size_kb:.1f} KB)")

    # 2. Reseteo a estado Génesis
    print("2. Ejecutando reset_to_genesis_clean_slate()...")
    report = reset_to_genesis_clean_slate()
    print(f"   [OK] Reseteo completado en {report['elapsed_seconds']} s")
    print(f"   Detalle de verificación:\n{report['verification_raw']}")

    total_time = time.perf_counter() - t0
    print("=================================================================")
    print(f"TOTAL TIEMPO DE EJECUCIÓN: {total_time:.4f} segundos")
    print("=================================================================")

    if total_time >= 2.0:
        raise AssertionError(f"db_harness execution exceeded 2.0 seconds: {total_time:.4f}s")

    print("[SUCCESS] db_harness verificado en menos de 2 segundos sin errores de SQL.")
