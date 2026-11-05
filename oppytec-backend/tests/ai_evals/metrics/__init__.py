"""
oppytec-backend/tests/ai_evals/metrics/__init__.py
Métricas y Evaluadores Personalizados para OppyFy v2.0 (Zero-Float Guarantee).
"""
from __future__ import annotations

from .custom_evaluators import (
    AnswerRelevanceEvaluator,
    ContextPrecisionEvaluator,
    FaithfulnessEvaluator,
    GastronomicEvalResult,
    HallucinationEvaluator,
    run_all_evaluators,
)

__all__ = [
    "AnswerRelevanceEvaluator",
    "ContextPrecisionEvaluator",
    "FaithfulnessEvaluator",
    "GastronomicEvalResult",
    "HallucinationEvaluator",
    "run_all_evaluators",
]
