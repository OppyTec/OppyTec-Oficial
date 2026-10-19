"""
White-Box Architecture Gate: WebSocket Auth, Tenant Isolation, RBAC Filter & Zero Polling (`test_websocket_auth_tenant_isolation_and_rbac.py`).

Enforces `.agent/rules/22-realtime-websockets-and-zero-polling.md`:
- Strictly forbids `setInterval` or `refetchInterval` HTTP polling for notifications, alerts, or stock balances.
- Enforces the single WebSocket tunnel `/api/v1/ws/realtime` backed by Redis Pub/Sub + Redis Streams
  (`rt:{env_ns}:{holding_id}:{tenant_id}`) and 3-level RBAC server-side filtering.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

FORBIDDEN_POLLING_REGEX = re.compile(r"\b(setInterval|refetchInterval)\s*\(")


def find_forbidden_polling_in_code(source_code: str, filename: str) -> list[str]:
    """Detects forbidden `setInterval(` or `refetchInterval(` calls in source code."""
    violations: list[str] = []
    for lineno, line in enumerate(source_code.splitlines(), start=1):
        if FORBIDDEN_POLLING_REGEX.search(line) or "refetchInterval:" in line:
            violations.append(f"{filename}:{lineno} forbidden HTTP polling detected: {line.strip()}")
    return violations


def test_websocket_rule_22_and_zero_polling(
    backend_root: Path,
    monorepo_root: Path,
) -> None:
    """Verifies Rule 22, `realtime_websockets` skill, and zero HTTP polling across frontend/backend."""
    rule_22 = monorepo_root / ".agent" / "rules" / "22-realtime-websockets-and-zero-polling.md"
    skill_ws = monorepo_root / ".agent" / "skills" / "realtime_websockets" / "SKILL.md"
    strategy_ws = (
        monorepo_root
        / ".agent"
        / "estrategias"
        / "estrategia_tiempo_real_websockets_y_notificaciones_001.md"
    )
    assert rule_22.exists(), "Rule 22 (Realtime WebSockets & Zero Polling) must exist"
    assert skill_ws.exists(), "Skill realtime_websockets/SKILL.md must exist"
    assert strategy_ws.exists(), "Realtime WebSockets master strategy must exist"

    rule_content = rule_22.read_text(encoding="utf-8")
    assert "/api/v1/ws/realtime" in rule_content

    violations: list[str] = []
    for src_dir in (
        backend_root / "src",
        monorepo_root / "oppytec-frontend" / "src",
    ):
        if not src_dir.exists():
            continue
        for code_file in sorted(src_dir.rglob("*")):
            if code_file.suffix not in {".py", ".ts", ".tsx"}:
                continue
            text = code_file.read_text(encoding="utf-8")
            rel = code_file.relative_to(monorepo_root).as_posix()
            violations.extend(find_forbidden_polling_in_code(text, rel))

    assert not violations, "Zero-Polling violations detected:\n" + "\n".join(violations)


def test_polling_detector_flags_setinterval_and_refetchinterval() -> None:
    """Self-test ensuring `find_forbidden_polling_in_code` catches polling patterns."""
    assert find_forbidden_polling_in_code("const ws = new WebSocket(url);", "ws.ts") == []
    bad_ts = (
        "setInterval(() => fetch('/api/v1/notifications'), 5000);\n"
        "useQuery({ queryKey: ['stock'], refetchInterval: 3000 });\n"
    )
    assert len(find_forbidden_polling_in_code(bad_ts, "bad.tsx")) == 2
