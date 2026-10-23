#!/usr/bin/env python3
"""
.agent/skills/jev-decision-engine/jev_router.py — Motor de Enrutamiento Cognitivo JEV (Sistema 1)
Clasifica de manera determinista e instantánea (< 15ms) cualquier requerimiento de usuario
hacia los 12 Agentes Especializados del Escuadrón de OppyTec v2.0.

Implementa:
1. `JevTaskClassification`: Dictamen tipado con Agente Líder, Agentes de Soporte, Modo (FAST_TRACK vs DAG_PIPELINE) y Confianza.
2. `JevPipelineStage`: Grafo Dirigido Acíclico (DAG) de 4 Etapas con orden lógico estricto de dependencias:
   - Etapa 1: Definición y Contratos (02-software-architect, 03-database-alembic-and-backup-engineer)
   - Etapa 2: Construcción en Paralelo (04-backend-senior-dev, 05-frontend-senior-dev)
   - Etapa 3: Capas Cruzadas y Especialistas (06-ai-oppyfy-and-jev-engineer, 07-i18n-and-fx-currency-specialist, 08-environments-and-observability-engineer)
   - Etapa 4: Calidad, Veto de Seguridad y Cierre (09-qa-parity-and-test-engineer, 10-cybersecurity-redteam-auditor, 11-git-worktree-merge-arbiter, 12-tech-writer-openspec-archify)
3. Matriz de Palabras Clave y Señales Semánticas Calibradas.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from pathlib import Path
from typing import Any


class ExecutionMode(str, Enum):
    FAST_TRACK = "FAST_TRACK"
    DAG_PIPELINE = "DAG_PIPELINE"


class SquadAgentId(str, Enum):
    ORCHESTRATOR = "01-orchestrator-pm"
    ARCHITECT = "02-software-architect"
    DATABASE = "03-database-alembic-and-backup-engineer"
    BACKEND = "04-backend-senior-dev"
    FRONTEND = "05-frontend-senior-dev"
    OPPYFY_JEV = "06-ai-oppyfy-and-jev-engineer"
    I18N_FX = "07-i18n-and-fx-currency-specialist"
    ENV_OBS = "08-environments-and-observability-engineer"
    QA = "09-qa-parity-and-test-engineer"
    RED_TEAM = "10-cybersecurity-redteam-auditor"
    MERGE_ARBITER = "11-git-worktree-merge-arbiter"
    TECH_WRITER = "12-tech-writer-openspec-archify"


@dataclass(frozen=True)
class SquadAgentMeta:
    id: SquadAgentId
    name: str
    stage: int
    tier: str
    focus: str


SQUAD_CATALOG: dict[SquadAgentId, SquadAgentMeta] = {
    SquadAgentId.ORCHESTRATOR: SquadAgentMeta(
        id=SquadAgentId.ORCHESTRATOR,
        name="Orquestador y Project Manager",
        stage=0,
        tier="Gemini 4 Argon",
        focus="Orquestación DAG, Git Worktrees, claims_registry.json y supervisión general",
    ),
    SquadAgentId.ARCHITECT: SquadAgentMeta(
        id=SquadAgentId.ARCHITECT,
        name="Arquitecto de Software DDD & Clean Architecture",
        stage=1,
        tier="Gemini 4 Argon",
        focus="DDD, Clean Architecture, paridad Legacy, Pre-Spec y Gate JEV",
    ),
    SquadAgentId.DATABASE: SquadAgentMeta(
        id=SquadAgentId.DATABASE,
        name="Especialista en Base de Datos, Alembic y Backups 4-Capas",
        stage=1,
        tier="Gemini 3.8 Flash",
        focus="PostgreSQL Multi-Schema (public/tenant_*), Alembic 0001..N y Backups zst+age",
    ),
    SquadAgentId.BACKEND: SquadAgentMeta(
        id=SquadAgentId.BACKEND,
        name="Programador Senior Backend, RBAC Dual y R2",
        stage=2,
        tier="Gemini 3.8 Flash / Argon",
        focus="FastAPI, SQLAlchemy 2 Async, RBAC 3-Niveles, Endpoints REST RFC 7807, Cuotas R2",
    ),
    SquadAgentId.FRONTEND: SquadAgentMeta(
        id=SquadAgentId.FRONTEND,
        name="Programador Senior Frontend, ADN Visual Legacy y Mobile-First",
        stage=2,
        tier="Gemini 3.8 Flash",
        focus="React 19, Tailwind, ADN Visual Legacy 3 temas, Mobile-First, <Can>, Vite, WebSockets UI",
    ),
    SquadAgentId.OPPYFY_JEV: SquadAgentMeta(
        id=SquadAgentId.OPPYFY_JEV,
        name="Ingeniero de IA OppyFy y Motor JEV",
        stage=3,
        tier="Gemini 3.8 Flash / Argon",
        focus="Asistente OppyFy (RAG 3-Capas, créditos, logs), Motor JEV Sistema 1",
    ),
    SquadAgentId.I18N_FX: SquadAgentMeta(
        id=SquadAgentId.I18N_FX,
        name="Especialista en i18n y Multi-Moneda FX",
        stage=3,
        tier="Gemini 3.8 Flash",
        focus="i18n Estático/Dinámico (11 namespaces es/en, 'Pollo King') y Multi-Moneda FX (BCCh/BCE Decimal)",
    ),
    SquadAgentId.ENV_OBS: SquadAgentMeta(
        id=SquadAgentId.ENV_OBS,
        name="Ingeniero de Entornos y Observabilidad 4-Pilares",
        stage=3,
        tier="Gemini 3.8 Flash",
        focus="5 Entornos (local..production), Docker, OpenTelemetry, Grafana LGTM, Sentry, Umami",
    ),
    SquadAgentId.QA: SquadAgentMeta(
        id=SquadAgentId.QA,
        name="Ingeniero de QA, Tests 1:1 y Paridad con Legacy",
        stage=4,
        tier="Gemini 4 Argon / Flash",
        focus="Testing 5D, Vitest, Pytest unit/integration/e2e, Locust 500 RPS, bucle autoreparación",
    ),
    SquadAgentId.RED_TEAM: SquadAgentMeta(
        id=SquadAgentId.RED_TEAM,
        name="Auditor Estricto de Ciberseguridad Red Team (Veto)",
        stage=4,
        tier="Gemini 4 Argon",
        focus="11 Vectores Red Team (IDOR, Injection, Tenant Escape), Semgrep/Trivy, Veto Final",
    ),
    SquadAgentId.MERGE_ARBITER: SquadAgentMeta(
        id=SquadAgentId.MERGE_ARBITER,
        name="Especialista en Git Worktrees y Árbitro de Smart Merge",
        stage=4,
        tier="Gemini 4 Argon",
        focus="Merge Train (rebase + ff-only), resolución de conflictos determinista",
    ),
    SquadAgentId.TECH_WRITER: SquadAgentMeta(
        id=SquadAgentId.TECH_WRITER,
        name="Technical Writer, OpenSpec Bipartito, Graphify y Archify",
        stage=4,
        tier="Gemini 3.8 Flash",
        focus="Bóvedas OpenSpec (business vs engineering), Graphify AST, Atlas Archify, Bitácora",
    ),
}

# Señales semánticas de alta precisión para cada agente
AGENT_SIGNALS: dict[SquadAgentId, tuple[str, ...]] = {
    SquadAgentId.FRONTEND: (
        "vista", "vistas", "pantalla", "pantallas", "componente", "componentes",
        "botón", "boton", "tabla", "formulario", "modal", "dialog", "diseño", "diseno",
        "css", "tailwind", "react", "vite", "frontend", "ui", "ux", "tema", "color",
        "sidebar", "navbar", "dashboard", "holding", "holdings", "tenants", "usuarios clientes",
        "no se ve", "no muestran contenido", "no muestra", "icono", "iconos", "render",
    ),
    SquadAgentId.BACKEND: (
        "api", "endpoint", "endpoints", "router", "schemas", "fastapi", "sqlalchemy",
        "backend", "servicio", "pydantic", "payload", "post", "get", "put", "patch", "delete",
        "controlador", "uow", "unit of work", "repository", "cuota", "cuotas", "r2", "bucket",
    ),
    SquadAgentId.DATABASE: (
        "base de datos", "database", "postgres", "postgresql", "alembic", "migracion",
        "migraciones", "migration", "tabla bd", "esquema", "schema", "search_path", "backup",
        "respaldo", "restore", "sql", "columna", "foreign key", "0001", "0002", "0003",
    ),
    SquadAgentId.ARCHITECT: (
        "arquitectura", "clean architecture", "ddd", "dominio", "capas", "entidad",
        "value object", "agregado", "spec previa", "refactorizar estructura", "patron",
    ),
    SquadAgentId.I18N_FX: (
        "i18n", "traduccion", "traducciones", "idioma", "idiomas", "ingles", "espanol",
        "english", "spanish", "locales", "namespace", "pollo king", "fx", "divisa",
        "moneda", "tipo de cambio", "bcch", "bce", "dolar", "euro", "clp", "usd",
    ),
    SquadAgentId.OPPYFY_JEV: (
        "oppyfy", "asistente ia", "ia", "ai", "rag", "creditos ia", "tokens ia",
        "jev", "sistema 1", "decision engine", "llm_request_logs", "prompt injection",
    ),
    SquadAgentId.ENV_OBS: (
        "entorno", "entornos", "docker", "docker-compose", "container", "contenedor",
        "observabilidad", "opentelemetry", "otel", "grafana", "prometheus", "loki",
        "sentry", "umami", "telemetria", "logs docker", "nginx",
    ),
    SquadAgentId.QA: (
        "test", "tests", "prueba", "pruebas", "unit test", "integration test", "e2e",
        "vitest", "pytest", "locust", "coverage", "cobertura", "qa", "calidad",
        "fallo el test", "paridad", "regression", "regresion",
    ),
    SquadAgentId.RED_TEAM: (
        "seguridad", "ciberseguridad", "vulnerabilidad", "idor", "xss", "sqli", "injection",
        "semgrep", "trivy", "pip-audit", "pnpm audit", "kali", "red team", "veto", "bypass",
    ),
    SquadAgentId.MERGE_ARBITER: (
        "git", "worktree", "worktrees", "merge", "rebase", "conflicto", "merge train",
        "rama", "branch", "fast-forward", "ff-only", "pull request", "pr",
    ),
    SquadAgentId.TECH_WRITER: (
        "documentacion", "documentar", "openspec", "spec", "specs", "bitacora",
        "archify", "atlas", "mapa visual", "graphify", "readme", "obsidian",
    ),
    SquadAgentId.ORCHESTRATOR: (
        "fase", "plan maestro", "orquestar", "coordinar", "todo el escuadron", "dag",
    ),
}


@dataclass(frozen=True)
class PipelineStage:
    stage_number: int
    stage_name: str
    agents: list[SquadAgentId]
    execution_type: str  # "PARALLEL" | "SEQUENTIAL"


@dataclass(frozen=True)
class JevTaskClassification:
    primary_agent: SquadAgentId
    primary_agent_name: str
    mode: ExecutionMode
    confidence: Decimal
    supporting_agents: list[SquadAgentId]
    rationale: str
    pipeline: list[PipelineStage]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["confidence"] = str(self.confidence)
        data["primary_agent"] = self.primary_agent.value
        data["mode"] = self.mode.value
        data["supporting_agents"] = [a.value for a in self.supporting_agents]
        for stage in data["pipeline"]:
            stage["agents"] = [a.value if isinstance(a, SquadAgentId) else a for a in stage["agents"]]
        return data

    def to_header(self) -> str:
        supp_str = (
            f" + [{', '.join(a.value.split('-')[1] for a in self.supporting_agents)}]"
            if self.supporting_agents
            else ""
        )
        return (
            f"🎯 **[JEV Router v2.0]** "
            f"**Agente Líder:** `{self.primary_agent.value}`{supp_str} | "
            f"**Modo:** `{self.mode.value}` | "
            f"**Confianza:** `{self.confidence * 100:.1f}%`"
        )


def _tokenize(text: str) -> set[str]:
    clean = re.sub(r"[^a-zA-Z0-9áéíóúñÁÉÍÓÚÑ_\s-]", " ", text.lower())
    return {token for token in clean.split() if len(token) > 1}


def classify_user_request(prompt: str) -> JevTaskClassification:
    """
    Evalúa la intención de la tarea mediante JEV (Sistema 1) determinista.
    Calcula scores por coincidencia de señales normalizadas y calibración de confianza.
    """
    prompt_lower = prompt.lower()
    tokens = _tokenize(prompt)

    scores: dict[SquadAgentId, int] = {agent: 0 for agent in SquadAgentId}

    for agent_id, signals in AGENT_SIGNALS.items():
        for signal in signals:
            if " " in signal:
                if signal in prompt_lower:
                    scores[agent_id] += 3
            else:
                if signal in tokens:
                    scores[agent_id] += 2

    # Ordenar agentes por score descendente
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_agent, top_score = ranked[0]

    # Si no hay señales claras, el Orquestador toma la coordinación por defecto
    if top_score == 0:
        top_agent = SquadAgentId.ORCHESTRATOR
        top_score = 1
        confidence = Decimal("0.70")
    else:
        # Calibración de confianza JEV (0.80..0.99)
        raw_conf = Decimal("0.80") + Decimal(min(top_score, 10)) * Decimal("0.019")
        confidence = min(raw_conf, Decimal("0.99")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Identificar agentes de soporte (score > 1 y distinto del líder)
    supporting: list[SquadAgentId] = [
        agent for agent, score in ranked[1:]
        if score >= 2 and agent != top_agent and agent != SquadAgentId.ORCHESTRATOR
    ]

    # Detectar si la tarea requiere DAG Multi-Agente
    # Regla: Si intervienen Frontend y Backend, o DB + Backend, o se pide algo transversal
    is_multi_agent = len(supporting) > 0 or any(
        kw in prompt_lower
        for kw in ("completo", "flujo", "crear modulo", "refactorizar", "paridad", "ambos", "fullstack")
    )

    if not is_multi_agent or len(supporting) == 0:
        mode = ExecutionMode.FAST_TRACK
        meta = SQUAD_CATALOG[top_agent]
        pipeline = [
            PipelineStage(
                stage_number=meta.stage,
                stage_name=f"Ejecución Directa ({meta.name})",
                agents=[top_agent],
                execution_type="PARALLEL",
            )
        ]
        rationale = f"Tarea acotada exclusivamente al ámbito de {meta.name}."
    else:
        mode = ExecutionMode.DAG_PIPELINE
        all_involved = [top_agent] + supporting

        # Si intervienen cambios de código, siempre involucrar QA en la etapa de cierre
        if (SquadAgentId.FRONTEND in all_involved or SquadAgentId.BACKEND in all_involved) and (
            SquadAgentId.QA not in all_involved
        ):
            all_involved.append(SquadAgentId.QA)

        # Agrupar por etapas lógicas de dependencias
        stage_groups: dict[int, list[SquadAgentId]] = {1: [], 2: [], 3: [], 4: []}
        for agent in all_involved:
            stg = SQUAD_CATALOG[agent].stage
            if stg == 0:
                continue
            if agent not in stage_groups[stg]:
                stage_groups[stg].append(agent)

        stage_names = {
            1: "Definición de Arquitectura, Contratos y Esquemas DB",
            2: "Construcción en Código (Backend & Frontend en Paralelo)",
            3: "Capas Especializadas (i18n, FX, OppyFy, Observabilidad)",
            4: "Quality Gate, Pruebas 5D, Veto de Seguridad y Documentación",
        }

        pipeline = []
        for stg_num in (1, 2, 3, 4):
            agents_in_stage = stage_groups[stg_num]
            if agents_in_stage:
                pipeline.append(
                    PipelineStage(
                        stage_number=stg_num,
                        stage_name=stage_names[stg_num],
                        agents=agents_in_stage,
                        execution_type="PARALLEL" if len(agents_in_stage) > 1 else "SEQUENTIAL",
                    )
                )

        rationale = (
            f"Tarea transversal con dependencias ordenadas: "
            f"{' -> '.join(f'Etapa {s.stage_number} ({len(s.agents)} agentes)' for s in pipeline)}."
        )

    return JevTaskClassification(
        primary_agent=top_agent,
        primary_agent_name=SQUAD_CATALOG[top_agent].name,
        mode=mode,
        confidence=confidence,
        supporting_agents=supporting,
        rationale=rationale,
        pipeline=pipeline,
    )


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python jev_router.py \"<prompt del usuario>\" [--json]")
        sys.exit(1)

    prompt_arg = sys.argv[1]
    is_json = "--json" in sys.argv

    classification = classify_user_request(prompt_arg)

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


if __name__ == "__main__":
    main()
