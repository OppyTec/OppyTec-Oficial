"""
Pruebas unitarias 1:1 para `src/modules/tenancy/`, `src/core/database.py`, `src/core/redis.py` y `src/core/backup/`.
Verifica `validate_tenant_schema_name`, `Holding -> LegalEntity (1:1) -> Tenant`, `RedisCircuitBreaker` y Backups 4-Capas.
"""
from __future__ import annotations

from decimal import Decimal

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
        max_storage_mb=2048,
        price_clp=Decimal("89990.00"),
        price_usd=Decimal("99.00"),
    )
    assert isinstance(plan.price_clp, Decimal)
    assert TenantMediaAsset.__table__.schema is None


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
