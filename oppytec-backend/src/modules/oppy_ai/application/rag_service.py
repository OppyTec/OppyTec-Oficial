"""
Orquestador RAG de 3 Capas de `OppyFy` (`src/modules/oppy_ai/application/rag_service.py`).
Implementa las 3 capas complementarias de recuperación sin fuga de arquitectura interna:
1. Capa 1: Memoria conversacional con ventana móvil y medidor de salud de contexto.
2. Capa 2: Ejecución determinista viva de herramientas (datos vivos SQL filtrados por RBAC y redactados en costos).
   Regla Inmutable: Prohibido estrictamente cachear la Capa 2 (is_cacheable = False).
3. Capa 3: Búsqueda vectorial en `public.spec_chunks` (pgvector HNSW) solo sobre `specs/business-domain/` (0% código interno),
   documentos privados del local (`tenant_documents` / `document_chunks`) y memorias evolutivas (`tenant_ai_memories`).
4. Caché semántica bi-nivel: L1 Redis (TTL 48h = 172.800s) + L2 pgvector para preguntas conceptuales.
"""
from __future__ import annotations

import os
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from src.modules.oppy_ai.application.tool_router import RoutedToolExecutionResult
from src.modules.oppy_ai.domain.context_meter import (
    ContextHealthEvaluation,
    evaluate_context_usage,
)
from src.modules.oppy_ai.domain.oppyfy_rbac import PayloadValue

ALLOWED_PUBLIC_SPEC_VAULT_PREFIX: str = "specs/business-domain"
REDIS_L1_CACHE_TTL_SECONDS: int = 172800  # 48 Horas


@runtime_checkable
class SemanticCachePort(Protocol):
    """Puerto de interfaz para la caché semántica L1/L2."""

    def get(self, query_text: str) -> str | None:
        """Obtiene la respuesta conceptual en caché si no ha expirado."""

    def set(self, query_text: str, response: str, ttl_seconds: int = REDIS_L1_CACHE_TTL_SECONDS) -> None:
        """Almacena la respuesta conceptual con TTL de 48h."""


class InMemoryRedisSemanticCache:
    """Implementación de referencia en memoria para la caché L1 Redis con TTL de 48 horas."""

    def __init__(self, default_ttl_seconds: int = REDIS_L1_CACHE_TTL_SECONDS) -> None:
        self._default_ttl = default_ttl_seconds
        self._store: dict[str, tuple[str, float]] = {}

    def get(self, query_text: str) -> str | None:
        key = query_text.strip().lower()
        if key in self._store:
            response, expiry = self._store[key]
            if time.time() < expiry:
                return response
            del self._store[key]
        return None

    def set(self, query_text: str, response: str, ttl_seconds: int | None = None) -> None:
        key = query_text.strip().lower()
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        self._store[key] = (response, time.time() + ttl)

    def invalidate(self, query_text: str) -> None:
        key = query_text.strip().lower()
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


@dataclass(frozen=True)
class TenantDocumentChunkRecord:
    """Fragmento de un documento privado del local (`document_chunks`) vinculado a `oppyfy_subdomain_id`."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    oppyfy_subdomain_id: int
    chunk_text: str


@dataclass(frozen=True)
class TenantMemoryRecord:
    """Memoria episódica/semántica del local (`tenant_ai_memories` - patrón Mem0)."""

    memory_id: uuid.UUID
    user_id: int | None
    agent_affinity: str
    memory_fact: str


@dataclass(frozen=True)
class BusinessSpecChunkRecord:
    """
    Fragmento de manual funcional (`public.spec_chunks`).
    Solo admite rutas dentro de `specs/business-domain/`.
    """

    chunk_id: uuid.UUID
    spec_rel_path: str
    module_slug: str
    content_markdown: str


@dataclass(frozen=True)
class RagThreeLayerBundle:
    """Paquete consolidado de las 3 capas del RAG de `OppyFy` listo para el micro-prompt `Pi`."""

    layer1_live_tool_data: dict[str, Any]
    layer2_tenant_doc_chunks: tuple[str, ...]
    layer2_tenant_memories: tuple[str, ...]
    layer3a_business_spec_chunks: tuple[str, ...]
    is_cacheable: bool
    context_health: ContextHealthEvaluation = field(
        default_factory=lambda: evaluate_context_usage(0)
    )

    def to_compact_context_dict(
        self,
    ) -> dict[str, str | int | Decimal | bool | list[str]]:
        """Empaqueta las 3 capas en un diccionario minimalista estilo `Pi`."""
        compact: dict[str, str | int | Decimal | bool | list[str]] = {}
        for k, v in self.layer1_live_tool_data.items():
            if isinstance(v, (str, int, Decimal, bool)):
                compact[f"L1_{k}"] = v
            else:
                compact[f"L1_{k}"] = str(v)
        compact["L2_docs"] = list(self.layer2_tenant_doc_chunks)
        compact["L2_memories"] = list(self.layer2_tenant_memories)
        compact["L3A_business_specs"] = list(self.layer3a_business_spec_chunks)
        return compact


class ThreeLayerRagService:
    """
    Orquestador RAG de 3 Capas de `OppyFy`:
    - Capa 1: Ventana móvil y medidor de salud de contexto.
    - Capa 2: Ejecución determinista viva de herramientas (estrictamente excluida de la caché).
    - Capa 3: Búsqueda vectorial en `public.spec_chunks` (solo `specs/business-domain`),
      `document_chunks` y memorias del local.
    - Caché semántica L1 Redis (TTL 48h) para consultas conceptuales.
    """

    def __init__(
        self,
        *,
        tenant_doc_chunks: Sequence[TenantDocumentChunkRecord] = (),
        tenant_memories: Sequence[TenantMemoryRecord] = (),
        business_spec_chunks: Sequence[BusinessSpecChunkRecord] = (),
        semantic_cache: SemanticCachePort | None = None,
    ) -> None:
        self._tenant_doc_chunks = list(tenant_doc_chunks)
        self._tenant_memories = list(tenant_memories)
        self._business_spec_chunks: list[BusinessSpecChunkRecord] = []
        self._cache = semantic_cache or InMemoryRedisSemanticCache()
        for spec_chunk in business_spec_chunks:
            self.register_business_spec_chunk(spec_chunk)

    @property
    def semantic_cache(self) -> SemanticCachePort:
        """Acceso al puerto de caché semántica L1."""
        return self._cache

    def register_business_spec_chunk(self, chunk: BusinessSpecChunkRecord) -> None:
        """
        Registra un chunk en la Capa 3A validando que pertenezca exclusivamente a
        `specs/business-domain` (0% fuga de código o arquitectura interna).
        """
        raw_path = chunk.spec_rel_path.strip().lstrip("/")
        normalized_path = os.path.normpath(raw_path)
        if (
            not normalized_path.startswith(ALLOWED_PUBLIC_SPEC_VAULT_PREFIX)
            or "engineering-code" in normalized_path
            or normalized_path.startswith("src")
            or "/src" in normalized_path
            or normalized_path.startswith("..")
        ):
            raise ValueError(
                f"RAG Isolation Error: '{chunk.spec_rel_path}' is outside '{ALLOWED_PUBLIC_SPEC_VAULT_PREFIX}'."
            )
        self._business_spec_chunks.append(chunk)

    def check_conceptual_cache(self, user_prompt: str) -> str | None:
        """Verifica la caché semántica L1 Redis para preguntas conceptuales (TTL 48h)."""
        return self._cache.get(user_prompt)

    def store_conceptual_cache(
        self,
        user_prompt: str,
        answer: str,
        *,
        is_cacheable: bool,
    ) -> bool:
        """
        Almacena la respuesta en la caché semántica solo si es conceptual y no contiene datos vivos de Capa 2.
        """
        if not is_cacheable:
            return False
        self._cache.set(user_prompt, answer, ttl_seconds=REDIS_L1_CACHE_TTL_SECONDS)
        return True

    def build_three_layer_context(
        self,
        *,
        user_prompt: str,
        authorized_subdomain_id: int,
        user_id: int,
        routed_tool_result: RoutedToolExecutionResult | None,
        agent_affinity: str = "general",
        prior_thread_tokens: int = 0,
    ) -> RagThreeLayerBundle:
        """
        Construye el contexto unificado de las 3 Capas:
        - Capa 1: Evaluación de salud y presupuesto de ventana móvil.
        - Capa 2: Datos vivos de la herramienta en código duro (ya redactados según `can_view_costs`).
        - Capa 3A: Manuales funcionales de `specs/business-domain`.
        - Capa 3B/C: `document_chunks` del sub-dominio y `tenant_ai_memories`.
        """
        prompt_terms = {tok.lower() for tok in user_prompt.split() if len(tok) > 2}

        # Capa 1: Context health
        context_health = evaluate_context_usage(prior_thread_tokens)

        # Capa 2: Live tool data
        layer1_data: dict[str, Any] = (
            dict(routed_tool_result.sanitized_payload) if routed_tool_result is not None else {}
        )

        # Capa 3B: Documentos privados del local filtrados estrictamente por oppyfy_subdomain_id
        matching_docs = [
            chunk.chunk_text
            for chunk in self._tenant_doc_chunks
            if chunk.oppyfy_subdomain_id == authorized_subdomain_id
        ]

        # Capa 3C: Memorias evolutivas del local
        matching_memories = [
            mem.memory_fact
            for mem in self._tenant_memories
            if (mem.user_id is None or mem.user_id == user_id)
            and mem.agent_affinity in ("general", agent_affinity)
        ]

        # Capa 3A: Manuales funcionales de specs/business-domain
        matching_specs: list[str] = []
        for spec in self._business_spec_chunks:
            text_lower = spec.content_markdown.lower()
            if not prompt_terms or any(term in text_lower for term in prompt_terms):
                matching_specs.append(spec.content_markdown)
        if not matching_specs and self._business_spec_chunks:
            matching_specs.append(self._business_spec_chunks[0].content_markdown)

        # Invariante: si hay datos vivos de Capa 2 (operational tool), estrictamente prohibido cachear
        is_cacheable = len(layer1_data) == 0

        return RagThreeLayerBundle(
            layer1_live_tool_data=layer1_data,
            layer2_tenant_doc_chunks=tuple(matching_docs),
            layer2_tenant_memories=tuple(matching_memories),
            layer3a_business_spec_chunks=tuple(matching_specs),
            is_cacheable=is_cacheable,
            context_health=context_health,
        )
