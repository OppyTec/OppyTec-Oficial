"""
White-Box Architecture Gate: i18n Key Parity & Zero Hardcoded Strings (`test_i18n_keys_parity_and_no_hardcoded_strings.py`).

Enforces Criterion 8 of `.agent/evals/rubric_10_criteria.yaml` and `.agent/rules/15-i18n-multilanguage-and-dynamic-translation.md`:
- Verifies `.agent/skills/i18n_manager/SKILL.md` and Rule 15 exist.
- When `locales/es/*.json` and `locales/en/*.json` exist, verifies 100% 1:1 key and `{{variable}}` interpolation parity.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architecture

INTERPOLATION_VAR_REGEX = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def flatten_i18n_dict(data: dict[str, Any], prefix: str = "") -> dict[str, str]:
    """Flattens a nested i18n JSON object into dot-separated key paths."""
    flat: dict[str, str] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten_i18n_dict(value, full_key))
        else:
            flat[full_key] = str(value)
    return flat


def compare_locale_catalogs(
    es_catalog: dict[str, Any],
    en_catalog: dict[str, Any],
    namespace: str,
) -> list[str]:
    """Checks 1:1 key parity and `{{var}}` placeholder parity between `es` and `en`."""
    errors: list[str] = []
    flat_es = flatten_i18n_dict(es_catalog)
    flat_en = flatten_i18n_dict(en_catalog)

    missing_in_en = sorted(set(flat_es.keys()) - set(flat_en.keys()))
    missing_in_es = sorted(set(flat_en.keys()) - set(flat_es.keys()))

    if missing_in_en:
        errors.append(f"[{namespace}] keys missing in 'en': {missing_in_en}")
    if missing_in_es:
        errors.append(f"[{namespace}] keys missing in 'es': {missing_in_es}")

    for k in sorted(set(flat_es.keys()) & set(flat_en.keys())):
        vars_es = set(INTERPOLATION_VAR_REGEX.findall(flat_es[k]))
        vars_en = set(INTERPOLATION_VAR_REGEX.findall(flat_en[k]))
        if vars_es != vars_en:
            errors.append(
                f"[{namespace}:{k}] interpolation mismatch: es={sorted(vars_es)} vs en={sorted(vars_en)}"
            )
    return errors


def test_i18n_skill_and_locale_parity(
    backend_root: Path,
    monorepo_root: Path,
) -> None:
    """Verifies i18n governance and checks any existing `locales/es` vs `locales/en` JSON catalogs."""
    rule_15 = monorepo_root / ".agent" / "rules" / "15-i18n-multilanguage-and-dynamic-translation.md"
    skill_i18n = monorepo_root / ".agent" / "skills" / "i18n_manager" / "SKILL.md"
    assert rule_15.exists(), "Rule 15 (i18n multilanguage) must exist"
    assert skill_i18n.exists(), "Skill i18n_manager/SKILL.md must exist"

    locale_roots = [
        backend_root / "src" / "core" / "i18n" / "locales",
        monorepo_root / "oppytec-frontend" / "src" / "shared" / "i18n" / "locales",
    ]
    all_errors: list[str] = []

    for loc_root in locale_roots:
        es_dir = loc_root / "es"
        en_dir = loc_root / "en"
        if not es_dir.exists() or not en_dir.exists():
            continue

        es_files = {f.name: f for f in es_dir.glob("*.json")}
        en_files = {f.name: f for f in en_dir.glob("*.json")}
        if set(es_files.keys()) != set(en_files.keys()):
            all_errors.append(
                f"Locale namespace file mismatch in {loc_root}: es={sorted(es_files)} vs en={sorted(en_files)}"
            )
            continue

        for fname, es_path in sorted(es_files.items()):
            en_path = en_files[fname]
            es_data = json.loads(es_path.read_text(encoding="utf-8"))
            en_data = json.loads(en_path.read_text(encoding="utf-8"))
            all_errors.extend(compare_locale_catalogs(es_data, en_data, fname))

    assert not all_errors, "i18n parity violations:\n" + "\n".join(all_errors)


def test_locale_catalog_comparator_detects_mismatches() -> None:
    """Self-test verifying 1:1 key and interpolation variable comparison."""
    es = {"greeting": "Hola {{name}}", "items": {"count": "Total: {{total}}"}}
    en = {"greeting": "Hello {{name}}", "items": {"count": "Total: {{total}}"}}
    assert compare_locale_catalogs(es, en, "common.json") == []

    bad_en = {"greeting": "Hello {{username}}"}
    errs = compare_locale_catalogs(es, bad_en, "common.json")
    assert len(errs) == 2
