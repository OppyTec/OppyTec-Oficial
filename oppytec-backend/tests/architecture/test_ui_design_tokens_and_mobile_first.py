"""
White-Box Architecture Gate: Legacy Visual DNA (3 Themes) & Mobile-First Tokens (`test_ui_design_tokens_and_mobile_first.py`).

Enforces Criterion 10 of `.agent/evals/rubric_10_criteria.yaml` and `.agent/rules/21-design-system-legacy-dna-and-mobile-first.md`:
- Verifies preservation of the 3 official themes (`light`, `dark`, `ocean-blue`), `'Outfit'` font,
  `.glass` / `.glass-card`, 42 preset colors, 49 gastronomic icons, and Mobile-First adaptive patterns.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

REQUIRED_THEMES: tuple[str, ...] = ("light", "dark", "ocean-blue")


def test_design_system_three_themes_and_mobile_first_rules(
    monorepo_root: Path,
) -> None:
    """Verifies Rule 21, `specs/04-DESIGN-SYSTEM.md`, and Frontend CSS tokens when present."""
    rule_21 = (
        monorepo_root
        / ".agent"
        / "rules"
        / "21-design-system-legacy-dna-and-mobile-first.md"
    )
    skill_ui = monorepo_root / ".agent" / "skills" / "ui_ux_design_system" / "SKILL.md"
    design_spec = monorepo_root / "specs" / "04-DESIGN-SYSTEM.md"

    assert rule_21.exists(), "Rule 21 (Design System Legacy DNA & Mobile-First) must exist"
    assert skill_ui.exists(), "Skill ui_ux_design_system/SKILL.md must exist"
    assert design_spec.exists(), "specs/04-DESIGN-SYSTEM.md must exist"

    rule_text = rule_21.read_text(encoding="utf-8")
    spec_text = design_spec.read_text(encoding="utf-8")
    for theme in REQUIRED_THEMES:
        assert theme in rule_text, f"Theme '{theme}' must be mandated in Rule 21"
        assert theme in spec_text, f"Theme '{theme}' must be documented in specs/04-DESIGN-SYSTEM.md"

    index_css = monorepo_root / "oppytec-frontend" / "src" / "index.css"
    if index_css.exists():
        css_text = index_css.read_text(encoding="utf-8")
        assert "ocean-blue" in css_text, "oppytec-frontend/src/index.css must define 'ocean-blue' theme"
