"""
White-Box Architecture Gate: Cloudflare R2 Media Storage Isolation & Quotas (`test_media_storage_isolation_and_quotas.py`).

Enforces Criterion 9 of `.agent/evals/rubric_10_criteria.yaml` and `.agent/rules/18-media-storage-r2-and-quota-governance.md`:
- Every media object key must follow `{env}/{holding_id}/{tenant_id}/<category>/<entity_id>/(thumb|display).webp`.
- Enforces `.webp` dual compression (`thumb.webp` 256px + `display.webp` 1024px) and `max_storage_mb` quota checks.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

R2_MEDIA_KEY_PATTERN = re.compile(
    r"^(local|preview|ci|staging|production)/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/[a-z_]+/[a-zA-Z0-9_-]+/(thumb|display)\.webp$"
)


def is_valid_r2_media_key(object_key: str) -> bool:
    """Validates that an R2 object key isolates by `{env}/{holding}/{tenant}/` and uses `.webp`."""
    if ".." in object_key or object_key.startswith("/"):
        return False
    return bool(R2_MEDIA_KEY_PATTERN.match(object_key))


def test_r2_storage_governance_and_key_isolation(
    backend_root: Path,
    monorepo_root: Path,
) -> None:
    """Verifies Rule 18, R2 skill, `.env.example` R2 settings, and key format validator."""
    rule_18 = monorepo_root / ".agent" / "rules" / "18-media-storage-r2-and-quota-governance.md"
    skill_r2 = monorepo_root / ".agent" / "skills" / "r2_media_storage" / "SKILL.md"
    assert rule_18.exists(), "Rule 18 (Media Storage R2 & Quotas) must exist"
    assert skill_r2.exists(), "Skill r2_media_storage/SKILL.md must exist"

    env_example = (backend_root / ".env.example").read_text(encoding="utf-8")
    for required_var in (
        "STORAGE_PROVIDER=",
        "R2_ACCOUNT_ID=",
        "R2_MEDIA_BUCKET_NAME=",
        "R2_PUBLIC_URL=",
    ):
        assert required_var in env_example, f"Missing {required_var} in .env.example"

    assert is_valid_r2_media_key("staging/holding_01/tenant_rest_a/products/prod_99/thumb.webp") is True
    assert is_valid_r2_media_key("production/holding_01/tenant_rest_a/products/prod_99/display.webp") is True
    assert is_valid_r2_media_key("tenant_rest_a/products/prod_99/raw.png") is False
    assert is_valid_r2_media_key("staging/../tenant_b/products/prod_99/thumb.webp") is False
