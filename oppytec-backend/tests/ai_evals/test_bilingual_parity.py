"""
oppytec-backend/tests/ai_evals/test_bilingual_parity.py
Suite de Pruebas de Paridad Bilingüe, Regla "Pollo King", i18n y Multi-Moneda FX.

Fase 6 del Plan Maestro de Evals y Observabilidad LLM con Langfuse:
1. Paridad de 50 casos en Golden Dataset Gastronómico (ES vs EN).
2. Regla Inviolable: "Pollo King" y marcas registradas de clientes NUNCA se traducen (PROHIBIDO "King Chicken").
3. Paridad lingüística de tokens (ratio razonable ES/EN).
4. Multi-Moneda FX en telemetría de tokens (USD, CLP, EUR) 100% Decimal con tasas BCCh y BCE Frankfurter.
5. Auditoría de sincronización 100% de claves i18n en frontend (oppyfy.json).
"""
from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import pytest

from src.core.fx.fx_service import FXService
from src.modules.oppy_ai.application.metered_ai_service import (
    MeteredAIService,
    ModelConfigRegistry,
    DEFAULT_MODEL_TARIFFS,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASETS_DIR = Path(__file__).parent / "datasets"
ES_DATASET_PATH = DATASETS_DIR / "gastronomic_golden_dataset.json"
EN_DATASET_PATH = DATASETS_DIR / "gastronomic_golden_dataset_en.json"

FRONTEND_LOCALES_DIR = REPO_ROOT / "oppytec-frontend" / "src" / "shared" / "i18n" / "locales"
ES_OPPYFY_I18N = FRONTEND_LOCALES_DIR / "es" / "oppyfy.json"
EN_OPPYFY_I18N = FRONTEND_LOCALES_DIR / "en" / "oppyfy.json"

PROTECTED_BRANDS = ["Pollo King", "Cevichería Central"]
FORBIDDEN_TRANSLATIONS = ["King Chicken", "Chicken King", "Rey Pollo", "Central Ceviche"]


def _load_json(path: Path) -> Any:
    assert path.is_file(), f"El archivo requerido no existe: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _flatten_dict_keys(d: dict[str, Any], prefix: str = "") -> set[str]:
    keys = set()
    for k, v in d.items():
        curr = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys.update(_flatten_dict_keys(v, curr))
        else:
            keys.add(curr)
    return keys


# ----------------------------------------------------------------------
# 1. Paridad Estructural del Golden Dataset Gastronómico
# ----------------------------------------------------------------------

class TestGoldenDatasetStructuralParity:
    """Valida la integridad estructural 1:1 entre los datasets en español e inglés."""

    @pytest.fixture(scope="class")
    @classmethod
    def datasets(cls) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        es_data = _load_json(ES_DATASET_PATH)
        en_data = _load_json(EN_DATASET_PATH)
        return es_data, en_data

    def test_datasets_exist_and_have_exact_50_cases(
        self, datasets: tuple[list[dict[str, Any]], list[dict[str, Any]]]
    ) -> None:
        es_cases, en_cases = datasets
        assert len(es_cases) == 50, f"Se esperaban 50 casos en ES, se hallaron {len(es_cases)}"
        assert len(en_cases) == 50, f"Se esperaban 50 casos en EN, se hallaron {len(en_cases)}"

    def test_test_ids_match_in_exact_sequence(
        self, datasets: tuple[list[dict[str, Any]], list[dict[str, Any]]]
    ) -> None:
        es_cases, en_cases = datasets
        for idx, (es, en) in enumerate(zip(es_cases, en_cases), start=1):
            expected_id = f"EVAL-GASTRO-{idx:03d}"
            assert es["test_id"] == expected_id
            assert en["test_id"] == expected_id
            assert es["domain"] == en["domain"], f"Desajuste de dominio en {expected_id}"
            assert es["category"] == en["category"], f"Desajuste de categoría en {expected_id}"
            assert es["expected_tools"] == en["expected_tools"], f"Desajuste de herramientas en {expected_id}"
            assert es["evaluation_criteria"] == en["evaluation_criteria"], f"Desajuste de criterios en {expected_id}"

    def test_all_five_domains_have_exactly_10_cases(
        self, datasets: tuple[list[dict[str, Any]], list[dict[str, Any]]]
    ) -> None:
        es_cases, en_cases = datasets
        domains = ["banquetes", "mermas_costeo", "stock_fefo", "facturas_compras", "muro_fuego_seguridad"]
        for domain in domains:
            count_es = sum(1 for c in es_cases if c["domain"] == domain)
            count_en = sum(1 for c in en_cases if c["domain"] == domain)
            assert count_es == 10, f"El dominio {domain} tiene {count_es} casos en ES (requerido: 10)"
            assert count_en == 10, f"El dominio {domain} tiene {count_en} casos en EN (requerido: 10)"

    def test_required_fields_and_no_empty_strings(
        self, datasets: tuple[list[dict[str, Any]], list[dict[str, Any]]]
    ) -> None:
        es_cases, en_cases = datasets
        required_keys = {
            "test_id", "domain", "category", "prompt", "ground_truth",
            "expected_tools", "forbidden_content", "required_entities", "evaluation_criteria"
        }
        for dataset, lang in [(es_cases, "ES"), (en_cases, "EN")]:
            for case in dataset:
                assert required_keys.issubset(case.keys()), f"Faltan claves en caso {case.get('test_id')} ({lang})"
                assert len(case["prompt"].strip()) >= 20, f"Prompt muy corto en {case['test_id']} ({lang})"
                assert len(case["ground_truth"].strip()) >= 20, f"Ground truth muy corto en {case['test_id']} ({lang})"
                assert len(case["required_entities"]) >= 1, f"Sin required_entities en {case['test_id']} ({lang})"


# ----------------------------------------------------------------------
# 2. Regla Inviolable "Pollo King" y Marcas Comerciales
# ----------------------------------------------------------------------

class TestProtectedBrandInvariance:
    """Verifica que marcas comerciales ("Pollo King", "Cevichería Central") NUNCA se traduzcan."""

    def test_no_forbidden_translations_in_datasets(self) -> None:
        en_raw = EN_DATASET_PATH.read_text(encoding="utf-8")
        es_raw = ES_DATASET_PATH.read_text(encoding="utf-8")

        for forbidden in FORBIDDEN_TRANSLATIONS:
            assert forbidden.lower() not in en_raw.lower(), (
                f"VIOLACIÓN CRÍTICA: Traducción prohibida '{forbidden}' encontrada en dataset inglés!"
            )
            assert forbidden.lower() not in es_raw.lower(), (
                f"VIOLACIÓN CRÍTICA: Traducción prohibida '{forbidden}' encontrada en dataset español!"
            )

    def test_pollo_king_preservation_across_languages(self) -> None:
        es_cases = _load_json(ES_DATASET_PATH)
        en_cases = _load_json(EN_DATASET_PATH)

        for es, en in zip(es_cases, en_cases):
            for brand in PROTECTED_BRANDS:
                es_has_brand = brand in es["prompt"] or brand in es["ground_truth"]
                en_has_brand = brand in en["prompt"] or brand in en["ground_truth"]

                assert es_has_brand == en_has_brand, (
                    f"Inconsistencia de marca '{brand}' en caso {es['test_id']}: "
                    f"ES={es_has_brand}, EN={en_has_brand}. La marca debe conservarse en ambos idiomas."
                )

                if es_has_brand:
                    # Debe aparecer la marca textual exacta
                    assert brand in en["prompt"] or brand in en["ground_truth"], (
                        f"La marca '{brand}' no se encuentra en el caso inglés {en['test_id']}"
                    )

    def test_frontend_oppyfy_i18n_preserves_pollo_king(self) -> None:
        assert EN_OPPYFY_I18N.is_file(), f"Archivo faltante: {EN_OPPYFY_I18N}"
        en_raw = EN_OPPYFY_I18N.read_text(encoding="utf-8")

        for forbidden in FORBIDDEN_TRANSLATIONS:
            assert forbidden.lower() not in en_raw.lower(), (
                f"Traducción prohibida '{forbidden}' detectada en frontend locales/en/oppyfy.json"
            )

        assert "Pollo King" in en_raw, (
            "La marca inmutable 'Pollo King' debe aparecer en frontend locales/en/oppyfy.json"
        )


# ----------------------------------------------------------------------
# 3. Paridad Lingüística de Tokens y Longitud
# ----------------------------------------------------------------------

class TestBilingualTokenAndLengthParity:
    """Verifica que las versiones en inglés y español mantengan coherencia de tamaño y tokens."""

    def test_token_and_word_ratios_within_normal_multilingual_bounds(self) -> None:
        es_cases = _load_json(ES_DATASET_PATH)
        en_cases = _load_json(EN_DATASET_PATH)

        ratios_prompt: list[float] = []
        ratios_ground_truth: list[float] = []

        for es, en in zip(es_cases, en_cases):
            words_es_p = len(es["prompt"].split())
            words_en_p = len(en["prompt"].split())
            ratio_p = words_en_p / words_es_p
            ratios_prompt.append(ratio_p)

            words_es_gt = len(es["ground_truth"].split())
            words_en_gt = len(en["ground_truth"].split())
            ratio_gt = words_en_gt / words_es_gt
            ratios_ground_truth.append(ratio_gt)

            # Ratios caso a caso entre 0.60 y 1.45 (el inglés suele ser entre 10% y 20% más conciso)
            assert 0.60 <= ratio_p <= 1.45, (
                f"Ratio de longitud anómalo en prompt {es['test_id']}: {ratio_p:.2f} ({words_en_p}/{words_es_p})"
            )
            assert 0.60 <= ratio_gt <= 1.45, (
                f"Ratio de longitud anómalo en ground_truth {es['test_id']}: {ratio_gt:.2f} ({words_en_gt}/{words_es_gt})"
            )

        avg_prompt_ratio = sum(ratios_prompt) / len(ratios_prompt)
        avg_gt_ratio = sum(ratios_ground_truth) / len(ratios_ground_truth)

        # El promedio general debe estar entre 0.80 y 1.15
        assert 0.80 <= avg_prompt_ratio <= 1.15, f"Promedio ratio prompts fuera de rango: {avg_prompt_ratio:.2f}"
        assert 0.80 <= avg_gt_ratio <= 1.15, f"Promedio ratio ground truths fuera de rango: {avg_gt_ratio:.2f}"


# ----------------------------------------------------------------------
# 4. Multi-Moneda FX y Precisión Decimal en Telemetría de Tokens
# ----------------------------------------------------------------------

class TestMultiCurrencyFxTokenTelemetry:
    """Verifica que el cálculo y conversión de costos de tokens opere al 100% con Decimal y tasas oficiales."""

    def test_fx_service_institutional_defaults_precision(self) -> None:
        fx = FXService(seed_default_rates=True)

        usd_clp = fx.get_exchange_rate("USD", "CLP")
        eur_clp = fx.get_exchange_rate("EUR", "CLP")
        eur_usd = fx.get_exchange_rate("EUR", "USD")

        assert isinstance(usd_clp, Decimal)
        assert isinstance(eur_clp, Decimal)
        assert isinstance(eur_usd, Decimal)

        assert usd_clp == Decimal("950.00000000")
        assert eur_clp == Decimal("1035.50000000")
        assert eur_usd == Decimal("1.09000000")

    def test_token_cost_calculation_zero_floats(self) -> None:
        registry = ModelConfigRegistry()
        service = MeteredAIService(
            jev_port=None,  # type: ignore[arg-type]
            llm_port=None,  # type: ignore[arg-type]
            rag_service=None,  # type: ignore[arg-type]
            model_registry=registry,
        )

        cost_usd, cost_clp = service.calculate_token_cost(
            "gemini-3.8-flash",
            input_tokens=1500,
            cached_tokens=500,
            output_tokens=300,
        )

        assert isinstance(cost_usd, Decimal), "El costo en USD no es Decimal"
        assert isinstance(cost_clp, Decimal), "El costo en CLP no es Decimal"

        # Verificar cálculos matemáticos exactos:
        # Tarifas gemini-3.8-flash: input=$0.15/1M, cached=$0.0375/1M, output=$0.60/1M
        # input: 1500 * 0.15 / 1_000_000 = 0.000225
        # cached: 500 * 0.0375 / 1_000_000 = 0.00001875
        # output: 300 * 0.60 / 1_000_000 = 0.000180
        # total_usd = 0.00042375 -> redondeo a 6 decimales = 0.000424
        # clp = 0.000424 * 950 = 0.4028 -> redondeo a 2 decimales = 0.40
        assert cost_usd == Decimal("0.000424")
        assert cost_clp == Decimal("0.40")

    def test_multi_currency_triangulation_usd_clp_eur_without_loss(self) -> None:
        fx = FXService(seed_default_rates=True)

        token_cost_usd = Decimal("12.500000")

        # Conversión directa USD -> CLP
        cost_clp = fx.convert_amount(token_cost_usd, "USD", "CLP")
        expected_clp = (token_cost_usd * Decimal("950.00000000")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        assert cost_clp == expected_clp
        assert cost_clp == Decimal("11875.00")

        # Conversión directa USD -> EUR (vía inversa de EUR/USD = 1.09)
        cost_eur = fx.convert_amount(token_cost_usd, "USD", "EUR")
        expected_eur_rate = (Decimal("1") / Decimal("1.09000000")).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        expected_eur = (token_cost_usd * expected_eur_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        assert cost_eur == expected_eur
        assert cost_eur == Decimal("11.47")

        # Asegurar que ningún float se haya generado en las operaciones
        assert isinstance(cost_clp, Decimal)
        assert isinstance(cost_eur, Decimal)

    def test_claude_sonnet_high_context_fx_conversion(self) -> None:
        registry = ModelConfigRegistry()
        service = MeteredAIService(
            jev_port=None,  # type: ignore[arg-type]
            llm_port=None,  # type: ignore[arg-type]
            rag_service=None,  # type: ignore[arg-type]
            model_registry=registry,
        )

        # 50,000 input tokens, 20,000 cached tokens, 5,000 output tokens
        # claude-3-7-sonnet: in=3.00, cached=0.75, out=15.00
        cost_usd, cost_clp = service.calculate_token_cost(
            "claude-3-7-sonnet",
            input_tokens=50000,
            cached_tokens=20000,
            output_tokens=5000,
            usd_to_clp_rate=Decimal("960.00"),
        )

        # in: 50000 * 3 / 1M = 0.150000
        # cached: 20000 * 0.75 / 1M = 0.015000
        # out: 5000 * 15 / 1M = 0.075000
        # total_usd = 0.240000
        # total_clp = 0.240000 * 960 = 230.40
        assert cost_usd == Decimal("0.240000")
        assert cost_clp == Decimal("230.40")


# ----------------------------------------------------------------------
# 5. Auditoría de Sincronización i18n Frontend (oppyfy.json)
# ----------------------------------------------------------------------

class TestFrontendI18nSynchronization:
    """Audita que las claves i18n creadas en frontend estén sincronizadas al 100% sin omitir ninguna."""

    @pytest.fixture(scope="class")
    @classmethod
    def i18n_data(cls) -> tuple[dict[str, Any], dict[str, Any]]:
        es_data = _load_json(ES_OPPYFY_I18N)
        en_data = _load_json(EN_OPPYFY_I18N)
        return es_data, en_data

    def test_both_oppyfy_locales_exist(self) -> None:
        assert ES_OPPYFY_I18N.is_file(), f"Falta {ES_OPPYFY_I18N}"
        assert EN_OPPYFY_I18N.is_file(), f"Falta {EN_OPPYFY_I18N}"

    def test_complete_key_symmetry_100_percent(
        self, i18n_data: tuple[dict[str, Any], dict[str, Any]]
    ) -> None:
        es_dict, en_dict = i18n_data
        es_keys = _flatten_dict_keys(es_dict)
        en_keys = _flatten_dict_keys(en_dict)

        missing_in_en = es_keys - en_keys
        missing_in_es = en_keys - es_keys

        assert not missing_in_en, f"Claves faltantes en locales/en/oppyfy.json: {missing_in_en}"
        assert not missing_in_es, f"Claves sobrantes en locales/en/oppyfy.json: {missing_in_es}"
        assert es_keys == en_keys, "Las claves de internacionalización no son 100% simétricas"

    def test_feedback_categories_complete_and_localized(
        self, i18n_data: tuple[dict[str, Any], dict[str, Any]]
    ) -> None:
        es_dict, en_dict = i18n_data

        expected_categories = {"hallucination", "math_error", "incomplete", "bad_formatting", "other"}
        es_cats = es_dict.get("feedback", {}).get("categories", {})
        en_cats = en_dict.get("feedback", {}).get("categories", {})

        assert set(es_cats.keys()) == expected_categories
        assert set(en_cats.keys()) == expected_categories

        for cat in expected_categories:
            assert len(es_cats[cat].strip()) > 3
            assert len(en_cats[cat].strip()) > 3
            # Validar que no se hayan dejado textos idénticos en español en el archivo en inglés
            assert es_cats[cat] != en_cats[cat], f"Categoría {cat} sin traducir en inglés"

    def test_placeholder_interpolation_variables_parity(
        self, i18n_data: tuple[dict[str, Any], dict[str, Any]]
    ) -> None:
        es_dict, en_dict = i18n_data
        es_keys = _flatten_dict_keys(es_dict)

        import re
        placeholder_regex = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")

        def get_value(d: dict[str, Any], path: str) -> str:
            parts = path.split(".")
            val: Any = d
            for p in parts:
                val = val[p]
            return str(val)

        for key in es_keys:
            val_es = get_value(es_dict, key)
            val_en = get_value(en_dict, key)

            vars_es = set(placeholder_regex.findall(val_es))
            vars_en = set(placeholder_regex.findall(val_en))

            assert vars_es == vars_en, (
                f"Desajuste de variables de interpolación en '{key}': "
                f"ES tiene {vars_es}, EN tiene {vars_en}"
            )
