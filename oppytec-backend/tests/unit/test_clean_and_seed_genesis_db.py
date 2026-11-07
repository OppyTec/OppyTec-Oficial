"""
oppytec-backend/tests/unit/test_clean_and_seed_genesis_db.py
Pruebas unitarias y de integración para el respaldo JSON de Mock Data (`mock_data_backup.json`)
y el script idempotente de Limpieza Total y Bootstrap Génesis (`scripts/clean_and_seed_genesis_db.py`).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pwdlib import PasswordHash
from scripts.clean_and_seed_genesis_db import (
    DEFAULT_AI_MODELS,
    PUBLIC_TABLES_TO_PURGE,
    clean_and_seed_genesis_db,
)
from sqlalchemy import text

from src.core.database import create_db_engine


def test_mock_data_backup_json_exists_and_has_complete_sections(
    backend_root: Path,
    monorepo_root: Path,
) -> None:
    """Verifica que `mock_data_backup.json` exista tanto en backend como en frontend con todas las categorías."""
    backend_fixture = backend_root / "fixtures" / "mock_data_backup.json"
    frontend_fixture = (
        monorepo_root
        / "oppytec-frontend"
        / "src"
        / "shared"
        / "mock"
        / "mock_data_backup.json"
    )

    assert backend_fixture.exists(), "Debe existir oppytec-backend/fixtures/mock_data_backup.json"
    assert frontend_fixture.exists(), "Debe existir oppytec-frontend/src/shared/mock/mock_data_backup.json"

    backend_raw = backend_fixture.read_text(encoding="utf-8")
    frontend_raw = frontend_fixture.read_text(encoding="utf-8")
    assert backend_raw == frontend_raw, "Ambos archivos de respaldo deben ser idénticos"

    payload = json.loads(backend_raw)
    assert "metadata" in payload
    assert "postgresql_pre_clean_snapshot" in payload
    assert "backend_modules" in payload
    assert "frontend_modules" in payload

    backend_mods = payload["backend_modules"]
    for expected_back in (
        "tenancy_router",
        "identity_router",
        "catalog_router",
        "oppy_ai_router",
        "sandbox_service",
    ):
        assert expected_back in backend_mods, f"Falta módulo backend '{expected_back}' en mock_data_backup.json"

    frontend_mods = payload["frontend_modules"]
    for expected_front in (
        "inventory",
        "inventory_alerts",
        "activities",
        "consumo",
        "events",
        "historial",
        "invoices",
        "procurement",
        "projection",
        "gestion",
        "recetas",
        "combos",
        "grupos_opciones",
        "holding_hub",
        "platform_admin",
    ):
        assert expected_front in frontend_mods, f"Falta módulo frontend '{expected_front}' en mock_data_backup.json"


def test_clean_and_seed_constants_integrity() -> None:
    """Verifica que las 21 tablas contaminadas de `public` y los 6 modelos IA estén declarados."""
    assert len(PUBLIC_TABLES_TO_PURGE) == 21
    assert "holdings" in PUBLIC_TABLES_TO_PURGE
    assert "legal_entities" in PUBLIC_TABLES_TO_PURGE
    assert "tenants" in PUBLIC_TABLES_TO_PURGE
    assert "client_users" in PUBLIC_TABLES_TO_PURGE
    assert len(DEFAULT_AI_MODELS) == 6


@pytest.mark.asyncio
async def test_clean_and_seed_genesis_db_idempotency() -> None:
    """Ejecuta `clean_and_seed_genesis_db()` y verifica el estado 100% limpio Génesis y el hash Argon2id."""
    report = await clean_and_seed_genesis_db()

    assert report.genesis_email == "OppyTec.Admin@gmail.com"
    assert report.genesis_username == "oppytec.admin"
    assert report.counts["holdings"] == 0
    assert report.counts["legal_entities"] == 0
    assert report.counts["tenants"] == 0
    assert report.counts["client_users"] == 0
    assert report.counts["global_users"] == 1
    assert report.counts["app_modules"] == 7
    assert report.counts["global_roles"] == 4
    assert report.counts["global_permissions"] == 1
    assert report.counts["system_plans"] == 3
    assert report.counts["ai_model_configs"] == 6
    assert report.counts["saas_ai_policy_config"] == 1

    # Verificar el hash Argon2id directamente en PostgreSQL
    engine = create_db_engine()
    try:
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT email, username, hashed_password, is_superuser_god, is_deleted,
                               preferred_language, preferred_currency
                        FROM public.global_users
                        WHERE id = 1
                        """
                    )
                )
            ).mappings().first()
            assert row is not None
            assert str(row["email"]) == "OppyTec.Admin@gmail.com"
            assert str(row["username"]) == "oppytec.admin"
            assert bool(row["is_superuser_god"]) is True
            assert bool(row["is_deleted"]) is False
            assert str(row["preferred_language"]) == "es"
            assert str(row["preferred_currency"]) == "CLP"
            assert PasswordHash.recommended().verify(
                "oppytec2026", str(row["hashed_password"])
            )
    finally:
        await engine.dispose()
