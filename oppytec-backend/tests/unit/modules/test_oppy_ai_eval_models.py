"""
oppytec-backend/tests/unit/modules/test_oppy_ai_eval_models.py
Pruebas Unitarias para los Modelos ORM SQLAlchemy 2.0 Async de AI Evals y Feedback
y verificación de la migración correlativa Alembic 0017.
"""
from __future__ import annotations

import ast
import uuid
from decimal import Decimal
from pathlib import Path

import pytest

from src.modules.oppy_ai.infrastructure.models import (
    AIChatFeedbackModel,
    AIEvalBenchmarkModel,
    AIEvalCaseResultModel,
)

pytestmark = pytest.mark.unit


def test_ai_eval_benchmark_model_attributes_and_defaults() -> None:
    """Verifica que AIEvalBenchmarkModel posea todos los campos especificados con tipos y defaults."""
    benchmark_id = uuid.uuid4()
    benchmark = AIEvalBenchmarkModel(
        id=benchmark_id,
        suite_name="oppyfy_golden_dataset_v1",
        model_name="gemini-2.5-flash",
    )

    assert benchmark.id == benchmark_id
    assert benchmark.suite_name == "oppyfy_golden_dataset_v1"
    assert benchmark.model_name == "gemini-2.5-flash"
    assert benchmark.total_cases == 0
    assert benchmark.passed_cases == 0
    assert benchmark.avg_faithfulness == Decimal("0.0000")
    assert benchmark.avg_relevance == Decimal("0.0000")
    assert benchmark.avg_context_precision == Decimal("0.0000")
    assert benchmark.avg_hallucination_rate == Decimal("0.0000")
    assert benchmark.passed_thresholds is False
    assert AIEvalBenchmarkModel.__tablename__ == "ai_eval_benchmarks"
    assert AIEvalBenchmarkModel.metadata.schema == "public"


def test_ai_eval_case_result_model_attributes() -> None:
    """Verifica que AIEvalCaseResultModel contenga los campos y defaults de evaluación granular."""
    case_id_uuid = uuid.uuid4()
    bench_id = uuid.uuid4()

    case_result = AIEvalCaseResultModel(
        id=case_id_uuid,
        benchmark_id=bench_id,
        case_id="case_costing_001",
        category="costing",
        prompt="¿Cuál es el costo unitario de Pechuga de Pollo?",
        expected_output="El costo unitario es 2500 CLP/kg.",
        actual_output="El costo unitario es 2500 CLP/kg según kardex.",
        retrieved_context="Context: catalog item pechuga de pollo cost 2500 CLP",
        faithfulness=Decimal("0.9500"),
        relevance=Decimal("0.9800"),
        hallucination_detected=False,
        latency_ms=420,
        passed=True,
    )

    assert case_result.id == case_id_uuid
    assert case_result.benchmark_id == bench_id
    assert case_result.case_id == "case_costing_001"
    assert case_result.category == "costing"
    assert case_result.faithfulness == Decimal("0.9500")
    assert case_result.relevance == Decimal("0.9800")
    assert case_result.hallucination_detected is False
    assert case_result.latency_ms == 420
    assert case_result.passed is True
    assert AIEvalCaseResultModel.__tablename__ == "ai_eval_case_results"
    assert AIEvalCaseResultModel.metadata.schema == "public"


def test_ai_chat_feedback_model_attributes() -> None:
    """Verifica que AIChatFeedbackModel almacene feedback humano RLHF con trace_id."""
    feedback_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    message_id = uuid.uuid4()

    feedback = AIChatFeedbackModel(
        id=feedback_id,
        tenant_id=tenant_id,
        user_id=user_id,
        message_id=message_id,
        trace_id="langfuse_trace_9876543210abcdef",
        feedback_type="negative",
        failure_category="hallucination",
        user_correction="El proveedor real es Distribuidora Gastronómica, no Comercializadora.",
        rating=1,
    )

    assert feedback.id == feedback_id
    assert feedback.tenant_id == tenant_id
    assert feedback.user_id == user_id
    assert feedback.message_id == message_id
    assert feedback.trace_id == "langfuse_trace_9876543210abcdef"
    assert feedback.feedback_type == "negative"
    assert feedback.failure_category == "hallucination"
    assert feedback.user_correction is not None
    assert feedback.rating == 1
    assert AIChatFeedbackModel.__tablename__ == "ai_chat_feedbacks"


def test_benchmark_case_results_cascade_relationship() -> None:
    """Verifica la relación bidireccional entre AIEvalBenchmarkModel y AIEvalCaseResultModel."""
    bench = AIEvalBenchmarkModel(
        suite_name="oppyfy_eval_suite_v2",
        model_name="gemini-2.5-flash",
    )
    case1 = AIEvalCaseResultModel(
        case_id="c1",
        category="rag",
        prompt="p1",
        expected_output="e1",
        actual_output="a1",
        faithfulness=Decimal("0.9000"),
        relevance=Decimal("0.9200"),
    )
    bench.case_results.append(case1)

    assert len(bench.case_results) == 1
    assert bench.case_results[0].case_id == "c1"
    assert case1.benchmark is bench


def test_alembic_0017_structure_and_scope() -> None:
    """Verifica que la migración 0017 cumpla con la linealidad correlativa ininterrumpida y las reglas de Alembic."""
    migration_file = (
        Path(__file__).parents[3]
        / "alembic"
        / "versions"
        / "0017_public_ai_benchmarks_and_tenant_feedback.py"
    )
    assert migration_file.exists(), f"Migración {migration_file} no encontrada"

    content = migration_file.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(migration_file))

    assignments = {}
    functions = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                    assignments[target.id] = node.value.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and isinstance(node.value, ast.Constant):
                assignments[node.target.id] = node.value.value
        elif isinstance(node, ast.FunctionDef):
            functions.add(node.name)

    assert assignments.get("revision") == "0017_public_ai_benchmarks_and_tenant_feedback"
    assert assignments.get("down_revision") == "0016_tenant_invoices_dte_and_supplier_aliases"
    assert assignments.get("migration_scope") == "public"
    assert "upgrade" in functions
    assert "downgrade" in functions
    assert "_apply_public_upgrades" in functions
    assert "_apply_tenant_upgrade_to_schema" in functions
    assert "_apply_public_downgrades" in functions
    assert "_apply_tenant_downgrade_to_schema" in functions
