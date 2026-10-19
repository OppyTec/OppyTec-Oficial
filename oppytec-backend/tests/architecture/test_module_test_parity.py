"""
White-Box Architecture Gate: 1:1 Co-Creation Test Parity (`test_module_test_parity.py`).

Enforces Criterion 7 of `.agent/evals/rubric_10_criteria.yaml` and `.agent/rules/05-testing-and-dod.md`:
- `src/main.py` has its paired smoke test `tests/smoke/test_system_boot_and_health.py`.
- Every implemented business module in `src/modules/<module_name>/` (containing non-`__init__.py` code)
  must have a corresponding test suite in `tests/unit/modules/test_<module_name>_services.py` or `tests/`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_main_and_implemented_modules_have_paired_tests(
    backend_root: Path,
    monorepo_root: Path,
) -> None:
    """Verifies 1:1 test parity for `src/main.py` and any implemented `src/modules/*`."""
    rule_05 = monorepo_root / ".agent" / "rules" / "05-testing-and-dod.md"
    assert rule_05.exists(), "Rule 05 (Testing & DoD) must exist"

    main_py = backend_root / "src" / "main.py"
    smoke_test = backend_root / "tests" / "smoke" / "test_system_boot_and_health.py"
    assert main_py.exists(), "oppytec-backend/src/main.py must exist"
    assert smoke_test.exists(), "Smoke test for src/main.py must exist"

    modules_dir = backend_root / "src" / "modules"
    if not modules_dir.exists():
        return

    missing_tests: list[str] = []
    for mod_dir in sorted(p for p in modules_dir.iterdir() if p.is_dir()):
        code_files = [
            f
            for f in mod_dir.rglob("*.py")
            if f.name != "__init__.py"
        ]
        if not code_files:
            continue

        mod_name = mod_dir.name
        candidate_unit_test = (
            backend_root / "tests" / "unit" / "modules" / f"test_{mod_name}_services.py"
        )
        candidate_any_test = list((backend_root / "tests").rglob(f"*{mod_name}*.py"))
        if not candidate_unit_test.exists() and not candidate_any_test:
            missing_tests.append(
                f"Module 'src/modules/{mod_name}' has {len(code_files)} implementation file(s) "
                f"but no paired test (expected 'tests/unit/modules/test_{mod_name}_services.py')."
            )

    assert not missing_tests, "1:1 Co-Creation test parity violations:\n" + "\n".join(missing_tests)
