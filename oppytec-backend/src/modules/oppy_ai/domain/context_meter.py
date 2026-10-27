"""
Medidor de Porcentaje de Ventana de Contexto Anti-Alucinación (`src/modules/oppy_ai/domain/context_meter.py`).
- Calcula en `Decimal` (cero `float`) el porcentaje de tokens utilizados (`context_usage_percent`).
- Semáforo de salud:
  * Verde (<65.00%): `OPTIMAL_GREEN`
  * Ámbar (65.01% - 85.00%): `WARNING_AMBER` (alerta preventiva configurable desde 80.00%)
  * Rojo (>85.00%): `CRITICAL_RED` con bloqueo anti-alucinación (`is_anti_hallucination_blocked=True`).
- Al superar el límite seguro del 85.00%, se bloquea la adición de mensajes crudos y se exige
  compactación/síntesis de hilo para rollover fresco al 5.00% de contexto.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

ContextHealthStatus = Literal["OPTIMAL_GREEN", "WARNING_AMBER", "CRITICAL_RED"]

MAX_SAFE_THREAD_TOKENS: int = 8192
DEFAULT_MAX_SAFE_THREAD_TOKENS: int = MAX_SAFE_THREAD_TOKENS
GREEN_MAX_PERCENT: Decimal = Decimal("65.00")
AMBER_START_PERCENT: Decimal = Decimal("65.01")
AMBER_MAX_PERCENT: Decimal = Decimal("85.00")
PREVENTIVE_ALERT_THRESHOLD_PERCENT: Decimal = Decimal("80.00")
COMPACTION_REQUIRED_PERCENT: Decimal = Decimal("85.00")
FRESH_THREAD_INITIAL_PERCENT: Decimal = Decimal("5.00")
_TWO_DECIMALS = Decimal("0.01")


@dataclass(frozen=True)
class ContextHealthEvaluation:
    """Resultado inmutable del cálculo de salud de la ventana de contexto de `OppyFy`."""

    accumulated_tokens: int
    max_safe_tokens: int
    context_usage_percent: Decimal
    status: ContextHealthStatus
    preventive_alert: bool
    requires_auto_compaction: bool
    recommendation_key: str
    is_anti_hallucination_blocked: bool = False


@dataclass(frozen=True)
class ThreadCompactionSummary:
    """Resumen estructurado para traspaso asistido a un hilo fresco al `5.00%` de contexto."""

    source_thread_id: uuid.UUID
    new_thread_id: uuid.UUID
    synthesized_summary: str
    new_context_usage_percent: Decimal
    safe_token_budget_allocated: int = 409


def evaluate_context_usage(
    accumulated_tokens: int,
    *,
    max_safe_tokens: int = MAX_SAFE_THREAD_TOKENS,
) -> ContextHealthEvaluation:
    """
    Calcula en `Decimal` el porcentaje de uso de la ventana de contexto (`0.00` a `100.00`):
    - Verde: `< 65.00%` (`OPTIMAL_GREEN`)
    - Ámbar: `65.01% - 85.00%` (`WARNING_AMBER`), dispara `preventive_alert=True` cuando supera `80.00%`.
    - Rojo: `> 85.00%` (`CRITICAL_RED`), activa `is_anti_hallucination_blocked=True` y `requires_auto_compaction=True`.
    """
    if max_safe_tokens <= 0:
        raise ValueError("max_safe_tokens must be strictly positive.")
    safe_tokens = max(0, accumulated_tokens)

    raw_percent = (Decimal(safe_tokens) * Decimal("100")) / Decimal(max_safe_tokens)
    clamped_percent = min(Decimal("100.00"), raw_percent).quantize(
        _TWO_DECIMALS, rounding=ROUND_HALF_UP
    )

    is_blocked = clamped_percent > COMPACTION_REQUIRED_PERCENT
    requires_compaction = is_blocked
    preventive_alert = clamped_percent > PREVENTIVE_ALERT_THRESHOLD_PERCENT

    if is_blocked:
        status: ContextHealthStatus = "CRITICAL_RED"
        rec_key = "oppyfy.context_meter.critical_handover_required"
    elif clamped_percent > GREEN_MAX_PERCENT:
        status = "WARNING_AMBER"
        rec_key = (
            "oppyfy.context_meter.preventive_alert_80"
            if preventive_alert
            else "oppyfy.context_meter.amber_notice"
        )
    else:
        status = "OPTIMAL_GREEN"
        rec_key = "oppyfy.context_meter.optimal"

    return ContextHealthEvaluation(
        accumulated_tokens=safe_tokens,
        max_safe_tokens=max_safe_tokens,
        context_usage_percent=clamped_percent,
        status=status,
        preventive_alert=preventive_alert,
        requires_auto_compaction=requires_compaction,
        recommendation_key=rec_key,
        is_anti_hallucination_blocked=is_blocked,
    )


def calculate_safe_rollover_token_budget(
    max_safe_tokens: int = MAX_SAFE_THREAD_TOKENS,
    initial_percent: Decimal = FRESH_THREAD_INITIAL_PERCENT,
) -> int:
    """Calcula la cantidad de tokens asignables al resumen inicial en el nuevo hilo (5% del límite seguro)."""
    if max_safe_tokens <= 0:
        raise ValueError("max_safe_tokens must be strictly positive.")
    budget = (Decimal(max_safe_tokens) * initial_percent) / Decimal("100.00")
    return int(budget.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def compact_thread_for_fresh_handover(
    *,
    source_thread_id: uuid.UUID,
    messages: Sequence[str],
    new_thread_id: uuid.UUID | None = None,
    max_safe_tokens: int = MAX_SAFE_THREAD_TOKENS,
) -> ThreadCompactionSummary:
    """
    Compacta los mensajes clave de un hilo que alcanzó el límite seguro y genera un
    `ThreadCompactionSummary` inicializado al `5.00%` de contexto con presupuesto seguro de tokens.
    """
    target_id = new_thread_id or uuid.uuid4()
    retained_tail = [m.strip() for m in messages[-3:] if m.strip()]
    synthesized = (
        " | ".join(retained_tail)
        if retained_tail
        else "Hilo inicializado sin historial previo."
    )
    budget = calculate_safe_rollover_token_budget(max_safe_tokens)
    return ThreadCompactionSummary(
        source_thread_id=source_thread_id,
        new_thread_id=target_id,
        synthesized_summary=f"[COMPACTED_HANDOVER] {synthesized}",
        new_context_usage_percent=FRESH_THREAD_INITIAL_PERCENT,
        safe_token_budget_allocated=budget,
    )
