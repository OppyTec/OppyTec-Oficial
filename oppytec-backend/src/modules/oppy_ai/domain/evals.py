"""
oppytec-backend/src/modules/oppy_ai/domain/evals.py
Dominio Puro DDD de Evaluación Sistemática (Evals) y Observabilidad LLM para OppyFy v2.0.

Contiene:
- Value Objects: `EvalScore`, `EvalMetricThresholds`, `TraceContext`.
- Entidades y Agregados: `AIEvalBenchmark`, `AIEvalCaseResult`, `AIChatFeedback`.
- Excepciones de Dominio: `AIEvalDomainError`, `EvalThresholdNotMetError`, `InvalidFeedbackPayloadError`, `TracerConfigurationError`.

Reglas de Oro:
- 0 floats: uso estricto de `Decimal` en métricas, scores y costos.
- Independiente de infraestructura: sin dependencias a FastAPI, SQLAlchemy o SDKs propietarios.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import secrets
from typing import Any, Literal
from uuid import UUID, uuid4

FeedbackType = Literal["positive", "negative"]
FailureCategory = Literal["hallucination", "incomplete", "math_error", "bad_formatting", "other"]

VALID_FEEDBACK_TYPES: frozenset[str] = frozenset({"positive", "negative"})
VALID_FAILURE_CATEGORIES: frozenset[str] = frozenset(
    {"hallucination", "incomplete", "math_error", "bad_formatting", "other"}
)


# ---------------------------------------------------------------------------
# Excepciones de Dominio
# ---------------------------------------------------------------------------


class AIEvalDomainError(Exception):
    """Excepción base para violaciones de reglas de dominio en AI Evals y Observabilidad."""


class EvalThresholdNotMetError(AIEvalDomainError):
    """Excepción lanzada cuando una evaluación no alcanza los umbrales de calidad mínimos inviolables."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class InvalidFeedbackPayloadError(AIEvalDomainError):
    """Excepción lanzada cuando la estructura o contenido del feedback humano es inválido."""


class TracerConfigurationError(AIEvalDomainError):
    """Excepción lanzada ante configuraciones o identificadores de trazabilidad inválidos."""


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvalScore:
    """
    Wrapper inmutable de puntuación normalizada [0.00, 1.00] con tipo Decimal estricto.
    Prohíbe terminantemente valores de tipo float para garantizar exactitud determinista.
    """

    value: Decimal

    def __post_init__(self) -> None:
        if type(self.value).__name__ == "float":
            raise AIEvalDomainError("Floats are strictly forbidden in EvalScore; use Decimal or str.")
        if not isinstance(self.value, Decimal):
            try:
                converted = Decimal(str(self.value))
                object.__setattr__(self, "value", converted)
            except Exception as exc:
                raise AIEvalDomainError(f"Cannot convert {self.value!r} to Decimal in EvalScore: {exc}") from exc

        if self.value < Decimal("0.00") or self.value > Decimal("1.00"):
            raise AIEvalDomainError(
                f"EvalScore value must be between Decimal('0.00') and Decimal('1.00'), got {self.value}"
            )

    def to_decimal(self) -> Decimal:
        return self.value

    def __lt__(self, other: EvalScore | Decimal) -> bool:
        other_val = other.value if isinstance(other, EvalScore) else other
        return self.value < other_val

    def __le__(self, other: EvalScore | Decimal) -> bool:
        other_val = other.value if isinstance(other, EvalScore) else other
        return self.value <= other_val

    def __gt__(self, other: EvalScore | Decimal) -> bool:
        other_val = other.value if isinstance(other, EvalScore) else other
        return self.value > other_val

    def __ge__(self, other: EvalScore | Decimal) -> bool:
        other_val = other.value if isinstance(other, EvalScore) else other
        return self.value >= other_val

    def __eq__(self, other: object) -> bool:
        if isinstance(other, EvalScore):
            return self.value == other.value
        if isinstance(other, Decimal):
            return self.value == other
        return False

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class EvalMetricThresholds:
    """
    Encapsula los umbrales de calidad mínimos inviolables para los Quality Gates de OppyFy.
    - min_faithfulness: >= 0.85
    - min_relevance: >= 0.85
    - min_context_precision: >= 0.80
    - max_hallucination_rate: <= 0.05
    - max_critical_hallucination_rate: <= 0.00 (Tolerancia Cero en costos, alérgenos y stock FEFO)
    """

    min_faithfulness: Decimal = Decimal("0.85")
    min_relevance: Decimal = Decimal("0.85")
    min_context_precision: Decimal = Decimal("0.80")
    max_hallucination_rate: Decimal = Decimal("0.05")
    max_critical_hallucination_rate: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        for attr in (
            "min_faithfulness",
            "min_relevance",
            "min_context_precision",
            "max_hallucination_rate",
            "max_critical_hallucination_rate",
        ):
            val = getattr(self, attr)
            if type(val).__name__ == "float":
                raise AIEvalDomainError(f"Floats are strictly forbidden in EvalMetricThresholds.{attr}")
            if not isinstance(val, Decimal):
                object.__setattr__(self, attr, Decimal(str(val)))

    @staticmethod
    def _coerce_decimal(val: Decimal | EvalScore) -> Decimal:
        if isinstance(val, EvalScore):
            return val.value
        if type(val).__name__ == "float":
            raise AIEvalDomainError("Floats are strictly forbidden in metric evaluation; use Decimal.")
        if not isinstance(val, Decimal):
            return Decimal(str(val))
        return val

    def is_passing(
        self,
        faithfulness: Decimal | EvalScore,
        relevance: Decimal | EvalScore,
        context_precision: Decimal | EvalScore,
        hallucination: Decimal | EvalScore,
        critical_hallucination: Decimal | EvalScore = Decimal("0.00"),
    ) -> bool:
        """Determina de forma booleana y determinista si las métricas superan el Quality Gate."""
        f = self._coerce_decimal(faithfulness)
        r = self._coerce_decimal(relevance)
        cp = self._coerce_decimal(context_precision)
        h = self._coerce_decimal(hallucination)
        ch = self._coerce_decimal(critical_hallucination)

        return (
            f >= self.min_faithfulness
            and r >= self.min_relevance
            and cp >= self.min_context_precision
            and h <= self.max_hallucination_rate
            and ch <= self.max_critical_hallucination_rate
        )

    def validate_or_raise(
        self,
        faithfulness: Decimal | EvalScore,
        relevance: Decimal | EvalScore,
        context_precision: Decimal | EvalScore,
        hallucination: Decimal | EvalScore,
        critical_hallucination: Decimal | EvalScore = Decimal("0.00"),
    ) -> None:
        """Lanza `EvalThresholdNotMetError` detallando cada métrica que no cumplió el umbral."""
        f = self._coerce_decimal(faithfulness)
        r = self._coerce_decimal(relevance)
        cp = self._coerce_decimal(context_precision)
        h = self._coerce_decimal(hallucination)
        ch = self._coerce_decimal(critical_hallucination)

        failures: dict[str, dict[str, str]] = {}

        if f < self.min_faithfulness:
            failures["faithfulness"] = {"actual": str(f), "required_min": str(self.min_faithfulness)}
        if r < self.min_relevance:
            failures["relevance"] = {"actual": str(r), "required_min": str(self.min_relevance)}
        if cp < self.min_context_precision:
            failures["context_precision"] = {"actual": str(cp), "required_min": str(self.min_context_precision)}
        if h > self.max_hallucination_rate:
            failures["hallucination"] = {"actual": str(h), "required_max": str(self.max_hallucination_rate)}
        if ch > self.max_critical_hallucination_rate:
            failures["critical_hallucination"] = {
                "actual": str(ch),
                "required_max": str(self.max_critical_hallucination_rate),
            }

        if failures:
            msg = f"AI Eval Quality Gate failed: {len(failures)} threshold(s) not met."
            raise EvalThresholdNotMetError(msg, details=failures)


@dataclass(frozen=True)
class TraceContext:
    """
    Contexto inmutable de trazabilidad W3C distribuido (Langfuse + OpenTelemetry / Tempo).
    Permite correlación bidireccional mediante `traceparent`.
    """

    trace_id: str
    span_id: str
    tenant_id: UUID
    user_id: UUID | None = None
    tags: dict[str, str] = field(default_factory=dict)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.trace_id or not isinstance(self.trace_id, str):
            raise TracerConfigurationError("trace_id must be a non-empty string.")
        if not self.span_id or not isinstance(self.span_id, str):
            raise TracerConfigurationError("span_id must be a non-empty string.")
        if not isinstance(self.tenant_id, UUID):
            raise TracerConfigurationError(f"tenant_id must be a UUID instance, got {type(self.tenant_id)}")

    def w3c_traceparent(self) -> str:
        """Formatea el encabezado estándar W3C traceparent version 00."""
        return f"00-{self.trace_id}-{self.span_id}-01"

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        user_id: UUID | None = None,
        tags: dict[str, str] | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
    ) -> TraceContext:
        """Factory para generar un contexto con identificadores de 32 y 16 caracteres hexadecimales."""
        t_id = trace_id or secrets.token_hex(16)
        s_id = span_id or secrets.token_hex(8)
        return cls(
            trace_id=t_id,
            span_id=s_id,
            tenant_id=tenant_id,
            user_id=user_id,
            tags=tags or {},
        )


# ---------------------------------------------------------------------------
# Entidades y Agregados de Dominio
# ---------------------------------------------------------------------------


@dataclass
class AIEvalCaseResult:
    """
    Resultado individual de la evaluación de un caso específico del Golden Dataset.
    """

    benchmark_id: UUID
    case_id: str
    category: str
    prompt: str
    expected_output: str
    actual_output: str
    retrieved_context: list[str] = field(default_factory=list)
    faithfulness: Decimal = Decimal("0.00")
    relevance: Decimal = Decimal("0.00")
    context_precision: Decimal = Decimal("0.00")
    hallucination_detected: bool = False
    critical_hallucination: bool = False
    latency_ms: int = 0
    passed: bool = False
    id: UUID = field(default_factory=uuid4)
    error_message: str | None = None

    def __post_init__(self) -> None:
        for attr in ("faithfulness", "relevance", "context_precision"):
            val = getattr(self, attr)
            if type(val).__name__ == "float":
                raise AIEvalDomainError(f"Floats are strictly forbidden in AIEvalCaseResult.{attr}")
            if not isinstance(val, Decimal):
                setattr(self, attr, Decimal(str(val)))


@dataclass
class AIEvalBenchmark:
    """
    Agregado Raíz que representa una corrida de evaluación de OppyFy sobre un suite de pruebas.
    Calcula deterministamente promedios con `Decimal` y evalúa el cumplimiento de umbrales.
    """

    suite_name: str
    model_name: str
    id: UUID = field(default_factory=uuid4)
    total_cases: int = 0
    passed_cases: int = 0
    avg_faithfulness: Decimal = Decimal("0.0000")
    avg_relevance: Decimal = Decimal("0.0000")
    avg_context_precision: Decimal = Decimal("0.0000")
    avg_hallucination_rate: Decimal = Decimal("0.0000")
    avg_critical_hallucination_rate: Decimal = Decimal("0.0000")
    passed_thresholds: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    case_results: list[AIEvalCaseResult] = field(default_factory=list)

    def add_case_result(
        self,
        case: AIEvalCaseResult,
        thresholds: EvalMetricThresholds | None = None,
    ) -> None:
        """Añade un caso evaluado y recalcula métricas agregadas."""
        self.case_results.append(case)
        self.recalculate_aggregates(thresholds=thresholds)

    def recalculate_aggregates(
        self,
        thresholds: EvalMetricThresholds | None = None,
    ) -> None:
        """Recalcula métricas agregadas en precisión exacta Decimal."""
        if not self.case_results:
            self.total_cases = 0
            self.passed_cases = 0
            self.avg_faithfulness = Decimal("0.0000")
            self.avg_relevance = Decimal("0.0000")
            self.avg_context_precision = Decimal("0.0000")
            self.avg_hallucination_rate = Decimal("0.0000")
            self.avg_critical_hallucination_rate = Decimal("0.0000")
            self.passed_thresholds = False
            return

        active_thresholds = thresholds or EvalMetricThresholds()
        n = Decimal(len(self.case_results))
        self.total_cases = len(self.case_results)
        self.passed_cases = sum(1 for c in self.case_results if c.passed)

        sum_faith = sum(c.faithfulness for c in self.case_results)
        sum_rel = sum(c.relevance for c in self.case_results)
        sum_prec = sum(c.context_precision for c in self.case_results)
        sum_halluc = Decimal(sum(1 for c in self.case_results if c.hallucination_detected))
        sum_crit_halluc = Decimal(sum(1 for c in self.case_results if c.critical_hallucination))

        self.avg_faithfulness = (sum_faith / n).quantize(Decimal("0.0001"))
        self.avg_relevance = (sum_rel / n).quantize(Decimal("0.0001"))
        self.avg_context_precision = (sum_prec / n).quantize(Decimal("0.0001"))
        self.avg_hallucination_rate = (sum_halluc / n).quantize(Decimal("0.0001"))
        self.avg_critical_hallucination_rate = (sum_crit_halluc / n).quantize(Decimal("0.0001"))

        self.passed_thresholds = active_thresholds.is_passing(
            faithfulness=self.avg_faithfulness,
            relevance=self.avg_relevance,
            context_precision=self.avg_context_precision,
            hallucination=self.avg_hallucination_rate,
            critical_hallucination=self.avg_critical_hallucination_rate,
        )

    @property
    def pass_rate_percent(self) -> Decimal:
        """Porcentaje de casos aprobados (0.00% a 100.00%)."""
        if self.total_cases == 0:
            return Decimal("0.00")
        return (Decimal(self.passed_cases) / Decimal(self.total_cases) * Decimal("100.00")).quantize(
            Decimal("0.01")
        )


@dataclass
class AIChatFeedback:
    """
    Entidad de Feedback humano para RLHF y curaduría continua del Golden Dataset.
    Enlaza la interacción directa con el `trace_id` de Langfuse.
    """

    tenant_id: UUID
    message_id: str
    trace_id: str
    feedback_type: FeedbackType
    id: UUID = field(default_factory=uuid4)
    user_id: UUID | None = None
    failure_category: FailureCategory | None = None
    user_correction: str | None = None
    rating: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.feedback_type not in VALID_FEEDBACK_TYPES:
            raise InvalidFeedbackPayloadError(
                f"feedback_type must be one of {sorted(VALID_FEEDBACK_TYPES)}, got {self.feedback_type!r}"
            )

        if self.feedback_type == "positive":
            if self.failure_category is not None:
                raise InvalidFeedbackPayloadError(
                    "failure_category cannot be provided when feedback_type is 'positive'."
                )
        elif self.feedback_type == "negative":
            if self.failure_category is not None and self.failure_category not in VALID_FAILURE_CATEGORIES:
                raise InvalidFeedbackPayloadError(
                    f"failure_category must be one of {sorted(VALID_FAILURE_CATEGORIES)}, got {self.failure_category!r}"
                )

        if self.rating is not None and not isinstance(self.rating, int):
            raise InvalidFeedbackPayloadError(f"rating must be an integer, got {type(self.rating).__name__}")
