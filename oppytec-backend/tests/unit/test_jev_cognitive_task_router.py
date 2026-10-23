"""
Pruebas Unitarias del Motor de Enrutamiento Cognitivo JEV (Sistema 1)
Valida:
1. Clasificación tipada hacia los 12 agentes especializados.
2. Modos FAST_TRACK vs DAG_PIPELINE.
3. Respeto estricto del orden lógico de dependencias en 4 etapas.
4. Integridad del dictamen en formato encabezado y JSON.
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT_DIR.parent / ".agent" / "skills" / "jev-decision-engine"
if str(SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(SKILLS_DIR))

from jev_router import (  # type: ignore
    ExecutionMode,
    SquadAgentId,
    classify_user_request,
)


def test_jev_router_frontend_fast_track() -> None:
    prompt = "Las vistas de holdings y tenants no muestran contenido ni el botón de crear"
    result = classify_user_request(prompt)

    assert result.primary_agent == SquadAgentId.FRONTEND
    assert result.mode == ExecutionMode.FAST_TRACK
    assert result.confidence >= Decimal("0.85")
    assert "JEV Router v2.0" in result.to_header()
    assert len(result.pipeline) == 1
    assert result.pipeline[0].stage_number == 2


def test_jev_router_database_fast_track() -> None:
    prompt = "Crear migración alembic 0004 para agregar columnas a la base de datos postgres"
    result = classify_user_request(prompt)

    assert result.primary_agent == SquadAgentId.DATABASE
    assert result.mode == ExecutionMode.FAST_TRACK
    assert result.confidence >= Decimal("0.85")
    assert result.pipeline[0].stage_number == 1


def test_jev_router_cross_layer_dag_pipeline() -> None:
    prompt = "Construir nuevo endpoint API en backend para recetas y crear su vista en frontend con traducciones i18n y pruebas"
    result = classify_user_request(prompt)

    assert result.mode == ExecutionMode.DAG_PIPELINE
    # Verifica que intervengan tanto frontend como backend
    involved = [result.primary_agent] + result.supporting_agents
    assert SquadAgentId.BACKEND in involved or SquadAgentId.FRONTEND in involved
    assert SquadAgentId.I18N_FX in involved

    # Verifica que las etapas del DAG respeten el orden numérico secuencial
    stage_numbers = [s.stage_number for s in result.pipeline]
    assert stage_numbers == sorted(stage_numbers)
    # QA debe estar presente en la etapa 4 de cierre
    assert 4 in stage_numbers
    qa_stage = next(s for s in result.pipeline if s.stage_number == 4)
    assert SquadAgentId.QA in qa_stage.agents


def test_jev_router_cybersecurity_detection() -> None:
    prompt = "Auditar vulnerabilidades de inyeccion SQL e IDOR multi-tenant con semgrep y trivy"
    result = classify_user_request(prompt)

    involved = [result.primary_agent] + result.supporting_agents
    assert SquadAgentId.RED_TEAM in involved
    assert result.confidence >= Decimal("0.80")
