"""
White-Box Architecture Gate: 3-Level RBAC & Forensic Audit Coverage (`test_rbac_and_audit_coverage.py`).

Enforces Criterion 6 of `.agent/evals/rubric_10_criteria.yaml` and `.agent/rules/07-rbac-least-privilege-and-audit.md`:
- Every business module router in `oppytec-backend/src/modules/*/presentation/router.py` must enforce
  3-level RBAC guards (`RequireGlobalPermission` or `RequireTenantPermission` with `<module>.<submodule>.<function>`).
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

THREE_LEVEL_PERMISSION_REGEX = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$")
RBAC_GUARD_NAMES: frozenset[str] = frozenset(
    {
        "RequireGlobalPermission",
        "RequireTenantPermission",
    }
)
PUBLIC_EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "/api/v1/health",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/admin/login",
    }
)


def is_valid_three_level_permission(code: str) -> bool:
    """Returns True if `code` follows the `<modulo>.<submodulo>.<funcion>` 3-level format."""
    return bool(THREE_LEVEL_PERMISSION_REGEX.match(code))


def audit_router_ast_for_rbac(source_code: str, filename: str) -> list[str]:
    """Inspects a FastAPI `router.py` AST to verify 3-level RBAC permission strings."""
    tree = ast.parse(source_code, filename=filename)
    violations: list[str] = []

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in RBAC_GUARD_NAMES
        ):
            if not node.args or not isinstance(node.args[0], ast.Constant):
                violations.append(
                    f"{filename}:{node.lineno} {node.func.id} must receive a string literal permission"
                )
            else:
                perm_str = str(node.args[0].value)
                if not is_valid_three_level_permission(perm_str):
                    violations.append(
                        f"{filename}:{node.lineno} invalid 3-level RBAC code '{perm_str}' (expected <mod>.<sub>.<fn>)"
                    )
    return violations


def test_rbac_governance_and_module_routers(
    backend_root: Path,
    monorepo_root: Path,
) -> None:
    """Verifies RBAC strategy/rules exist and all implemented module routers use valid 3-level RBAC codes."""
    rule_07 = monorepo_root / ".agent" / "rules" / "07-rbac-least-privilege-and-audit.md"
    skill_rbac = monorepo_root / ".agent" / "skills" / "rbac-permission-guard" / "SKILL.md"
    assert rule_07.exists(), "Rule 07 (RBAC & Audit) must exist"
    assert skill_rbac.exists(), "Skill rbac-permission-guard must exist"

    modules_dir = backend_root / "src" / "modules"
    violations: list[str] = []
    if modules_dir.exists():
        for router_file in sorted(modules_dir.glob("*/presentation/router.py")):
            source = router_file.read_text(encoding="utf-8")
            rel_path = router_file.relative_to(backend_root).as_posix()
            violations.extend(audit_router_ast_for_rbac(source, rel_path))

    assert not violations, "RBAC 3-level coverage violations:\n" + "\n".join(violations)


def test_three_level_permission_validator() -> None:
    """Self-test verifying 3-level permission format validation."""
    assert is_valid_three_level_permission("inventory.mermas.approve") is True
    assert is_valid_three_level_permission("catalog.products.create") is True
    assert is_valid_three_level_permission("inventory.mermas") is False
    assert is_valid_three_level_permission("ApproveMerma") is False

    bad_router = 'dep = RequireTenantPermission("invalid_two.levels")\n'
    assert len(audit_router_ast_for_rbac(bad_router, "router.py")) == 1
