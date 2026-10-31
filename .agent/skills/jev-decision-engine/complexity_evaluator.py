#!/usr/bin/env python3
"""
.agent/skills/jev-decision-engine/complexity_evaluator.py — Evaluador de Complejidad Cognitiva JEV
Calcula en tiempo constante (< 15 ms) el puntaje C_task en [0.0, 1.0] basado en 4 dimensiones:
1. S_graph   (35%): Vecindad Graphify AST e interconexión de entidades y claves foráneas.
2. S_domain  (30%): Criticidad del dominio (Seguridad/RBAC/Finanzas/Kardex vs CRUD vs i18n/CSS).
3. S_scope   (20%): Alcance del flujo (FAST_TRACK unipersonal vs DAG_PIPELINE multi-etapa).
4. S_context (15%): Densidad contextual, ambigüedad y contratos estructurales a respetar.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[3]
MODEL_ROUTER_FILE = ROOT_DIR / ".agent" / "config" / "model_router.json"


@dataclass(frozen=True)
class TaskComplexityReport:
    complexity_score: Decimal
    level: str  # "BAJO" | "MEDIO" | "ALTO"
    promoted_tier: str  # "tier_lightweight" | "tier_fast_execution" | "tier_reasoning_heavy"
    dimension_scores: dict[str, Decimal]
    dimension_weights: dict[str, Decimal]
    rationale: str
    target_symbols: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "complexity_score": str(self.complexity_score),
            "level": self.level,
            "promoted_tier": self.promoted_tier,
            "dimension_scores": {k: str(v) for k, v in self.dimension_scores.items()},
            "dimension_weights": {k: str(v) for k, v in self.dimension_weights.items()},
            "rationale": self.rationale,
            "target_symbols": self.target_symbols,
        }

    def explain(self) -> str:
        lines = [
            f"📊 Desglose de Complejidad Cognitiva JEV (Score Global: {self.complexity_score} — {self.level}):",
            f"   • S_graph   ({self.dimension_weights.get('graph', Decimal('0.35')) * 100:.0f}%): {self.dimension_scores.get('graph', Decimal('0.0'))} — Interconexión AST y entidades",
            f"   • S_domain  ({self.dimension_weights.get('domain', Decimal('0.30')) * 100:.0f}%): {self.dimension_scores.get('domain', Decimal('0.0'))} — Criticidad de dominio de negocio",
            f"   • S_scope   ({self.dimension_weights.get('scope', Decimal('0.20')) * 100:.0f}%): {self.dimension_scores.get('scope', Decimal('0.0'))} — Alcance de ejecución (FAST_TRACK vs DAG)",
            f"   • S_context ({self.dimension_weights.get('context', Decimal('0.15')) * 100:.0f}%): {self.dimension_scores.get('context', Decimal('0.0'))} — Densidad contextual y contratos",
            f"   ➔ Tier Dinámico Resultante: `{self.promoted_tier}`",
            f"   ➔ Justificación: {self.rationale}",
        ]
        return "\n".join(lines)


def _load_router_config() -> dict[str, Any]:
    if MODEL_ROUTER_FILE.exists():
        try:
            return json.loads(MODEL_ROUTER_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _extract_potential_symbols(prompt: str) -> list[str]:
    """Extrae posibles nombres de entidades, tablas o módulos a partir del prompt."""
    tokens = re.findall(r"\b[A-Za-zÁÉÍÓÚáéíóúñÑ][A-Za-z0-9_ÁÉÍÓÚáéíóúñÑ]{2,}\b", prompt)
    known_entities = {
        "kardex", "invoice", "sales", "tenant", "holding", "user", "role", "permission",
        "movement", "product", "inventory", "currency", "fx", "audit", "account", "transaction",
        "factura", "facturacion", "usuario", "unidad", "precio", "impuesto", "postal",
        "cliente", "clientes", "producto", "productos", "proveedor", "proveedores",
        "orden", "ordenes", "item", "items", "receta", "recetas", "categoria", "categorias"
    }
    extracted = [t.lower() for t in tokens if t.lower() in known_entities]
    return list(dict.fromkeys(extracted))


def _evaluate_graph_dimension(
    prompt: str,
    target_symbols: list[str],
) -> tuple[Decimal, list[str]]:
    """
    Evalúa la dimensión S_graph (35%) consultando Graphify AST o aplicando heurística de conectividad.
    """
    symbols = target_symbols or _extract_potential_symbols(prompt)
    edge_count = 0

    # Intento de consulta no bloqueante a Graphify AST si hay símbolos
    try:
        from graph_navigator import v2_graph  # type: ignore
        for sym in symbols[:3]:
            res = v2_graph.neighbors(sym, limit=10)
            edge_count += len(res.get("edges", []))
    except Exception:
        # Fallback si no está en sys.path o el grafo está en construcción
        pass

    prompt_lower = prompt.lower()

    # Indicadores explícitos de aislamiento / tabla plana / cosmética
    isolation_keywords = [
        "plana", "solo lectura", "aislada", "sin claves", "constante", "estatica",
        "codigo postal", "codigos postales", "badge", "color", "label", "icono"
    ]
    if any(kw in prompt_lower for kw in isolation_keywords) and not any(
        crit in prompt_lower for crit in ["kardex", "transaccion", "fx", "tenant", "alembic"]
    ):
        return Decimal("0.10"), symbols

    # Si encontramos aristas AST reales
    if edge_count >= 3:
        return Decimal("1.00"), symbols
    elif edge_count == 2:
        return Decimal("0.70"), symbols
    elif edge_count == 1:
        return Decimal("0.40"), symbols

    # Heurística léxica si no hubo coincidencias en graph.json
    cross_table_keywords = [
        "vinculada", "vinculado", "relacion", "relaciones", "foreign key", "fk",
        "kardex", "facturacion", "multi-tenant", "transaccional", "recalculo",
        "calculo fx", "cálculo fx", "interconexion", "join", "inventario multi-tenant"
    ]
    matched_cross = [kw for kw in cross_table_keywords if kw in prompt_lower]
    if len(matched_cross) >= 2:
        return Decimal("1.00"), symbols
    elif len(matched_cross) == 1:
        return Decimal("0.65"), symbols

    # Operaciones CRUD o interacción con entidades/endpoints
    data_ops = ["crud", "endpoint", "endpoints", "tabla", "modelo", "servicio", "repositorio", "formulario"]
    if any(op in prompt_lower for op in data_ops) or symbols:
        return Decimal("0.45"), symbols

    return Decimal("0.20"), symbols


def _evaluate_domain_dimension(prompt: str, cfg: dict[str, Any]) -> Decimal:
    """
    Evalúa la dimensión S_domain (30%) según la criticidad del negocio.
    """
    prompt_lower = prompt.lower()
    weights_cfg = cfg.get("domain_criticality_weights", {})

    high_cfg = weights_cfg.get("high", {})
    high_kws = high_cfg.get("keywords", [
        "transaccion", "transacciones", "kardex", "balance", "moneda", "fx",
        "rbac", "auth", "tenant", "tenants", "cifrado", "alembic", "migracion",
        "acid", "conciliacion", "red team", "seguridad", "ciberseguridad", "rebase"
    ])
    if any(kw in prompt_lower for kw in high_kws):
        return Decimal(str(high_cfg.get("weight", "1.00")))

    med_cfg = weights_cfg.get("medium", {})
    med_kws = med_cfg.get("keywords", [
        "formulario", "filtro", "busqueda", "paginacion", "crud", "endpoint",
        "servicio", "repositorio", "uow", "componente", "modal"
    ])
    if any(kw in prompt_lower for kw in med_kws):
        return Decimal(str(med_cfg.get("weight", "0.50")))

    low_cfg = weights_cfg.get("low", {})
    low_kws = low_cfg.get("keywords", [
        "estilo", "color", "traduccion", "i18n", "solo lectura", "plana",
        "constante", "badge", "label", "icono", "codigo postal"
    ])
    if any(kw in prompt_lower for kw in low_kws):
        return Decimal(str(low_cfg.get("weight", "0.10")))

    return Decimal("0.40")


def _evaluate_scope_dimension(
    mode: str,
    supporting_agents: list[str],
    prompt: str,
) -> Decimal:
    """
    Evalúa la dimensión S_scope (20%) según el modo y número de agentes/etapas.
    """
    prompt_lower = prompt.lower()
    if mode == "DAG_PIPELINE" or len(supporting_agents) >= 2:
        # Multi-agente con múltiples etapas
        supp_count = len(supporting_agents)
        base = Decimal("0.70") + Decimal(min(supp_count, 3)) * Decimal("0.10")
        return min(base, Decimal("1.00"))
    elif mode == "DAG_PIPELINE" or len(supporting_agents) == 1:
        return Decimal("0.70")

    # FAST_TRACK: Evaluar si es puramente cosmética/atómica o si involucra cierta lógica
    cosmetic_kws = ["color", "badge", "estilo", "css", "traduccion", "solo lectura", "plana", "codigo postal", "label", "icono"]
    if any(kw in prompt_lower for kw in cosmetic_kws) and not any(
        crit in prompt_lower for crit in ["crud", "endpoint", "kardex", "transaccion", "fx"]
    ):
        return Decimal("0.10")

    return Decimal("0.30")


def _evaluate_context_dimension(prompt: str) -> Decimal:
    """
    Evalúa la dimensión S_context (15%) midiendo densidad conceptual y contratos a respetar.
    """
    prompt_lower = prompt.lower()
    density_indicators = [
        "refactorizar", "paridad legacy", "clean architecture", "multi-tenant",
        "transaccional", "recalculo", "acid", "audit", "aislamiento", "cuota",
        "concurrencia", "restriccion", "validacion estricta", "dependencia"
    ]
    matched = [kw for kw in density_indicators if kw in prompt_lower]

    score = Decimal("0.10")
    if len(matched) >= 3 or (len(prompt) > 160 and len(matched) >= 2):
        score = Decimal("1.00")
    elif len(matched) >= 2 or len(prompt) > 140:
        score = Decimal("0.75")
    elif len(matched) == 1 or len(prompt) > 80:
        score = Decimal("0.45")

    return score


def evaluate_task_complexity(
    prompt: str,
    primary_agent: str,
    supporting_agents: list[str] | None = None,
    mode: str = "FAST_TRACK",
    target_symbols: list[str] | None = None,
) -> TaskComplexityReport:
    """
    Evalúa matemáticamente la complejidad cognitiva de una tarea en tiempo constante (< 15 ms).
    Calcula: C_task = min(1.0, w_graph * S_graph + w_domain * S_domain + w_scope * S_scope + w_context * S_context).
    """
    cfg = _load_router_config()
    supporting = supporting_agents or []

    # Carga de pesos configurables (con fallbacks declarativos)
    weights_cfg = cfg.get("dimension_weights", {})
    w_graph = Decimal(str(weights_cfg.get("graph", "0.35")))
    w_domain = Decimal(str(weights_cfg.get("domain", "0.30")))
    w_scope = Decimal(str(weights_cfg.get("scope", "0.20")))
    w_context = Decimal(str(weights_cfg.get("context", "0.15")))

    # 1. Dimensión Graphify AST (35%)
    s_graph, discovered_symbols = _evaluate_graph_dimension(prompt, target_symbols or [])

    # 2. Dimensión Criticidad de Dominio (30%)
    s_domain = _evaluate_domain_dimension(prompt, cfg)

    # 3. Dimensión Alcance (20%)
    s_scope = _evaluate_scope_dimension(mode, supporting, prompt)

    # 4. Dimensión Densidad de Contexto (15%)
    s_context = _evaluate_context_dimension(prompt)

    # Cálculo consolidado C_task en [0.0, 1.0]
    raw_score = (
        (w_graph * s_graph)
        + (w_domain * s_domain)
        + (w_scope * s_scope)
        + (w_context * s_context)
    )
    complexity_score = min(Decimal("1.00"), raw_score).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Clasificación en Tiers según umbrales configurados
    thresholds = cfg.get("complexity_thresholds", {})
    light_max = Decimal(str(thresholds.get("lightweight_max", "0.34")))
    heavy_min = Decimal(str(thresholds.get("reasoning_heavy_min", "0.70")))

    if complexity_score <= light_max:
        level = "BAJO"
        promoted_tier = "tier_lightweight"
        rationale = f"Complejidad cognitiva baja ({complexity_score} <= {light_max}). Tarea atómica o de catálogo plano sin alta interconexión."
    elif complexity_score >= heavy_min:
        level = "ALTO"
        promoted_tier = "tier_reasoning_heavy"
        rationale = f"Complejidad cognitiva alta ({complexity_score} >= {heavy_min}). Demanda razonamiento profundo, interconexión transaccional y validación estricta."
    else:
        level = "MEDIO"
        promoted_tier = "tier_fast_execution"
        rationale = f"Complejidad cognitiva moderada ({complexity_score}). Ejecución estándar balanceada de construcción y mantenimiento."

    dimension_scores = {
        "graph": s_graph.quantize(Decimal("0.01")),
        "domain": s_domain.quantize(Decimal("0.01")),
        "scope": s_scope.quantize(Decimal("0.01")),
        "context": s_context.quantize(Decimal("0.01")),
    }
    dimension_weights = {
        "graph": w_graph,
        "domain": w_domain,
        "scope": w_scope,
        "context": w_context,
    }

    return TaskComplexityReport(
        complexity_score=complexity_score,
        level=level,
        promoted_tier=promoted_tier,
        dimension_scores=dimension_scores,
        dimension_weights=dimension_weights,
        rationale=rationale,
        target_symbols=discovered_symbols,
    )
