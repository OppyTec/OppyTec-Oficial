"""
oppytec-backend/tests/unit/modules/test_oppy_ai_evals_domain.py
Pruebas Unitarias de Arquitectura DDD, Value Objects, Agregados y Contratos
del Dominio de AI Evals y Observabilidad LLM para OppyFy v2.0 (Etapa 1).
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.modules.oppy_ai.domain import (
    VALID_FAILURE_CATEGORIES,
    VALID_FEEDBACK_TYPES,
    AIChatFeedback,
    AIChatFeedbackRepositoryPort,
    AIEvalBenchmark,
    AIEvalCaseResult,
    AIEvalDomainError,
    EvalMetricThresholds,
    EvalScore,
    EvalThresholdNotMetError,
    InvalidFeedbackPayloadError,
    LLMEvalSuitePort,
    LLMTracerPort,
    TraceContext,
    TracerConfigurationError,
)

pytestmark = pytest.mark.unit


# ===========================================================================
# 1. Pruebas de Value Object: EvalScore
# ===========================================================================


def test_eval_score_valid_decimal_instantiation() -> None:
    """Verifica que EvalScore acepta instancias de Decimal dentro del rango [0.00, 1.00]."""
    score_zero = EvalScore(Decimal("0.00"))
    score_mid = EvalScore(Decimal("0.85"))
    score_one = EvalScore(Decimal("1.00"))

    assert score_zero.to_decimal() == Decimal("0.00")
    assert score_mid.to_decimal() == Decimal("0.85")
    assert score_one.to_decimal() == Decimal("1.00")
    assert str(score_mid) == "0.85"


def test_eval_score_string_coercion() -> None:
    """Verifica que EvalScore coacciona strings numéricos a Decimal de forma exacta."""
    score = EvalScore("0.92")  # type: ignore[arg-type]
    assert score.to_decimal() == Decimal("0.92")


def test_eval_score_rejects_floats() -> None:
    """Verifica la regla inmutable: PROHIBIDO el uso de floats en scores de evaluación."""
    with pytest.raises(AIEvalDomainError, match="Floats are strictly forbidden"):
        EvalScore(0.85)  # type: ignore[arg-type]


def test_eval_score_out_of_bounds() -> None:
    """Verifica que EvalScore rechaza valores menores a 0.00 o mayores a 1.00."""
    with pytest.raises(AIEvalDomainError, match="must be between"):
        EvalScore(Decimal("-0.01"))

    with pytest.raises(AIEvalDomainError, match="must be between"):
        EvalScore(Decimal("1.01"))


def test_eval_score_comparisons() -> None:
    """Verifica los operadores de ordenación y comparación en EvalScore."""
    s1 = EvalScore(Decimal("0.80"))
    s2 = EvalScore(Decimal("0.85"))
    s3 = EvalScore(Decimal("0.85"))

    assert s1 < s2
    assert s1 <= s2
    assert s2 > s1
    assert s2 >= s1
    assert s2 == s3
    assert s1 != s2
    assert s2 == Decimal("0.85")
    assert s1 < Decimal("0.85")


# ===========================================================================
# 2. Pruebas de Value Object: EvalMetricThresholds
# ===========================================================================


def test_eval_metric_thresholds_defaults() -> None:
    """Verifica los umbrales estándar de la industria definidos en el Plan Maestro."""
    thresholds = EvalMetricThresholds()
    assert thresholds.min_faithfulness == Decimal("0.85")
    assert thresholds.min_relevance == Decimal("0.85")
    assert thresholds.min_context_precision == Decimal("0.80")
    assert thresholds.max_hallucination_rate == Decimal("0.05")
    assert thresholds.max_critical_hallucination_rate == Decimal("0.00")


def test_eval_metric_thresholds_rejects_floats() -> None:
    """Verifica que EvalMetricThresholds rechaza inicialización con floats."""
    with pytest.raises(AIEvalDomainError, match="Floats are strictly forbidden"):
        EvalMetricThresholds(min_faithfulness=0.85)  # type: ignore[arg-type]


def test_eval_metric_thresholds_passing_case() -> None:
    """Verifica que una combinación óptima de métricas aprueba el Quality Gate."""
    thresholds = EvalMetricThresholds()
    passed = thresholds.is_passing(
        faithfulness=Decimal("0.90"),
        relevance=Decimal("0.88"),
        context_precision=Decimal("0.82"),
        hallucination=Decimal("0.02"),
        critical_hallucination=Decimal("0.00"),
    )
    assert passed is True


def test_eval_metric_thresholds_failing_faithfulness() -> None:
    """Verifica que fidelidad < 0.85 falla el gate."""
    thresholds = EvalMetricThresholds()
    passed = thresholds.is_passing(
        faithfulness=Decimal("0.84"),  # < 0.85
        relevance=Decimal("0.90"),
        context_precision=Decimal("0.85"),
        hallucination=Decimal("0.01"),
        critical_hallucination=Decimal("0.00"),
    )
    assert passed is False


def test_eval_metric_thresholds_failing_relevance() -> None:
    """Verifica que relevancia < 0.85 falla el gate."""
    thresholds = EvalMetricThresholds()
    passed = thresholds.is_passing(
        faithfulness=Decimal("0.90"),
        relevance=Decimal("0.8499"),  # < 0.85
        context_precision=Decimal("0.85"),
        hallucination=Decimal("0.01"),
        critical_hallucination=Decimal("0.00"),
    )
    assert passed is False


def test_eval_metric_thresholds_failing_context_precision() -> None:
    """Verifica que precisión de contexto < 0.80 falla el gate."""
    thresholds = EvalMetricThresholds()
    passed = thresholds.is_passing(
        faithfulness=Decimal("0.90"),
        relevance=Decimal("0.90"),
        context_precision=Decimal("0.79"),  # < 0.80
        hallucination=Decimal("0.01"),
        critical_hallucination=Decimal("0.00"),
    )
    assert passed is False


def test_eval_metric_thresholds_failing_hallucination_rate() -> None:
    """Verifica que tasa de alucinación general > 0.05 falla el gate."""
    thresholds = EvalMetricThresholds()
    passed = thresholds.is_passing(
        faithfulness=Decimal("0.90"),
        relevance=Decimal("0.90"),
        context_precision=Decimal("0.85"),
        hallucination=Decimal("0.0501"),  # > 0.05
        critical_hallucination=Decimal("0.00"),
    )
    assert passed is False


def test_eval_metric_thresholds_zero_tolerance_critical_hallucination() -> None:
    """Verifica que CUALQUIER alucinación crítica en costos/alérgenos/stock (> 0.00) falla de inmediato."""
    thresholds = EvalMetricThresholds()
    passed = thresholds.is_passing(
        faithfulness=Decimal("0.99"),
        relevance=Decimal("0.99"),
        context_precision=Decimal("0.95"),
        hallucination=Decimal("0.01"),
        critical_hallucination=Decimal("0.0001"),  # Inadmisible en dominio gastronómico
    )
    assert passed is False


def test_eval_metric_thresholds_validate_or_raise_success() -> None:
    """Verifica que validate_or_raise no levanta excepción si todo está en norma."""
    thresholds = EvalMetricThresholds()
    # No debe lanzar excepción
    thresholds.validate_or_raise(
        faithfulness=Decimal("0.92"),
        relevance=Decimal("0.89"),
        context_precision=Decimal("0.85"),
        hallucination=Decimal("0.03"),
        critical_hallucination=Decimal("0.00"),
    )


def test_eval_metric_thresholds_validate_or_raise_failure_details() -> None:
    """Verifica que validate_or_raise levanta EvalThresholdNotMetError con el mapa de fallas."""
    thresholds = EvalMetricThresholds()
    with pytest.raises(EvalThresholdNotMetError) as exc_info:
        thresholds.validate_or_raise(
            faithfulness=Decimal("0.80"),  # Falla
            relevance=Decimal("0.75"),     # Falla
            context_precision=Decimal("0.85"),
            hallucination=Decimal("0.08"),  # Falla
            critical_hallucination=Decimal("0.02"),  # Falla
        )

    err = exc_info.value
    assert "AI Eval Quality Gate failed" in str(err)
    assert "faithfulness" in err.details
    assert "relevance" in err.details
    assert "hallucination" in err.details
    assert "critical_hallucination" in err.details
    assert "context_precision" not in err.details


# ===========================================================================
# 3. Pruebas de Value Object: TraceContext
# ===========================================================================


def test_trace_context_factory_and_w3c_header() -> None:
    """Verifica la generación de TraceContext y la serialización al estándar W3C traceparent."""
    tenant_id = uuid4()
    user_id = uuid4()

    ctx = TraceContext.create(
        tenant_id=tenant_id,
        user_id=user_id,
        tags={"environment": "production", "channel": "web_chat"},
    )

    assert len(ctx.trace_id) == 32
    assert len(ctx.span_id) == 16
    assert ctx.tenant_id == tenant_id
    assert ctx.user_id == user_id
    assert ctx.tags["environment"] == "production"

    header = ctx.w3c_traceparent()
    assert header.startswith("00-")
    assert header.endswith("-01")
    assert f"-{ctx.trace_id}-{ctx.span_id}-" in header


def test_trace_context_validation() -> None:
    """Verifica que TraceContext requiere tipos correctos."""
    with pytest.raises(TracerConfigurationError, match="trace_id must be a non-empty string"):
        TraceContext(trace_id="", span_id="span123", tenant_id=uuid4())

    with pytest.raises(TracerConfigurationError, match="span_id must be a non-empty string"):
        TraceContext(trace_id="trace123", span_id="", tenant_id=uuid4())

    with pytest.raises(TracerConfigurationError, match="tenant_id must be a UUID instance"):
        TraceContext(trace_id="trace123", span_id="span123", tenant_id="not-a-uuid")  # type: ignore[arg-type]


# ===========================================================================
# 4. Pruebas del Agregado Raíz: AIEvalBenchmark y Casos AIEvalCaseResult
# ===========================================================================


def test_ai_eval_case_result_creation_and_float_rejection() -> None:
    """Verifica la creación de AIEvalCaseResult y el rechazo estricto de floats."""
    benchmark_id = uuid4()
    case = AIEvalCaseResult(
        benchmark_id=benchmark_id,
        case_id="case_banquets_01",
        category="banquets",
        prompt="Escalar risotto para 120 pax",
        expected_output="12 kg arroz arborio",
        actual_output="12 kg arroz arborio",
        retrieved_context=["Receta base Risotto 10 pax: 1.0 kg arroz"],
        faithfulness=Decimal("0.95"),
        relevance=Decimal("0.92"),
        context_precision=Decimal("0.88"),
        hallucination_detected=False,
        critical_hallucination=False,
        latency_ms=450,
        passed=True,
    )

    assert case.benchmark_id == benchmark_id
    assert case.case_id == "case_banquets_01"
    assert case.passed is True
    assert isinstance(case.id, UUID)

    with pytest.raises(AIEvalDomainError, match="Floats are strictly forbidden"):
        AIEvalCaseResult(
            benchmark_id=benchmark_id,
            case_id="case_invalid",
            category="costing",
            prompt="costo plato",
            expected_output="1000",
            actual_output="1000",
            faithfulness=0.95,  # type: ignore[arg-type]
        )


def test_ai_eval_benchmark_aggregation_and_pass_rate() -> None:
    """Verifica el cálculo de promedios exactos y pass rate percent en AIEvalBenchmark."""
    benchmark = AIEvalBenchmark(
        suite_name="gastronomic_golden_dataset_v1",
        model_name="gemini-1.5-pro",
    )

    assert benchmark.total_cases == 0
    assert benchmark.pass_rate_percent == Decimal("0.00")
    assert benchmark.passed_thresholds is False

    # Caso 1: Aprobado impecable
    case1 = AIEvalCaseResult(
        benchmark_id=benchmark.id,
        case_id="c1",
        category="allergens",
        prompt="¿Contiene gluten?",
        expected_output="No contiene",
        actual_output="No contiene",
        faithfulness=Decimal("1.00"),
        relevance=Decimal("0.95"),
        context_precision=Decimal("0.90"),
        hallucination_detected=False,
        critical_hallucination=False,
        passed=True,
    )

    # Caso 2: Aprobado aceptable
    case2 = AIEvalCaseResult(
        benchmark_id=benchmark.id,
        case_id="c2",
        category="fefo_stock",
        prompt="¿Qué lote usar?",
        expected_output="Lote 104",
        actual_output="Lote 104",
        faithfulness=Decimal("0.90"),
        relevance=Decimal("0.85"),
        context_precision=Decimal("0.80"),
        hallucination_detected=False,
        critical_hallucination=False,
        passed=True,
    )

    benchmark.add_case_result(case1)
    benchmark.add_case_result(case2)

    assert benchmark.total_cases == 2
    assert benchmark.passed_cases == 2
    assert benchmark.pass_rate_percent == Decimal("100.00")
    # Promedios:
    # Faithfulness: (1.00 + 0.90) / 2 = 0.9500
    assert benchmark.avg_faithfulness == Decimal("0.9500")
    # Relevance: (0.95 + 0.85) / 2 = 0.9000
    assert benchmark.avg_relevance == Decimal("0.9000")
    # Context Precision: (0.90 + 0.80) / 2 = 0.8500
    assert benchmark.avg_context_precision == Decimal("0.8500")
    assert benchmark.avg_hallucination_rate == Decimal("0.0000")
    assert benchmark.avg_critical_hallucination_rate == Decimal("0.0000")
    assert benchmark.passed_thresholds is True


def test_ai_eval_benchmark_detects_threshold_failure_on_critical_hallucination() -> None:
    """Verifica que si un caso presenta alucinación crítica en alérgenos, el benchmark entero reprueba el gate."""
    benchmark = AIEvalBenchmark(
        suite_name="gastronomic_golden_dataset_v1",
        model_name="gemini-1.5-flash",
    )

    # Caso 1: OK
    benchmark.add_case_result(
        AIEvalCaseResult(
            benchmark_id=benchmark.id,
            case_id="c1",
            category="costing",
            prompt="Costo receta",
            expected_output="$5.000",
            actual_output="$5.000",
            faithfulness=Decimal("0.90"),
            relevance=Decimal("0.90"),
            context_precision=Decimal("0.85"),
            passed=True,
        )
    )

    # Caso 2: Alucinación crítica detectada en alérgenos (ej: inventó que no tenía maní)
    benchmark.add_case_result(
        AIEvalCaseResult(
            benchmark_id=benchmark.id,
            case_id="c2",
            category="allergens",
            prompt="¿Tiene frutos secos?",
            expected_output="Sí, almendras",
            actual_output="No tiene",
            faithfulness=Decimal("0.40"),
            relevance=Decimal("0.70"),
            context_precision=Decimal("0.60"),
            hallucination_detected=True,
            critical_hallucination=True,
            passed=False,
        )
    )

    assert benchmark.total_cases == 2
    assert benchmark.passed_cases == 1
    assert benchmark.pass_rate_percent == Decimal("50.00")
    assert benchmark.avg_critical_hallucination_rate > Decimal("0.00")
    assert benchmark.passed_thresholds is False


# ===========================================================================
# 5. Pruebas de Entidad: AIChatFeedback (RLHF)
# ===========================================================================


def test_ai_chat_feedback_positive_valid() -> None:
    """Verifica que el feedback positivo es válido y no debe contener categoría de falla."""
    tenant_id = uuid4()
    feedback = AIChatFeedback(
        tenant_id=tenant_id,
        message_id="msg_abc123",
        trace_id="trace_xyz789",
        feedback_type="positive",
        rating=1,
    )

    assert feedback.feedback_type == "positive"
    assert feedback.failure_category is None
    assert feedback.rating == 1
    assert isinstance(feedback.created_at, datetime)


def test_ai_chat_feedback_positive_rejects_failure_category() -> None:
    """Verifica que no se puede adjuntar failure_category si el feedback es positivo."""
    with pytest.raises(InvalidFeedbackPayloadError, match="failure_category cannot be provided"):
        AIChatFeedback(
            tenant_id=uuid4(),
            message_id="msg_1",
            trace_id="tr_1",
            feedback_type="positive",
            failure_category="hallucination",
        )


def test_ai_chat_feedback_negative_with_valid_categories() -> None:
    """Verifica que el feedback negativo acepta todas las categorías canónicas de fallo."""
    tenant_id = uuid4()

    for category in VALID_FAILURE_CATEGORIES:
        fb = AIChatFeedback(
            tenant_id=tenant_id,
            message_id=f"msg_{category}",
            trace_id="trace_001",
            feedback_type="negative",
            failure_category=category,  # type: ignore[arg-type]
            user_correction="La receta real lleva 200g de mantequilla sin sal.",
            rating=-1,
        )
        assert fb.failure_category == category
        assert fb.user_correction is not None


def test_ai_chat_feedback_negative_rejects_invalid_category() -> None:
    """Verifica que el feedback negativo rechaza categorías fuera del vocabulario controlado."""
    with pytest.raises(InvalidFeedbackPayloadError, match="failure_category must be one of"):
        AIChatFeedback(
            tenant_id=uuid4(),
            message_id="msg_1",
            trace_id="tr_1",
            feedback_type="negative",
            failure_category="invented_category",  # type: ignore[arg-type]
        )


def test_ai_chat_feedback_rejects_invalid_feedback_type() -> None:
    """Verifica que feedback_type solo acepta 'positive' o 'negative'."""
    with pytest.raises(InvalidFeedbackPayloadError, match="feedback_type must be one of"):
        AIChatFeedback(
            tenant_id=uuid4(),
            message_id="msg_1",
            trace_id="tr_1",
            feedback_type="neutral",  # type: ignore[arg-type]
        )


def test_ai_chat_feedback_rejects_non_integer_rating() -> None:
    """Verifica que rating debe ser entero (evitando floats)."""
    with pytest.raises(InvalidFeedbackPayloadError, match="rating must be an integer"):
        AIChatFeedback(
            tenant_id=uuid4(),
            message_id="msg_1",
            trace_id="tr_1",
            feedback_type="positive",
            rating=4.5,  # type: ignore[arg-type]
        )


# ===========================================================================
# 6. Pruebas de Puertos de Arquitectura Limpia (Protocols)
# ===========================================================================


def test_domain_protocols_runtime_checkable() -> None:
    """Verifica que los puertos del dominio son Protocols verificables en runtime."""

    class DummyTracer:
        async def trace_generation(self, *args, **kwargs) -> str:
            return "span_1"

        async def trace_tool_call(self, *args, **kwargs) -> str:
            return "tool_1"

        async def record_feedback(self, *args, **kwargs) -> bool:
            return True

        async def flush(self) -> None:
            pass

    class DummyEvalSuite:
        async def run_suite(self, *args, **kwargs) -> AIEvalBenchmark:
            return AIEvalBenchmark(suite_name="dummy", model_name="dummy")

        async def evaluate_case(self, *args, **kwargs) -> AIEvalCaseResult:
            return AIEvalCaseResult(
                benchmark_id=uuid4(),
                case_id="d1",
                category="test",
                prompt="p",
                expected_output="e",
                actual_output="a",
            )

    class DummyFeedbackRepo:
        async def save_feedback(self, feedback: AIChatFeedback) -> AIChatFeedback:
            return feedback

        async def list_feedback(self, tenant_id: UUID, *args, **kwargs) -> list[AIChatFeedback]:
            return []

        async def get_by_trace_id(self, tenant_id: UUID, trace_id: str) -> list[AIChatFeedback]:
            return []

    assert isinstance(DummyTracer(), LLMTracerPort)
    assert isinstance(DummyEvalSuite(), LLMEvalSuitePort)
    assert isinstance(DummyFeedbackRepo(), AIChatFeedbackRepositoryPort)
