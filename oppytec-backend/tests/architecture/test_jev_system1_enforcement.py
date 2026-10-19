"""
White-Box Architecture Gate: JEV (System 1) Decision Engine Enforcement (`test_jev_system1_enforcement.py`).

Enforces Criterion 1 & 9 of `.agent/evals/rubric_10_criteria.yaml` and `.agent/rules/14-jev-system1-mandatory-gate.md`:
- Verifies JEV System 1 skill/contracts and `.agent/guardrails/jev_policies.yaml`.
- Verifies mandatory `jev_system1_evaluation` gate in `specs/openspec.config.yaml` and engineering specs.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture


def test_jev_system1_gate_and_policies(monorepo_root: Path) -> None:
    """Verifies JEV System 1 rule, skill, policies, and mandatory OpenSpec evaluation gate."""
    rule_14 = monorepo_root / ".agent" / "rules" / "14-jev-system1-mandatory-gate.md"
    jev_skill = monorepo_root / ".agent" / "skills" / "jev-decision-engine" / "SKILL.md"
    jev_policies = monorepo_root / ".agent" / "guardrails" / "jev_policies.yaml"
    openspec_cfg_path = monorepo_root / "specs" / "openspec.config.yaml"

    assert rule_14.exists(), "Rule 14 (JEV System 1 Mandatory Gate) must exist"
    assert jev_skill.exists(), "Skill jev-decision-engine/SKILL.md must exist"
    assert jev_policies.exists(), ".agent/guardrails/jev_policies.yaml must exist"

    policies = yaml.safe_load(jev_policies.read_text(encoding="utf-8"))
    assert policies["mode"] == "enforcing"
    assert "OppyTec-Legacy/**" in policies["immutable_read_only_paths"]

    openspec_cfg = yaml.safe_load(openspec_cfg_path.read_text(encoding="utf-8"))
    req_keys = openspec_cfg["vaults"]["engineering_code"]["required_frontmatter_keys"]
    assert "jev_system1_evaluation" in req_keys

    ec_dir = monorepo_root / "specs" / "engineering-code"
    if ec_dir.exists():
        for code_spec in sorted(ec_dir.glob("*.code.spec.md")):
            content = code_spec.read_text(encoding="utf-8")
            assert "jev_system1_evaluation:" in content, (
                f"{code_spec.name} is missing mandatory 'jev_system1_evaluation' gate"
            )
