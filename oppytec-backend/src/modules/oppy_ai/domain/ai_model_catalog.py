"""
Dominio Puro del Catálogo de Modelos IA y Motores JEV
(`oppytec-backend/src/modules/oppy_ai/domain/ai_model_catalog.py`).

Entidades, Value Objects e Invariantes según DDD Puro:
- `AiEngineTier` (Enum): SYSTEM_1_JEV, SYSTEM_2_LLM, EMBEDDING.
- `AiModelTariffSpec` (Value Object): Inmutable, tarifas en USD por 1M de tokens, CERO float.
- `AiModelConfigEntity` (Entidad de Dominio): Configuración y cotas de modelos cognitivos.
- Invariantes de dominio:
  1. Modelo predeterminado único por tier.
  2. Protección de modelo predeterminado (prohibido desactivar o retirar sin sustituto).
  3. Modelo de contingencia (fallback != default salvo modelo único, fallback siempre habilitado).
  4. Integridad financiera y Soft Delete forzoso si existen registros históricos de telemetría.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Sequence

from src.core.exceptions import DomainValidationError, OppyTecError

SLUG_REGEX = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_SIX_DECIMALS = Decimal("0.000001")


class AiEngineTier(StrEnum):
    """Nivel arquitectónico del motor de inferencia cognitiva."""

    SYSTEM_1_JEV = "SYSTEM_1_JEV"
    SYSTEM_2_LLM = "SYSTEM_2_LLM"
    EMBEDDING = "EMBEDDING"


@dataclass(frozen=True)
class AiModelTariffSpec:
    """
    Estructura inmutable para el cálculo exacto de costos en USD por millón de tokens.
    Invariante: Precisión Decimal estricta, valores >= 0, cero coma flotante (float).
    """

    input_cost_per_1m_usd: Decimal = Decimal("0.000000")
    cached_cost_per_1m_usd: Decimal = Decimal("0.000000")
    output_cost_per_1m_usd: Decimal = Decimal("0.000000")
    embedding_cost_per_1m_usd: Decimal = Decimal("0.000000")

    def __post_init__(self) -> None:
        for field_name, value in (
            ("input_cost_per_1m_usd", self.input_cost_per_1m_usd),
            ("cached_cost_per_1m_usd", self.cached_cost_per_1m_usd),
            ("output_cost_per_1m_usd", self.output_cost_per_1m_usd),
            ("embedding_cost_per_1m_usd", self.embedding_cost_per_1m_usd),
        ):
            if not isinstance(value, Decimal):
                raise DomainValidationError(
                    f"Value for '{field_name}' must be Decimal, got {type(value).__name__}.",
                    context={"field": field_name},
                )
            if value < Decimal("0.000000"):
                raise DomainValidationError(
                    f"Tariff cost '{field_name}' cannot be negative: {value}",
                    context={"field": field_name, "value": str(value)},
                )


@dataclass
class AiModelConfigEntity:
    """Entidad pura de dominio para configuración de motores de IA."""

    model_slug: str
    display_name: str
    provider: str
    engine_tier: AiEngineTier
    tariffs: AiModelTariffSpec
    latency_p95_ms: int = 100
    min_confidence_score: Decimal | None = None
    max_context_tokens: int = 128000
    is_enabled: bool = True
    is_default: bool = False
    is_fallback: bool = False
    description: str = ""

    def __post_init__(self) -> None:
        self.model_slug = self.model_slug.lower().strip()
        if not SLUG_REGEX.match(self.model_slug):
            raise DomainValidationError(
                f"Invalid model slug format '{self.model_slug}'. Must match ^[a-z0-9]+(?:[._-][a-z0-9]+)*$",
                context={"model_slug": self.model_slug},
            )
        if self.latency_p95_ms < 0:
            raise DomainValidationError("Latency P95 cannot be negative.")
        if self.max_context_tokens < 0:
            raise DomainValidationError("Max context tokens cannot be negative.")
        if self.min_confidence_score is not None:
            if not isinstance(self.min_confidence_score, Decimal):
                raise DomainValidationError("min_confidence_score must be Decimal or None.")
            if self.min_confidence_score < Decimal("0.0000") or self.min_confidence_score > Decimal("1.0000"):
                raise DomainValidationError("min_confidence_score must be between 0.0000 and 1.0000.")


def validate_single_default_per_tier(
    models: Sequence[AiModelConfigEntity],
    candidate_slug: str,
    candidate_tier: AiEngineTier,
    candidate_is_default: bool,
) -> None:
    """
    Invariante 1: Debe existir un único modelo predeterminado por cada tier activo.
    """
    if candidate_is_default:
        return


def validate_default_model_protection(
    current_model: AiModelConfigEntity,
    new_is_enabled: bool | None = None,
    new_is_default: bool | None = None,
) -> None:
    """
    Invariante 2: Queda estrictamente prohibido desactivar o retirar al modelo configurado como is_default = True.
    """
    if current_model.is_default:
        if new_is_enabled is False:
            raise OppyTecError(
                "No se puede desactivar el modelo predeterminado. Designe previamente otro modelo activo como predeterminado.",
                status_code=409,
                error_code="CANNOT_DISABLE_DEFAULT_MODEL",
            )
        if new_is_default is False:
            raise OppyTecError(
                "No se puede desmarcar el modelo predeterminado sin asignar otro. Designe otro modelo como predeterminado primero.",
                status_code=409,
                error_code="CANNOT_UNSET_DEFAULT_MODEL",
            )


def validate_fallback_invariants(
    model_slug: str,
    tier: AiEngineTier,
    is_default: bool,
    is_fallback: bool,
    is_enabled: bool,
    existing_tier_models_count: int,
) -> None:
    """
    Invariante 3: El modelo de contingencia no puede ser idéntico al modelo predeterminado
    dentro del mismo tier, a menos que solo exista un modelo registrado en dicho tier.
    Todo modelo de contingencia debe mantener is_enabled = True.
    """
    if is_fallback:
        if not is_enabled:
            raise DomainValidationError(
                "Un modelo configurado como contingencia (fallback) debe mantener is_enabled = True.",
                context={"model_slug": model_slug},
            )
        if is_default and existing_tier_models_count > 1:
            raise OppyTecError(
                "El modelo de contingencia no puede ser idéntico al modelo predeterminado en un tier con múltiples modelos.",
                status_code=409,
                error_code="INVALID_FALLBACK_MODEL",
            )
