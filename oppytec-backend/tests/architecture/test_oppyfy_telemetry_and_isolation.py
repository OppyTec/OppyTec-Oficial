"""
White-Box Architecture Gate: OppyFy Telemetry & RAG Isolation (`test_oppyfy_telemetry_and_isolation.py`).

Enforces Criterion 9 of `.agent/evals/rubric_10_criteria.yaml` and `.agent/rules/13-oppyfy-ai-governance-and-telemetry.md`:
1. AST Gate: Zero direct SDK calls to Gemini, OpenAI or Anthropic outside the sanctioned
   adapter layer (`src/adapters/ai/`), ensuring every invocation passes through `MeteredAIService`
   and records telemetry in the ineludible sink `public.llm_request_logs`.
2. AST Gate: The 3-Layer RAG engine (`ThreeLayerRagService`) and spec vault are strictly restricted
   to `specs/business-domain/` and strictly prohibited from indexing `specs/engineering-code/`,
   `docs/adr/`, or application source code `src/`.
3. AST Gate: All deterministic operational tools in `src/modules/oppy_ai/application/operational_tools/`
   implement Hard-Code Data Stripping via `@hardcoded_data_stripping` decorator or `redact_cost_fields` call.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

FORBIDDEN_AI_SDK_MODULES = (
    "google.generativeai",
    "google.genai",
    "openai",
    "anthropic",
)

FORBIDDEN_RAG_SPEC_DIRECTORIES = (
    "specs/engineering-code",
    "docs/adr",
    "oppytec-backend/src",
)


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


def test_ast_zero_direct_ai_sdk_bypassing_metered_service(
    backend_root: Path,
) -> None:
    """
    AST Analysis: 0 direct SDK calls to Gemini, OpenAI or Anthropic outside
    the sanctioned `src/adapters/ai/` adapter layer.
    Ensures all AI interactions must route through the universal `MeteredAIService`
    and the ineludible sink of `public.llm_request_logs`.
    """
    src_dir = backend_root / "src"
    allowed_adapters_dir = src_dir / "adapters" / "ai"

    violations: list[str] = []

    for py_file in src_dir.rglob("*.py"):
        # The only sanctioned directory for raw AI SDK integrations is src/adapters/ai/
        try:
            py_file.relative_to(allowed_adapters_dir)
            continue
        except ValueError:
            pass  # File is outside src/adapters/ai/, must be checked strictly

        source_code = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source_code, filename=str(py_file))
        except SyntaxError as err:
            violations.append(f"{py_file}: SyntaxError during AST parse: {err}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in FORBIDDEN_AI_SDK_MODULES:
                        if alias.name == forbidden or alias.name.startswith(f"{forbidden}."):
                            violations.append(
                                f"{py_file}:{node.lineno} imports '{alias.name}'. Direct AI SDK usage "
                                f"outside 'src/adapters/ai/' bypasses MeteredAIService telemetry."
                            )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for forbidden in FORBIDDEN_AI_SDK_MODULES:
                        if node.module == forbidden or node.module.startswith(f"{forbidden}."):
                            violations.append(
                                f"{py_file}:{node.lineno} imports from '{node.module}'. Direct AI SDK "
                                f"usage outside 'src/adapters/ai/' bypasses MeteredAIService telemetry."
                            )

    assert not violations, (
        f"Found {len(violations)} security violations bypassing MeteredAIService:\n"
        + "\n".join(violations)
    )

    # Verify that in src/adapters/ai/gemini_adapter.py and MeteredAIService, telemetry emission is ineludible
    gemini_adapter_file = allowed_adapters_dir / "gemini_adapter.py"
    assert gemini_adapter_file.exists(), "src/adapters/ai/gemini_adapter.py must exist"
    gemini_tree = ast.parse(gemini_adapter_file.read_text(encoding="utf-8"))

    calls_to_sink: list[int] = []
    for node in ast.walk(gemini_tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr in ("record_llm_usage", "record_decision")
            ):
                calls_to_sink.append(node.lineno)

    assert len(calls_to_sink) >= 1, (
        "MeteredGeminiAdapter must contain calls to telemetry sink 'record_llm_usage' "
        "to guarantee public.llm_request_logs persistence."
    )

    metered_service_file = backend_root / "src" / "modules" / "oppy_ai" / "application" / "metered_ai_service.py"
    metered_tree = ast.parse(metered_service_file.read_text(encoding="utf-8"))
    metered_sink_calls = [
        node.lineno
        for node in ast.walk(metered_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ("_record_usage", "record_llm_usage")
    ]
    assert len(metered_sink_calls) >= 1, (
        "MeteredAIService must contain calls to record usage to the telemetry sink."
    )


def test_ast_rag_engine_strict_business_domain_isolation(
    backend_root: Path,
) -> None:
    """
    AST Analysis: The 3-layer RAG ingestion engine (`ThreeLayerRagService`)
    only reads and accepts spec chunks from `specs/business-domain/`.
    It is strictly forbidden from indexing `specs/engineering-code/`,
    `docs/adr/`, or application source code (`src/`).
    """
    rag_file = backend_root / "src" / "modules" / "oppy_ai" / "application" / "rag_service.py"
    assert rag_file.exists(), f"{rag_file} must exist"

    source_code = rag_file.read_text(encoding="utf-8")
    tree = ast.parse(source_code, filename=str(rag_file))

    # 1. Verify constant ALLOWED_PUBLIC_SPEC_VAULT_PREFIX is defined as 'specs/business-domain'
    vault_prefix_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ALLOWED_PUBLIC_SPEC_VAULT_PREFIX":
                    if isinstance(node.value, ast.Constant):
                        assert node.value.value == "specs/business-domain", (
                            f"ALLOWED_PUBLIC_SPEC_VAULT_PREFIX must be 'specs/business-domain', "
                            f"found {node.value.value!r}"
                        )
                        vault_prefix_found = True
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "ALLOWED_PUBLIC_SPEC_VAULT_PREFIX":
                if isinstance(node.value, ast.Constant):
                    assert node.value.value == "specs/business-domain", (
                        f"ALLOWED_PUBLIC_SPEC_VAULT_PREFIX must be 'specs/business-domain', "
                        f"found {node.value.value!r}"
                    )
                    vault_prefix_found = True

    assert vault_prefix_found, (
        "ALLOWED_PUBLIC_SPEC_VAULT_PREFIX must be explicitly defined in rag_service.py"
    )

    # 2. Verify register_business_spec_chunk enforces isolation
    method_found = False
    validates_prefix = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "register_business_spec_chunk":
            method_found = True
            for child in ast.walk(node):
                if isinstance(child, ast.Raise):
                    validates_prefix = True

    assert method_found, "ThreeLayerRagService.register_business_spec_chunk must be defined"
    assert validates_prefix, "register_business_spec_chunk must raise an exception when prefix is invalid"

    # 3. Verify no forbidden directories are allowed in any oppy_ai module
    oppy_ai_dir = backend_root / "src" / "modules" / "oppy_ai"
    violations: list[str] = []
    for py_file in oppy_ai_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        tree_mod = ast.parse(content, filename=str(py_file))

        docstring_constants: set[int] = set()
        if (
            tree_mod.body
            and isinstance(tree_mod.body[0], ast.Expr)
            and isinstance(tree_mod.body[0].value, ast.Constant)
        ):
            docstring_constants.add(id(tree_mod.body[0].value))

        for node in ast.walk(tree_mod):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                ):
                    docstring_constants.add(id(node.body[0].value))

            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in docstring_constants:
                    continue
                for forbidden in ("specs/engineering-code", "docs/adr"):
                    if forbidden in node.value:
                        violations.append(
                            f"{py_file}:{node.lineno} references forbidden directory '{forbidden}'"
                        )

    assert not violations, (
        f"Found {len(violations)} forbidden spec references in oppy_ai:\n"
        + "\n".join(violations)
    )

    # 4. Verify behavioral enforcement: ThreeLayerRagService strictly rejects non-business paths
    from src.modules.oppy_ai.application.rag_service import (
        BusinessSpecChunkRecord,
        ThreeLayerRagService,
    )
    import uuid

    rag_service = ThreeLayerRagService()

    for forbidden_path in (
        "specs/engineering-code/001-adr.md",
        "docs/adr/001-adr.md",
        "src/core/security.py",
        "oppytec-backend/src/main.py",
        "/etc/passwd",
    ):
        with pytest.raises(ValueError, match="RAG Isolation Error"):
            rag_service.register_business_spec_chunk(
                BusinessSpecChunkRecord(
                    chunk_id=uuid.uuid4(),
                    spec_rel_path=forbidden_path,
                    module_slug="security",
                    content_markdown="# Confidential",
                )
            )

    # Allowed path must succeed
    rag_service.register_business_spec_chunk(
        BusinessSpecChunkRecord(
            chunk_id=uuid.uuid4(),
            spec_rel_path="specs/business-domain/recipes.md",
            module_slug="recipes",
            content_markdown="# Manual de Recetas de Cocina",
        )
    )


def test_ast_operational_tools_enforce_hardcoded_data_stripping(
    backend_root: Path,
) -> None:
    """
    AST Analysis: All deterministic operational tools in `src/modules/oppy_ai/application/operational_tools/`
    must implement the `@hardcoded_data_stripping` decorator or a direct call to `redact_cost_fields`
    to guarantee Hard-Code Data Stripping before any payload is exposed to the AI model.
    """
    tools_dir = backend_root / "src" / "modules" / "oppy_ai" / "application" / "operational_tools"
    assert tools_dir.exists(), f"{tools_dir} must exist"

    unprotected_tools: list[str] = []
    total_tools_checked = 0

    for py_file in sorted(tools_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue

        source_code = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source_code, filename=str(py_file))

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private helper functions starting with '_'
                if node.name.startswith("_"):
                    continue

                total_tools_checked += 1
                has_stripping_decorator = False
                has_redact_call = False

                # 1. Check decorators
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Name) and dec.id in (
                        "hardcoded_data_stripping",
                        "redact_cost_fields",
                    ):
                        has_stripping_decorator = True
                    elif isinstance(dec, ast.Attribute) and dec.attr in (
                        "hardcoded_data_stripping",
                        "redact_cost_fields",
                    ):
                        has_stripping_decorator = True

                # 2. Check function body for direct call to redact_cost_fields
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func = child.func
                        if isinstance(func, ast.Name) and func.id == "redact_cost_fields":
                            has_redact_call = True
                        elif isinstance(func, ast.Attribute) and func.attr == "redact_cost_fields":
                            has_redact_call = True

                if not (has_stripping_decorator or has_redact_call):
                    unprotected_tools.append(f"{py_file.name}:{node.name}")

    assert total_tools_checked >= 8, (
        f"Expected at least 8 operational tools, found {total_tools_checked}"
    )
    assert not unprotected_tools, (
        f"The following operational tools do not enforce Hard-Code Data Stripping "
        f"(@hardcoded_data_stripping or redact_cost_fields):\n"
        + "\n".join(unprotected_tools)
    )
