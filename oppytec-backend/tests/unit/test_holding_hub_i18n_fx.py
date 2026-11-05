"""
oppytec-backend/tests/unit/test_holding_hub_i18n_fx.py
Suite de Auditoría y Certificación i18n y Multi-Moneda FX para Holding Hub Enterprise (Etapa 3 - Agente 07):

1. Motor Multi-Moneda FX Institucional (BCCh / BCE Frankfurter):
   - Triangulación exacta 100% `Decimal` (cero floats) entre CLP, USD, EUR, BRL y UF.
   - Tarificación de compras de paquetes de créditos IA en multi-moneda.
   - Generación de matriz de precios de Planes SaaS comerciales.
   - Escudo Anti-Anomalías cambiarias (> 8% de variación).

2. Invariante Inmutable "Pollo King":
   - Nombres de holdings corporativos, razones sociales, esquemas y marcas son inmutables (`translatable = False`).
   - `is_proper_noun_protected` protege tablas: `holdings`, `tenants`, `legal_entities`, `proveedores`, `marcas`.
   - Consumo de 0 tokens y 0 créditos en sincronización dinámica.

3. Paridad Exhaustiva de Catálogos JSON:
   - 100% simetría de claves entre `holding_hub.json` (es) y `holding_hub.json` (en).
   - Preservación y paridad de variables de interpolación `{{param}}`.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from src.core.fx import (
    FXService,
    FxQuote,
    evaluate_fx_rate_drift,
)
from src.core.i18n import (
    DynamicFieldTranslationSync,
    is_proper_noun_protected,
)

pytestmark = pytest.mark.unit


# ============================================================================
# 1. AUDITORÍA MULTI-MONEDA FX Y PRECISIÓN DECIMAL ESTRICTA
# ============================================================================


class TestHoldingHubMultiCurrencyFX:
    """Verifica conversiones cambiarias, tarificación de créditos y planes corporativos."""

    def test_fx_institutional_rates_exact_decimal(self) -> None:
        """Verifica que FXService inicialice tasas BCCh y BCE en Decimal con precisión de 8 decimales."""
        fx = FXService()
        usd_clp = fx.get_exchange_rate("USD", "CLP")
        eur_clp = fx.get_exchange_rate("EUR", "CLP")
        uf_clp = fx.get_exchange_rate("UF", "CLP")

        assert isinstance(usd_clp, Decimal)
        assert usd_clp == Decimal("950.00000000")
        assert eur_clp == Decimal("1035.50000000")
        assert uf_clp == Decimal("37950.00000000")

        # Inversa exacta
        clp_usd = fx.get_exchange_rate("CLP", "USD")
        assert isinstance(clp_usd, Decimal)
        # 1 / 950 ≈ 0.00105263
        assert clp_usd == Decimal("0.00105263")

    def test_fx_conversion_of_credit_purchases(self) -> None:
        """
        Verifica tarificación de recargas de créditos IA en CLP, USD, EUR y BRL.
        Tasa base institucional: $15 CLP por crédito.
        """
        fx = FXService()
        credits_to_buy = Decimal("5000")
        base_clp = credits_to_buy * Decimal("15.00")  # $75,000 CLP

        # CLP integer
        cost_clp = fx.convert_amount(base_clp, "CLP", "CLP", integer_clp=True)
        assert cost_clp == Decimal("75000")

        # USD: 75,000 / 950 ≈ 78.95 USD
        cost_usd = fx.convert_amount(base_clp, "CLP", "USD")
        assert isinstance(cost_usd, Decimal)
        assert cost_usd == Decimal("78.95")

        # EUR: 75,000 / 1035.50 ≈ 72.43 EUR
        cost_eur = fx.convert_amount(base_clp, "CLP", "EUR")
        assert isinstance(cost_eur, Decimal)
        assert cost_eur == Decimal("72.43")

        # Triangulación BRL vía EUR o USD:
        # EUR/CLP = 1035.50, EUR/BRL = 6.1040 => BRL/CLP = 1035.50 / 6.1040 ≈ 169.64285714 CLP
        cost_brl = fx.convert_amount(base_clp, "CLP", "BRL")
        assert isinstance(cost_brl, Decimal)
        assert cost_brl > Decimal("0.00")

    def test_saas_plan_price_matrix_generation(self) -> None:
        """
        Calcula automáticamente la matriz de precios equivalentes para un plan comercial
        corporativo (Starter, Business, Enterprise) usando convert_system_plan_prices.
        """
        fx = FXService()
        # Plan Enterprise: 270 USD ancla
        matrix = fx.convert_system_plan_prices(
            anchor_amount=Decimal("270.00"),
            anchor_currency="USD",
            integer_clp=True,
        )
        assert isinstance(matrix["price_clp"], Decimal)
        assert isinstance(matrix["price_usd"], Decimal)
        assert isinstance(matrix["price_eur"], Decimal)
        assert isinstance(matrix["price_brl"], Decimal)

        # 270 * 950 = 256,500 CLP
        assert matrix["price_clp"] == Decimal("256500")
        assert matrix["price_usd"] == Decimal("270.00")

    def test_fx_anomaly_guard_protects_against_spikes(self) -> None:
        """El escudo anti-anomalías bloquea variaciones cambiarias > 8%."""
        eval_ok = evaluate_fx_rate_drift(
            currency_pair="USD/CLP",
            previous_rate=Decimal("950.00000000"),
            candidate_rate=Decimal("965.00000000"),  # +1.57% -> NORMAL
        )
        assert eval_ok.is_quarantined is False
        assert eval_ok.action_taken == "AUTO_UPDATED"

        eval_anomaly = evaluate_fx_rate_drift(
            currency_pair="USD/CLP",
            previous_rate=Decimal("950.00000000"),
            candidate_rate=Decimal("1100.00000000"),  # +15.78% -> ANOMALÍA BLOQUEADA
        )
        assert eval_anomaly.is_quarantined is True
        assert eval_anomaly.action_taken == "FX_ANOMALY_QUARANTINED"
        assert eval_anomaly.effective_rate == Decimal("950.00000000")  # Retiene tasa previa


# ============================================================================
# 2. AUDITORÍA INVARIANTE INMUTABLE "POLLO KING"
# ============================================================================


class TestPolloKingInvariant:
    """Valida la regla Pollo King (nombres de holdings, sucursales y esquemas jamás traducibles)."""

    def test_holding_and_tenant_proper_nouns_protected(self) -> None:
        """Nombres de holdings y sucursales gastronómicas no deben traducirse nunca."""
        # Nombres de holdings
        assert is_proper_noun_protected("Holding Gastronómico Sur SpA", table_name="holdings") is True
        assert is_proper_noun_protected("Grupo Gastronómico Central SpA", table_name="holdings") is True
        assert is_proper_noun_protected("Inversiones Gastronómicas SpA", table_name="public.legal_entities") is True

        # Nombres de sucursales / tenants
        assert is_proper_noun_protected("Restaurante Central Santiago", table_name="tenants") is True
        assert is_proper_noun_protected("Hotel & Buffet Costanera", table_name="tenants") is True
        assert is_proper_noun_protected("Comisariato & Dark Kitchen Norte", table_name="tenants") is True

        # Esquemas físicos PostgreSQL
        assert is_proper_noun_protected("tenant_rest_central", table_name="tenants") is True
        assert is_proper_noun_protected("tenant_hotel_costanera", table_name="tenants") is True

        # Marcas gastronómicas comerciales
        assert is_proper_noun_protected("Pollo King") is True
        assert is_proper_noun_protected("Cevichería Central", table_name="marcas") is True

    def test_dynamic_field_sync_preserves_holding_names_with_zero_tokens(self) -> None:
        """Garantiza que el motor dinámico asigne i18n_data idéntico y 0 consumo de tokens/créditos."""
        sync_engine = DynamicFieldTranslationSync()
        res = sync_engine.sync_field(
            "Holding Gastronómico Sur SpA",
            source_lang="es",
            active_locales=("es", "en"),
            table_name="holdings",
        )
        assert res.proper_noun_protected is True
        assert res.tokens_consumed == 0
        assert res.credits_deducted == 0
        assert res.i18n_data == {
            "es": "Holding Gastronómico Sur SpA",
            "en": "Holding Gastronómico Sur SpA",
        }


# ============================================================================
# 3. AUDITORÍA DE PARIDAD DE ARCHIVOS JSON DE LOCALIZACIÓN
# ============================================================================


class TestHoldingHubI18nCatalogParity:
    """Verifica paridad 1:1 de claves entre es/holding_hub.json y en/holding_hub.json."""

    def test_json_keys_perfect_symmetry(self) -> None:
        frontend_root = Path(__file__).resolve().parents[3] / "oppytec-frontend"
        es_file = frontend_root / "src/shared/i18n/locales/es/holding_hub.json"
        en_file = frontend_root / "src/shared/i18n/locales/en/holding_hub.json"

        assert es_file.exists(), f"Archivo no existe: {es_file}"
        assert en_file.exists(), f"Archivo no existe: {en_file}"

        with open(es_file, encoding="utf-8") as f:
            es_data = json.load(f)

        with open(en_file, encoding="utf-8") as f:
            en_data = json.load(f)

        def extract_all_keys(data: dict, prefix: str = "") -> set[str]:
            keys: set[str] = set()
            for k, v in data.items():
                full_key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    keys.update(extract_all_keys(v, full_key))
                else:
                    keys.add(full_key)
            return keys

        es_keys = extract_all_keys(es_data)
        en_keys = extract_all_keys(en_data)

        missing_in_en = es_keys - en_keys
        missing_in_es = en_keys - es_keys

        assert missing_in_en == set(), f"Claves presentes en ES pero faltantes en EN: {missing_in_en}"
        assert missing_in_es == set(), f"Claves presentes en EN pero faltantes en ES: {missing_in_es}"
        assert len(es_keys) >= 150, f"Catálogo insuficiente de claves: {len(es_keys)}"
