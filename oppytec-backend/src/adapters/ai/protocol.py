"""
Interfaces y registros de telemetría para proveedores cognitivos (`src/adapters/ai/protocol.py`).
Garantiza el registro obligatorio de cada invocación (`SYSTEM_1_JEV`, `SYSTEM_2_LLM`, `EMBEDDING`)
con precisión financiera `decimal.Decimal` (cero `float`) en `public.llm_request_logs`.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol, runtime_checkable

EngineTierLiteral = Literal["SYSTEM_1_JEV", "SYSTEM_2_LLM", "EMBEDDING"]


@dataclass(frozen=True)
class LlmUsageRecord:
    """
    Registro inmutable de consumo de IA listo para persistirse en `public.llm_request_logs`.
    """

    holding_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_schema: str
    user_id: int
    engine_tier: EngineTierLiteral
    caller_feature: str
    model_name: str
    input_tokens: int
    cached_tokens: int
    output_tokens: int
    provider_cost_usd: Decimal
    provider_cost_clp: Decimal
    credits_deducted: Decimal
    request_duration_ms: int
    thread_id: uuid.UUID | None = None
    api_success: bool = True
    error_message: str | None = None

    @property
    def total_tokens(self) -> int:
        """Suma exacta de tokens de entrada y salida."""
        return self.input_tokens + self.output_tokens


@runtime_checkable
class LlmTelemetrySinkPort(Protocol):
    """Puerto colector que persiste o acumula registros de `public.llm_request_logs`."""

    def record_llm_usage(self, record: LlmUsageRecord) -> None:
        """Registra una invocación cognitiva en `llm_request_logs`."""


@runtime_checkable
class LLMProviderPort(Protocol):
    """Puerto para generación de texto y artefactos estructurados (Sistema 2) con estilo minimalista `Pi`."""

    def generate_minimalist_response(
        self,
        *,
        holding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tenant_schema: str,
        user_id: int,
        caller_feature: str,
        user_prompt: str,
        compact_context_payload: dict[str, str | int | Decimal | bool | list[str]],
        language_code: str = "es",
        brand_name: str = "OppyFy",
        thread_id: uuid.UUID | None = None,
    ) -> tuple[str, LlmUsageRecord]:
        """Genera una respuesta concisa y devuelve `(texto_respuesta, registro_telemetria)`."""


@runtime_checkable
class EmbeddingPort(Protocol):
    """Puerto para vectorización semántica (`768` dimensiones en `Decimal`) medida en `llm_request_logs`."""

    def embed_text(
        self,
        *,
        holding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tenant_schema: str,
        user_id: int,
        caller_feature: str,
        text: str,
    ) -> tuple[list[Decimal], LlmUsageRecord]:
        """Genera el vector de embeddings en `Decimal` y su registro en `llm_request_logs`."""
