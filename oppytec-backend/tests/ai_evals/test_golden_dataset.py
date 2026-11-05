"""
oppytec-backend/tests/ai_evals/test_golden_dataset.py
Suite Principal de Evaluación Parametrizada sobre el Golden Dataset Gastronómico de OppyFy (50 Casos).

Verifica para cada caso:
1. Fidelidad (Faithfulness >= 0.85)
2. Relevancia de Respuesta (Answer Relevance >= 0.85, validando required_entities)
3. Precisión de Contexto (Context Precision >= 0.80)
4. Tasa de Alucinación (Hallucination Rate <= 0.05)
5. Tasa Crítica de Alucinación (Critical Hallucination Rate == 0.00 en alérgenos, costos y stock)
6. Ausencia total de contenido prohibido (código interno, cross-tenant, fórmulas incorrectas)
7. Inmutabilidad de la marca comercial 'Pollo King'.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

import pytest

from src.modules.oppy_ai.domain.evals import EvalMetricThresholds, EvalScore
from tests.ai_evals.metrics.custom_evaluators import run_all_evaluators

pytestmark = [pytest.mark.unit]

_DATASET_FILE = Path(__file__).resolve().parent / "datasets" / "gastronomic_golden_dataset.json"
with _DATASET_FILE.open("r", encoding="utf-8") as f:
    _DATA = json.load(f)
    ALL_CASES = _DATA if isinstance(_DATA, list) else _DATA["cases"]


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda c: f"{c['test_id']}_{c['domain']}")
def test_golden_dataset_case_quality_gates(
    case: dict[str, Any],
    eval_thresholds: EvalMetricThresholds,
    deterministic_oppyfy_responder: Callable[[dict[str, Any]], str],
) -> None:
    """
    Evalúa deterministamente cada uno de los 50 casos contra los 4 Quality Gates
    de DeepEval / Ragas adaptados para OppyTec con aritmética Decimal estricta.
    """
    test_id: str = case["test_id"]
    prompt: str = case["prompt"]
    ground_truth: str = case["ground_truth"]
    required_entities: list[str] = case["required_entities"]
    expected_tools: list[str] = case["expected_tools"]
    forbidden_content: list[str] = case.get("forbidden_content", [])
    is_critical: bool = case["is_critical"]

    # Generación de respuesta con el asistente OppyFy
    generated_answer = deterministic_oppyfy_responder(case)

    # Ejecución de los 4 evaluadores
    result = run_all_evaluators(
        test_id=test_id,
        prompt=prompt,
        generated_answer=generated_answer,
        ground_truth=ground_truth,
        required_entities=required_entities,
        expected_tools=expected_tools,
        forbidden_content=forbidden_content,
        is_critical=is_critical,
        thresholds=eval_thresholds,
    )

    # 1. Regla Inviolable: Cero Floats en scores
    assert isinstance(result.faithfulness.value, Decimal), f"Faithfulness must be Decimal, got {type(result.faithfulness.value)}"
    assert isinstance(result.answer_relevance.value, Decimal), f"Relevance must be Decimal, got {type(result.answer_relevance.value)}"
    assert isinstance(result.context_precision.value, Decimal), f"Context Precision must be Decimal, got {type(result.context_precision.value)}"
    assert isinstance(result.hallucination_rate.value, Decimal), f"Hallucination must be Decimal, got {type(result.hallucination_rate.value)}"
    assert isinstance(result.critical_hallucination_rate.value, Decimal), f"Critical Hallucination must be Decimal, got {type(result.critical_hallucination_rate.value)}"

    # 2. Criterios de Aceptación mínimos
    assert result.faithfulness >= eval_thresholds.min_faithfulness, (
        f"[{test_id}] Faithfulness failure: {result.faithfulness} < {eval_thresholds.min_faithfulness}. "
        f"Violations: {result.violations}"
    )
    assert result.answer_relevance >= eval_thresholds.min_relevance, (
        f"[{test_id}] Answer Relevance failure: {result.answer_relevance} < {eval_thresholds.min_relevance}. "
        f"Missing entities: {result.required_entities_missing}"
    )
    assert result.context_precision >= eval_thresholds.min_context_precision, (
        f"[{test_id}] Context Precision failure: {result.context_precision} < {eval_thresholds.min_context_precision}"
    )
    assert result.hallucination_rate <= eval_thresholds.max_hallucination_rate, (
        f"[{test_id}] Hallucination Rate exceeded: {result.hallucination_rate} > {eval_thresholds.max_hallucination_rate}"
    )

    # 3. Tolerancia Cero en casos críticos
    if is_critical:
        assert result.critical_hallucination_rate <= eval_thresholds.max_critical_hallucination_rate, (
            f"[{test_id}] Critical Hallucination Rate breach: {result.critical_hallucination_rate} > 0.00"
        )

    # 4. Verificación de Contenido Prohibido
    assert len(result.forbidden_content_detected) == 0, (
        f"[{test_id}] Forbidden content leaked: {result.forbidden_content_detected}"
    )

    # 5. Inmutabilidad de 'Pollo King'
    if "Pollo King" in prompt or "Pollo King" in ground_truth:
        assert "Pollo King" in generated_answer, (
            f"[{test_id}] Invariant violation: 'Pollo King' brand must be preserved in answers."
        )


def test_golden_dataset_macro_metrics_summary(
    eval_thresholds: EvalMetricThresholds,
    deterministic_oppyfy_responder: Callable[[dict[str, Any]], str],
) -> None:
    """
    Verifica que el promedio macro de todas las evaluaciones del dataset completo
    supere con holgura los SLAs requeridos (Faithfulness >= 0.90, Relevance >= 0.90).
    """
    total = Decimal(len(ALL_CASES))
    sum_faithfulness = Decimal("0.00")
    sum_relevance = Decimal("0.00")
    sum_context_precision = Decimal("0.00")
    sum_hallucination = Decimal("0.00")

    for case in ALL_CASES:
        answer = deterministic_oppyfy_responder(case)
        result = run_all_evaluators(
            test_id=case["test_id"],
            prompt=case["prompt"],
            generated_answer=answer,
            ground_truth=case["ground_truth"],
            required_entities=case["required_entities"],
            expected_tools=case["expected_tools"],
            forbidden_content=case.get("forbidden_content", []),
            is_critical=case["is_critical"],
            thresholds=eval_thresholds,
        )
        assert result.is_passing is True, f"Case {case['test_id']} failed: {result.violations}"
        sum_faithfulness += result.faithfulness.to_decimal()
        sum_relevance += result.answer_relevance.to_decimal()
        sum_context_precision += result.context_precision.to_decimal()
        sum_hallucination += result.hallucination_rate.to_decimal()

    macro_faithfulness = (sum_faithfulness / total).quantize(Decimal("0.01"))
    macro_relevance = (sum_relevance / total).quantize(Decimal("0.01"))
    macro_precision = (sum_context_precision / total).quantize(Decimal("0.01"))
    macro_hallucination = (sum_hallucination / total).quantize(Decimal("0.01"))

    assert macro_faithfulness >= Decimal("0.90"), f"Macro faithfulness too low: {macro_faithfulness}"
    assert macro_relevance >= Decimal("0.90"), f"Macro relevance too low: {macro_relevance}"
    assert macro_precision >= Decimal("0.85"), f"Macro precision too low: {macro_precision}"
    assert macro_hallucination <= Decimal("0.02"), f"Macro hallucination too high: {macro_hallucination}"
