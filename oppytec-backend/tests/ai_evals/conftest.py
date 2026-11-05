"""
oppytec-backend/tests/ai_evals/conftest.py
Fixtures de Evaluación y Observabilidad LLM para la Suite de Evals de OppyFy v2.0.

Provee:
- `golden_dataset_path`: Ruta canónica hacia `gastronomic_golden_dataset.json`.
- `golden_dataset`: Diccionario parseado del dataset de 50 casos curados.
- `golden_cases`: Lista de casos individuales para parametrización exhaustiva.
- `eval_thresholds`: Instancia canónica de `EvalMetricThresholds` (Zero Floats con `Decimal`).
- Evaluadores tipados: `faithfulness_evaluator`, `relevance_evaluator`, `context_precision_evaluator`, `hallucination_evaluator`.
- `deterministic_oppyfy_responder`: Generador determinista de respuestas simuladas alineadas con el sistema.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

import pytest

from src.modules.oppy_ai.domain.evals import EvalMetricThresholds
from tests.ai_evals.metrics.custom_evaluators import (
    AnswerRelevanceEvaluator,
    ContextPrecisionEvaluator,
    FaithfulnessEvaluator,
    HallucinationEvaluator,
)


@pytest.fixture(scope="session")
def golden_dataset_path() -> Path:
    """Retorna la ruta absoluta hacia `gastronomic_golden_dataset.json`."""
    return Path(__file__).resolve().parent / "datasets" / "gastronomic_golden_dataset.json"


@pytest.fixture(scope="session")
def golden_dataset(golden_dataset_path: Path) -> list[dict[str, Any]] | dict[str, Any]:
    """Carga y valida el archivo JSON del Golden Dataset."""
    with golden_dataset_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    cases = data if isinstance(data, list) else data["cases"]
    assert len(cases) == 50, f"Expected 50 golden cases, got {len(cases)}"
    return data


@pytest.fixture(scope="session")
def golden_cases(golden_dataset: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    """Retorna la lista de los 50 casos gastronómicos curados."""
    return golden_dataset if isinstance(golden_dataset, list) else golden_dataset["cases"]


@pytest.fixture(scope="session")
def eval_thresholds() -> EvalMetricThresholds:
    """
    Retorna los umbrales de calidad de OppyFy según las directrices de arquitectura:
    - Faithfulness >= 0.85
    - Answer Relevance >= 0.85
    - Context Precision >= 0.80
    - Hallucination Rate <= 0.05
    - Critical Hallucination Rate <= 0.00 (Tolerancia Cero en alérgenos, costos y stock)
    """
    return EvalMetricThresholds(
        min_faithfulness=Decimal("0.85"),
        min_relevance=Decimal("0.85"),
        min_context_precision=Decimal("0.80"),
        max_hallucination_rate=Decimal("0.05"),
        max_critical_hallucination_rate=Decimal("0.00"),
    )


@pytest.fixture(scope="session")
def faithfulness_evaluator(eval_thresholds: EvalMetricThresholds) -> FaithfulnessEvaluator:
    return FaithfulnessEvaluator(eval_thresholds.min_faithfulness)


@pytest.fixture(scope="session")
def relevance_evaluator(eval_thresholds: EvalMetricThresholds) -> AnswerRelevanceEvaluator:
    return AnswerRelevanceEvaluator(eval_thresholds.min_relevance)


@pytest.fixture(scope="session")
def context_precision_evaluator(eval_thresholds: EvalMetricThresholds) -> ContextPrecisionEvaluator:
    return ContextPrecisionEvaluator(eval_thresholds.min_context_precision)


@pytest.fixture(scope="session")
def hallucination_evaluator(eval_thresholds: EvalMetricThresholds) -> HallucinationEvaluator:
    return HallucinationEvaluator(
        max_hallucination_rate=eval_thresholds.max_hallucination_rate,
        max_critical_rate=eval_thresholds.max_critical_hallucination_rate,
    )


@pytest.fixture
def deterministic_oppyfy_responder() -> Callable[[dict[str, Any]], str]:
    """
    Retorna una función que simula la respuesta de OppyFy para un caso de evaluación.
    Si el caso contiene entidades requeridas y ground_truth, genera una respuesta
    estrictamente grounded y con honestidad epistémica.
    """
    def _respond(case: dict[str, Any]) -> str:
        # En caso de rechazo del muro de fuego
        if case["domain"] in ("muro_de_fuego", "muro_fuego_seguridad") and case["category"] not in (
            "consultas_sistema_boveda1",
            "boveda_1_business",
        ):
            return case["ground_truth"]
        # En caso gastronómico / operativo
        return f"[OppyFy] Para '{case['prompt']}': {case['ground_truth']}"

    return _respond
