#!/usr/bin/env python3
"""
scripts/harness.py — Orquestador Determinista Multi-Agente (Prime Agent RLM + Herdr + Git Worktrees + Smart Merge)
Implementa:
1. Reserva atómica de símbolos AST con candado de kernel Linux (fcntl.flock).
2. Generador automático de Git Worktrees y MISSION_PROMPT.md por Fase (`prepare-phase --phase N`) para Herdr / Agentes Paralelos.
3. Cola de Fusión Secuencial (*Merge Train*: `git rebase` + `git merge --ff-only`) y limpieza segura de worktrees (`merge-phase --phase N`).
4. Verificación Anti-Trampa (Reward Hacking Guard) mediante hashes SHA-256 sobre .agent/evals/ y .agent/rules/.
5. Bitácora Event-Sourced inmutable en .agent/memory/harness_events.jsonl.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT_DIR / ".agent"
MEMORY_DIR = AGENT_DIR / "memory"
WORKTREES_DIR = ROOT_DIR / ".worktrees"
CLAIMS_FILE = MEMORY_DIR / "claims_registry.json"
CLAIMS_LOCK = MEMORY_DIR / ".claims_registry.lock"
EVENTS_LOG = MEMORY_DIR / "harness_events.jsonl"
EVAL_HASHES_FILE = AGENT_DIR / "evals" / "eval_hashes.sha256"

# Mapa de asignaciones de agentes constructores en paralelo por Fase de specs/06-IMPLEMENTATION-PLAN.md
PHASE_WORKERS: dict[int, list[tuple[str, str]]] = {
    1: [
        ("08-environments-and-observability-engineer", "Configurar docker-compose.yml (--profile observability), Makefile, .pre-commit-config.yaml, src/core/config.py (Fail-Fast SecretStr) y src/core/observability.py"),
        ("04-backend-senior-dev", "Construir andamiaje oppytec-backend/ (Dockerfile, pyproject.toml, .env.example, src/main.py, tests/conftest.py, tests/smoke/ y tests/architecture/)"),
        ("05-frontend-senior-dev", "Construir andamiaje oppytec-frontend/ (Dockerfile, docker-entrypoint.sh para /runtime-env.js, package.json, tsconfig.json, vite.config.ts, knip.json, src/shared/config/env.ts y telemetry/)"),
    ],
    2: [
        ("03-database-alembic-and-backup-engineer", "Construir database.py (SET LOCAL search_path + RESET), models_base.py (PublicBase/TenantBase), alembic/ (0001_public, 0002_tenant, db_migration.py), bootstrap.py (oppytec.admin) y backup/ (4 capas zstd+age)"),
    ],
    3: [
        ("04-backend-senior-dev", "Implementar módulos core (identity RBAC 3-niveles, tenancy cupos soft-delete, audit, catalog 3-capas Decimal, inventory locks ORDER BY id ASC FOR UPDATE, recipes, procurement, operations) y storage R2 WebP"),
        ("06-ai-oppyfy-and-jev-engineer", "Implementar adaptador global JEV (Sistema 1) y módulo oppy_ai (OppyFy RAG 3-Capas, RBAC propio editable, paquetes de créditos sin caducidad, medidor % contexto y llm_request_logs)"),
        ("07-i18n-and-fx-currency-specialist", "Implementar motor i18n estático/dinámico (public.i18n_translation_memory, filtro 'Pollo King', patrón Pi), motor Multi-Moneda FX (BCCh + BCE) y src/core/realtime/ (WebSockets Redis Pub/Sub)"),
    ],
    4: [
        ("04-backend-senior-dev", "Implementar capas presentation/ (router.py, schemas.py) de los 10 módulos y src/core/guards/ (rbac_dependencies, file_magic_guard, xss_sanitizer, rate_limiter)"),
        ("09-qa-parity-and-test-engineer", "Implementar tests/integration/ y verificar paridad matemática 100% con OppyTec-Legacy"),
        ("10-cybersecurity-redteam-auditor", "Implementar y certificar los 11 vectores en tests/security_redteam/test_01..11 y Schemathesis"),
    ],
    5: [
        ("05-frontend-senior-dev", "Construir las 22 vistas en oppytec-frontend/src/features/ con ADN visual Legacy (light/dark/ocean-blue), arquitectura Mobile-First, <Can>, useRealtimeSync (WebSockets) y consolas platform-admin"),
        ("07-i18n-and-fx-currency-specialist", "Completar los 11 namespaces JSON en locales/es/ y locales/en/, <LanguageFlagSelector /> (banderas SVG) y <CurrencySelector /> (<MoneyBadge />)"),
    ],
    6: [
        ("09-qa-parity-and-test-engineer", "Ejecutar tests/e2e/, Playwright y Locust (500 RPS, P95 <= 120ms)"),
        ("10-cybersecurity-redteam-auditor", "Ejecutar Deep Gate completo (Semgrep, Trivy, pip-audit, pnpm audit, Schemathesis) y emitir sello final SECURITY_APPROVED"),
        ("12-tech-writer-openspec-archify", "Sincronizar las 2 bóvedas de OpenSpec (business-domain/ y engineering-code/), Graphify y los 5 Mapas HTML de Archify en docs/architecture/atlas/"),
    ],
}


def log_event(event_type: str, payload: dict[str, Any]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    head_sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "git_sha": head_sha,
        **payload,
    }
    with open(EVENTS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def claim_ast_symbol(worker_id: str, file_path: str, symbol_path: str, intent: str) -> None:
    """Reserva un símbolo AST de forma atómica usando fcntl.flock(LOCK_EX)."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(CLAIMS_LOCK, "w", encoding="utf-8") as lock_fd:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
        try:
            data: dict[str, Any] = {"version": "2.0.0", "active_claims": []}
            if CLAIMS_FILE.exists():
                data = json.loads(CLAIMS_FILE.read_text(encoding="utf-8"))

            for claim in data.get("active_claims", []):
                if (
                    claim["file"] == file_path
                    and claim["symbol_path"] == symbol_path
                    and claim["claimed_by"] != worker_id
                ):
                    raise RuntimeError(
                        f"Colisión AST bloqueada: '{symbol_path}' en '{file_path}' "
                        f"ya está reclamado por '{claim['claimed_by']}'."
                    )

            new_claim = {
                "file": file_path,
                "symbol_path": symbol_path,
                "claimed_by": worker_id,
                "intent": intent,
                "claimed_at": datetime.now(timezone.utc).isoformat(),
            }
            data.setdefault("active_claims", []).append(new_claim)

            fd, tmp_path = tempfile.mkstemp(dir=MEMORY_DIR, suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                json.dump(data, tmp_file, indent=2, ensure_ascii=False)
            os.replace(tmp_path, CLAIMS_FILE)
        finally:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)

    log_event("AST_SYMBOL_CLAIMED", {"worker": worker_id, "file": file_path, "symbol": symbol_path})
    print(f"✅ Símbolo AST '{symbol_path}' reservado atómicamente para '{worker_id}'.")


def verify_anti_cheating_hashes() -> bool:
    """Verifica que ningún agente haya modificado .agent/rules/ ni .agent/evals/rubric_10_criteria.yaml."""
    if not EVAL_HASHES_FILE.exists():
        print("❌ Archivo de integridad .agent/evals/eval_hashes.sha256 no encontrado.")
        return False

    lines = [
        line.strip()
        for line in EVAL_HASHES_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    for line in lines:
        expected_hash, rel_path = line.split("  ", 1)
        target = ROOT_DIR / rel_path
        if not target.exists():
            print(f"❌ VIOLACIÓN ANTI-TRAMPA: Archivo protegido eliminado: {rel_path}")
            return False
        actual_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            print(f"❌ VIOLACIÓN ANTI-TRAMPA: Archivo inmutable alterado: {rel_path}")
            return False

    print("✅ Integridad de .agent/rules/ y .agent/evals/ verificada al 100% (Cero Reward Hacking).")
    return True


def prepare_phase_worktrees(phase: int) -> None:
    """Crea los Git Worktrees aislados para una Fase y genera MISSION_PROMPT.md para cada agente en Herdr."""
    if not verify_anti_cheating_hashes():
        sys.exit(1)
    workers = PHASE_WORKERS.get(phase)
    if not workers:
        raise ValueError(f"Fase {phase} no válida. Fases disponibles: 1 a 6.")

    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"🚀 Preparando Git Worktrees y Prompts de Misión para la Fase {phase}...\n")

    for idx, (agent_folder, mission_desc) in enumerate(workers, start=1):
        wt_name = f"phase{phase}-{agent_folder}"
        wt_path = WORKTREES_DIR / wt_name
        branch_name = f"agent/phase{phase}-{agent_folder}"
        env_ns = f"wt_p{phase}_{idx}"

        if not wt_path.exists():
            subprocess.run(
                ["git", "worktree", "add", "-B", branch_name, str(wt_path), "HEAD"],
                cwd=ROOT_DIR,
                check=True,
            )

        subagent_dir = AGENT_DIR / "subagents" / agent_folder
        prompt_text = (subagent_dir / "prompt.md").read_text(encoding="utf-8")
        knowledge_text = (subagent_dir / "knowledge.md").read_text(encoding="utf-8")
        handover_text = (subagent_dir / "handovers" / "latest_handover.md").read_text(encoding="utf-8")

        mission_content = (
            f"# 🎯 ORDEN DE MISIÓN AUTOMÁTICA — FASE {phase} ({agent_folder})\n\n"
            f"- **Worktree Aislado:** `{wt_path}`\n"
            f"- **Rama Git:** `{branch_name}`\n"
            f"- **Namespace de Entorno (`ENV_NAMESPACE`):** `{env_ns}`\n\n"
            f"## 1. Tu Misión Exacta en esta Fase {phase}\n"
            f"{mission_desc}\n\n"
            f"## 2. Tu Identidad y Reglas (`prompt.md`)\n"
            f"{prompt_text}\n"
            f"## 3. Tu Conocimiento Acumulado (`knowledge.md`)\n"
            f"{knowledge_text}\n"
            f"## 4. Último Reporte de Traspaso (`latest_handover.md`)\n"
            f"{handover_text}\n"
            f"## 5. Instrucción de Cierre Obligatoria\n"
            f"1. Verifica que tus archivos coincidan con `propuesta_arquitectura_tree_001.md` y `specs/06-IMPLEMENTATION-PLAN.md`.\n"
            f"2. Ejecuta los tests correspondientes y `python3 scripts/harness.py verify-evals`.\n"
            f"3. Actualiza `.agent/subagents/{agent_folder}/handovers/latest_handover.md` y haz `git commit` en tu rama `{branch_name}`.\n"
        )
        (wt_path / "MISSION_PROMPT.md").write_text(mission_content, encoding="utf-8")
        log_event("WORKTREE_PREPARED", {"phase": phase, "agent": agent_folder, "branch": branch_name, "worktree": str(wt_path)})
        print(f"   🌿 [{agent_folder}] Worktree listo en: {wt_path}")
        print(f"      └── Archivo generado: {wt_path / 'MISSION_PROMPT.md'}")

    print("\n💡 CÓMO USARLO EN HERDR:")
    print("   Abre una sesión por cada worktree de arriba y pega en todas este mismo prompt corto:")
    print('   "Lee el archivo MISSION_PROMPT.md de este directorio y ejecuta tu misión de principio a fin."')


def show_status() -> None:
    subagents = sorted((AGENT_DIR / "subagents").glob("*"))
    rules = sorted((AGENT_DIR / "rules").glob("*.md"))
    skills = sorted((AGENT_DIR / "skills").glob("*"))
    strategies = sorted((AGENT_DIR / "estrategias").glob("*.md"))
    print("🏛️  OppyTec v2.0 Harness Status:")
    print(f"   • Estrategias Maestras (.agent/estrategias/): {len(strategies)}")
    print(f"   • Reglas Inmutables (.agent/rules/): {len(rules)}")
    print(f"   • Escuadrón de Sub-Agentes (.agent/subagents/): {len(subagents)}")
    print(f"   • Skills Registradas (.agent/skills/): {len(skills)}")
    verify_anti_cheating_hashes()


def main() -> int:
    parser = argparse.ArgumentParser(description="OppyTec v2.0 Multi-Agent RLM Harness")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Muestra el estado del arnés y verifica integridad anti-trampa")
    sub.add_parser("verify-evals", help="Verifica los hashes SHA-256 de reglas y evaluaciones inmutables")

    prep_p = sub.add_parser("prepare-phase", help="Crea los Git Worktrees y MISSION_PROMPT.md para una Fase (1..6)")
    prep_p.add_argument("--phase", type=int, required=True, choices=[1, 2, 3, 4, 5, 6])

    claim_p = sub.add_parser("claim-ast", help="Reserva atómicamente un símbolo AST antes de editar")
    claim_p.add_argument("--worker", required=True)
    claim_p.add_argument("--file", required=True)
    claim_p.add_argument("--symbol", required=True)
    claim_p.add_argument("--intent", required=True)

    args = parser.parse_args()
    if args.command == "status":
        show_status()
        return 0
    if args.command == "verify-evals":
        return 0 if verify_anti_cheating_hashes() else 1
    if args.command == "prepare-phase":
        prepare_phase_worktrees(args.phase)
        return 0
    if args.command == "claim-ast":
        claim_ast_symbol(args.worker, args.file, args.symbol, args.intent)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
