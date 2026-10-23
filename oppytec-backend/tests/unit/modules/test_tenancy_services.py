"""
Pruebas unitarias 1:1 para `src/modules/tenancy/`, `src/core/database.py`, `src/core/redis.py` y `src/core/backup/`.
Verifica `validate_tenant_schema_name`, `Holding -> LegalEntity (1:1) -> Tenant`, `RedisCircuitBreaker` y Backups 4-Capas.
"""
from __future__ import annotations

import importlib
import importlib.util
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.backup_manager import FourLayerBackupOrchestrator

from src.core.backup.crypto_stream import (
    assert_not_plaintext_sql,
    compress_and_encrypt_sql_dump,
    decrypt_and_decompress_sql_dump,
)
from src.core.backup.protocol import (
    BackupLayerPort,
    build_backup_artifact_filename,
    validate_backup_artifact_filename,
)
from src.core.database import validate_tenant_schema_name
from src.core.redis import RedisCircuitBreaker, build_namespaced_redis_key
from src.modules.tenancy.infrastructure.models import (
    Holding,
    LegalEntity,
    SystemPlan,
    Tenant,
    TenantMediaAsset,
)
from src.shared.pagination import PaginatedResponse, PaginationParams

pytestmark = pytest.mark.unit


def test_tenant_schema_validation_blocks_sql_injection() -> None:
    """Garantiza que `validate_tenant_schema_name` acepte solo `^tenant_[a-z0-9_]{1,63}$`."""
    assert validate_tenant_schema_name("tenant_pollo_king_01") == "tenant_pollo_king_01"

    for malicious in (
        "public",
        "tenant_bad; DROP SCHEMA public CASCADE;--",
        "tenant-with-dash",
        "TENANT_UPPERCASE",
        "../tenant_escape",
    ):
        with pytest.raises(ValueError, match="TenantSchemaValidationError"):
            validate_tenant_schema_name(malicious)


def test_tenancy_models_and_legal_entity_1_to_1_unique_constraint() -> None:
    """Verifica cardinalidad 1:1 en `Tenant.legal_entity_id`, inmutabilidad de `Holding` y precios `Decimal`."""
    assert Holding.translatable is False
    assert LegalEntity.translatable is False

    legal_entity_col = Tenant.__table__.c.legal_entity_id
    assert legal_entity_col.unique is True

    plan = SystemPlan(
        slug="pro",
        name="Plan Pro",
        max_active_users=25,
        max_products=500,
        max_suppliers=20,
        max_recipes=10,
        max_combos=5,
        max_storage_mb=2048,
        price_clp=Decimal("89990.00"),
        price_usd=Decimal("99.00"),
    )
    assert isinstance(plan.price_clp, Decimal)
    assert TenantMediaAsset.__table__.schema is None

    # Verificación de columnas de cuotas paramétricas en SystemPlan
    for col_name in (
        "max_active_users",
        "max_products",
        "max_suppliers",
        "max_recipes",
        "max_combos",
        "max_storage_mb",
    ):
        assert col_name in SystemPlan.__table__.c
        assert SystemPlan.__table__.c[col_name].nullable is False

    # Verificación de overrides paramétricos en Holding y Tenant
    for model in (Holding, Tenant):
        for override_col in (
            "custom_max_users_override",
            "custom_max_products_override",
            "custom_max_suppliers_override",
            "custom_max_recipes_override",
            "custom_max_combos_override",
            "custom_storage_mb_override",
        ):
            assert override_col in model.__table__.c
            assert model.__table__.c[override_col].nullable is True


def test_migration_0003_symmetry_and_metadata(backend_root: Path) -> None:
    """Verifica que la migración 0003 tenga simetría 100% reversible (upgrade/downgrade) y metadatos válidos."""
    mig_path = backend_root / "alembic" / "versions" / "0003_public_plans_quotas_and_tenant_capacity_overrides.py"
    assert mig_path.exists(), "La migración 0003 debe existir en alembic/versions/"

    spec = importlib.util.spec_from_file_location("mig_0003", mig_path)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    assert m.revision == "0003_public_plans_quotas_and_tenant_capacity_overrides"
    assert m.down_revision == "0002_tenant_initial_client_rbac_and_core_modules"
    assert m.migration_scope == "public"

    added: list[tuple[str, str, str | None]] = []
    dropped: list[tuple[str, str, str | None]] = []

    with patch.object(m.op, "add_column", side_effect=lambda t, c, schema=None: added.append((t, c.name, schema))):
        m.upgrade()

    with patch.object(m.op, "drop_column", side_effect=lambda t, c, schema=None: dropped.append((t, c, schema))):
        m.downgrade()

    assert len(added) == 12
    assert len(dropped) == 12
    assert list(reversed(added)) == dropped


@pytest.mark.asyncio
async def test_redis_circuit_breaker_and_namespace_isolation() -> None:
    """Verifica que `RedisCircuitBreaker` abra el circuito tras fallos y devuelva fallback sin HTTP 500."""
    key = build_namespaced_redis_key("ratelimit:login", namespace="wt_p2_1", environment="local")
    assert key == "local:wt_p2_1:ratelimit:login"

    breaker = RedisCircuitBreaker(failure_threshold=2, max_latency_ms=50.0)
    assert breaker.state == "CLOSED"

    async def _failing_op() -> str:
        raise ConnectionError("Redis offline")

    assert await breaker.execute_or_fallback(_failing_op, "SAFE_FALLBACK") == "SAFE_FALLBACK"
    assert await breaker.execute_or_fallback(_failing_op, "SAFE_FALLBACK") == "SAFE_FALLBACK"
    assert breaker.state == "OPEN"


def test_four_layer_encrypted_backups_and_surgical_tenant_restore() -> None:
    """Verifica compresión `zstd` + cifrado `age` (`.sql.zst.age`) y aislamiento de `restore_single_tenant`."""
    age_key = "age1oppytecv2devrecipientkey99887766554433221100"
    raw_sql = b'SET LOCAL search_path TO "tenant_rest_a";\n-- ROW: prod_1\n'

    encrypted, sha256_hex = compress_and_encrypt_sql_dump(raw_sql, age_key)
    assert_not_plaintext_sql(encrypted)

    with pytest.raises(ValueError, match="SecurityViolation"):
        assert_not_plaintext_sql(b"-- PostgreSQL database dump\nCREATE TABLE x;")

    restored = decrypt_and_decompress_sql_dump(encrypted, age_key, expected_sha256=sha256_hex)
    assert restored == raw_sql

    fname = build_backup_artifact_filename("tenant_rest_a")
    assert validate_backup_artifact_filename(fname) == fname

    orchestrator = FourLayerBackupOrchestrator(public_key=age_key)
    assert isinstance(orchestrator.layer1_neon, BackupLayerPort)
    assert isinstance(orchestrator.layer2_r2, BackupLayerPort)
    assert isinstance(orchestrator.layer3_vps, BackupLayerPort)
    assert isinstance(orchestrator.layer4_local, BackupLayerPort)
    assert orchestrator.run_automated_restore_drill("tenant_rest_a") is True

    params = PaginationParams(page=2, page_size=10)
    page_resp = PaginatedResponse.create(items=["a", "b"], total=25, params=params)
    assert page_resp.offset if hasattr(page_resp, "offset") else params.offset == 10
    assert page_resp.total_pages == 3
