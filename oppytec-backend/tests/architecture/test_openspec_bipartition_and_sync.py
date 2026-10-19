"""
White-Box Architecture Gate: OpenSpec Bipartition & Vault Synchronization (`test_openspec_bipartition_and_sync.py`).

Enforces Criterion 1 of `.agent/evals/rubric_10_criteria.yaml` and `.agent/rules/12-openspec-bipartition-and-sync.md`:
- `specs/openspec.config.yaml` defines the two strict vaults: `specs/business-domain` and `specs/engineering-code`.
- `specs/business-domain/` and `specs/engineering-code/` vaults are governed so that `business-domain/*.business.spec.md`
  contains 0% SQL or technical code paths (`CREATE TABLE`, `sqlalchemy`, `FastAPI`, `.py`, `.tsx`) and pairs 1:1 with `engineering-code/*.code.spec.md`.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture


def validate_business_spec_content(content: str, forbidden_patterns: list[str]) -> list[str]:
    """Returns any forbidden technical/SQL patterns found inside a business-domain spec."""
    return [pat for pat in forbidden_patterns if pat in content]


def test_openspec_bipartition_config_and_vaults(monorepo_root: Path) -> None:
    """Verifies `specs/openspec.config.yaml` and validates vault bipartition rules."""
    config_path = monorepo_root / "specs" / "openspec.config.yaml"
    assert config_path.exists(), "specs/openspec.config.yaml must exist"

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert config["schema"] == "spec-driven"
    vaults = config["vaults"]
    assert "business_domain" in vaults
    assert "engineering_code" in vaults

    bd_cfg = vaults["business_domain"]
    ec_cfg = vaults["engineering_code"]
    assert bd_cfg["path"] == "specs/business-domain"
    assert bd_cfg["suffix"] == ".business.spec.md"
    assert ec_cfg["path"] == "specs/engineering-code"
    assert ec_cfg["suffix"] == ".code.spec.md"
    assert "jev_system1_evaluation" in ec_cfg["required_frontmatter_keys"]

    forbidden_patterns: list[str] = list(bd_cfg.get("forbidden_patterns", []))
    assert "CREATE TABLE" in forbidden_patterns
    assert "sqlalchemy" in forbidden_patterns

    bd_dir = monorepo_root / bd_cfg["path"]
    ec_dir = monorepo_root / ec_cfg["path"]

    if bd_dir.exists():
        for b_spec in sorted(bd_dir.glob("*.business.spec.md")):
            text = b_spec.read_text(encoding="utf-8")
            found = validate_business_spec_content(text, forbidden_patterns)
            assert not found, f"{b_spec.name} contains forbidden technical patterns: {found}"

            stem_prefix = b_spec.name.replace(".business.spec.md", "")
            paired = ec_dir / f"{stem_prefix}.code.spec.md"
            assert paired.exists(), f"Missing 1:1 paired engineering spec: {paired}"
