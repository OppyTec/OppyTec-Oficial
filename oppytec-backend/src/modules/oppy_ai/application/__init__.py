"""
Capa de Aplicación de `OppyFy` (`oppytec-backend/src/modules/oppy_ai/application/`):
- `tool_router.py`: Agente Enrutador impulsado por `JEV (Sistema 1)` hacia herramientas en código duro y redacción de costos.
- `rag_service.py`: Orquestador RAG de 3 Capas (Herramientas SQL vivas, Documentos/Memorias del local y Manuales funcionales `specs/business-domain`).
- `metered_ai_service.py`: Orquestador E2E medido que verifica créditos, `JEV`, RBAC editable (`BLOCKED_UNAUTHORIZED_PROMPT`), Tool/RAG y `llm_request_logs`.
"""
from __future__ import annotations

from src.modules.oppy_ai.application.metered_ai_service import (
    MeteredAIService,
    OppyfyAuditEntry,
    OppyfyQueryRequest,
    OppyfyQueryResponse,
)
from src.modules.oppy_ai.application.rag_service import (
    BusinessSpecChunkRecord,
    RagThreeLayerBundle,
    TenantDocumentChunkRecord,
    TenantMemoryRecord,
    ThreeLayerRagService,
)
from src.modules.oppy_ai.application.tool_router import (
    HARD_CODED_TOOL_CATALOG,
    HardCodedToolCode,
    OppyfyToolRouter,
    RoutedToolExecutionResult,
)

__all__ = [
    "HARD_CODED_TOOL_CATALOG",
    "BusinessSpecChunkRecord",
    "HardCodedToolCode",
    "MeteredAIService",
    "OppyfyAuditEntry",
    "OppyfyQueryRequest",
    "OppyfyQueryResponse",
    "OppyfyToolRouter",
    "RagThreeLayerBundle",
    "RoutedToolExecutionResult",
    "TenantDocumentChunkRecord",
    "TenantMemoryRecord",
    "ThreeLayerRagService",
]
