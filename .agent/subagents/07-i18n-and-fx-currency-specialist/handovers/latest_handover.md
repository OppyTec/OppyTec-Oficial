# Handover — Agente 07 (i18n + FX + Realtime) — Fase 3

## Completed
- `core/i18n`: traductor estático (es/en, fallback es, `{{var}}`), `dynamic_field_sync` (filtro de nombres propios, dedupe SHA-256, prompt Pi minimalista), locales `common`/`errors` en paridad 1:1.
- `core/fx`: providers BCCh/BCE (Decimal), triangulación CLP/USD/EUR/BRL/UF, `anomaly_guard` (>0.08), override manual auditado.
- `core/realtime`: envelope, manager aislado por canal con RBAC de 3 niveles, publisher Pub/Sub+Stream con catch-up, router WS `/api/v1/ws/realtime` con JWT.
- Tests: `tests/unit/test_i18n_fx_and_realtime.py` (10 tests). ruff, mypy --strict y pytest pasan.

## Friction & Failures
- El agente previo se cortó por cuota; se revisó y validó su trabajo sin cambios de fondo.
- Encadenar uv run en un solo comando se colgó; ejecutar cada check por separado.

## Next Exact Action
- Merge Train (Agente 11); conectar i18n/FX/realtime a los routers de dominio en fases posteriores.
