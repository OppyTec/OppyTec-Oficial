"""
oppytec-backend/scripts/seed_ai_models.py
Script de sembrado idempotente para el catálogo maestro de modelos LLM y JEV
en `public.ai_model_configs`.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.core.database import get_database_engine, get_session_factory
from src.modules.oppy_ai.infrastructure.models import AiModelConfig

SEED_MODELS_DATA: list[dict[str, Any]] = [
    {
        "model_slug": "gemini-3.8-flash",
        "display_name": "Gemini 3.8 Flash",
        "provider": "google",
        "engine_tier": "SYSTEM_2_LLM",
        "input_cost_per_1m_usd": Decimal("0.150000"),
        "cached_cost_per_1m_usd": Decimal("0.037500"),
        "output_cost_per_1m_usd": Decimal("0.600000"),
        "embedding_cost_per_1m_usd": Decimal("0.000000"),
        "latency_p95_ms": 450,
        "min_confidence_score": None,
        "max_context_tokens": 1048576,
        "is_default": True,
        "is_fallback": False,
        "description": "Google Gemini 3.8 Flash - Modelo de alta velocidad y bajo costo para razonamiento operativo general.",
        "is_enabled": True,
        "is_deleted": False,
    },
    {
        "model_slug": "gemini-4-argon",
        "display_name": "Gemini 4 Argon",
        "provider": "google",
        "engine_tier": "SYSTEM_2_LLM",
        "input_cost_per_1m_usd": Decimal("1.250000"),
        "cached_cost_per_1m_usd": Decimal("0.312500"),
        "output_cost_per_1m_usd": Decimal("5.000000"),
        "embedding_cost_per_1m_usd": Decimal("0.000000"),
        "latency_p95_ms": 1200,
        "min_confidence_score": None,
        "max_context_tokens": 2097152,
        "is_default": False,
        "is_fallback": False,
        "description": "Google Gemini 4 Argon - Razonamiento avanzado para análisis financiero, escandallos y diagnósticos complejos.",
        "is_enabled": True,
        "is_deleted": False,
    },
    {
        "model_slug": "claude-3-7-sonnet",
        "display_name": "Claude 3.7 Sonnet",
        "provider": "anthropic",
        "engine_tier": "SYSTEM_2_LLM",
        "input_cost_per_1m_usd": Decimal("3.000000"),
        "cached_cost_per_1m_usd": Decimal("0.750000"),
        "output_cost_per_1m_usd": Decimal("15.000000"),
        "embedding_cost_per_1m_usd": Decimal("0.000000"),
        "latency_p95_ms": 1500,
        "min_confidence_score": None,
        "max_context_tokens": 200000,
        "is_default": False,
        "is_fallback": False,
        "description": "Anthropic Claude 3.7 Sonnet - Razonamiento híbrido estándar y de pensamiento extendido para auditorías y arquitectura.",
        "is_enabled": True,
        "is_deleted": False,
    },
    {
        "model_slug": "gpt-4o",
        "display_name": "GPT-4o",
        "provider": "openai",
        "engine_tier": "SYSTEM_2_LLM",
        "input_cost_per_1m_usd": Decimal("2.500000"),
        "cached_cost_per_1m_usd": Decimal("1.250000"),
        "output_cost_per_1m_usd": Decimal("10.000000"),
        "embedding_cost_per_1m_usd": Decimal("0.000000"),
        "latency_p95_ms": 800,
        "min_confidence_score": None,
        "max_context_tokens": 128000,
        "is_default": False,
        "is_fallback": True,
        "description": "OpenAI GPT-4o - Modelo multimodal de respaldo empresarial y alta fidelidad.",
        "is_enabled": True,
        "is_deleted": False,
    },
    {
        "model_slug": "jev-fast-classifier",
        "display_name": "JEV Fast Classifier",
        "provider": "oppytec",
        "engine_tier": "SYSTEM_1_JEV",
        "input_cost_per_1m_usd": Decimal("0.000000"),
        "cached_cost_per_1m_usd": Decimal("0.000000"),
        "output_cost_per_1m_usd": Decimal("0.000000"),
        "embedding_cost_per_1m_usd": Decimal("0.000000"),
        "latency_p95_ms": 50,
        "min_confidence_score": Decimal("0.8500"),
        "max_context_tokens": 8192,
        "is_default": False,
        "is_fallback": False,
        "description": "Motor local JEV System 1 determinista y sub-simbólico de ultra-baja latencia y cero costo de proveedor.",
        "is_enabled": True,
        "is_deleted": False,
    },
    {
        "model_slug": "text-embedding-004",
        "display_name": "Text Embedding 004",
        "provider": "google",
        "engine_tier": "EMBEDDING",
        "input_cost_per_1m_usd": Decimal("0.000000"),
        "cached_cost_per_1m_usd": Decimal("0.000000"),
        "output_cost_per_1m_usd": Decimal("0.000000"),
        "embedding_cost_per_1m_usd": Decimal("0.025000"),
        "latency_p95_ms": 100,
        "min_confidence_score": None,
        "max_context_tokens": 8192,
        "is_default": False,
        "is_fallback": False,
        "description": "Google Text Embedding 004 - Embeddings vectoriales de 768 dimensiones para RAG.",
        "is_enabled": True,
        "is_deleted": False,
    },
]


async def seed_ai_models() -> int:
    """Inserta o actualiza los modelos iniciales en `public.ai_model_configs`."""
    engine = get_database_engine()
    session_factory = get_session_factory(engine)
    seeded_count = 0

    async with session_factory() as session:
        for model_data in SEED_MODELS_DATA:
            stmt = select(AiModelConfig).where(AiModelConfig.model_slug == model_data["model_slug"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing is None:
                new_model = AiModelConfig(**model_data)
                session.add(new_model)
                seeded_count += 1
            else:
                for k, v in model_data.items():
                    setattr(existing, k, v)
                seeded_count += 1

        await session.commit()

    return seeded_count


if __name__ == "__main__":
    count = asyncio.run(seed_ai_models())
    print(f"Seeded/updated {count} AI models in public.ai_model_configs.")
