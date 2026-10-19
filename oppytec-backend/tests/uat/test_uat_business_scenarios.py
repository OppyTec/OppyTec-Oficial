"""
Escenarios de Aceptación de Usuario (UAT) Trazables a `specs/01-PRD.md`
(`tests/uat/test_uat_business_scenarios.py`).

Valida los 3 escenarios maestros de aceptación de negocio:
1. Escenario UAT 1 (Carlos — Propietario de Holding & Marcela — Gerente Multi-Sucursal):
   Operación multi-sucursal dentro del mismo Holding (`tenant_rest_a` y `tenant_hotel_b`), bloqueo estricto
   hacia sucursales de otros Holdings (`tenant_external_c`), liberación inmediata de cupo en `soft-delete`
   y exactitud financiera gastronómica en `Decimal`.
2. Escenario UAT 2 (Experiencia Global Nativa `i18n` + Multi-Moneda `FX`):
   Protección inmutable de nombres propios (`"Pollo King"`, `"Savory"`), memoria global de traducción con 0 tokens
   y motor cambiario institucional (`BCCh` + `BCE Frankfurter`) con triangulación `Decimal(18, 8)` y Anomaly Guard `> 8%`.
3. Escenario UAT 3 (Continuidad Operativa y Recuperación de Desastres 4-Capas `.sql.zst.age`):
   Simulacro automatizado de recuperación (`FourLayerBackupOrchestrator.run_automated_restore_drill("tenant_pacifico_centro")`)
   restaurando quirúrgicamente 1 Tenant sin afectar a Tenants vecinos ni al esquema `public`.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from scripts.backup_manager import FourLayerBackupOrchestrator

from src.core.backup.crypto_stream import (
    assert_not_plaintext_sql,
    compress_and_encrypt_sql_dump,
)
from src.core.backup.protocol import build_backup_artifact_filename
from src.core.fx import (
    FxQuote,
    FXService,
    evaluate_fx_rate_drift,
    parse_bcch_mindicador_payload,
    parse_ecb_frankfurter_payload,
)
from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.i18n import (
    DynamicFieldTranslationSync,
    is_proper_noun_protected,
)
from src.core.security import create_access_token
from src.main import create_app

pytestmark = pytest.mark.uat


def test_uat_01_multi_branch_holding_owner_seat_release_and_decimal_financial_accuracy() -> None:
    """
    Escenario UAT 1 (`specs/01-PRD.md` §2.2 y §3.2):
    - Carlos (Propietario de Holding) opera transversalmente en el Restaurante (`tenant_rest_a`) y el Hotel
      (`tenant_hotel_b`) de su mismo Holding con una sola sesión, pero recibe HTTP 403 si intenta consultar
      una sucursal ajena (`tenant_external_c`).
    - Al desvincular a un trabajador (`soft-delete`), su sesión queda revocada y su asiento se libera en el acto.
    - Los cálculos gastronómicos mantienen exactitud `Decimal` sin desviación de punto flotante.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()
    app = create_app()

    owner_token = create_access_token(
        user_id=700,
        holding_id="holding_carlos_gastro",
        tenant_id="tenant_rest_a",
        hierarchy_rank=0,
        is_holding_owner=True,
        contracted_modules=["catalog", "recipes", "tenancy", "analytics", "settings"],
        role_grants=[
            "catalog.units.convert",
            "recipes.escandallos.write",
            "tenancy.quotas.read",
            "tenancy.storage_quotas.read",
            "analytics.executive_summary.read",
            "settings.users.soft_delete",
        ],
        accessible_tenants=["tenant_rest_a", "tenant_hotel_b"],
    )

    with TestClient(app) as client:
        # Operación en Sucursal 1: Restaurante (`tenant_rest_a`)
        rest_headers = {
            "Authorization": f"Bearer {owner_token}",
            "X-Tenant-ID": "tenant_rest_a",
        }
        conv_resp = client.post(
            "/api/v1/catalog/units/convert",
            headers=rest_headers,
            json={
                "cantidad_compra": "4",
                "costo_compra_neto": "72000",
                "factor_compra_a_almacen": "12",
                "factor_almacen_a_receta": "1000",
            },
        )
        assert conv_resp.status_code == 200
        assert Decimal(conv_resp.json()["costo_unitario_almacen"]) == Decimal("6000.0000")
        assert Decimal(conv_resp.json()["costo_unitario_receta"]) == Decimal("6.0000")

        # Operación en Sucursal 2 del mismo Holding: Hotel (`tenant_hotel_b`)
        hotel_headers = {
            "Authorization": f"Bearer {owner_token}",
            "X-Tenant-ID": "tenant_hotel_b",
        }
        exec_hotel = client.get("/api/v1/analytics/executive-summary", headers=hotel_headers)
        assert exec_hotel.status_code == 200
        assert isinstance(Decimal(exec_hotel.json()["theoretical_pct"]), Decimal)

        # Bloqueo estricto hacia Tenant de otro Holding (`tenant_external_c`) -> HTTP 403
        forbidden_resp = client.get(
            "/api/v1/analytics/executive-summary",
            headers={
                "Authorization": f"Bearer {owner_token}",
                "X-Tenant-ID": "tenant_external_c",
            },
        )
        assert forbidden_resp.status_code == 403
        assert forbidden_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

        # Soft-Delete de trabajador retirado (`user_id=799`) libera asiento y revoca sesión en el acto
        soft_del_resp = client.post(
            "/api/v1/identity/users/799/soft-delete",
            headers=rest_headers,
            json={"reason": "Fin de contrato temporada alta"},
        )
        assert soft_del_resp.status_code == 200
        del_data = soft_del_resp.json()
        assert del_data["is_deleted"] is True
        assert del_data["session_revoked"] is True
        assert del_data["seat_released"] is True


def test_uat_02_i18n_pollo_king_protection_and_fx_central_bank_triangulation() -> None:
    """
    Escenario UAT 2 (`specs/01-PRD.md` §1.2 y §5.3):
    - Protección `i18n` de nombres propios (`"Pollo King"`, `"Savory"`) sin gastar tokens ni alterar la marca.
    - Motor Multi-Moneda FX (`BCCh` + `BCE Frankfurter`) con precisión `Decimal(18, 8)`, triangulación entre
      `CLP`, `USD`, `EUR`, `BRL`, `UF` y escudo anti-anomalías (`> 8%`).
    """
    assert is_proper_noun_protected("Pollo King") is True
    assert is_proper_noun_protected("Savory") is True

    sync_engine = DynamicFieldTranslationSync()
    pollo_sync = sync_engine.sync_field(
        "Pollo King",
        source_lang="es",
        active_locales=("es", "en"),
        table_name="proveedores",
    )
    assert pollo_sync.proper_noun_protected is True
    assert pollo_sync.tokens_consumed == 0
    assert pollo_sync.i18n_data == {"es": "Pollo King", "en": "Pollo King"}

    savory_sync = sync_engine.sync_field(
        "Helado de Chocolate Savory",
        source_lang="es",
        active_locales=("es", "en"),
    )
    assert savory_sync.i18n_data["en"] == "Chocolate Ice Cream Savory"
    assert savory_sync.tokens_consumed < 35

    # Parsers institucionales BCCh y BCE Frankfurter en Decimal(18, 8)
    bcch_quotes = parse_bcch_mindicador_payload(
        {
            "dolar": {"valor": "950.00"},
            "euro": {"valor": "1035.50"},
            "uf": {"valor": "37950.00"},
        }
    )
    bcch_map = {q.currency_pair: q.rate for q in bcch_quotes}
    assert bcch_map["USD/CLP"] == Decimal("950.00000000")
    assert bcch_map["UF/CLP"] == Decimal("37950.00000000")

    ecb_quotes = parse_ecb_frankfurter_payload(
        {
            "base": "EUR",
            "rates": {"USD": "1.0900", "BRL": "6.1040"},
        }
    )
    ecb_map = {q.currency_pair: q.rate for q in ecb_quotes}
    assert ecb_map["EUR/USD"] == Decimal("1.09000000")
    assert ecb_map["EUR/BRL"] == Decimal("6.10400000")

    # Triangulación y Anomaly Guard (> 8%)
    fx = FXService(seed_default_rates=True)
    assert fx.convert_amount(Decimal("100.00"), "USD", "CLP") == Decimal("95000.00")
    assert fx.convert_amount(Decimal("95000.00"), "CLP", "BRL") == Decimal("560.00")
    assert fx.convert_amount(Decimal("1.00"), "UF", "USD") == Decimal("39.95")

    drift = evaluate_fx_rate_drift(
        "USD/CLP",
        Decimal("950.00000000"),
        Decimal("1100.00000000"),
    )
    assert drift.is_quarantined is True
    assert drift.action_taken == "FX_ANOMALY_QUARANTINED"

    anomalous_quote = FxQuote(
        base_currency="USD",
        quote_currency="CLP",
        rate=Decimal("1100.00000000"),
        source_provider="BCCH_OFFICIAL",
        effective_date=datetime.now(tz=UTC),
    )
    ingest_res = fx.ingest_automatic_quote(anomalous_quote)
    assert ingest_res.is_quarantined is True
    assert fx.get_exchange_rate("USD", "CLP") == Decimal("950.00000000")


def test_uat_03_four_layer_encrypted_backup_and_surgical_single_tenant_restore_drill() -> None:
    """
    Escenario UAT 3 (`specs/01-PRD.md` §2.1 y Regla 19):
    - Simulacro automatizado de recuperación de desastres en las 4 capas de respaldos cifrados (`.sql.zst.age`)
      mediante `FourLayerBackupOrchestrator.run_automated_restore_drill("tenant_pacifico_centro")`.
    - Verifica que restaurar quirúrgicamente `tenant_pacifico_centro` genere primero su snapshot de seguridad
      en la Capa 4 Local y deje 100% intactos a los Tenants vecinos y al esquema `public`.
    """
    orchestrator = FourLayerBackupOrchestrator()

    # 1. Simulacro automatizado completo sobre `tenant_pacifico_centro`
    drill_ok = orchestrator.run_automated_restore_drill("tenant_pacifico_centro")
    assert drill_ok is True

    # 2. Verificación explícita de artefactos `.sql.zst.age` en las 4 capas y aislamiento de vecinos
    manifests = orchestrator.backup_scope(
        "tenant_pacifico_centro",
        raw_sql_lines=(
            "-- ROW: kardex_mov_101",
            "-- ROW: kardex_mov_102",
            "-- ROW: recipe_escandallo_201",
        ),
    )
    assert len(manifests) == 3
    for manifest in manifests:
        assert manifest.artifact_filename.endswith(".sql.zst.age")

    pulled_local = orchestrator.pull_r2_to_local_office()
    assert len(pulled_local) >= 1

    sql_dump = (
        b'SET LOCAL search_path TO "tenant_pacifico_centro";\n'
        b"-- ROW: restored_prod_1\n"
        b"-- ROW: restored_prod_2\n"
    )
    encrypted_payload, sha256_hex = compress_and_encrypt_sql_dump(
        sql_dump,
        orchestrator.public_key,
    )
    assert_not_plaintext_sql(encrypted_payload)
    assert build_backup_artifact_filename("tenant_pacifico_centro").endswith(".sql.zst.age")

    cluster_state: dict[str, dict[str, list[dict[str, object]]]] = {
        "public": {"holdings": [{"id": "holding_pacifico"}]},
        "tenant_pacifico_centro": {"restored_items": [{"raw": "corrupted_row"}]},
        "tenant_vecino_norte": {"restored_items": [{"raw": "intact_neighbor_data"}]},
    }
    restore_report = orchestrator.restore_engine.restore_single_tenant(
        cluster_state=cluster_state,
        target_tenant_schema="tenant_pacifico_centro",
        encrypted_backup=encrypted_payload,
        expected_sha256=sha256_hex,
        safety_layer=orchestrator.layer4_local,
    )
    assert restore_report.restored_tenant_schema == "tenant_pacifico_centro"
    assert restore_report.restored_rows_count == 2
    assert "tenant_vecino_norte" in restore_report.untouched_schemas
    assert "public" in restore_report.untouched_schemas
    assert cluster_state["tenant_vecino_norte"] == {
        "restored_items": [{"raw": "intact_neighbor_data"}]
    }
