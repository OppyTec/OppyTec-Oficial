"""
Adaptadores Cognitivos (`oppytec-backend/src/adapters/ai/`):
Protocolos y clientes medidos para `JEV (Sistema 1)` y `Gemini (Sistema 2 + Embeddings + Audio)`,
con registro obligatorio en `public.llm_request_logs`.
"""
from __future__ import annotations

from src.adapters.ai.gemini_adapter import (
    AudioUsageRecord,
    GeminiGenerationResult,
    MeteredGeminiAdapter,
)
from src.adapters.ai.jev_adapter import MeteredJevAdapter
from src.adapters.ai.jev_protocol import (
    JevBooleanResult,
    JevChoiceResult,
    JevDecisionPort,
    JevScoreLevel,
    JevScoreResult,
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
    "EmbeddingPort",
    "EngineTierLiteral",
    "GeminiGenerationResult",
    "JevBooleanResult",
    "JevChoiceResult",
    "JevDecisionPort",
    "JevScoreLevel",
    "JevScoreResult",
    "LLMProviderPort",
    "LlmTelemetrySinkPort",
    "LlmUsageRecord",
    "MeteredGeminiAdapter",
    "MeteredJevAdapter",
]
