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
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Compatibilidad de Locks a Nivel de Kernel (Linux/macOS con fcntl, fallback seguro para Windows)
try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    fcntl = None  # type: ignore[assignment]
    _HAS_FCNTL = False

ROOT_DIR = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT_DIR / ".agent"
MEMORY_DIR = AGENT_DIR / "memory"
WORKTREES_DIR = ROOT_DIR / ".worktrees"
CLAIMS_FILE = MEMORY_DIR / "claims_registry.json"
CLAIMS_LOCK = MEMORY_DIR / ".claims_registry.lock"
EVENTS_LOG = MEMORY_DIR / "harness_events.jsonl"
EVAL_HASHES_FILE = AGENT_DIR / "evals" / "eval_hashes.sha256"
MODEL_ROUTER_FILE = AGENT_DIR / "config" / "model_router.json"

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
    """Reserva un símbolo AST de forma atómica usando fcntl.flock(LOCK_EX) en POSIX o lock atómico en Windows."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(CLAIMS_LOCK, "w", encoding="utf-8") as lock_fd:
        if _HAS_FCNTL and fcntl is not None:
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
            if _HAS_FCNTL and fcntl is not None:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)

    log_event("AST_SYMBOL_CLAIMED", {"worker": worker_id, "file": file_path, "symbol": symbol_path})
    print(f"✅ Símbolo AST '{symbol_path}' reservado atómicamente para '{worker_id}'.")


def release_ast_symbol(
    worker_id: str | None = None,
    file_path: str | None = None,
    symbol_path: str | None = None,
    release_all: bool = False,
) -> int:
    """Libera reservas de símbolos AST en claims_registry.json de forma atómica usando fcntl.flock."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(CLAIMS_LOCK, "w", encoding="utf-8") as lock_fd:
        if _HAS_FCNTL and fcntl is not None:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
        try:
            data: dict[str, Any] = {"version": "2.0.0", "active_claims": []}
            if CLAIMS_FILE.exists():
                data = json.loads(CLAIMS_FILE.read_text(encoding="utf-8"))

            active = data.get("active_claims", [])
            remaining = []
            released = []

            for claim in active:
                match = True
                if release_all or (not worker_id and not file_path and not symbol_path):
                    match = True
                else:
                    if worker_id and worker_id not in claim.get("claimed_by", ""):
                        match = False
                    if file_path and claim.get("file") != file_path:
                        match = False
                    if symbol_path and claim.get("symbol_path") != symbol_path:
                        match = False

                if match:
                    released.append(claim)
                else:
                    remaining.append(claim)

            data["active_claims"] = remaining

            fd, tmp_path = tempfile.mkstemp(dir=MEMORY_DIR, suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                json.dump(data, tmp_file, indent=2, ensure_ascii=False)
            os.replace(tmp_path, CLAIMS_FILE)
        finally:
            if _HAS_FCNTL and fcntl is not None:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)

    log_event("AST_SYMBOLS_RELEASED", {"released_count": len(released), "remaining_count": len(remaining), "worker": worker_id})
    print(f"✅ Símbolos AST liberados: {len(released)} liberados, {len(remaining)} activos restantes.")
    return len(released)


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


def load_model_router_config() -> dict[str, Any]:
    """Carga la configuración declarativa de modelos y tiers desde .agent/config/model_router.json."""
    if not MODEL_ROUTER_FILE.exists():
        return {
            "version": "2.0.0",
            "active_provider_default": "gemini",
            "tiers": {},
            "agent_overrides": {},
            "providers_catalog": {},
        }
    return json.loads(MODEL_ROUTER_FILE.read_text(encoding="utf-8"))


def resolve_agent_model(agent_or_tier: str, complexity_tier: str | None = None) -> dict[str, Any]:
    """
    Resuelve el tier, modelo primario y cadena de fallbacks de un agente o tier específico.
    Si complexity_tier es provisto y dynamic_routing_enabled está activo, se permite
    promover o adaptar el tier según la complejidad cognitiva evaluada por JEV.
    """
    cfg = load_model_router_config()
    tiers = cfg.get("tiers", {})
    agent_overrides = cfg.get("agent_overrides", {})
    dynamic_enabled = cfg.get("dynamic_routing_enabled", True)

    # Determinar el tier base
    if agent_or_tier in tiers:
        base_tier_key = agent_or_tier
    else:
        base_tier_key = agent_overrides.get(agent_or_tier, "tier_fast_execution")

    effective_tier_key = base_tier_key
    was_promoted = False

    tier_hierarchy = ["tier_lightweight", "tier_fast_execution", "tier_reasoning_heavy"]

    if dynamic_enabled and complexity_tier and complexity_tier in tiers:
        base_idx = tier_hierarchy.index(base_tier_key) if base_tier_key in tier_hierarchy else 1
        comp_idx = tier_hierarchy.index(complexity_tier) if complexity_tier in tier_hierarchy else 1

        # Promoción si la complejidad cognitiva demanda un tier superior
        if comp_idx > base_idx:
            effective_tier_key = complexity_tier
            was_promoted = True
        elif comp_idx < base_idx and base_tier_key != "tier_reasoning_heavy":
            # Optimización de cuota para agentes estándar ante tareas ultraligeras/cosméticas
            effective_tier_key = complexity_tier

    tier_info = tiers.get(effective_tier_key, {
        "name": "Default Tier",
        "primary": "gemini/gemini-3.8-flash",
        "fallbacks": ["gemini/gemini-flash-lite"],
    })

    return {
        "target": agent_or_tier,
        "base_tier_key": base_tier_key,
        "tier_key": effective_tier_key,
        "tier_name": tier_info.get("name", effective_tier_key),
        "primary_model": tier_info.get("primary", "gemini/gemini-3.8-flash"),
        "fallback_chain": tier_info.get("fallbacks", []),
        "description": tier_info.get("description", ""),
        "was_promoted": was_promoted,
    }


def escalate_model_tier(agent_or_tier: str, reason: str = "TEST_FAILURE_REASONING_DEFICIT") -> dict[str, Any]:
    """
    Escala reactivamente el tier de un agente al tier superior inmediato
    (tier_lightweight -> tier_fast_execution -> tier_reasoning_heavy) tras una falla
    en Fast Gate < 15s o déficit de razonamiento demostrable.
    """
    resolution = resolve_agent_model(agent_or_tier)
    current_tier = resolution["tier_key"]

    tier_progression = {
        "tier_lightweight": "tier_fast_execution",
        "tier_fast_execution": "tier_reasoning_heavy",
        "tier_reasoning_heavy": "tier_reasoning_heavy",
    }
    next_tier = tier_progression.get(current_tier, "tier_reasoning_heavy")

    escalated_resolution = resolve_agent_model(agent_or_tier, complexity_tier=next_tier)
    event_payload = {
        "target": agent_or_tier,
        "previous_tier": current_tier,
        "escalated_tier": next_tier,
        "new_primary_model": escalated_resolution["primary_model"],
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log_event("MODEL_TIER_ESCALATED", event_payload)

    print(f"⚡ [AUTO-ESCALADO COGNITIVO ACTIVADO] Agente/Tier: '{agent_or_tier}'")
    print(f"   • Tier previo: {current_tier}")
    print(f"   • Nuevo Tier Promovido: 🚀 {next_tier}")
    print(f"   • Modelo Primario: {escalated_resolution['primary_model']}")
    print(f"   • Motivo: {reason}")
    return escalated_resolution


def trigger_model_fallback(agent_or_tier: str, failed_model: str, reason: str) -> dict[str, Any]:
    """Simula o ejecuta un fallback dinámico al siguiente modelo disponible cuando la cuota se agota."""
    resolution = resolve_agent_model(agent_or_tier)
    chain = [resolution["primary_model"]] + resolution["fallback_chain"]

    next_model = None
    if failed_model in chain:
        idx = chain.index(failed_model)
        if idx + 1 < len(chain):
            next_model = chain[idx + 1]
    else:
        next_model = resolution["fallback_chain"][0] if resolution["fallback_chain"] else "gemini/gemini-3.8-flash"

    if not next_model:
        next_model = "gemini/gemini-flash-lite"

    event_payload = {
        "target": agent_or_tier,
        "tier": resolution["tier_key"],
        "failed_model": failed_model,
        "reason": reason,
        "promoted_fallback_model": next_model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log_event("MODEL_FALLBACK_TRIGGERED", event_payload)

    print(f"⚠️ [MODEL FALLBACK ACTIVADO] Agente/Tier: '{agent_or_tier}'")
    print(f"   • Modelo agotado/fallido: {failed_model}")
    print(f"   • Motivo: {reason}")
    print(f"   • Nuevo Modelo Promovido: 🚀 {next_model}")
    print(f"   • Cadena restante: {chain[chain.index(next_model) + 1:] if next_model in chain else []}")
    return event_payload


def run_load_benchmark_cmd(concurrency: int = 100) -> None:
    """Ejecuta la prueba de carga y estrés concurrente contra el backend de OppyTec v2.0."""
    backend_py = ROOT_DIR / "oppytec-backend" / ".venv" / "bin" / "python"
    if not backend_py.exists():
        backend_py = Path(sys.executable)

    script = f"""
import asyncio, httpx, warnings
warnings.filterwarnings('ignore')
from src.main import app
from src.core.security import create_access_token
from tests.load.locustfile import run_burst_load_simulation

async def main():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver') as client:
        token = create_access_token(
            user_id=999, holding_id='holding_test', tenant_id='tenant_test',
            hierarchy_rank=20, contracted_modules=['catalog', 'inventory', 'operations', 'analytics'],
            role_grants=['catalog.units.convert', 'inventory.kardex.write', 'operations.sales.create'],
            accessible_tenants=['tenant_test']
        )
        headers = {{'Authorization': f'Bearer {{token}}', 'X-Tenant-ID': 'tenant_test'}}
        metrics = await run_burst_load_simulation(client, headers, concurrency={concurrency}, mode='stock_and_sales')
        print('======================================================================')
        print('⚡ BENCHMARK OFICIAL DE CARGA Y ESTRÉS — OPPYTEC V2.0 (LOCUST / ASYNCIO)')
        print('======================================================================')
        print(f'   • Peticiones Concurrentes:    {{metrics.total_requests}}')
        print(f'   • Throughput Proyectado:      {{metrics.projected_rps:.1f}} RPS (SLA Objetivo: >= 500 RPS)')
        print(f'   • Latencia P50 (Mediana):     {{metrics.p50_latency_ms:.2f}} ms')
        print(f'   • Latencia P95:               {{metrics.p95_latency_ms:.2f}} ms (SLA Objetivo: <= 120 ms)')
        print(f'   • Latencia P99:               {{metrics.p99_latency_ms:.2f}} ms')
        print(f'   • Errores HTTP 5xx:           {{metrics.http_5xx_count}} (Tolerancia: 0)')
        print(f'   • Peticiones Fallidas:        {{metrics.failed_requests}}')
        status = '✅ CERTIFICADO SLA (>= 500 RPS & P95 <= 120ms)' if metrics.p95_latency_ms <= 120 and metrics.projected_rps >= 500 else '❌ NO CUMPLE'
        print(f'   • Veredicto Final:            {{status}}')
        print('======================================================================')

asyncio.run(main())
"""
    subprocess.run([str(backend_py), "-c", script], cwd=ROOT_DIR / "oppytec-backend", check=True)


def run_eval_llm_cmd(verbose: bool = False, fail_fast: bool = False) -> int:
    """
    Quality Gate Automatizado de Evals y Observabilidad LLM (Fail-Closed).
    Ejecuta la suite de DeepEval/Evals en oppytec-backend/tests/ai_evals/
    y valida que:
    - Faithfulness >= 0.85
    - Answer Relevance >= 0.85
    - Context Precision >= 0.80
    - Hallucination Rate <= 0.05
    - Critical Hallucination Rate == 0.00 (Tolerancia Cero en alérgenos, costos y stock FEFO)
    - Invariante de marca comercial 'Pollo King' 100% preservado.
    Si cualquier métrica o test falla, retorna código de salida 1 y bloquea el merge/pipeline.
    """
    backend_pytest = ROOT_DIR / "oppytec-backend" / ".venv" / "bin" / "pytest"
    if not backend_pytest.exists():
        backend_pytest = Path("pytest")

    print("======================================================================")
    print("🧠 QUALITY GATE: EVALUACIÓN SISTEMÁTICA LLM (OPPYFY DEEPEVAL / RAGAS)")
    print("======================================================================")
    print("   • Umbrales Mínimos Inviolables (Fail-Closed):")
    print("     - Fidelidad (Faithfulness):          >= 0.85")
    print("     - Relevancia (Answer Relevance):     >= 0.85")
    print("     - Precisión Contexto (Precision):    >= 0.80")
    print("     - Tasa de Alucinación:               <= 0.05")
    print("     - Alucinación Crítica:               == 0.00 (Alérgenos, Costos y Stock FEFO)")
    print("     - Preservación Marca 'Pollo King':   100% Inmutable")
    print("   • Ejecutando suite: tests/ai_evals/ ...\n")

    cmd = [
        str(backend_pytest),
        str(ROOT_DIR / "oppytec-backend" / "tests" / "ai_evals"),
    ]
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    if fail_fast:
        cmd.append("-x")

    result = subprocess.run(
        cmd,
        cwd=ROOT_DIR / "oppytec-backend",
        check=False,
    )

    if result.returncode != 0:
        print("\n======================================================================")
        print("🚨 FAIL-CLOSED ACTIVADO: Quality Gate de AI Evals NO Superado")
        print("   Uno o más umbrales de fidelidad (< 0.85), alucinación (> 0.05) o alucinación crítica")
        print("   fueron violados. Bloqueo inmediato de CI/CD y Merge Train.")
        print("======================================================================\n")
        log_event("AI_EVAL_GATE_FAILED", {"exit_code": result.returncode})
        return 1

    print("\n======================================================================")
    print("🎯 QUALITY GATE AI EVALS SUPERADO AL 100% (CERO ALUCINACIÓN CRÍTICA)")
    print("   • Fidelidad (Faithfulness):           >= 0.85 [APROBADO]")
    print("   • Relevancia (Answer Relevance):       >= 0.85 [APROBADO]")
    print("   • Precisión Contexto (Precision):     >= 0.80 [APROBADO]")
    print("   • Tasa Alucinación (Hallucination):   <= 0.05 [APROBADO]")
    print("   • Alucinación Crítica:                == 0.00 [APROBADO]")
    print("   • Veredicto Final:                    CERTIFICADO (Fail-Closed Respetado)")
    print("======================================================================\n")
    log_event("AI_EVAL_GATE_PASSED", {"suite": "tests/ai_evals", "status": "APPROVED"})
    return 0


def run_test_fast_cmd() -> int:
    """
    Ejecuta el conjunto de tests rápidos de backend (Unit, Smoke, Integration)
    con el virtualenv oficial de oppytec-backend.
    """
    backend_pytest = ROOT_DIR / "oppytec-backend" / ".venv" / "bin" / "pytest"
    pytest_bin = str(backend_pytest) if backend_pytest.exists() else "pytest"
    cmd = [
        pytest_bin,
        "tests/unit",
        "tests/smoke",
        "tests/integration/test_holding_hub_api.py",
        "-k",
        "not test_projection_engine and not test_snapshot_service and not test_find_alternative_stock and not test_calculate_consumption_rates and not test_paginated_snapshots and not test_commit_preserving",
        "-q",
    ]
    res = subprocess.run(cmd, cwd=ROOT_DIR / "oppytec-backend")
    return res.returncode



def list_models_cmd() -> None:
    """Muestra el catálogo de proveedores, los tiers y la asignación de modelos de los 13 agentes."""
    cfg = load_model_router_config()
    print("🤖 Catálogo y Enrutador Dinámico de Modelos LLM (OppyTec v2.0)")
    print(f"   Versión: {cfg.get('version')} | Proveedor Predeterminado: {cfg.get('active_provider_default')}\n")

    print("📦 Proveedores Registrados en Catálogo:")
    for prov_key, prov in cfg.get("providers_catalog", {}).items():
        models_count = len(prov.get("models", []))
        sample_models = ", ".join(m["id"] for m in prov.get("models", [])[:3])
        print(f"   • [{prov_key}] {prov.get('name')}: {models_count} modelos ({sample_models}...)")

    print("\n🎯 Tiers Lógicos Abstractos:")
    for t_key, t_val in cfg.get("tiers", {}).items():
        print(f"   • [{t_key}] {t_val.get('name')}:")
        print(f"     └─ Primario: 🌟 {t_val.get('primary')}")
        print(f"     └─ Cadena Fallback: {' ➔ '.join(t_val.get('fallbacks', []))}")

    print("\n👥 Asignación del Escuadrón Multi-Agente (13 Agentes):")
    for agent_id, tier_key in cfg.get("agent_overrides", {}).items():
        resolved = resolve_agent_model(agent_id)
        first_fallback = resolved["fallback_chain"][0] if resolved["fallback_chain"] else "Ninguno"
        print(f"   • `{agent_id}` ➔ Tier: {tier_key}")
        print(f"     └── Primario: {resolved['primary_model']} (Fallback 1: {first_fallback})")


def route_task_cmd(prompt_text: str, is_json: bool = False, explain_complexity: bool = False) -> None:
    """Clasifica un requerimiento de usuario usando el Motor JEV Sistema 1 con asignación dinámica de modelos."""
    sys.path.insert(0, str(AGENT_DIR / "skills" / "jev-decision-engine"))
    from jev_router import classify_user_request  # type: ignore

    classification = classify_user_request(prompt_text)
    comp_rep = classification.complexity_report
    complexity_tier = comp_rep.promoted_tier if comp_rep else None

    primary_resolved = resolve_agent_model(classification.primary_agent.value, complexity_tier=complexity_tier)

    log_event("JEV_TASK_ROUTED", {
        "primary_agent": classification.primary_agent.value,
        "mode": classification.mode.value,
        "confidence": str(classification.confidence),
        "supporting": [a.value for a in classification.supporting_agents],
        "complexity_score": str(comp_rep.complexity_score) if comp_rep else "N/A",
        "complexity_level": comp_rep.level if comp_rep else "N/A",
        "assigned_tier": primary_resolved["tier_key"],
        "was_promoted": primary_resolved.get("was_promoted", False),
        "primary_model": primary_resolved["primary_model"],
        "primary_fallbacks": primary_resolved["fallback_chain"],
        "prompt_snippet": prompt_text[:120],
    })

    if is_json:
        data = classification.to_dict()
        data["model_resolution"] = primary_resolved
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(classification.to_header())
        if comp_rep:
            promoted_badge = " [Promovido]" if primary_resolved.get("was_promoted") else ""
            print(f"   📊 **Complejidad Evaluada:** {comp_rep.complexity_score} ({comp_rep.level}) ➔ **Tier Dinámico:** `{primary_resolved['tier_key']}`{promoted_badge}")
        print(f"   ⚙️ **Modelo Primario:** `{primary_resolved['primary_model']}` | **Fallback 1:** `{primary_resolved['fallback_chain'][0] if primary_resolved['fallback_chain'] else 'N/A'}`")
        if explain_complexity and comp_rep:
            print("\n" + comp_rep.explain())
        print(f"\n📋 Justificación: {classification.rationale}")
        print("\n🔀 Pipeline de Ejecución (Orden Lógico de Dependencias):")
        for stage in classification.pipeline:
            agents_detail: list[str] = []
            for a in stage.agents:
                m_info = resolve_agent_model(a.value, complexity_tier=complexity_tier)
                agents_detail.append(f"`{a.value}` (Modelo: `{m_info['primary_model']}`)")
            print(f"  • Etapa {stage.stage_number} [{stage.execution_type}]: {stage.stage_name}")
            print(f"    └─ Agentes asignados: {', '.join(agents_detail)}")


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


def nav_ast_cmd(symbol: str, legacy: bool = False, limit: int = 10) -> None:
    """Navega la vecindad AST de un símbolo (< 150 tokens) usando Graphify."""
    graphify_path = AGENT_DIR / "skills" / "graphify"
    if str(graphify_path.resolve()) not in sys.path:
        sys.path.insert(0, str(graphify_path.resolve()))
    from graph_navigator import legacy_graph, v2_graph  # type: ignore

    navigator = legacy_graph if legacy else v2_graph
    data = navigator.neighbors(symbol, limit=limit)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def sync_graph_cmd() -> None:
    """Escanea e indexa artefactos del proyecto y sincroniza docs/architecture/graphify/graph.json."""
    graph_path = ROOT_DIR / "docs" / "architecture" / "graphify" / "graph.json"
    master_path = ROOT_DIR / "docs" / "architecture" / "graphify" / "v2_phase6_master_graph.json"

    if not graph_path.exists():
        data: dict[str, Any] = {
            "graph_id": "v2_phase6_master_graph",
            "phase": "Fase 6 (Sincronización Continua Graphify)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": "12-tech-writer-openspec-archify",
            "invariants": [],
            "nodes": [],
            "edges": [],
            "metrics": {},
        }
    else:
        data = json.loads(graph_path.read_text(encoding="utf-8"))

    nodes_map: dict[str, dict[str, Any]] = {n["id"]: n for n in data.get("nodes", [])}
    edges_set: set[tuple[str, str, str]] = {
        (e["source"], e["target"], e["relation"]) for e in data.get("edges", [])
    }

    def add_node(node_id: str, label: str, node_type: str, path: str) -> None:
        nodes_map[node_id] = {
            "id": node_id,
            "label": label,
            "type": node_type,
            "path": Path(path).as_posix(),
        }

    def add_edge(source: str, target: str, relation: str) -> None:
        edges_set.add((source, target, relation))

    # 1. Escaneo de Migraciones Alembic
    alembic_dir = ROOT_DIR / "oppytec-backend" / "alembic" / "versions"
    if alembic_dir.exists():
        for mig_file in sorted(alembic_dir.glob("*.py")):
            if mig_file.name.startswith("__"):
                continue
            stem = mig_file.stem
            num = stem.split("_")[0] if "_" in stem else "mig"
            short_desc = "_".join(stem.split("_")[1:4])
            node_id = f"migration:{num}_{short_desc}"
            if num == "0001":
                label = "Alembic 0001 Migration: Genesis Public Tenancy & Global RBAC"
            elif num == "0002":
                label = "Alembic 0002 Migration: Tenant Client RBAC & Core Schemas"
            elif num == "0003":
                label = "Alembic 0003 Migration: Public Plans, Quotas & Tenant Capacity Overrides"
            else:
                label = f"Alembic {num} Migration: {stem[5:].replace('_', ' ').capitalize()}"
            add_node(node_id, label, "backend_migration", str(mig_file.relative_to(ROOT_DIR)))

        m0001 = next((nid for nid in nodes_map if nid.startswith("migration:0001")), None)
        m0002 = next((nid for nid in nodes_map if nid.startswith("migration:0002")), None)
        m0003 = next((nid for nid in nodes_map if nid.startswith("migration:0003")), None)

        if m0001 and "core:database" in nodes_map:
            add_edge(m0001, "core:database", "executes_on_public_schema")
        if m0002 and m0001:
            add_edge(m0002, m0001, "depends_on_public_genesis")
        if m0003 and m0002:
            add_edge(m0003, m0002, "extends_public_and_tenant_quotas")
        if m0003 and "module:tenancy" in nodes_map:
            add_edge(m0003, "module:tenancy", "enforces_plan_quotas_and_overrides")

    # 2. Escaneo de Routers FastAPI Backend
    modules_dir = ROOT_DIR / "oppytec-backend" / "src" / "modules"
    if modules_dir.exists():
        for mod_folder in sorted(modules_dir.iterdir()):
            if not mod_folder.is_dir():
                continue
            router_file = mod_folder / "presentation" / "router.py"
            if router_file.exists():
                mod_name = mod_folder.name
                node_id = f"router:{mod_name}"
                label = f"Backend Presentation Router ({mod_name}) /api/v1/{mod_name}"
                add_node(node_id, label, "backend_router", str(router_file.relative_to(ROOT_DIR)))
                if "app:backend_main" in nodes_map:
                    add_edge("app:backend_main", node_id, "mounts_api_router")
                if f"module:{mod_name}" in nodes_map:
                    add_edge(node_id, f"module:{mod_name}", "routes_to_domain_module")

    realtime_router = ROOT_DIR / "oppytec-backend" / "src" / "core" / "realtime" / "router.py"
    if realtime_router.exists():
        add_node(
            "router:core_realtime",
            "Backend Realtime WebSocket Router /api/v1/ws/realtime",
            "backend_router",
            str(realtime_router.relative_to(ROOT_DIR)),
        )
        if "app:backend_main" in nodes_map:
            add_edge("app:backend_main", "router:core_realtime", "mounts_ws_router")
        if "core:realtime_ws" in nodes_map:
            add_edge("router:core_realtime", "core:realtime_ws", "routes_to_realtime_ws")

    # 2b. Componentes Core de Code Mode sobre MCP
    core_mcp_bridge = ROOT_DIR / "oppytec-backend" / "src" / "core" / "mcp_bridge" / "manager.py"
    if core_mcp_bridge.exists():
        add_node(
            "core:mcp_bridge",
            "Core MCP Dynamic Bridge Manager (Lifecycle & Tool Discovery)",
            "backend_core",
            str(core_mcp_bridge.relative_to(ROOT_DIR)),
        )
        if "module:oppy_ai" in nodes_map:
            add_edge("module:oppy_ai", "core:mcp_bridge", "discovers_and_routes_mcp_tools")

    core_sandbox = ROOT_DIR / "oppytec-backend" / "src" / "core" / "sandbox" / "runner.py"
    if core_sandbox.exists():
        add_node(
            "core:code_mode_sandbox",
            "Core Code Mode Sandboxed Runner (AST Validation, Watchdog & Hard-Code Stripping)",
            "backend_core",
            str(core_sandbox.relative_to(ROOT_DIR)),
        )
        if "core:mcp_bridge" in nodes_map:
            add_edge("core:code_mode_sandbox", "core:mcp_bridge", "executes_mcp_calls_via_bridge")
        if "module:oppy_ai" in nodes_map:
            add_edge("module:oppy_ai", "core:code_mode_sandbox", "executes_synthesized_scripts")

    code_mode_service = ROOT_DIR / "oppytec-backend" / "src" / "modules" / "oppy_ai" / "application" / "code_mode_service.py"
    if code_mode_service.exists():
        add_node(
            "service:oppyfy_code_mode",
            "OppyFy Code Mode Application Service (Multi-Tenant & FinOps Telemetry)",
            "backend_service",
            str(code_mode_service.relative_to(ROOT_DIR)),
        )
        if "module:oppy_ai" in nodes_map:
            add_edge("service:oppyfy_code_mode", "module:oppy_ai", "orchestrates_code_mode")
        if "core:code_mode_sandbox" in nodes_map:
            add_edge("service:oppyfy_code_mode", "core:code_mode_sandbox", "invokes_isolated_sandbox")
        if "core:mcp_bridge" in nodes_map:
            add_edge("service:oppyfy_code_mode", "core:mcp_bridge", "searches_capabilities")

    ai_catalog_service = ROOT_DIR / "oppytec-backend" / "src" / "modules" / "oppy_ai" / "application" / "ai_model_catalog_service.py"
    if ai_catalog_service.exists():
        add_node(
            "service:ai_model_catalog",
            "AI Model & JEV Catalog Application Service (CRUD, Hot-Reload & RBAC Guard)",
            "backend_service",
            str(ai_catalog_service.relative_to(ROOT_DIR)),
        )
        if "module:oppy_ai" in nodes_map:
            add_edge("service:ai_model_catalog", "module:oppy_ai", "manages_ai_models_and_tariffs")
        m0012 = next((nid for nid in nodes_map if "0012" in nid), None)
        if m0012:
            add_edge("service:ai_model_catalog", m0012, "reads_and_writes_ai_model_configs")
        if "router:oppy_ai" in nodes_map:
            add_edge("router:oppy_ai", "service:ai_model_catalog", "dispatches_catalog_crud_requests")

    # 2c. Holding Hub Enterprise Services & Router
    holding_hub_router = ROOT_DIR / "oppytec-backend" / "src" / "modules" / "tenancy" / "presentation" / "holding_hub_router.py"
    if holding_hub_router.exists():
        add_node(
            "router:holding_hub",
            "Backend Holding Hub REST Router /api/v1/holding-hub",
            "backend_router",
            str(holding_hub_router.relative_to(ROOT_DIR)),
        )
        if "app:backend_main" in nodes_map:
            add_edge("app:backend_main", "router:holding_hub", "mounts_holding_hub_router")
        if "module:tenancy" in nodes_map:
            add_edge("router:holding_hub", "module:tenancy", "routes_to_tenancy_holding_hub")

    holding_hub_service = ROOT_DIR / "oppytec-backend" / "src" / "modules" / "tenancy" / "application" / "holding_hub_service.py"
    if holding_hub_service.exists():
        add_node(
            "service:holding_hub",
            "Holding Hub Enterprise Application Service (Consolidation & Credits)",
            "backend_service",
            str(holding_hub_service.relative_to(ROOT_DIR)),
        )
        if "module:tenancy" in nodes_map:
            add_edge("module:tenancy", "service:holding_hub", "orchestrates_holding_hub_service")
        if "router:holding_hub" in nodes_map:
            add_edge("router:holding_hub", "service:holding_hub", "invokes_holding_hub_service")
        m0018 = next((nid for nid in nodes_map if "0018" in nid), None)
        if m0018:
            add_edge("service:holding_hub", m0018, "persists_credit_distributions_and_purchases")

    holding_briefing_service = ROOT_DIR / "oppytec-backend" / "src" / "modules" / "oppy_ai" / "application" / "holding_briefing_service.py"
    if holding_briefing_service.exists():
        add_node(
            "service:holding_briefing",
            "Holding AI Executive Briefing Service (Oppy Daily Briefing)",
            "backend_service",
            str(holding_briefing_service.relative_to(ROOT_DIR)),
        )
        if "module:oppy_ai" in nodes_map:
            add_edge("module:oppy_ai", "service:holding_briefing", "orchestrates_holding_briefing")
        if "router:holding_hub" in nodes_map:
            add_edge("router:holding_hub", "service:holding_briefing", "invokes_ai_briefing")

    # 3. Componentes Clave de Frontend
    fe_i18n_selector = ROOT_DIR / "oppytec-frontend" / "src" / "shared" / "i18n" / "LanguageFlagSelector.tsx"
    if fe_i18n_selector.exists():
        rel_path = str(fe_i18n_selector.relative_to(ROOT_DIR))
        add_node(
            "frontend:language_provider",
            "LanguageProvider Component & Context Wrapper (React 19 i18n)",
            "frontend_shared_component",
            rel_path,
        )
        add_node(
            "frontend:use_language",
            "useLanguage Hook (Active Language & Context Switcher)",
            "frontend_shared_hook",
            rel_path,
        )
        add_node(
            "frontend:language_flag_selector",
            "LanguageFlagSelector Component (SVG Flags ES/US & Dropdown)",
            "frontend_shared_component",
            rel_path,
        )
        if "frontend:app_shell" in nodes_map:
            add_edge("frontend:app_shell", "frontend:language_provider", "mounts_language_provider")
            add_edge("frontend:app_shell", "frontend:language_flag_selector", "renders_navbar_flag_selector")
        if "frontend:shared_i18n" in nodes_map:
            add_edge("frontend:language_provider", "frontend:shared_i18n", "provides_i18n_context")
            add_edge("frontend:language_flag_selector", "frontend:shared_i18n", "renders_svg_flags_and_locales")
        add_edge("frontend:use_language", "frontend:language_provider", "consumes_language_context")
        add_edge("frontend:language_flag_selector", "frontend:use_language", "invokes_language_switcher")
        if "frontend:feature_platform_admin" in nodes_map:
            add_edge("frontend:feature_platform_admin", "frontend:language_flag_selector", "renders_admin_flag_selector")

    fe_currency_selector = ROOT_DIR / "oppytec-frontend" / "src" / "shared" / "currency" / "CurrencySelector.tsx"
    if fe_currency_selector.exists():
        rel_path = str(fe_currency_selector.relative_to(ROOT_DIR))
        add_node(
            "frontend:currency_selector",
            "CurrencySelector Component & MoneyBadge (CLP/USD/EUR/BRL BigInt 10^8 Formatter)",
            "frontend_shared_component",
            rel_path,
        )
        if "frontend:shared_fx_currency" in nodes_map:
            add_edge("frontend:currency_selector", "frontend:shared_fx_currency", "renders_currency_dropdown_and_badge")
        if "frontend:app_shell" in nodes_map:
            add_edge("frontend:app_shell", "frontend:currency_selector", "renders_navbar_currency_selector")
        if "frontend:admin_management_views" in nodes_map:
            add_edge("frontend:admin_management_views", "frontend:currency_selector", "formats_tenant_pricing_currency")

    fe_quota_indicator = ROOT_DIR / "oppytec-frontend" / "src" / "shared" / "components" / "ui" / "QuotaProgressIndicator.tsx"
    if fe_quota_indicator.exists():
        rel_path = str(fe_quota_indicator.relative_to(ROOT_DIR))
        add_node(
            "frontend:quota_progress_indicator",
            "Frontend UI Quota Progress Indicator (4-State Semaphore 80/95/100%)",
            "frontend_ui_token",
            rel_path,
        )
        if "frontend:admin_management_views" in nodes_map:
            add_edge("frontend:admin_management_views", "frontend:quota_progress_indicator", "renders_quota_usage_semaphores")
        m0003 = next((nid for nid in nodes_map if nid.startswith("migration:0003")), None)
        if m0003:
            add_edge("frontend:quota_progress_indicator", m0003, "displays_plan_quotas_usage")

    fe_admin_views = ROOT_DIR / "oppytec-frontend" / "src" / "features" / "platform-admin" / "AdminManagementViews.tsx"
    if fe_admin_views.exists():
        rel_path = str(fe_admin_views.relative_to(ROOT_DIR))
        add_node(
            "frontend:admin_management_views",
            "Frontend Admin Management Views (Holdings, Legal Entities, Tenants & Client Users)",
            "frontend_feature_submodule",
            rel_path,
        )
        if "frontend:feature_platform_admin" in nodes_map:
            add_edge("frontend:feature_platform_admin", "frontend:admin_management_views", "contains_crud_views")
        if "frontend:dynamic_admin_table" in nodes_map:
            add_edge("frontend:admin_management_views", "frontend:dynamic_admin_table", "renders_table")
        if "frontend:dynamic_admin_form" in nodes_map:
            add_edge("frontend:admin_management_views", "frontend:dynamic_admin_form", "renders_modals")
        if "frontend:shared_rbac_can" in nodes_map:
            add_edge("frontend:admin_management_views", "frontend:shared_rbac_can", "enforces_rbac_can_guard")
        if "frontend:shared_i18n" in nodes_map:
            add_edge("frontend:admin_management_views", "frontend:shared_i18n", "translates_platform_admin_keys")
        if "module:tenancy" in nodes_map:
            add_edge("frontend:admin_management_views", "module:tenancy", "consumes_admin_rest_api")
        m0003 = next((nid for nid in nodes_map if nid.startswith("migration:0003")), None)
        if m0003:
            add_edge("frontend:admin_management_views", m0003, "manages_tenant_quotas_from_schema")

    fe_admin_table = ROOT_DIR / "oppytec-frontend" / "src" / "shared" / "components" / "admin" / "DynamicAdminTable.tsx"
    if fe_admin_table.exists():
        add_node(
            "frontend:dynamic_admin_table",
            "Frontend Shared Dynamic Admin Table (Declarative RBAC <Can>, i18n & Live Filter)",
            "frontend_shared_component",
            str(fe_admin_table.relative_to(ROOT_DIR)),
        )

    fe_admin_form = ROOT_DIR / "oppytec-frontend" / "src" / "shared" / "components" / "admin" / "DynamicAdminForm.tsx"
    if fe_admin_form.exists():
        add_node(
            "frontend:dynamic_admin_form",
            "Frontend Shared Dynamic Admin Form (Typed Schema Inputs & Modal Binding)",
            "frontend_shared_component",
            str(fe_admin_form.relative_to(ROOT_DIR)),
        )

    fe_ai_models_page = ROOT_DIR / "oppytec-frontend" / "src" / "features" / "platform-admin" / "ai-models" / "AiModelsPage.tsx"
    if fe_ai_models_page.exists():
        rel_path = str(fe_ai_models_page.relative_to(ROOT_DIR))
        add_node(
            "frontend:ai_models_page",
            "Platform Admin AI Models & JEV Engine Catalog View (RBAC 3-Tier CRUD & KPIs)",
            "frontend_feature_submodule",
            rel_path,
        )
        if "frontend:feature_platform_admin" in nodes_map:
            add_edge("frontend:feature_platform_admin", "frontend:ai_models_page", "mounts_ai_models_catalog")
        if "service:ai_model_catalog" in nodes_map:
            add_edge("frontend:ai_models_page", "service:ai_model_catalog", "consumes_ai_models_crud_api")
        m0012 = next((nid for nid in nodes_map if "0012" in nid), None)
        if m0012:
            add_edge("frontend:ai_models_page", m0012, "displays_ai_model_configs_schema")

    fe_holding_hub = ROOT_DIR / "oppytec-frontend" / "src" / "features" / "holding-hub" / "HoldingHubPage.tsx"
    if fe_holding_hub.exists():
        rel_path = str(fe_holding_hub.relative_to(ROOT_DIR))
        add_node(
            "frontend:feature_holding_hub",
            "Frontend Holding Hub Enterprise Feature (Central, Plans, Credits & AI Briefing)",
            "frontend_feature",
            rel_path,
        )
        if "frontend:app_shell" in nodes_map:
            add_edge("frontend:app_shell", "frontend:feature_holding_hub", "mounts_holding_hub_route")
        if "router:holding_hub" in nodes_map:
            add_edge("frontend:feature_holding_hub", "router:holding_hub", "consumes_holding_hub_api")
        if "frontend:currency_selector" in nodes_map:
            add_edge("frontend:feature_holding_hub", "frontend:currency_selector", "formats_holding_currency")
        if "frontend:shared_i18n" in nodes_map:
            add_edge("frontend:feature_holding_hub", "frontend:shared_i18n", "translates_holding_hub_namespace")

    # 4. Suites de Test
    fe_test_map = {
        "suite:frontend_admin_views_test": (
            ROOT_DIR / "oppytec-frontend" / "src" / "features" / "platform-admin" / "AdminManagementViews.test.tsx",
            "Frontend Admin Views & RBAC Interactive Vitest Suite",
            [("suite:frontend_admin_views_test", "frontend:admin_management_views", "verifies_modal_crud_and_rbac_veto")],
        ),
        "suite:frontend_i18n_test": (
            ROOT_DIR / "oppytec-frontend" / "src" / "shared" / "i18n" / "i18n.test.tsx",
            "Frontend i18n & Language Switcher Vitest Suite",
            [
                ("suite:frontend_i18n_test", "frontend:language_flag_selector", "tests_language_selection_and_persistence"),
                ("suite:frontend_i18n_test", "frontend:language_provider", "tests_language_provider_context"),
            ],
        ),
        "suite:frontend_currency_test": (
            ROOT_DIR / "oppytec-frontend" / "src" / "shared" / "currency" / "currency.test.tsx",
            "Frontend FX Currency Formatter & Selectors Vitest Suite",
            [("suite:frontend_currency_test", "frontend:currency_selector", "tests_currency_formatting_and_selection")],
        ),
        "suite:frontend_env_test": (
            ROOT_DIR / "oppytec-frontend" / "src" / "shared" / "config" / "env.test.ts",
            "Frontend Environment & Runtime Configuration Vitest Suite",
            [("suite:frontend_env_test", "frontend:app_shell", "verifies_runtime_env_and_invariants")],
        ),
        "suite:frontend_telemetry_test": (
            ROOT_DIR / "oppytec-frontend" / "src" / "shared" / "telemetry" / "telemetry.test.ts",
            "Frontend Telemetry & OpenTelemetry Vitest Suite",
            [("suite:frontend_telemetry_test", "frontend:app_shell", "verifies_telemetry_and_spans")],
        ),
        "suite:code_mode_sandbox_security_test": (
            ROOT_DIR / "oppytec-backend" / "tests" / "security_redteam" / "test_17_code_mode_sandbox_security.py",
            "Code Mode Sandbox Security & Red Team Offensive Suite (10 Vectors)",
            [
                ("suite:code_mode_sandbox_security_test", "core:code_mode_sandbox", "audits_sandbox_escapes_and_watchdog"),
                ("suite:code_mode_sandbox_security_test", "core:mcp_bridge", "audits_anti_idor_and_stripping"),
            ],
        ),
        "suite:oppyfy_code_mode_test": (
            ROOT_DIR / "oppytec-backend" / "tests" / "unit" / "modules" / "test_oppyfy_code_mode.py",
            "OppyFy Code Mode Application Service Unit Test Suite",
            [("suite:oppyfy_code_mode_test", "service:oppyfy_code_mode", "verifies_token_savings_and_chat_payload")],
        ),
        "suite:mcp_bridge_test": (
            ROOT_DIR / "oppytec-backend" / "tests" / "unit" / "core" / "test_mcp_bridge.py",
            "MCP Dynamic Bridge Manager Unit Test Suite",
            [("suite:mcp_bridge_test", "core:mcp_bridge", "verifies_tool_registration_and_sdk_generation")],
        ),
        "suite:sandbox_runner_test": (
            ROOT_DIR / "oppytec-backend" / "tests" / "unit" / "core" / "test_sandbox_runner.py",
            "Code Mode Sandbox Runner Unit Test Suite",
            [("suite:sandbox_runner_test", "core:code_mode_sandbox", "verifies_ast_limits_and_stripping")],
        ),
        "suite:ai_model_catalog_unit_test": (
            ROOT_DIR / "oppytec-backend" / "tests" / "unit" / "modules" / "test_ai_model_catalog.py",
            "AI Model Catalog Domain & CRUD API Unit Test Suite",
            [
                ("suite:ai_model_catalog_unit_test", "service:ai_model_catalog", "tests_crud_hot_reload_and_soft_delete"),
                ("suite:ai_model_catalog_unit_test", "router:oppy_ai", "tests_rbac_authorization_matrix"),
            ],
        ),
        "suite:ai_model_catalog_observability_test": (
            ROOT_DIR / "oppytec-backend" / "tests" / "unit" / "modules" / "test_ai_model_catalog_observability.py",
            "AI Model Catalog OpenTelemetry & Latency SLA Observability Suite",
            [
                ("suite:ai_model_catalog_observability_test", "service:ai_model_catalog", "verifies_otel_spans_and_latency_sla"),
            ],
        ),
        "suite:frontend_ai_models_vitest": (
            ROOT_DIR / "oppytec-frontend" / "src" / "features" / "platform-admin" / "ai-models" / "__tests__" / "AiModelsPage.test.tsx",
            "Frontend Platform Admin AI Models Page Vitest Suite",
            [
                ("suite:frontend_ai_models_vitest", "frontend:ai_models_page", "verifies_modal_crud_filters_and_rbac"),
            ],
        ),
        "suite:ai_model_catalog_security_test": (
            ROOT_DIR / "oppytec-backend" / "tests" / "security_redteam" / "test_19_ai_model_catalog_security_and_rbac.py",
            "AI Model Catalog Security & Red Team Offensive Suite (RBAC, IDOR & Soft-Delete)",
            [
                ("suite:ai_model_catalog_security_test", "service:ai_model_catalog", "audits_soft_delete_and_invariants"),
                ("suite:ai_model_catalog_security_test", "router:oppy_ai", "audits_rbac_privilege_escalation_and_idor"),
            ],
        ),
        "suite:ai_evals_golden_dataset": (
            ROOT_DIR / "oppytec-backend" / "tests" / "ai_evals" / "test_golden_dataset.py",
            "OppyFy AI Evals Golden Dataset & Metric Gates Suite (50 Cases)",
            [
                ("suite:ai_evals_golden_dataset", "module:oppy_ai", "evaluates_faithfulness_and_hallucination"),
            ],
        ),
        "suite:ai_evals_hallucination_resilience": (
            ROOT_DIR / "oppytec-backend" / "tests" / "ai_evals" / "test_hallucination_resilience.py",
            "OppyFy AI Evals Hallucination Resilience & Epistemic Honesty Suite",
            [
                ("suite:ai_evals_hallucination_resilience", "module:oppy_ai", "evaluates_zero_critical_hallucination"),
            ],
        ),
        "suite:ai_evals_bilingual_parity": (
            ROOT_DIR / "oppytec-backend" / "tests" / "ai_evals" / "test_bilingual_parity.py",
            "OppyFy AI Evals Bilingual (es/en) & Pollo King Invariant Parity Suite",
            [
                ("suite:ai_evals_bilingual_parity", "module:oppy_ai", "evaluates_bilingual_translation_parity"),
            ],
        ),
        "suite:backend_holding_hub_api": (
            ROOT_DIR / "oppytec-backend" / "tests" / "integration" / "test_holding_hub_api.py",
            "Backend Holding Hub REST API & RBAC Multi-Level Integration Suite",
            [
                ("suite:backend_holding_hub_api", "router:holding_hub", "tests_holding_hub_endpoints_and_anti_idor"),
            ],
        ),
        "suite:backend_holding_hub_domain": (
            ROOT_DIR / "oppytec-backend" / "tests" / "unit" / "test_holding_hub_domain.py",
            "Backend Holding Hub Domain Logic & Credit Calculations Suite",
            [
                ("suite:backend_holding_hub_domain", "service:holding_hub", "verifies_credit_distribution_and_plans"),
            ],
        ),
        "suite:backend_holding_briefing": (
            ROOT_DIR / "oppytec-backend" / "tests" / "unit" / "test_holding_briefing.py",
            "Backend Holding AI Executive Briefing & Safety Cap Suite",
            [
                ("suite:backend_holding_briefing", "service:holding_briefing", "verifies_two_paragraph_briefing"),
            ],
        ),
        "suite:backend_holding_observability": (
            ROOT_DIR / "oppytec-backend" / "tests" / "unit" / "test_holding_hub_observability.py",
            "Backend Holding Hub OpenTelemetry Spans & Sentry Context Suite",
            [
                ("suite:backend_holding_observability", "service:holding_hub", "verifies_otel_spans_and_latency_sla"),
            ],
        ),
        "suite:frontend_holding_hub_vitest": (
            ROOT_DIR / "oppytec-frontend" / "src" / "features" / "holding-hub" / "HoldingHub.test.tsx",
            "Frontend Holding Hub Enterprise Layout, Tabs, FX & AI Briefing Vitest Suite",
            [
                ("suite:frontend_holding_hub_vitest", "frontend:feature_holding_hub", "verifies_holding_hub_ui_and_i18n"),
            ],
        ),
    }
    for s_id, (s_path, s_label, s_edges) in fe_test_map.items():
        if s_path.exists():
            add_node(s_id, s_label, "verification_suite", str(s_path.relative_to(ROOT_DIR)))
            for src, tgt, rel in s_edges:
                add_edge(src, tgt, rel)

    sorted_nodes = sorted(nodes_map.values(), key=lambda n: n["id"])
    sorted_edges = sorted(
        [{"source": s, "target": t, "relation": r} for (s, t, r) in edges_set if s in nodes_map and t in nodes_map],
        key=lambda e: (e["source"], e["target"], e["relation"]),
    )

    data["nodes"] = sorted_nodes
    data["edges"] = sorted_edges

    metrics = data.get("metrics", {})
    metrics["nodes_count"] = len(sorted_nodes)
    metrics["edges_count"] = len(sorted_edges)
    metrics["backend_modules"] = sum(1 for n in sorted_nodes if n.get("type") == "backend_module")
    metrics["backend_routers"] = sum(1 for n in sorted_nodes if n.get("type") == "backend_router")
    metrics["alembic_migrations"] = sum(1 for n in sorted_nodes if n.get("type") == "backend_migration")
    metrics["frontend_features"] = sum(1 for n in sorted_nodes if n.get("type") == "frontend_feature")
    metrics["frontend_shared_kernels"] = sum(1 for n in sorted_nodes if n.get("type") == "frontend_shared")
    metrics["verification_suites"] = sum(1 for n in sorted_nodes if n.get("type") == "verification_suite")
    metrics["frontend_admin_views"] = 4
    metrics["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["metrics"] = metrics

    graph_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    graph_path.write_text(serialized, encoding="utf-8")
    if master_path.parent.exists():
        master_path.write_text(serialized, encoding="utf-8")

    # Sincronización automática de docs/architecture/graphify/visualizer.html
    visualizer_path = ROOT_DIR / "docs" / "architecture" / "graphify" / "visualizer.html"
    visualizer_synced = False
    if visualizer_path.exists():
        html_content = visualizer_path.read_text(encoding="utf-8")
        script_pattern = re.compile(
            r'(<script\s+id=["\']initial-graph-data["\']\s+type=["\']application/json["\']>)(.*?)(</script>)',
            re.DOTALL,
        )
        if script_pattern.search(html_content):
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            updated_html = script_pattern.sub(
                rf"\g<1>\n{formatted_json}\n  \g<3>",
                html_content,
            )
            visualizer_path.write_text(updated_html, encoding="utf-8")
            visualizer_synced = True

    log_event("GRAPHIFY_SYNCED", {
        "nodes_count": len(sorted_nodes),
        "edges_count": len(sorted_edges),
        "alembic_migrations": metrics["alembic_migrations"],
        "backend_routers": metrics["backend_routers"],
        "verification_suites": metrics["verification_suites"],
        "visualizer_synced": visualizer_synced,
    })
    print("🔄 Grafo de Arquitectura Graphify sincronizado con éxito:")
    print(f"   • Nodos totales: {len(sorted_nodes)} (Routers: {metrics['backend_routers']}, Migraciones: {metrics['alembic_migrations']}, Suites: {metrics['verification_suites']})")
    print(f"   • Aristas totales: {len(sorted_edges)}")
    print(f"   • Destino: {graph_path.relative_to(ROOT_DIR)}")
    if visualizer_synced:
        print(f"   • Visualizador HTML: {visualizer_path.relative_to(ROOT_DIR)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="OppyTec v2.0 Multi-Agent RLM Harness")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Muestra el estado del arnés y verifica integridad anti-trampa")
    sub.add_parser("verify-evals", help="Verifica los hashes SHA-256 de reglas y evaluaciones inmutables")
    sub.add_parser("test-fast", help="Ejecuta los tests rápidos (Fast Gate / Unit / Smoke / Integration) con pytest")

    eval_llm_p = sub.add_parser("eval-llm", help="Ejecuta la suite de DeepEval/Evals de OppyFy y valida Quality Gates (Fail-Closed)")
    eval_llm_p.add_argument("-v", "--verbose", action="store_true", help="Salida detallada de pytest")
    eval_llm_p.add_argument("-x", "--exitfirst", action="store_true", help="Detener en el primer fallo (Fail-Fast)")

    route_p = sub.add_parser("route-task", help="Clasifica y enruta una tarea hacia los 13 agentes con JEV")
    route_p.add_argument("prompt", help="Texto del requerimiento del usuario a clasificar")
    route_p.add_argument("--json", action="store_true", help="Salida en formato JSON estructurado")
    route_p.add_argument("--explain-complexity", action="store_true", help="Muestra el desglose de los 4 factores de complejidad cognitiva JEV")

    prep_p = sub.add_parser("prepare-phase", help="Crea los Git Worktrees y MISSION_PROMPT.md para una Fase (1..6)")
    prep_p.add_argument("--phase", type=int, required=True, choices=[1, 2, 3, 4, 5, 6])

    claim_p = sub.add_parser("claim-ast", help="Reserva atómicamente un símbolo AST antes de editar")
    claim_p.add_argument("--worker", required=True)
    claim_p.add_argument("--file", required=True)
    claim_p.add_argument("--symbol", required=True)
    claim_p.add_argument("--intent", required=True)

    release_p = sub.add_parser("release-ast", help="Libera reservas de símbolos AST tras completar la tarea")
    release_p.add_argument("--worker", default=None, help="Worker ID o prefijo a liberar (opcional)")
    release_p.add_argument("--file", default=None, help="Ruta de archivo específico (opcional)")
    release_p.add_argument("--symbol", default=None, help="Símbolo AST específico (opcional)")
    release_p.add_argument("--all", action="store_true", help="Liberar todos los símbolos activos")

    nav_p = sub.add_parser("nav", help="Navega la vecindad AST de un símbolo con Graphify (< 150 tokens)")
    nav_p.add_argument("symbol", help="Símbolo AST o componente a consultar")
    nav_p.add_argument("--legacy", action="store_true", help="Consultar grafo de OppyTec-Legacy")
    nav_p.add_argument("--limit", type=int, default=10, help="Límite máximo de nodos/aristas devueltos (def: 10)")

    sub.add_parser("sync-graph", help="Escanea y sincroniza artefactos del proyecto en docs/architecture/graphify/graph.json")

    sub.add_parser("list-models", help="Muestra el catálogo multi-proveedor, tiers abstractos y asignación de modelos de los 13 agentes")

    bench_p = sub.add_parser("benchmark-load", help="Ejecuta la prueba de carga y estrés concurrente (SLA >= 500 RPS y P95 <= 120ms)")
    bench_p.add_argument("--concurrency", type=int, default=100, help="Número de peticiones concurrentes (def: 100)")

    resolve_m_p = sub.add_parser("resolve-model", help="Resuelve el tier, modelo primario y cadena de fallbacks de un agente o tier")
    resolve_m_p.add_argument("target", help="ID del Agente (ej: 04-backend-senior-dev) o nombre del tier (ej: tier_reasoning_heavy)")
    resolve_m_p.add_argument("--json", action="store_true", help="Salida en formato JSON")

    fallback_p = sub.add_parser("trigger-fallback", help="Ejecuta/simula una degradación por cuota agotada (HTTP 429) hacia el siguiente modelo")
    fallback_p.add_argument("target", help="ID del Agente o nombre del tier")
    fallback_p.add_argument("--failed-model", required=True, help="Modelo que agotó cuota o falló")
    fallback_p.add_argument("--reason", default="HTTP 429 Quota Exceeded / Rate Limit", help="Motivo de la falla")

    escalate_p = sub.add_parser("escalate-model", help="Escala reactivamente el tier de un agente al siguiente tier superior")
    escalate_p.add_argument("target", help="ID del Agente o nombre del tier")
    escalate_p.add_argument("--reason", default="TEST_FAILURE_REASONING_DEFICIT", help="Motivo del escalado reactivo")

    args = parser.parse_args()
    if args.command == "status":
        show_status()
        return 0
    if args.command == "verify-evals":
        return 0 if verify_anti_cheating_hashes() else 1
    if args.command == "test-fast":
        return run_test_fast_cmd()
    if args.command == "eval-llm":
        return run_eval_llm_cmd(verbose=args.verbose, fail_fast=args.exitfirst)
    if args.command == "route-task":
        route_task_cmd(args.prompt, args.json, getattr(args, "explain_complexity", False))
        return 0
    if args.command == "list-models":
        list_models_cmd()
        return 0
    if args.command == "benchmark-load":
        run_load_benchmark_cmd(args.concurrency)
        return 0
    if args.command == "resolve-model":
        res = resolve_agent_model(args.target)
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"🎯 Target: `{res['target']}` ➔ Tier: `{res['tier_key']}` ({res['tier_name']})")
            print(f"   • Modelo Primario: 🌟 {res['primary_model']}")
            print(f"   • Cadena de Fallbacks: {' ➔ '.join(res['fallback_chain']) if res['fallback_chain'] else 'Ninguno'}")
            if res.get('description'):
                print(f"   • Propósito: {res['description']}")
        return 0
    if args.command == "trigger-fallback":
        trigger_model_fallback(args.target, args.failed_model, args.reason)
        return 0
    if args.command == "escalate-model":
        escalate_model_tier(args.target, args.reason)
        return 0
    if args.command == "prepare-phase":
        prepare_phase_worktrees(args.phase)
        return 0
    if args.command == "claim-ast":
        claim_ast_symbol(args.worker, args.file, args.symbol, args.intent)
        return 0
    if args.command == "release-ast":
        release_ast_symbol(args.worker, args.file, args.symbol, getattr(args, "all", False))
        return 0
    if args.command == "nav":
        nav_ast_cmd(args.symbol, args.legacy, args.limit)
        return 0
    if args.command == "sync-graph":
        sync_graph_cmd()
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
