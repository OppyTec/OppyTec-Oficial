"""
White-Box Architecture Gate: Multi-Currency FX Precision & Decimal Governance (`test_fx_currency_precision_and_governance.py`).

Enforces Criterion 3 & 8 of `.agent/evals/rubric_10_criteria.yaml` and `.agent/rules/16-multi-currency-fx-and-pricing-governance.md`:
- Strictly forbids `float` for monetary amounts, prices, costs, stock quantities, unit conversions, and FX rates
  across `src/core/fx/` and `src/modules/*/domain/`. Only `decimal.Decimal` is permitted.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def find_float_usage_in_domain_ast(source_code: str, filename: str = "<memory>") -> list[str]:
    """Scans Python AST for any `float` type annotation or `float(...)` call."""
    tree = ast.parse(source_code, filename=filename)
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "float":
            violations.append(
                f"{filename}:{node.lineno} forbidden usage of 'float' (use decimal.Decimal instead)"
            )
    return violations


def test_zero_float_in_fx_and_domain_modules(
    backend_root: Path,
    monorepo_root: Path,
) -> None:
    """Verifies FX rule/skill exist and scans `src/core/fx/` and `src/modules/*/domain/` for `float`."""
    rule_16 = monorepo_root / ".agent" / "rules" / "16-multi-currency-fx-and-pricing-governance.md"
    skill_fx = monorepo_root / ".agent" / "skills" / "fx_currency_manager" / "SKILL.md"
    assert rule_16.exists(), "Rule 16 (Multi-Currency FX) must exist"
    assert skill_fx.exists(), "Skill fx_currency_manager/SKILL.md must exist"

    scan_files: list[Path] = []
    fx_dir = backend_root / "src" / "core" / "fx"
    modules_dir = backend_root / "src" / "modules"

    if fx_dir.exists():
        scan_files.extend(sorted(fx_dir.rglob("*.py")))
    if modules_dir.exists():
        scan_files.extend(sorted(modules_dir.glob("*/domain/**/*.py")))

    all_violations: list[str] = []
    for py_file in scan_files:
        source = py_file.read_text(encoding="utf-8")
        rel_path = py_file.relative_to(backend_root).as_posix()
        all_violations.extend(find_float_usage_in_domain_ast(source, rel_path))

    assert not all_violations, (
        "Forbidden 'float' detected in financial/FX/domain layer:\n" + "\n".join(all_violations)
    )


def test_ast_float_detector_catches_annotations_and_calls() -> None:
    """Self-test ensuring the AST inspector flags `float` annotations and casts."""
    valid_code = (
        "from decimal import Decimal\n"
        "def convert_fx(amount: Decimal, rate: Decimal) -> Decimal:\n"
        "    return (amount * rate).quantize(Decimal('0.00000001'))\n"
    )
    assert find_float_usage_in_domain_ast(valid_code) == []

    invalid_code = (
        "def bad_price(amount: float) -> float:\n"
        "    return float(amount) * 1.19\n"
    )
    assert len(find_float_usage_in_domain_ast(invalid_code, "fx.py")) == 3
