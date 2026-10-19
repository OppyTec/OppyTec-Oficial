# Makefile — Orquestación Determinista y Quality Gates de OppyTec v2.0
.PHONY: fast-gate main-gate deep-gate check smart-merge migration-rebase verify-evals up up-obs down

PYTHON ?= python3
PYTEST ?= $(PYTHON) -m pytest

verify-evals:
	@$(PYTHON) scripts/harness.py verify-evals

fast-gate: verify-evals
	@echo "⚡ Ejecutando Fast Gate (< 15s): Integridad Evals + Tests Unitarios y de Arquitectura..."
	@cd oppytec-backend && $(PYTEST) tests/unit tests/architecture -q

main-gate: fast-gate
	@echo "🛡️  Ejecutando Main Gate (< 3m): Smoke + Integración + Vectores Red Team 01..11..."
	@cd oppytec-backend && $(PYTEST) tests/smoke tests/integration tests/security_redteam -q

deep-gate: main-gate
	@echo "🔥 Ejecutando Deep Gate: Contratos Schemathesis + E2E + Auditoría..."
	@cd oppytec-backend && $(PYTEST) tests/contracts tests/e2e -q

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
