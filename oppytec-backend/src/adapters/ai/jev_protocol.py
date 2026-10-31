"""
Protocolo del Motor Global de Decisiones `JEV (Sistema 1)` (`src/adapters/ai/jev_protocol.py`).
Provee las 3 primitivas tipadas e inmutables (`decide_boolean`, `decide_choice`, `decide_score`),
evaluación por lotes (`decide_choice_batch`) y telemetría desacoplada para `public.jev_request_logs`
con umbrales de confianza calibrados en `Decimal` (`confidence`, `meets_threshold`, `fallback_required`).
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol, runtime_checkable

from src.adapters.ai.protocol import LlmUsageRecord

JevScoreLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
DEFAULT_JEV_CONFIDENCE_THRESHOLD: Decimal = Decimal("0.85")
MAX_JEV_BATCH_SIZE: int = 1500


@dataclass(frozen=True, kw_only=True)
class JevUsageRecord:
    """
    Registro inmutable de telemetría de micro-decisiones sub-simbólicas JEV (Sistema 1).
    Listo para persistirse en `public.jev_request_logs`.
    """

    holding_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_schema: str
    user_id: int | None = None
    trace_id: str | None = None
    caller_feature: str
    decision_id: str
    decision_primitive: str
    input_summary: str
    result_value: str
    confidence_score: Decimal
    calibrated_action: str
    model_name: str
    estimated_tokens: int = 0
    provider_cost_usd: Decimal = Decimal("0.000000")
    provider_cost_clp: Decimal = Decimal("0.00")
    credits_deducted: Decimal = Decimal("0.00")
    latency_ms: int = 0
    is_success: bool = True
    error_message: str | None = None
    created_at: datetime | None = None


@runtime_checkable
class JevTelemetrySinkPort(Protocol):
    """
    Puerto colector desacoplado para telemetría especializada del motor JEV (Sistema 1)
    en `public.jev_request_logs`.
    """

    def record_jev_usage(self, record: JevUsageRecord) -> None:
        """Registra un evento individual de decisión JEV en la bitácora."""
        ...

    def record_jev_usage_batch(self, records: Sequence[JevUsageRecord]) -> None:
        """Registra un lote de eventos de decisión JEV en la bitácora."""
        ...


@dataclass(frozen=True)
class JevChoiceBatchItem:
    """Item para evaluación por lote en `decide_choice_batch`."""

    decision_id: str
    prompt_or_input: str
    candidates: Sequence[str]
    threshold: Decimal = DEFAULT_JEV_CONFIDENCE_THRESHOLD


@dataclass(frozen=True)
class JevBooleanResult:
    """Resultado inmutable de una micro-decisión binaria (`Jev.boolean` / `Noul`)."""

    decision_id: str
    value: bool
    confidence: Decimal
    threshold: Decimal
    meets_threshold: bool
    fallback_required: bool
    rationale_code: str
    usage_record: LlmUsageRecord
    jev_record: JevUsageRecord | None = None


@dataclass(frozen=True)
class JevChoiceResult:
    """Resultado inmutable de una micro-decisión de opción múltiple (`Jev.choice`)."""

    decision_id: str
    value: str
    confidence: Decimal
    threshold: Decimal
    meets_threshold: bool
    fallback_required: bool
    alternatives: tuple[tuple[str, Decimal], ...]
    usage_record: LlmUsageRecord
    jev_record: JevUsageRecord | None = None


@dataclass(frozen=True)
class JevScoreResult:
    """Resultado inmutable de una evaluación cuantitativa o de juez (`Jev.score`)."""

    decision_id: str
    level: JevScoreLevel
    numeric_score: Decimal
    confidence: Decimal
    threshold: Decimal
    meets_threshold: bool
    fallback_required: bool
    usage_record: LlmUsageRecord
    jev_record: JevUsageRecord | None = None


@runtime_checkable
class JevDecisionPort(Protocol):
    """
    Puerto transversal del Motor `JEV (Sistema 1)` para todo OppyTec v2.0.
    Opera en `< 500 ms` y registra el 100% de las decisiones en `public.jev_request_logs`
    y `public.llm_request_logs`.
    """

    def decide_boolean(
        self,
        *,
        decision_id: str,
        prompt_or_input: str,
        holding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tenant_schema: str,
        user_id: int,
        caller_feature: str,
        threshold: Decimal = DEFAULT_JEV_CONFIDENCE_THRESHOLD,
        thread_id: uuid.UUID | None = None,
    ) -> JevBooleanResult:
        """Evalúa una condición binaria difusa o guardrail de seguridad (`Jev.boolean`)."""

    def decide_choice(
        self,
        *,
        decision_id: str,
        prompt_or_input: str,
        candidates: Sequence[str],
        holding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tenant_schema: str,
        user_id: int,
        caller_feature: str,
        threshold: Decimal = DEFAULT_JEV_CONFIDENCE_THRESHOLD,
        thread_id: uuid.UUID | None = None,
    ) -> JevChoiceResult:
        """Elige la opción semántica óptima dentro de un conjunto cerrado (`Jev.choice`)."""

    def decide_choice_batch(
        self,
        *,
        items: Sequence[JevChoiceBatchItem],
        holding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tenant_schema: str,
        user_id: int,
        caller_feature: str,
        threshold: Decimal = DEFAULT_JEV_CONFIDENCE_THRESHOLD,
        thread_id: uuid.UUID | None = None,
    ) -> Sequence[JevChoiceResult]:
        """Evalúa un lote de micro-decisiones de opción múltiple registrando en lote (`Jev.choice_batch`)."""

    def decide_score(
        self,
        *,
        decision_id: str,
        prompt_or_input: str,
        holding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tenant_schema: str,
        user_id: int,
        caller_feature: str,
        threshold: Decimal = DEFAULT_JEV_CONFIDENCE_THRESHOLD,
        thread_id: uuid.UUID | None = None,
    ) -> JevScoreResult:
        """Califica severidad, riesgo, urgencia o fidelidad de respuesta (`Jev.score`)."""
