"""
Adaptadores Cognitivos (`oppytec-backend/src/adapters/ai/`):
Protocolos y clientes medidos para `JEV (Sistema 1)` y `Gemini (Sistema 2 + Embeddings + Audio)`,
con registro obligatorio en `public.jev_request_logs` y `public.llm_request_logs`.
"""
from __future__ import annotations

from src.adapters.ai.gemini_adapter import (
    AudioUsageRecord,
    GeminiGenerationResult,
    MeteredGeminiAdapter,
)
from src.adapters.ai.jev_adapter import (
    DatabaseJevTelemetrySink,
    InMemoryJevTelemetrySink,
    InMemoryTelemetrySink,
    MeteredJevAdapter,
)
from src.adapters.ai.jev_protocol import (
    DEFAULT_JEV_CONFIDENCE_THRESHOLD,
    MAX_JEV_BATCH_SIZE,
    JevBooleanResult,
    JevChoiceBatchItem,
    JevChoiceResult,
    JevDecisionPort,
    JevScoreLevel,
    JevScoreResult,
    JevTelemetrySinkPort,
    JevUsageRecord,
)
from src.adapters.ai.protocol import (
    EmbeddingPort,
    EngineTierLiteral,
    LLMProviderPort,
    LlmTelemetrySinkPort,
    LlmUsageRecord,
)

__all__ = [
    "AudioUsageRecord",
    "DEFAULT_JEV_CONFIDENCE_THRESHOLD",
    "DatabaseJevTelemetrySink",
    "EmbeddingPort",
    "EngineTierLiteral",
    "GeminiGenerationResult",
    "InMemoryJevTelemetrySink",
    "InMemoryTelemetrySink",
    "JevBooleanResult",
    "JevChoiceBatchItem",
    "JevChoiceResult",
    "JevDecisionPort",
    "JevScoreLevel",
    "JevScoreResult",
    "JevTelemetrySinkPort",
    "JevUsageRecord",
    "LLMProviderPort",
    "LlmTelemetrySinkPort",
    "LlmUsageRecord",
    "MAX_JEV_BATCH_SIZE",
    "MeteredGeminiAdapter",
    "MeteredJevAdapter",
]
