"""
oppytec-backend/src/modules/oppy_ai/infrastructure/repositories.py
Implementación de Repositorios para Feedback Humano (RLHF) y Curación Continua de OppyFy.
Cumple con:
- `AIChatFeedbackRepositoryPort` en la capa de dominio puro.
- SQLAlchemy 2.0 Async para persistencia en esquemas dinámicos `tenant_*`.
- Repositorio en memoria `InMemoryAIChatFeedbackRepository` para pruebas unitarias y fallback.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.oppy_ai.domain.evals import AIChatFeedback
from src.modules.oppy_ai.domain.ports import AIChatFeedbackRepositoryPort
from src.modules.oppy_ai.infrastructure.models import AIChatFeedbackModel

logger = logging.getLogger("oppytec.ai.feedback_repository")


def _is_valid_uuid(val: str | None) -> bool:
    """Verifica si una cadena representa un UUID válido."""
    if not val:
        return False
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _model_to_feedback(model: AIChatFeedbackModel) -> AIChatFeedback:
    """Convierte un AIChatFeedbackModel de SQLAlchemy en la entidad de dominio puro AIChatFeedback."""
    return AIChatFeedback(
        id=model.id,
        tenant_id=model.tenant_id,
        user_id=model.user_id,
        message_id=str(model.message_id) if model.message_id else "",
        trace_id=model.trace_id,
        feedback_type=model.feedback_type,  # type: ignore[arg-type]
        failure_category=model.failure_category,  # type: ignore[arg-type]
        user_correction=model.user_correction,
        rating=model.rating,
        created_at=model.created_at,
    )


class SqlAlchemyAIChatFeedbackRepository(AIChatFeedbackRepositoryPort):
    """
    Repositorio transaccional SQLAlchemy 2.0 Async para la entidad `AIChatFeedback`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_feedback(self, feedback: AIChatFeedback) -> AIChatFeedback:
        """Persiste o actualiza un registro de feedback humano."""
        stmt = select(AIChatFeedbackModel).where(AIChatFeedbackModel.id == feedback.id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()

        msg_uuid = uuid.UUID(feedback.message_id) if _is_valid_uuid(feedback.message_id) else None

        if not model:
            model = AIChatFeedbackModel(
                id=feedback.id,
                tenant_id=feedback.tenant_id,
                user_id=feedback.user_id,
                message_id=msg_uuid,
                trace_id=feedback.trace_id,
                feedback_type=feedback.feedback_type,
                failure_category=feedback.failure_category,
                user_correction=feedback.user_correction,
                rating=feedback.rating,
                created_at=feedback.created_at,
            )
            self.session.add(model)
        else:
            model.feedback_type = feedback.feedback_type
            model.failure_category = feedback.failure_category
            model.user_correction = feedback.user_correction
            model.rating = feedback.rating
            if msg_uuid:
                model.message_id = msg_uuid

        await self.session.flush()
        return _model_to_feedback(model)

    async def list_feedback(
        self,
        tenant_id: UUID,
        message_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AIChatFeedback]:
        """Obtiene una lista paginada de feedbacks para el tenant indicado."""
        stmt = (
            select(AIChatFeedbackModel)
            .where(AIChatFeedbackModel.tenant_id == tenant_id)
        )
        if message_id:
            if _is_valid_uuid(message_id):
                stmt = stmt.where(AIChatFeedbackModel.message_id == uuid.UUID(message_id))
            else:
                return []

        stmt = stmt.order_by(AIChatFeedbackModel.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [_model_to_feedback(m) for m in models]

    async def get_by_trace_id(
        self,
        tenant_id: UUID,
        trace_id: str,
    ) -> list[AIChatFeedback]:
        """Obtiene feedbacks vinculados a un identificador de traza específico."""
        stmt = (
            select(AIChatFeedbackModel)
            .where(
                AIChatFeedbackModel.tenant_id == tenant_id,
                AIChatFeedbackModel.trace_id == trace_id,
            )
            .order_by(AIChatFeedbackModel.created_at.asc())
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [_model_to_feedback(m) for m in models]


class InMemoryAIChatFeedbackRepository(AIChatFeedbackRepositoryPort):
    """
    Repositorio 100% en memoria de Feedback de usuarios.
    Ideal para tests unitarios ultrarrápidos (< 1ms) y entornos aislados sin DB.
    """

    def __init__(self) -> None:
        self._feedbacks: dict[UUID, AIChatFeedback] = {}

    def clear(self) -> None:
        self._feedbacks.clear()

    async def save_feedback(self, feedback: AIChatFeedback) -> AIChatFeedback:
        self._feedbacks[feedback.id] = feedback
        return feedback

    async def list_feedback(
        self,
        tenant_id: UUID,
        message_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AIChatFeedback]:
        matching = [
            f for f in self._feedbacks.values()
            if f.tenant_id == tenant_id
            and (message_id is None or f.message_id == message_id)
        ]
        # Ordenar descendente por created_at
        matching.sort(key=lambda x: x.created_at, reverse=True)
        return matching[offset : offset + limit]

    async def get_by_trace_id(
        self,
        tenant_id: UUID,
        trace_id: str,
    ) -> list[AIChatFeedback]:
        matching = [
            f for f in self._feedbacks.values()
            if f.tenant_id == tenant_id and f.trace_id == trace_id
        ]
        matching.sort(key=lambda x: x.created_at)
        return matching


__all__ = [
    "InMemoryAIChatFeedbackRepository",
    "SqlAlchemyAIChatFeedbackRepository",
]
