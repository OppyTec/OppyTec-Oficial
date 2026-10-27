"""
Capa de Aplicación de `OppyFy` (`oppytec-backend/src/modules/oppy_ai/application/`):
- `tool_router.py`: Agente Enrutador impulsado por `JEV (Sistema 1)` hacia herramientas en código duro y redacción de costos.
- `rag_service.py`: Orquestador RAG de 3 Capas (Herramientas SQL vivas, Documentos/Memorias del local y Manuales funcionales `specs/business-domain`).
- `metered_ai_service.py`: Orquestador E2E medido que verifica créditos, `JEV`, RBAC editable (`BLOCKED_UNAUTHORIZED_PROMPT`), Tool/RAG y `llm_request_logs`.
- `token_consumption_service.py`: Consola FinOps de consumo de tokens y auditoría de IA.
- `ai_credit_packs_service.py`: CRUD de paquetes de créditos IA independientes para Platform Admin.
- `operational_tools/`: Herramientas operativas deterministas (inventario, banquetes, FEFO, mermas, canvas).
"""
from __future__ import annotations

from src.modules.oppy_ai.application.ai_credit_packs_service import (
    AiCreditPackNotFoundError,
    AiCreditPacksService,
    CreditPackDTO,
    CreditPackPurchaseQuoteDTO,
)
from src.modules.oppy_ai.application.metered_ai_service import (
    DEFAULT_MODEL_TARIFFS,
    MeteredAIService,
    ModelConfigRegistry,
    ModelTariff,
    OppyfyAuditEntry,
    OppyfyQueryRequest,
    OppyfyQueryResponse,
)
from src.modules.oppy_ai.application.rag_service import (
    BusinessSpecChunkRecord,
    InMemoryRedisSemanticCache,
    RagThreeLayerBundle,
    SemanticCachePort,
    TenantDocumentChunkRecord,
    TenantMemoryRecord,
    ThreeLayerRagService,
)
from src.modules.oppy_ai.application.token_consumption_service import (
    FinOpsAnalyticsDTO,
    HoldingGroupDTO,
    TenantGroupDTO,
    TokenConsumptionAggregatorService,
    TokenConsumptionSummaryDTO,
    TokenLogItemDTO,
)
from src.modules.oppy_ai.application.tool_router import (
    HARD_CODED_TOOL_CATALOG,
    HardCodedToolCode,
    OppyfyToolRouter,
    RoutedToolExecutionResult,
)

__all__ = [
    "DEFAULT_MODEL_TARIFFS",
    "HARD_CODED_TOOL_CATALOG",
    "AiCreditPackNotFoundError",
    "AiCreditPacksService",
    "BusinessSpecChunkRecord",
    "CreditPackDTO",
    "CreditPackPurchaseQuoteDTO",
    "FinOpsAnalyticsDTO",
    "HardCodedToolCode",
    "HoldingGroupDTO",
    "InMemoryRedisSemanticCache",
    "MeteredAIService",
    "ModelConfigRegistry",
    "ModelTariff",
    "OppyfyAuditEntry",
    "OppyfyQueryRequest",
    "OppyfyQueryResponse",
    "OppyfyToolRouter",
    "RagThreeLayerBundle",
    "RoutedToolExecutionResult",
    "SemanticCachePort",
    "TenantDocumentChunkRecord",
    "TenantGroupDTO",
    "TenantMemoryRecord",
    "ThreeLayerRagService",
    "TokenConsumptionAggregatorService",
    "TokenConsumptionSummaryDTO",
    "TokenLogItemDTO",
]
