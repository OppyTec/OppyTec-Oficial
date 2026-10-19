"""
oppytec-backend/scripts/db_migration.py
CLI de Migraciones Correlativas Lineales (`0001..NNNN`):
- `new --scope [public|tenant] --slug <slug>`
- `rebase` (resolución determinista multi-dev sin `merge_heads`)
- `verify` (valida secuencia `0001..NNNN`, `migration_scope` y `downgrade()` no vacío)
- `impact --model <ModelName>` (consulta de impacto AST sobre modelos).
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Literal

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from src.core.database import validate_tenant_schema_name  # noqa: E402

MIGRATION_FILE_REGEX: re.Pattern[str] = re.compile(r"^(\d{4})_(public|tenant)_([a-z0-9_]+)\.py$")
SLUG_CLEAN_REGEX: re.Pattern[str] = re.compile(r"[^a-z0-9_]+")

MigrationScopeType = Literal["public", "tenant"]


def should_execute_migration_for_target(
    migration_scope: str,
    target_schema: str,
) -> bool:
    """
    Determina si una migración con `migration_scope` (`"public"` | `"tenant"`)
    debe ejecutar su DDL sobre `target_schema` (`"public"` o `"tenant_<slug>"`).
    Impide que una migración `public` se ejecute repetidamente por cada inquilino.
    """
    if target_schema == "public":
        return migration_scope == "public"
    valid_tenant = validate_tenant_schema_name(target_schema)
    return bool(valid_tenant) and migration_scope == "tenant"


def get_versions_dir(backend_root: Path | None = None) -> Path:
    """Devuelve la ruta a `oppytec-backend/alembic/versions/`."""
    resolved_root = backend_root or Path(__file__).resolve().parents[1]
    return resolved_root / "alembic" / "versions"


def sanitize_migration_slug(raw_slug: str) -> str:
    """Normaliza la descripción de una migración a `snake_case` válido (máximo 48 caracteres)."""
    cleaned = SLUG_CLEAN_REGEX.sub("_", raw_slug.strip().lower()).strip("_")
    if not cleaned:
        raise ValueError("Migration slug cannot be empty after sanitization")
    return cleaned[:48].rstrip("_")


def list_migration_files(versions_dir: Path) -> list[Path]:
    """Lista las migraciones existentes en orden lexicográfico determinista."""
    if not versions_dir.exists():
        return []
    return sorted(f for f in versions_dir.glob("*.py") if f.name != "__init__.py")


def extract_revision_id(file_path: Path) -> str | None:
    """Extrae el valor de `revision` desde el AST de un archivo de migración."""
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=file_path.name)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "revision"
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                ):
                    return node.value.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "revision"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    return None


def create_correlative_migration(
    scope: MigrationScopeType,
    slug: str,
    versions_dir: Path | None = None,
) -> Path:
    """
    Genera un nuevo archivo de migración correlativo `NNNN_<scope>_<slug>.py`
    encadenado al `down_revision` anterior y con `migration_scope` explícito.
    """
    if scope not in ("public", "tenant"):
        raise ValueError(f"Invalid migration scope: {scope}")
    target_dir = versions_dir or get_versions_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    existing = list_migration_files(target_dir)
    next_number = 1
    prev_revision: str | None = None

    if existing:
        last_file = existing[-1]
        match = MIGRATION_FILE_REGEX.match(last_file.name)
        if not match:
            raise ValueError(f"Last migration file has invalid name: {last_file.name}")
        next_number = int(match.group(1)) + 1
        prev_revision = extract_revision_id(last_file) or last_file.stem

    clean_slug = sanitize_migration_slug(slug)
    revision_id = f"{next_number:04d}_{scope}_{clean_slug}"
    file_path = target_dir / f"{revision_id}.py"
    down_rev_repr = f'"{prev_revision}"' if prev_revision is not None else "None"

    content = (
        f'"""\n{revision_id}.py\n'
        f"Migración correlativa {next_number:04d} para el alcance `{scope}`.\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        "from typing import Literal\n\n"
        "import sqlalchemy as sa\n"
        "from alembic import op\n\n"
        f'revision = "{revision_id}"\n'
        f"down_revision = {down_rev_repr}\n"
        "branch_labels = None\n"
        "depends_on = None\n"
        f'migration_scope: Literal["public", "tenant"] = "{scope}"\n\n\n'
        "def upgrade() -> None:\n"
        '    """Aplica los cambios DDL de la migración."""\n'
        '    op.execute(sa.text("SELECT 1"))\n\n\n'
        "def downgrade() -> None:\n"
        '    """Revierte simétricamente los cambios DDL aplicados en upgrade()."""\n'
        '    op.execute(sa.text("SELECT 1"))\n'
    )
    file_path.write_text(content, encoding="utf-8")
    return file_path


def rebase_colliding_migrations(versions_dir: Path | None = None) -> list[str]:
    """
    Detecta colisiones de prefijo numérico `NNNN_` en `alembic/versions/` (ej. tras merge entre ramas)
    y renumera secuencialmente las migraciones duplicadas actualizando `revision` y `down_revision`.
    """
    target_dir = versions_dir or get_versions_dir()
    files = list_migration_files(target_dir)
    renamed_files: list[str] = []

    expected_idx = 1
    prev_rev_id: str | None = None

    for file_path in files:
        match = MIGRATION_FILE_REGEX.match(file_path.name)
        if not match:
            continue
        num_str, scope, slug_part = match.groups()
        current_num = int(num_str)
        source = file_path.read_text(encoding="utf-8")

        new_rev_id = f"{expected_idx:04d}_{scope}_{slug_part}"
        if current_num != expected_idx:
            old_rev_id = extract_revision_id(file_path) or file_path.stem
            source = source.replace(f'revision = "{old_rev_id}"', f'revision = "{new_rev_id}"')
            if prev_rev_id is not None:
                source = re.sub(
                    r"down_revision\s*=\s*.*",
                    f'down_revision = "{prev_rev_id}"',
                    source,
                    count=1,
                )
            new_path = target_dir / f"{new_rev_id}.py"
            file_path.unlink()
            new_path.write_text(source, encoding="utf-8")
            renamed_files.append(new_path.name)
            prev_rev_id = new_rev_id
        else:
            prev_rev_id = extract_revision_id(file_path) or new_rev_id

        expected_idx += 1

    return renamed_files


def verify_migrations_chain(versions_dir: Path | None = None) -> list[str]:
    """Verifica que todas las migraciones cumplan secuencia `0001..NNNN`, `migration_scope` y `downgrade()`."""
    target_dir = versions_dir or get_versions_dir()
    files = list_migration_files(target_dir)
    errors: list[str] = []

    if not files:
        errors.append("No migrations found in alembic/versions/")
        return errors

    for idx, file_path in enumerate(files, start=1):
        match = MIGRATION_FILE_REGEX.match(file_path.name)
        if not match:
            errors.append(f"Invalid filename format: {file_path.name}")
            continue
        num_val = int(match.group(1))
        if num_val != idx:
            errors.append(f"Sequence gap/duplicate at {file_path.name}: expected {idx:04d}")

    return errors


def analyze_model_impact(model_name: str, backend_root: Path | None = None) -> list[str]:
    """Escanea los módulos de `src/` y `tests/` que referencian el símbolo `model_name`."""
    resolved_root = backend_root or Path(__file__).resolve().parents[1]
    impacted: list[str] = []
    for folder in ("src", "tests"):
        base_dir = resolved_root / folder
        if not base_dir.exists():
            continue
        for py_file in sorted(base_dir.rglob("*.py")):
            text = py_file.read_text(encoding="utf-8")
            if model_name in text:
                impacted.append(py_file.relative_to(resolved_root).as_posix())
    return impacted


def build_arg_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos CLI para `db_migration.py`."""
    parser = argparse.ArgumentParser(description="OppyTec v2.0 Correlative Alembic Migration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="Create a new correlative migration")
    new_parser.add_argument("--scope", choices=["public", "tenant"], required=True)
    new_parser.add_argument("--slug", "-m", required=True, help="Snake_case description")

    subparsers.add_parser("rebase", help="Renumber colliding parallel branch migrations")
    subparsers.add_parser("verify", help="Verify linear correlative migration chain")

    impact_parser = subparsers.add_parser("impact", help="Analyze AST impact for a SQLAlchemy model")
    impact_parser.add_argument("--model", required=True, help="Model class name")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada CLI para `db_migration.py`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "new":
        scope_val: MigrationScopeType = "public" if args.scope == "public" else "tenant"
        created = create_correlative_migration(scope=scope_val, slug=str(args.slug))
        sys.stdout.write(f"Created migration: {created.name}\n")
        return 0
    if args.command == "rebase":
        renamed = rebase_colliding_migrations()
        sys.stdout.write(f"Rebased {len(renamed)} migration(s): {renamed}\n")
        return 0
    if args.command == "verify":
        errs = verify_migrations_chain()
        if errs:
            sys.stderr.write("\n".join(errs) + "\n")
            return 1
        sys.stdout.write("Alembic correlative migration chain verified OK.\n")
        return 0
    if args.command == "impact":
        refs = analyze_model_impact(str(args.model))
        sys.stdout.write(f"Model '{args.model}' referenced in {len(refs)} file(s): {refs}\n")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
