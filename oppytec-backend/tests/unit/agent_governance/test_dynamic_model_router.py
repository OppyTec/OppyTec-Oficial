"""
oppytec-backend/tests/unit/agent_governance/test_dynamic_model_router.py
Suite de Pruebas Unitarias para la Asignación Dinámica de Modelos LLM por Complejidad Cognitiva JEV
Valida:
1. Clasificación y cálculo de C_task para tareas ligeras (< 0.35).
2. Clasificación y promoción a tier_reasoning_heavy para tareas complejas (>= 0.70).
3. Cadena de fallback intacta ante contingencias de cuota (HTTP 429).
4. SLA de latencia en tiempo constante (< 20 ms).
5. Auto-escalado cognitivo reactivo (escalate_model_tier).
6. Explicabilidad y desglose en 4 dimensiones ponderadas (AST, dominio, alcance, contexto).
7. Retrocompatibilidad y estabilidad de agentes con base tier_reasoning_heavy.
"""
from __future__ import annotations

import sys
import time
from decimal import Decimal
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parents[4]
SKILLS_DIR = ROOT_DIR / ".agent" / "skills" / "jev-decision-engine"
SCRIPTS_DIR = ROOT_DIR / "scripts"

for p in (str(SKILLS_DIR), str(SCRIPTS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from complexity_evaluator import (  # noqa: E402
    TaskComplexityReport,
    evaluate_task_complexity,
)
from jev_router import (  # noqa: E402
    ExecutionMode,
    SquadAgentId,
    classify_user_request,
)
from harness import (  # noqa: E402
    escalate_model_tier,
    resolve_agent_model,
    trigger_model_fallback,
)


def test_task_complexity_lightweight_task() -> None:
    """Verifica que una tabla plana de solo lectura se clasifique con C_task < 0.35 y tier_lightweight."""
    prompt = "crear tabla plana de solo lectura para codigos postales"
    report = evaluate_task_complexity(prompt, primary_agent="04-backend-senior-dev")

    assert isinstance(report, TaskComplexityReport)
    assert report.complexity_score < Decimal("0.35")
    assert report.level == "BAJO"
    assert report.promoted_tier == "tier_lightweight"

    # Resolución de modelo dinámica para el agente backend
    resolved = resolve_agent_model("04-backend-senior-dev", complexity_tier=report.promoted_tier)
    assert resolved["tier_key"] == "tier_lightweight"
    assert "gemini-3.8-flash" in resolved["primary_model"] or "gemini-flash-lite" in resolved["fallback_chain"]


def test_task_complexity_heavy_reasoning_promotion() -> None:
    """Verifica que una tarea transaccional multi-tabla promueva automáticamente a tier_reasoning_heavy (C_task >= 0.70)."""
    prompt = "crear tabla transaccional de facturación vinculada a kardex con cálculo FX e inventario multi-tenant"
    classification = classify_user_request(prompt)

    report = classification.complexity_report
    assert report is not None
    assert report.complexity_score >= Decimal("0.70")
    assert report.level == "ALTO"
    assert report.promoted_tier == "tier_reasoning_heavy"

    # Verificar promoción de 04-backend-senior-dev a Argon
    resolved = resolve_agent_model("04-backend-senior-dev", complexity_tier=report.promoted_tier)
    assert resolved["tier_key"] == "tier_reasoning_heavy"
    assert resolved["was_promoted"] is True
    assert resolved["primary_model"] == "gemini/gemini-4-argon"
    assert "anthropic/claude-3-7-sonnet" in resolved["fallback_chain"]


def test_fallback_chain_integrity_429() -> None:
    """Valida que la cadena de fallback opere deterministamente ante agotamiento de cuota."""
    # Resolución en tier_reasoning_heavy
    resolved = resolve_agent_model("tier_reasoning_heavy")
    primary = resolved["primary_model"]
    fallbacks = resolved["fallback_chain"]

    assert primary == "gemini/gemini-4-argon"
    assert fallbacks[0] == "anthropic/claude-3-7-sonnet"
    assert "openai/gpt-4o" in fallbacks

    # Simular trigger de fallback
    event = trigger_model_fallback("tier_reasoning_heavy", primary, "HTTP 429 Quota Exceeded")
    assert event["promoted_fallback_model"] == "anthropic/claude-3-7-sonnet"
    assert event["failed_model"] == primary


def test_latency_sla_under_20ms() -> None:
    """Valida que el cómputo de complejidad cognitiva cumpla el SLA estricto de < 20 ms."""
    prompt = "crear tabla transaccional de facturación vinculada a kardex con cálculo FX e inventario multi-tenant"

    # Warmup
    evaluate_task_complexity(prompt, "04-backend-senior-dev")

    iterations = 50
    start = time.perf_counter()
    for _ in range(iterations):
        evaluate_task_complexity(prompt, "04-backend-senior-dev", mode="DAG_PIPELINE")
    elapsed_total_ms = (time.perf_counter() - start) * 1000
    avg_latency_ms = elapsed_total_ms / iterations

    assert avg_latency_ms < 20.0, f"Latencia promedio {avg_latency_ms:.2f}ms excede el SLA de 20ms"


def test_escalate_model_tier_reactive() -> None:
    """Valida el mecanismo de auto-escalado cognitivo reactivo ante fallas."""
    # 1. Agente en tier_fast_execution escala a tier_reasoning_heavy
    escalated = escalate_model_tier("04-backend-senior-dev", reason="TEST_FAILURE_REASONING_DEFICIT")
    assert escalated["tier_key"] == "tier_reasoning_heavy"
    assert escalated["primary_model"] == "gemini/gemini-4-argon"

    # 2. Agente en tier_lightweight escala a tier_fast_execution
    escalated_light = escalate_model_tier("07-i18n-and-fx-currency-specialist", reason="UNEXPECTED_COMPLEXITY")
    assert escalated_light["tier_key"] == "tier_fast_execution"
    assert escalated_light["primary_model"] == "gemini/gemini-3.8-flash"


def test_complexity_dimensions_and_explainability() -> None:
    """Valida que el desglose de 4 dimensiones y el método explain() contengan todos los factores."""
    prompt = "crear endpoint crud de clientes con paginacion y filtros simples"
    report = evaluate_task_complexity(prompt, primary_agent="04-backend-senior-dev")

    # Verificar 4 dimensiones presentes
    dims = report.dimension_scores
    assert set(dims.keys()) == {"graph", "domain", "scope", "context"}
    for d, score in dims.items():
        assert Decimal("0.0") <= score <= Decimal("1.0")

    # Verificar ponderaciones presentes
    weights = report.dimension_weights
    assert set(weights.keys()) == {"graph", "domain", "scope", "context"}
    total_weight = sum(weights.values())
    assert total_weight == Decimal("1.00")

    # Verificar salida de explain()
    explanation = report.explain()
    assert "S_graph" in explanation
    assert "S_domain" in explanation
    assert "S_scope" in explanation
    assert "S_context" in explanation
    assert "Tier Dinámico Resultante" in explanation


def test_architect_preserves_reasoning_heavy_floor() -> None:
    """Valida que un agente arquitecto cuya base es tier_reasoning_heavy no se degrade ante tareas ligeras."""
    prompt = "ajustar estilo de botón secundario"
    report = evaluate_task_complexity(prompt, primary_agent="02-software-architect")

    # El reporte de la tarea puede ser bajo
    assert report.complexity_score < Decimal("0.35")

    # Sin embargo, la resolución de modelo del arquitecto conserva su piso crítico de razonamiento
    resolved = resolve_agent_model("02-software-architect", complexity_tier=report.promoted_tier)
    assert resolved["tier_key"] == "tier_reasoning_heavy"
    assert resolved["primary_model"] == "gemini/gemini-4-argon"
