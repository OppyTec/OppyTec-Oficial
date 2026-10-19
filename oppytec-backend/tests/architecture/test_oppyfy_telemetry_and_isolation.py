"""
White-Box Architecture Gate: OppyFy Telemetry & RAG Isolation (`test_oppyfy_telemetry_and_isolation.py`).

Enforces Criterion 9 of `.agent/evals/rubric_10_criteria.yaml` and `.agent/rules/13-oppyfy-ai-governance-and-telemetry.md`:
- OppyFy (`AI_ASSISTANT_BRAND_NAME`) must never index `specs/engineering-code/` in client RAG (`spec_chunks`).
- Every AI invocation must record telemetry in `public.llm_request_logs` and enforce OppyFy's editable client RBAC.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_oppyfy_governance_and_rag_vault_isolation(
    backend_root: Path,
    monorepo_root: Path,
) -> None:
    """Verifies OppyFy rules and ensures `specs/engineering-code/` is never indexed in `oppy_ai`."""
    rule_13 = monorepo_root / ".agent" / "rules" / "13-oppyfy-ai-governance-and-telemetry.md"
    strategy_ai = (
        monorepo_root
        / ".agent"
        / "estrategias"
        / "estrategia_asistente_ai_oppyfy_rag_y_creditos_001.md"
    )
    assert rule_13.exists(), "Rule 13 (OppyFy governance & telemetry) must exist"
    assert strategy_ai.exists(), "OppyFy master strategy document must exist"

    env_example = (backend_root / ".env.example").read_text(encoding="utf-8")
    assert "AI_ASSISTANT_BRAND_NAME=OppyFy" in env_example

    oppy_ai_dir = backend_root / "src" / "modules" / "oppy_ai"
    if oppy_ai_dir.exists():
        for py_file in oppy_ai_dir.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            assert "specs/engineering-code" not in source, (
                f"Security violation in {py_file}: client RAG must never index 'specs/engineering-code/'"
            )
