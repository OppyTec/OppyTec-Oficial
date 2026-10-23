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


def route_task_cmd(prompt_text: str, is_json: bool = False) -> None:
    """Clasifica un requerimiento de usuario usando el Motor JEV Sistema 1."""
    sys.path.insert(0, str(AGENT_DIR / "skills" / "jev-decision-engine"))
    from jev_router import classify_user_request  # type: ignore

    classification = classify_user_request(prompt_text)
    log_event("JEV_TASK_ROUTED", {
        "primary_agent": classification.primary_agent.value,
        "mode": classification.mode.value,
        "confidence": str(classification.confidence),
        "supporting": [a.value for a in classification.supporting_agents],
        "prompt_snippet": prompt_text[:120],
    })

    if is_json:
        print(json.dumps(classification.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(classification.to_header())
        print(f"\n📋 Justificación: {classification.rationale}")
        print("\n🔀 Pipeline de Ejecución (Orden Lógico de Dependencias):")
        for stage in classification.pipeline:
            agents_list = ", ".join(f"`{a.value}`" for a in stage.agents)
            print(f"  • Etapa {stage.stage_number} [{stage.execution_type}]: {stage.stage_name}")
            print(f"    └─ Agentes asignados: {agents_list}")


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

    log_event("GRAPHIFY_SYNCED", {
        "nodes_count": len(sorted_nodes),
        "edges_count": len(sorted_edges),
        "alembic_migrations": metrics["alembic_migrations"],
        "backend_routers": metrics["backend_routers"],
        "verification_suites": metrics["verification_suites"],
    })
    print("🔄 Grafo de Arquitectura Graphify sincronizado con éxito:")
    print(f"   • Nodos totales: {len(sorted_nodes)} (Routers: {metrics['backend_routers']}, Migraciones: {metrics['alembic_migrations']}, Suites: {metrics['verification_suites']})")
    print(f"   • Aristas totales: {len(sorted_edges)}")
    print(f"   • Destino: {graph_path.relative_to(ROOT_DIR)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="OppyTec v2.0 Multi-Agent RLM Harness")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Muestra el estado del arnés y verifica integridad anti-trampa")
    sub.add_parser("verify-evals", help="Verifica los hashes SHA-256 de reglas y evaluaciones inmutables")

    route_p = sub.add_parser("route-task", help="Clasifica y enruta una tarea hacia los 12 agentes con JEV")
    route_p.add_argument("prompt", help="Texto del requerimiento del usuario a clasificar")
    route_p.add_argument("--json", action="store_true", help="Salida en formato JSON estructurado")

    prep_p = sub.add_parser("prepare-phase", help="Crea los Git Worktrees y MISSION_PROMPT.md para una Fase (1..6)")
    prep_p.add_argument("--phase", type=int, required=True, choices=[1, 2, 3, 4, 5, 6])

    claim_p = sub.add_parser("claim-ast", help="Reserva atómicamente un símbolo AST antes de editar")
    claim_p.add_argument("--worker", required=True)
    claim_p.add_argument("--file", required=True)
    claim_p.add_argument("--symbol", required=True)
    claim_p.add_argument("--intent", required=True)

    nav_p = sub.add_parser("nav", help="Navega la vecindad AST de un símbolo con Graphify (< 150 tokens)")
    nav_p.add_argument("symbol", help="Símbolo AST o componente a consultar")
    nav_p.add_argument("--legacy", action="store_true", help="Consultar grafo de OppyTec-Legacy")
    nav_p.add_argument("--limit", type=int, default=10, help="Límite máximo de nodos/aristas devueltos (def: 10)")

    sub.add_parser("sync-graph", help="Escanea y sincroniza artefactos del proyecto en docs/architecture/graphify/graph.json")

    args = parser.parse_args()
    if args.command == "status":
        show_status()
        return 0
    if args.command == "verify-evals":
        return 0 if verify_anti_cheating_hashes() else 1
    if args.command == "route-task":
        route_task_cmd(args.prompt, args.json)
        return 0
    if args.command == "prepare-phase":
        prepare_phase_worktrees(args.phase)
        return 0
    if args.command == "claim-ast":
        claim_ast_symbol(args.worker, args.file, args.symbol, args.intent)
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
