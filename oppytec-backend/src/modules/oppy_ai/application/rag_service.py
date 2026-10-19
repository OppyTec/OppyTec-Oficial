"""
Orquestador RAG de 3 Capas de `OppyFy` (`src/modules/oppy_ai/application/rag_service.py`).
Implementa las 3 capas complementarias de recuperación sin fuga de arquitectura interna:
1. Capa 1: Herramientas en código duro del Tenant (datos vivos SQL filtrados por RBAC y redactados en costos).
2. Capa 2: Documentos privados del local (`tenant_documents` / `document_chunks` filtrados por
   `oppyfy_subdomain_id`) + memorias evolutivas (`tenant_ai_memories` con `agent_affinity`).
3. Capa 3A: Manuales funcionales de `specs/business-domain` (`spec_chunks`), garantizando 0% fuga de código interno.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from src.modules.oppy_ai.application.tool_router import RoutedToolExecutionResult
from src.modules.oppy_ai.domain.oppyfy_rbac import PayloadValue

ALLOWED_PUBLIC_SPEC_VAULT_PREFIX: str = "specs/business-domain"


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

    layer1_live_tool_data: dict[str, PayloadValue]
    layer2_tenant_doc_chunks: tuple[str, ...]
    layer2_tenant_memories: tuple[str, ...]
    layer3a_business_spec_chunks: tuple[str, ...]
    is_cacheable: bool

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
    - Filtra estrictamente `document_chunks` por `oppyfy_subdomain_id` autorizado.
    - Filtra `spec_chunks` garantizando que provengan únicamente de `specs/business-domain`.
    - Prohíbe cachear consultas que incluyan datos vivos de Capa 1 (`is_cacheable=False`).
    """

    def __init__(
        self,
        *,
        tenant_doc_chunks: Sequence[TenantDocumentChunkRecord] = (),
        tenant_memories: Sequence[TenantMemoryRecord] = (),
        business_spec_chunks: Sequence[BusinessSpecChunkRecord] = (),
    ) -> None:
        self._tenant_doc_chunks = list(tenant_doc_chunks)
        self._tenant_memories = list(tenant_memories)
        self._business_spec_chunks: list[BusinessSpecChunkRecord] = []
        for spec_chunk in business_spec_chunks:
            self.register_business_spec_chunk(spec_chunk)

    def register_business_spec_chunk(self, chunk: BusinessSpecChunkRecord) -> None:
        """
        Registra un chunk en la Capa 3A validando que pertenezca exclusivamente a
        `specs/business-domain` (0% fuga de código o arquitectura interna).
        """
        normalized_path = chunk.spec_rel_path.strip().lstrip("/")
        if not normalized_path.startswith(ALLOWED_PUBLIC_SPEC_VAULT_PREFIX):
            raise ValueError(
                f"RAG Isolation Error: '{chunk.spec_rel_path}' is outside '{ALLOWED_PUBLIC_SPEC_VAULT_PREFIX}'."
            )
        self._business_spec_chunks.append(chunk)

    def build_three_layer_context(
        self,
        *,
        user_prompt: str,
        authorized_subdomain_id: int,
        user_id: int,
        routed_tool_result: RoutedToolExecutionResult | None,
        agent_affinity: str = "general",
    ) -> RagThreeLayerBundle:
        """
        Construye el contexto unificado de las 3 Capas:
        - Capa 1: Datos vivos de la herramienta en código duro (ya redactados según `can_view_costs`).
        - Capa 2: `document_chunks` cuyo `oppyfy_subdomain_id == authorized_subdomain_id` +
          `tenant_ai_memories` del local/usuario.
        - Capa 3A: Manuales funcionales de `specs/business-domain`.
        """
        prompt_terms = {tok.lower() for tok in user_prompt.split() if len(tok) > 2}

        layer1_data: dict[str, PayloadValue] = (
            dict(routed_tool_result.sanitized_payload) if routed_tool_result is not None else {}
        )

        # Capa 2: Documentos privados del local filtrados estrictamente por oppyfy_subdomain_id
        matching_docs = [
            chunk.chunk_text
            for chunk in self._tenant_doc_chunks
            if chunk.oppyfy_subdomain_id == authorized_subdomain_id
        ]

        # Capa 2: Memorias evolutivas del local (globales del local o específicas del trabajador)
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

        # Regla estricta: si hay datos vivos de Capa 1, prohibido cachear
        is_cacheable = len(layer1_data) == 0

        return RagThreeLayerBundle(
            layer1_live_tool_data=layer1_data,
            layer2_tenant_doc_chunks=tuple(matching_docs),
            layer2_tenant_memories=tuple(matching_memories),
            layer3a_business_spec_chunks=tuple(matching_specs),
            is_cacheable=is_cacheable,
        )
