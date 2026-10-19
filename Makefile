# Makefile — Orquestación Determinista y Quality Gates de OppyTec v2.0
.PHONY: fast-gate main-gate deep-gate check smart-merge migration-rebase verify-evals up up-obs down

PYTHON ?= python3
PYTEST ?= $(PYTHON) -m pytest

UV ?= uv

verify-evals:
	@$(PYTHON) scripts/harness.py verify-evals

fast-gate: verify-evals
	@echo "⚡ Ejecutando Fast Gate (< 15s): Integridad Evals + Ruff + Mypy Strict + Tests Unit/Arch/Smoke..."
	@$(UV) --directory oppytec-backend run ruff check .
	@$(UV) --directory oppytec-backend run mypy --strict src/ tests/
	@$(UV) --directory oppytec-backend run pytest tests/unit tests/architecture tests/smoke -q

main-gate: fast-gate
	@echo "🛡️  Ejecutando Main Gate (< 3m): Smoke + Integración + Vectores Red Team 01..11..."
	@$(UV) --directory oppytec-backend run pytest tests/smoke tests/integration tests/security_redteam -q

deep-gate: main-gate
	@echo "🔥 Ejecutando Deep Gate: Contratos Schemathesis + E2E + Auditoría..."
	@$(UV) --directory oppytec-backend run pytest tests/contracts tests/e2e -q

check: fast-gate

smart-merge: verify-evals
	@$(PYTHON) scripts/harness.py status

migration-rebase:
	@$(PYTHON) oppytec-backend/scripts/db_migration.py verify

up:
	docker compose up -d

up-obs:
	docker compose --profile observability up -d

down:
	docker compose --profile observability down
