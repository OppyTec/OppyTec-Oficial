"""
oppytec-backend/src/modules/oppy_ai/domain/ports.py
Puertos de Dominio (Protocols) para Evaluación Sistemática (Evals) y Observabilidad LLM.

Define las abstracciones requeridas por la arquitectura limpia para:
- `LLMTracerPort`: Interfaz de telemetría especializada (Langfuse / OpenTelemetry).
- `LLMEvalSuitePort`: Interfaz para corridas de suites de evaluación y benchmarks.
- `AIChatFeedbackRepositoryPort`: Repositorio para persistencia y consulta de feedback RLHF.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from src.modules.oppy_ai.domain.evals import (
    AIChatFeedback,
    AIEvalBenchmark,
    AIEvalCaseResult,
    EvalMetricThresholds,
    TraceContext,
)


@runtime_checkable
class LLMTracerPort(Protocol):
    """
    Puerto para la instrumentación y exportación de trazas especializadas de LLM (Langfuse / Tempo).
    Garantiza el desacoplamiento total de clientes o SDKs propietarios de telemetría.
    """

    async def trace_generation(
        self,
        context: TraceContext,
        model: str,
        prompt: str,
        completion: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: Decimal,
        latency_ms: int,
        tags: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Registra una generación de LLM y retorna el identificador de span/trace."""
        ...

    async def trace_tool_call(
        self,
        context: TraceContext,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: dict[str, Any],
        latency_ms: int,
        error: str | None = None,
    ) -> str:
        """Registra la ejecución de una herramienta operativa (tool calling) dentro del span."""
        ...

    async def record_feedback(
        self,
        feedback: AIChatFeedback,
    ) -> bool:
        """Registra la puntuación o feedback humano asociado a un trace existente."""
        ...

    async def flush(self) -> None:
        """Fuerza la descarga del búfer en cola hacia el colector de trazas."""
        ...


@runtime_checkable
class LLMEvalSuitePort(Protocol):
    """
    Puerto para la ejecución de benchmarks y suites de evaluación de calidad (DeepEval / Ragas).
    """

    async def run_suite(
        self,
        suite_name: str,
        model_name: str,
        dataset_path_or_cases: list[dict[str, Any]] | str,
        thresholds: EvalMetricThresholds | None = None,
    ) -> AIEvalBenchmark:
        """Ejecuta una batería completa de casos de prueba y consolida el agregado de benchmark."""
        ...

    async def evaluate_case(
        self,
        case_id: str,
        prompt: str,
        expected_output: str,
        actual_output: str,
        retrieved_context: list[str],
        category: str = "general",
    ) -> AIEvalCaseResult:
        """Evalúa un único caso de prueba calculando fidelidad, relevancia y detección de alucinaciones."""
        ...


@runtime_checkable
class AIChatFeedbackRepositoryPort(Protocol):
    """
    Puerto de repositorio para la persistencia transaccional y consulta de feedback de usuarios.
    """

    async def save_feedback(self, feedback: AIChatFeedback) -> AIChatFeedback:
        """Persiste o actualiza un registro de feedback."""
        ...

    async def list_feedback(
        self,
        tenant_id: UUID,
        message_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AIChatFeedback]:
        """Obtiene una lista paginada de feedbacks para el tenant indicado."""
        ...

    async def get_by_trace_id(
        self,
        tenant_id: UUID,
        trace_id: str,
    ) -> list[AIChatFeedback]:
        """Obtiene feedbacks vinculados a un identificador de traza específico."""
        ...
