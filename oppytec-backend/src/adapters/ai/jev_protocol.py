"""
Protocolo del Motor Global de Decisiones `JEV (Sistema 1)` (`src/adapters/ai/jev_protocol.py`).
Provee las 3 primitivas tipadas e inmutables (`decide_boolean`, `decide_choice`, `decide_score`)
con umbrales de confianza calibrados en `Decimal` (`confidence`, `meets_threshold`, `fallback_required`).
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol, runtime_checkable

from src.adapters.ai.protocol import LlmUsageRecord

JevScoreLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
DEFAULT_JEV_CONFIDENCE_THRESHOLD: Decimal = Decimal("0.85")


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


@runtime_checkable
class JevDecisionPort(Protocol):
    """
    Puerto transversal del Motor `JEV (Sistema 1)` para todo OppyTec v2.0.
    Opera en `< 500 ms` y registra el 100% de las decisiones en `public.llm_request_logs`.
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
