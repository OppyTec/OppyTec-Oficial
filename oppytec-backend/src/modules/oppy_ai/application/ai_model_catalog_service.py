"""
oppytec-backend/src/modules/oppy_ai/application/ai_model_catalog_service.py
Servicio de Aplicación para el Catálogo y CRUD de Modelos LLM y Motores JEV (`public.ai_model_configs`).
Cumple Clean Architecture, Invariantes DDD de AiModelCatalog y hot-reload en `ModelConfigRegistry`.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from src.core.exceptions import DomainValidationError, OppyTecError, ResourceNotFoundError
from src.modules.oppy_ai.application.metered_ai_service import ModelConfigRegistry, ModelTariff
from src.modules.oppy_ai.domain.ai_model_catalog import (
    AiEngineTier,
    validate_default_model_protection,
    validate_fallback_invariants,
)
from src.modules.oppy_ai.infrastructure.models import AiModelConfig

if TYPE_CHECKING:
    from src.modules.oppy_ai.presentation.schemas import (
        AiModelConfigCreateRequest,
        AiModelConfigUpdateRequest,
    )

logger = logging.getLogger("oppytec.ai.catalog_service")


def _build_default_catalog() -> list[AiModelConfig]:
    """Carga los modelos canónicos iniciales del catálogo con exactamente un default por tier."""
    now = datetime.now(UTC)
    return [
        AiModelConfig(
            id=1,
            model_slug="gemini-3.8-flash",
            display_name="Gemini 3.8 Flash",
            provider="Google DeepMind",
            engine_tier=AiEngineTier.SYSTEM_2_LLM.value,
            input_cost_per_1m_usd=Decimal("0.075000"),
            cached_cost_per_1m_usd=Decimal("0.018750"),
            output_cost_per_1m_usd=Decimal("0.300000"),
            embedding_cost_per_1m_usd=Decimal("0.000000"),
            latency_p95_ms=750,
            min_confidence_score=None,
            max_context_tokens=1000000,
            is_enabled=True,
            is_default=True,
            is_fallback=False,
            description="Modelo insignia ultrarrápido y balanceado para el asistente operativo OppyFy.",
            is_deleted=False,
            created_at=now,
            updated_at=now,
        ),
        AiModelConfig(
            id=2,
            model_slug="claude-3-7-sonnet",
            display_name="Claude 3.7 Sonnet",
            provider="Anthropic",
            engine_tier=AiEngineTier.SYSTEM_2_LLM.value,
            input_cost_per_1m_usd=Decimal("3.000000"),
            cached_cost_per_1m_usd=Decimal("0.300000"),
            output_cost_per_1m_usd=Decimal("15.000000"),
            embedding_cost_per_1m_usd=Decimal("0.000000"),
            latency_p95_ms=1200,
            min_confidence_score=None,
            max_context_tokens=200000,
            is_enabled=True,
            is_default=False,
            is_fallback=True,
            description="Modelo de razonamiento analítico de alta precisión para escandallos y proyección.",
            is_deleted=False,
            created_at=now,
            updated_at=now,
        ),
        AiModelConfig(
            id=3,
            model_slug="jev-fast-classifier",
            display_name="Clasificador Rápido JEV",
            provider="JEV Internal",
            engine_tier=AiEngineTier.SYSTEM_1_JEV.value,
            input_cost_per_1m_usd=Decimal("0.000000"),
            cached_cost_per_1m_usd=Decimal("0.000000"),
            output_cost_per_1m_usd=Decimal("0.000000"),
            embedding_cost_per_1m_usd=Decimal("0.000000"),
            latency_p95_ms=45,
            min_confidence_score=Decimal("0.8500"),
            max_context_tokens=8192,
            is_enabled=True,
            is_default=True,
            is_fallback=False,
            description="Motor de decisión binaria e intenciones operativas de Sistema 1 con micro-latencia.",
            is_deleted=False,
            created_at=now,
            updated_at=now,
        ),
        AiModelConfig(
            id=4,
            model_slug="text-embedding-004",
            display_name="Text Embedding 004",
            provider="Google DeepMind",
            engine_tier=AiEngineTier.EMBEDDING.value,
            input_cost_per_1m_usd=Decimal("0.000000"),
            cached_cost_per_1m_usd=Decimal("0.000000"),
            output_cost_per_1m_usd=Decimal("0.000000"),
            embedding_cost_per_1m_usd=Decimal("0.025000"),
            latency_p95_ms=150,
            min_confidence_score=None,
            max_context_tokens=8192,
            is_enabled=True,
            is_default=True,
            is_fallback=False,
            description="Modelo de vectorización semántica de texto para memoria y RAG.",
            is_deleted=False,
            created_at=now,
            updated_at=now,
        ),
    ]


class AiModelCatalogService:
    """
    Servicio de gestión integral del Catálogo de Modelos IA y Motores JEV.
    Garantiza consistencia transaccional de modelos predeterminados, cero float
    y sincronización inmediata en caliente con `ModelConfigRegistry`.
    """

    def __init__(
        self,
        *,
        model_registry: ModelConfigRegistry | None = None,
        initial_models: list[AiModelConfig] | None = None,
    ) -> None:
        self._model_registry = model_registry
        self._models: dict[str, AiModelConfig] = {}
        self._telemetry_counts: dict[str, int] = {}
        self._next_id: int = 1

        models_to_load = initial_models if initial_models is not None else _build_default_catalog()
        for m in models_to_load:
            normalized = m.model_slug.lower().strip()
            self._models[normalized] = m
            if m.id >= self._next_id:
                self._next_id = m.id + 1
            self._sync_registry(m)

    def _sync_registry(self, model: AiModelConfig) -> None:
        """Sincroniza en caliente el modelo con `ModelConfigRegistry`."""
        if self._model_registry is not None:
            self._model_registry.set_tariff(
                ModelTariff(
                    model_slug=model.model_slug,
                    engine_tier=model.engine_tier,
                    input_cost_per_1m_usd=model.input_cost_per_1m_usd,
                    cached_cost_per_1m_usd=model.cached_cost_per_1m_usd,
                    output_cost_per_1m_usd=model.output_cost_per_1m_usd,
                    embedding_cost_per_1m_usd=model.embedding_cost_per_1m_usd,
                    is_enabled=model.is_enabled and not model.is_deleted,
                )
            )

    def count_telemetry_references(self, model_slug: str) -> int:
        """Devuelve el total de bitácoras históricas asociadas a `model_slug`."""
        normalized = model_slug.lower().strip()
        return self._telemetry_counts.get(normalized, 0)

    def set_telemetry_count(self, model_slug: str, count: int) -> None:
        """Registra o simula la existencia de registros de telemetría histórica."""
        normalized = model_slug.lower().strip()
        self._telemetry_counts[normalized] = max(0, count)

    def reset(self) -> None:
        """Restablece el catálogo a sus modelos canónicos predeterminados."""
        self._models.clear()
        self._telemetry_counts.clear()
        self._next_id = 1
        for m in _build_default_catalog():
            normalized = m.model_slug.lower().strip()
            self._models[normalized] = m
            if m.id >= self._next_id:
                self._next_id = m.id + 1
            self._sync_registry(m)

    def list_models(
        self,
        *,
        include_deleted: bool = False,
        tier: str | None = None,
        is_enabled: bool | None = None,
        provider: str | None = None,
    ) -> Sequence[AiModelConfig]:
        """Lista los modelos del catálogo aplicando filtros opcionales de estado y tier."""
        results: list[AiModelConfig] = []
        for model in self._models.values():
            if not include_deleted and model.is_deleted:
                continue
            if tier is not None and model.engine_tier.upper() != tier.upper():
                continue
            if is_enabled is not None and model.is_enabled != is_enabled:
                continue
            if provider is not None and model.provider.lower() != provider.lower():
                continue
            results.append(model)
        return sorted(results, key=lambda m: (m.engine_tier, not m.is_default, m.model_slug))

    def get_model_by_slug(self, model_slug: str) -> AiModelConfig:
        """Obtiene un modelo por su slug o arroja HTTP 404 RFC 7807."""
        normalized = model_slug.lower().strip()
        model = self._models.get(normalized)
        if model is None or model.is_deleted:
            raise ResourceNotFoundError(
                f"AI Model with slug '{model_slug}' was not found in catalog.",
                error_code="MODEL_NOT_FOUND",
                context={"model_slug": model_slug},
            )
        return model

    def create_model(
        self,
        data: AiModelConfigCreateRequest | Mapping[str, Any],
    ) -> AiModelConfig:
        """
        Crea un nuevo modelo cognitivo en el catálogo validando slug único e invariantes.
        Si se designa como predeterminado, conmuta atómicamente el predeterminado anterior del mismo tier.
        """
        if hasattr(data, "model_dump"):
            raw = data.model_dump()
        elif isinstance(data, Mapping):
            raw = dict(data)
        else:
            raw = getattr(data, "__dict__", {})

        slug = str(raw["model_slug"]).lower().strip()
        display_name = str(raw["display_name"])
        provider = str(raw["provider"])
        engine_tier = str(raw.get("engine_tier", "SYSTEM_2_LLM"))
        input_cost = Decimal(str(raw.get("input_cost_per_1m_usd", "0.000000")))
        cached_cost = Decimal(str(raw.get("cached_cost_per_1m_usd", "0.000000")))
        output_cost = Decimal(str(raw.get("output_cost_per_1m_usd", "0.000000")))
        embedding_cost = Decimal(str(raw.get("embedding_cost_per_1m_usd", "0.000000")))
        latency = int(raw.get("latency_p95_ms", 100))
        raw_min_conf = raw.get("min_confidence_score")
        min_conf = Decimal(str(raw_min_conf)) if raw_min_conf is not None else None
        max_tokens = int(raw.get("max_context_tokens", 128000))
        is_enabled = bool(raw.get("is_enabled", True))
        is_default = bool(raw.get("is_default", False))
        is_fallback = bool(raw.get("is_fallback", False))
        description = str(raw.get("description", ""))

        if slug in self._models and not self._models[slug].is_deleted:
            raise OppyTecError(
                f"AI Model with slug '{slug}' already exists in catalog.",
                status_code=409,
                error_code="MODEL_ALREADY_EXISTS",
                context={"model_slug": slug},
            )

        tier_models = [m for m in self._models.values() if m.engine_tier == engine_tier and not m.is_deleted]
        validate_fallback_invariants(
            model_slug=slug,
            tier=AiEngineTier(engine_tier),
            is_default=is_default,
            is_fallback=is_fallback,
            is_enabled=is_enabled,
            existing_tier_models_count=len(tier_models) + 1,
        )

        now = datetime.now(UTC)
        new_model = AiModelConfig(
            id=self._next_id,
            model_slug=slug,
            display_name=display_name,
            provider=provider,
            engine_tier=engine_tier,
            input_cost_per_1m_usd=input_cost,
            cached_cost_per_1m_usd=cached_cost,
            output_cost_per_1m_usd=output_cost,
            embedding_cost_per_1m_usd=embedding_cost,
            latency_p95_ms=latency,
            min_confidence_score=min_conf,
            max_context_tokens=max_tokens,
            is_enabled=is_enabled,
            is_default=is_default,
            is_fallback=is_fallback,
            description=description,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        self._next_id += 1

        # Invariante 1: Conmutar atómicamente el modelo predeterminado si aplica
        if is_default:
            for existing in tier_models:
                if existing.is_default:
                    existing.is_default = False
                    existing.updated_at = now
                    self._sync_registry(existing)

        self._models[slug] = new_model
        self._sync_registry(new_model)
        logger.info("AI Model '%s' created in catalog (tier=%s, default=%s)", slug, engine_tier, is_default)
        return new_model

    def update_model(
        self,
        model_slug: str,
        data: AiModelConfigUpdateRequest | Mapping[str, Any],
    ) -> AiModelConfig:
        """
        Actualiza los parámetros y cotas operativas de un modelo.
        Protege invariantes de modelo predeterminado y actualiza en caliente el registry.
        """
        model = self.get_model_by_slug(model_slug)
        now = datetime.now(UTC)

        if hasattr(data, "model_dump"):
            payload = data.model_dump(exclude_unset=True)
        elif isinstance(data, Mapping):
            payload = dict(data)
        else:
            payload = getattr(data, "__dict__", {})

        # Invariante 2: Protección del modelo predeterminado
        new_is_enabled = payload.get("is_enabled")
        new_is_default = payload.get("is_default")
        if model.is_default:
            if new_is_enabled is False:
                raise OppyTecError(
                    "No se puede desactivar el modelo predeterminado. Designe previamente otro modelo activo como predeterminado.",
                    status_code=409,
                    error_code="CANNOT_DISABLE_DEFAULT_MODEL",
                    context={"model_slug": model_slug},
                )
            if new_is_default is False:
                raise OppyTecError(
                    "No se puede desmarcar el modelo predeterminado directamente. Designe otro modelo como predeterminado.",
                    status_code=409,
                    error_code="CANNOT_UNSET_DEFAULT_MODEL",
                    context={"model_slug": model_slug},
                )

        target_tier = payload.get("engine_tier", model.engine_tier)
        tier_models = [m for m in self._models.values() if m.engine_tier == target_tier and not m.is_deleted]

        candidate_is_default = new_is_default if new_is_default is not None else model.is_default
        candidate_is_fallback = payload.get("is_fallback", model.is_fallback)
        candidate_is_enabled = new_is_enabled if new_is_enabled is not None else model.is_enabled

        validate_fallback_invariants(
            model_slug=model_slug,
            tier=AiEngineTier(target_tier),
            is_default=candidate_is_default,
            is_fallback=candidate_is_fallback,
            is_enabled=candidate_is_enabled,
            existing_tier_models_count=len(tier_models),
        )

        # Si se conmuta a default, desmarcar el default previo en el tier
        if candidate_is_default and not model.is_default:
            for other in tier_models:
                if other.model_slug != model.model_slug and other.is_default:
                    other.is_default = False
                    other.updated_at = now
                    self._sync_registry(other)

        for field_name, value in payload.items():
            if hasattr(model, field_name) and value is not None:
                setattr(model, field_name, value)

        model.updated_at = now
        self._sync_registry(model)
        logger.info("AI Model '%s' updated in catalog", model_slug)
        return model

    def delete_model(self, model_slug: str, *, hard_delete: bool = False) -> bool:
        """
        Elimina o retira lógicamente un modelo.
        - Si model.is_default == True: Rechaza con HTTP 409 Conflict.
        - Si cuenta con telemetría histórica asociada: Aplica Soft-Delete forzoso (is_deleted=True, is_enabled=False).
          Rechaza hard_delete si está referenciado.
        - Si telemetry_references == 0 y se solicita hard_delete: Ejecuta Hard Delete físico.
        """
        model = self.get_model_by_slug(model_slug)

        if model.is_default:
            raise OppyTecError(
                "No se puede eliminar ni desactivar el modelo predeterminado. Designe otro modelo antes de proceder.",
                status_code=409,
                error_code="CANNOT_DELETE_DEFAULT_MODEL",
                context={"model_slug": model_slug},
            )

        telemetry_refs = self.count_telemetry_references(model_slug)
        if telemetry_refs > 0:
            if hard_delete:
                raise OppyTecError(
                    "El modelo posee telemetría financiera histórica asociada. Queda terminantemente prohibida su eliminación física.",
                    status_code=409,
                    error_code="CANNOT_HARD_DELETE_REFERENCED_MODEL",
                    context={"model_slug": model_slug, "telemetry_references": telemetry_refs},
                )
            model.is_deleted = True
            model.is_enabled = False
            model.updated_at = datetime.now(UTC)
            self._sync_registry(model)
            logger.info("AI Model '%s' soft-deleted (preserved %d telemetry records)", model_slug, telemetry_refs)
            return True

        # telemetry_refs == 0
        if hard_delete:
            del self._models[model.model_slug.lower().strip()]
            if self._model_registry is not None:
                self._model_registry.remove_tariff(model_slug)
            logger.info("AI Model '%s' hard-deleted physically (0 telemetry references)", model_slug)
            return True

        # Soft delete estándar sin referencias
        model.is_deleted = True
        model.is_enabled = False
        model.updated_at = datetime.now(UTC)
        self._sync_registry(model)
        logger.info("AI Model '%s' soft-deleted without references", model_slug)
        return True
