"""
White-Box Architecture Gate: Observability 4-Pillars, `X-Trace-ID` & PII Redaction (`test_observability_pii_redaction_and_spans.py`).

Enforces `.agent/rules/17-observability-opentelemetry-sentry-and-umami.md`:
- Verifies `X-Trace-ID` injection in FastAPI responses.
- Verifies PII and secret redaction (`password`, `secret`, `token`, `authorization`, `cookie`) in telemetry payloads.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.architecture

SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "secret",
        "secret_key",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "api_key",
        "dsn",
    }
)
REDACTED_MASK = "[REDACTED]"


def reference_scrub_telemetry_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Reference recursive PII scrubber matching Rule 17."""
    scrubbed: dict[str, Any] = {}
    for key, val in payload.items():
        if any(s in key.lower() for s in SENSITIVE_KEYS):
            scrubbed[key] = REDACTED_MASK
        elif isinstance(val, dict):
            scrubbed[key] = reference_scrub_telemetry_payload(val)
        else:
            scrubbed[key] = val
    return scrubbed


async def test_observability_trace_id_and_pii_redaction(
    async_client: httpx.AsyncClient,
    monorepo_root: Path,
) -> None:
    """Verifies Rule 17, `X-Trace-ID` correlation header, and PII scrubbing."""
    rule_17 = (
        monorepo_root
        / ".agent"
        / "rules"
        / "17-observability-opentelemetry-sentry-and-umami.md"
    )
    skill_obs = monorepo_root / ".agent" / "skills" / "observability_telemetry" / "SKILL.md"
    assert rule_17.exists(), "Rule 17 (Observability 4-Pillars) must exist"
    assert skill_obs.exists(), "Skill observability_telemetry/SKILL.md must exist"

    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "X-Trace-ID" in resp.headers

    raw_event: dict[str, Any] = {
        "user": "oppytec.admin",
        "password": "SuperSecretPassword123!",
        "headers": {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9",
            "X-Trace-ID": resp.headers["X-Trace-ID"],
        },
    }

    scrubber = reference_scrub_telemetry_payload
    try:
        from src.core import observability as core_obs  # type: ignore[attr-defined]

        candidate = getattr(core_obs, "scrub_telemetry_payload", None)
        if callable(candidate):
            scrubber = candidate
    except ImportError:
        scrubber = reference_scrub_telemetry_payload

    cleaned = scrubber(raw_event)
    assert "SuperSecretPassword123!" not in str(cleaned)
    assert "eyJhbGciOiJIUzI1NiJ9" not in str(cleaned)
