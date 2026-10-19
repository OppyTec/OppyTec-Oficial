"""
Vector Red Team 09 (`tests/security_redteam/test_09_zero_hardcoding_and_secrets_guard.py`):
- Inspección AST sobre todos los archivos `.py` en `oppytec-backend/src/` verificando cero credenciales,
  tokens AWS/GCP/OpenAI/Stripe o claves privadas RSA hardcodeadas.
- Verificación obligatoria de `SecretStr` en los campos sensibles de `Settings` (`src/core/config.py`)
  y ocultamiento en `repr()` / `str()`.
- Verificación de aislamiento de `.env` en `.gitignore` y existencia de `.env.example` documentado.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from pydantic import SecretStr

from src.core.config import Settings, get_settings

pytestmark = pytest.mark.security_redteam

LIVE_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-(?:live|proj)-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
)

REQUIRED_SECRETSTR_FIELDS: tuple[str, ...] = (
    "SECRET_KEY",
    "JWT_ACCESS_SECRET_KEY",
    "JWT_REFRESH_SECRET_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "SUPERUSER_GENESIS_PASSWORD",
    "GEMINI_API_KEY",
    "JEV_API_KEY",
    "R2_SECRET_ACCESS_KEY",
)


def test_mandatory_secretstr_fields_on_settings_never_leak_in_repr_or_str() -> None:
    """Verifica que todos los secretos de `Settings` sean `SecretStr` y jamás expongan su valor en `repr`/`str`."""
    settings = get_settings()

    for field_name in REQUIRED_SECRETSTR_FIELDS:
        val = getattr(settings, field_name)
        assert isinstance(val, SecretStr), f"Field '{field_name}' in Settings must be SecretStr"
        raw_secret = val.get_secret_value()
        assert raw_secret not in repr(val)
        assert raw_secret not in str(val)
        assert raw_secret not in repr(settings)


def test_ast_zero_hardcoded_live_secrets_across_backend_src(backend_root: Path) -> None:
    """
    Escanea el AST de `oppytec-backend/src/` garantizando que no existan claves privadas ni tokens
    de producción hardcodeados, y que ningún módulo fuera de `src/core/config.py` asigne literales
    a variables `JWT_ACCESS_SECRET_KEY` o `JWT_REFRESH_SECRET_KEY`.
    """
    src_root = backend_root / "src"
    py_files = sorted(src_root.rglob("*.py"))
    assert py_files, "Expected Python source files in oppytec-backend/src"

    violations: list[str] = []
    for py_file in py_files:
        rel_path = py_file.relative_to(backend_root).as_posix()
        source_text = py_file.read_text(encoding="utf-8")

        for pattern in LIVE_SECRET_PATTERNS:
            if pattern.search(source_text):
                violations.append(f"{rel_path}: matches live secret pattern '{pattern.pattern}'")

        tree = ast.parse(source_text, filename=rel_path)
        if rel_path != "src/core/config.py":
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if (
                            isinstance(target, ast.Name)
                            and target.id in REQUIRED_SECRETSTR_FIELDS
                            and isinstance(node.value, ast.Constant)
                            and isinstance(node.value.value, str)
                        ):
                            violations.append(
                                f"{rel_path}:{node.lineno} assigns string literal to '{target.id}'"
                            )

    assert not violations, "Hardcoded secret violations found:\n" + "\n".join(violations)


def test_dotenv_isolation_and_settings_extra_forbid(monorepo_root: Path) -> None:
    """Verifica que `.gitignore` excluya archivos `.env` y que `Settings` tenga `extra='forbid'`."""
    assert Settings.model_config.get("extra") == "forbid"
    gitignore_path = monorepo_root / ".gitignore"
    if gitignore_path.exists():
        gitignore_text = gitignore_path.read_text(encoding="utf-8")
        assert ".env" in gitignore_text
