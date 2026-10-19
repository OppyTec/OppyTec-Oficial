"""
White-Box Architecture Gate: Clean Architecture Boundaries (`test_clean_architecture.py`).

Enforces Criterion 2 of `.agent/evals/rubric_10_criteria.yaml`:
- `oppytec-backend/src/modules/*/domain/` must remain 100% pure Python + `decimal.Decimal` + domain dataclasses/value objects.
- `domain/` is strictly forbidden from importing infrastructure or presentation frameworks:
  `fastapi`, `sqlalchemy`, `httpx`, `redis`, `alembic`, `asyncpg`, `uvicorn`.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

FORBIDDEN_DOMAIN_IMPORTS: frozenset[str] = frozenset(
    {
        "fastapi",
        "sqlalchemy",
        "httpx",
        "redis",
        "alembic",
        "asyncpg",
        "uvicorn",
        "starlette",
    }
)


def find_forbidden_imports_in_source(source_code: str, filename: str = "<memory>") -> list[str]:
    """Parses Python source AST and returns any forbidden top-level imports."""
    tree = ast.parse(source_code, filename=filename)
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                if root_pkg in FORBIDDEN_DOMAIN_IMPORTS:
                    violations.append(
                        f"{filename}:{node.lineno} forbidden import '{alias.name}'"
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            root_pkg = node.module.split(".")[0]
            if root_pkg in FORBIDDEN_DOMAIN_IMPORTS:
                violations.append(
                    f"{filename}:{node.lineno} forbidden from-import '{node.module}'"
                )
    return violations


def test_domain_layers_have_zero_infrastructure_imports(backend_root: Path) -> None:
    """Scans all `src/modules/*/domain/**/*.py` files via AST for forbidden imports."""
    modules_dir = backend_root / "src" / "modules"
    all_violations: list[str] = []

    if modules_dir.exists():
        for domain_file in sorted(modules_dir.glob("*/domain/**/*.py")):
            source = domain_file.read_text(encoding="utf-8")
            rel_path = domain_file.relative_to(backend_root).as_posix()
            all_violations.extend(find_forbidden_imports_in_source(source, rel_path))

    assert not all_violations, (
        "Clean Architecture violation in domain/ layer:\n" + "\n".join(all_violations)
    )


def test_ast_scanner_detects_forbidden_framework_imports() -> None:
    """Self-test ensuring the AST scanner catches FastAPI, SQLAlchemy, HTTPX, and Redis."""
    pure_domain_code = (
        "from dataclasses import dataclass\n"
        "from decimal import Decimal\n\n"
        "@dataclass(frozen=True)\n"
        "class Money:\n"
        "    amount: Decimal\n"
    )
    assert find_forbidden_imports_in_source(pure_domain_code) == []

    impure_domain_code = (
        "from decimal import Decimal\n"
        "import fastapi\n"
        "from sqlalchemy.ext.asyncio import AsyncSession\n"
        "import httpx\n"
        "from redis.asyncio import Redis\n"
    )
    detected = find_forbidden_imports_in_source(impure_domain_code, "domain/bad.py")
    assert len(detected) == 4
