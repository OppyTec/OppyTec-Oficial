"""
Medidor de Porcentaje de Ventana de Contexto Anti-Alucinación (`src/modules/oppy_ai/domain/context_meter.py`).
- Calcula en `Decimal` (cero `float`) el porcentaje de tokens utilizados (`context_usage_percent`).
- Dispara alerta preventiva al superar el `80%` (y semáforo ámbar desde `66%`).
- Ejecuta compactación/resumen automático hacia un hilo fresco al alcanzar el límite seguro (`>= 86%` o `100%`).
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

ContextHealthStatus = Literal["OPTIMAL_GREEN", "WARNING_AMBER", "CRITICAL_RED"]

DEFAULT_MAX_SAFE_THREAD_TOKENS: int = 16000
AMBER_START_PERCENT: Decimal = Decimal("66.00")
PREVENTIVE_ALERT_THRESHOLD_PERCENT: Decimal = Decimal("80.00")
COMPACTION_REQUIRED_PERCENT: Decimal = Decimal("86.00")
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


@dataclass(frozen=True)
class ThreadCompactionSummary:
    """Resumen estructurado para traspaso asistido a un hilo fresco al `5.00%` de contexto."""

    source_thread_id: uuid.UUID
    new_thread_id: uuid.UUID
    synthesized_summary: str
    new_context_usage_percent: Decimal


def evaluate_context_usage(
    accumulated_tokens: int,
    *,
    max_safe_tokens: int = DEFAULT_MAX_SAFE_THREAD_TOKENS,
) -> ContextHealthEvaluation:
    """
    Calcula en `Decimal` el porcentaje de uso de la ventana de contexto (`0.00` a `100.00`):
    - Activa `preventive_alert=True` cuando supera `80.00%`.
    - Activa `requires_auto_compaction=True` cuando alcanza o supera `86.00%` (o el límite de tokens).
    """
    if max_safe_tokens <= 0:
        raise ValueError("max_safe_tokens must be strictly positive.")
    safe_tokens = max(0, accumulated_tokens)

    raw_percent = (Decimal(safe_tokens) * Decimal("100")) / Decimal(max_safe_tokens)
    clamped_percent = min(Decimal("100.00"), raw_percent).quantize(
        _TWO_DECIMALS, rounding=ROUND_HALF_UP
    )

    preventive_alert = clamped_percent > PREVENTIVE_ALERT_THRESHOLD_PERCENT
    requires_compaction = clamped_percent >= COMPACTION_REQUIRED_PERCENT

    if requires_compaction:
        status: ContextHealthStatus = "CRITICAL_RED"
        rec_key = "oppyfy.context_meter.critical_handover_required"
    elif clamped_percent >= AMBER_START_PERCENT:
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
    )


def compact_thread_for_fresh_handover(
    *,
    source_thread_id: uuid.UUID,
    messages: Sequence[str],
    new_thread_id: uuid.UUID | None = None,
) -> ThreadCompactionSummary:
    """
    Compacta los mensajes clave de un hilo que alcanzó el límite seguro y genera un
    `ThreadCompactionSummary` inicializado al `5.00%` de contexto.
    """
    target_id = new_thread_id or uuid.uuid4()
    retained_tail = [m.strip() for m in messages[-3:] if m.strip()]
    synthesized = (
        " | ".join(retained_tail)
        if retained_tail
        else "Hilo inicializado sin historial previo."
    )
    return ThreadCompactionSummary(
        source_thread_id=source_thread_id,
        new_thread_id=target_id,
        synthesized_summary=f"[COMPACTED_HANDOVER] {synthesized}",
        new_context_usage_percent=FRESH_THREAD_INITIAL_PERCENT,
    )
