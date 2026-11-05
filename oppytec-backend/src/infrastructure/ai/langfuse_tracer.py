"""
oppytec-backend/src/infrastructure/ai/langfuse_tracer.py
Adaptador de Observabilidad y Telemetría Especializada LLM para Langfuse Self-Hosted.
Implementa `LLMTracerPort` cumpliendo la arquitectura limpia y las reglas de oro de OppyTec v2.0:
- Zero floats en dinero: Decimal estricto para costos en USD (`provider_cost_usd`).
- Manejo asíncrono no bloqueante con patrón Circuit Breaker y degradación elegante:
  Si Langfuse está caído, offline o lento (> timeout), el chat de OppyFy NUNCA se degrada ni falla.
- Censura estricta de PII en origen (`scrub_telemetry_payload` y `scrub_pii_text`):
  Enmascara RUTs, correos personales, tarjetas y tokens sin alterar la razón social inmutable ('Pollo King').
- Registro en memoria RAM para inspección determinista en CI, pruebas unitarias y entornos locales.
"""
from __future__ import annotations

import base64
import logging
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
from pydantic import SecretStr

from src.core.config import get_settings
from src.core.observability import scrub_pii_text, scrub_telemetry_payload
from src.modules.oppy_ai.domain.evals import AIChatFeedback, TraceContext
from src.modules.oppy_ai.domain.ports import LLMTracerPort

logger = logging.getLogger("oppytec.ai.langfuse_tracer")


class LangfuseTracer(LLMTracerPort):
    """
    Adaptador resiliente de trazabilidad LLM que exporta trazas, generaciones,
    llamadas a herramientas (tool calls) y scores de feedback humano hacia Langfuse API.
    """

    def __init__(
        self,
        *,
        host: str | None = None,
        public_key: SecretStr | str | None = None,
        secret_key: SecretStr | str | None = None,
        timeout_seconds: float = 2.0,
        circuit_breaker_threshold: int = 3,
        circuit_cooldown_seconds: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
        enabled: bool = True,
    ) -> None:
        settings = get_settings()
        self.host = (host or settings.LANGFUSE_HOST or "http://localhost:3000").rstrip("/")
        
        raw_pub = public_key if public_key is not None else settings.LANGFUSE_PUBLIC_KEY
        if isinstance(raw_pub, SecretStr):
            self.public_key = raw_pub.get_secret_value()
        elif raw_pub:
            self.public_key = str(raw_pub)
        else:
            self.public_key = None

        raw_sec = secret_key if secret_key is not None else settings.LANGFUSE_SECRET_KEY
        if isinstance(raw_sec, SecretStr):
            self.secret_key = raw_sec.get_secret_value()
        elif raw_sec:
            self.secret_key = str(raw_sec)
        else:
            self.secret_key = None

        self.timeout_seconds = timeout_seconds
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_cooldown_seconds = circuit_cooldown_seconds
        self.enabled = enabled

        self._custom_client = http_client
        self._consecutive_failures: int = 0
        self._circuit_open_until: float = 0.0

        # Almacenamiento en memoria para pruebas e inspección forense en CI
        self._recorded_generations: list[dict[str, Any]] = []
        self._recorded_tool_calls: list[dict[str, Any]] = []
        self._recorded_feedbacks: list[dict[str, Any]] = []

    @property
    def is_configured(self) -> bool:
        """Determina si las credenciales mínimas de Langfuse están configuradas."""
        return bool(self.public_key and self.secret_key and self.enabled)

    @property
    def is_circuit_open(self) -> bool:
        """Indica si el circuit breaker está activo debido a fallas consecutivas en el colector."""
        if self._consecutive_failures >= self.circuit_breaker_threshold:
            now = time.monotonic()
            if now < self._circuit_open_until:
                return True
            # Período de enfriamiento cumplido: se intenta half-open
            return False
        return False

    def _get_auth_header(self) -> dict[str, str]:
        """Genera encabezado HTTP Basic Auth requerido por la API de ingestión de Langfuse."""
        if not self.public_key or not self.secret_key:
            return {}
        credentials = f"{self.public_key}:{self.secret_key}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        return {"Authorization": f"Basic {encoded}"}

    async def _post_ingestion_event(self, batch_payload: list[dict[str, Any]]) -> bool:
        """
        Envía un lote de eventos al endpoint /api/public/ingestion de Langfuse.
        Si la red falla o Langfuse está offline, activa el circuit breaker sin arrojar excepciones.
        """
        if not self.is_configured or self.is_circuit_open:
            return False

        url = f"{self.host}/api/public/ingestion"
        headers = {
            "Content-Type": "application/json",
            **self._get_auth_header(),
        }

        client = self._custom_client
        should_close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout_seconds)
            should_close_client = True

        try:
            response = await client.post(url, json={"batch": batch_payload}, headers=headers)
            if response.status_code in (200, 201, 207):
                self._consecutive_failures = 0
                return True
            else:
                self._consecutive_failures += 1
                logger.warning(
                    "Langfuse ingestion returned non-200 status: %d, body: %s",
                    response.status_code,
                    response.text[:200],
                )
                if self._consecutive_failures >= self.circuit_breaker_threshold:
                    self._circuit_open_until = time.monotonic() + self.circuit_cooldown_seconds
                    logger.warning(
                        "Langfuse Circuit Breaker OPEN for %.1f seconds",
                        self.circuit_cooldown_seconds,
                    )
                return False
        except Exception as exc:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.circuit_breaker_threshold:
                self._circuit_open_until = time.monotonic() + self.circuit_cooldown_seconds
                logger.warning(
                    "Langfuse Circuit Breaker OPEN after exception: %s. Graceful degradation active.",
                    exc,
                )
            else:
                logger.warning(
                    "Langfuse export failed gracefully (attempt %d/%d): %s",
                    self._consecutive_failures,
                    self.circuit_breaker_threshold,
                    exc,
                )
            return False
        finally:
            if should_close_client:
                await client.aclose()

    async def trace_generation(
        self,
        context: TraceContext,
        model: str,
        prompt: str,
        completion: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: Decimal,
        latency_ms: int,
        tags: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Registra una generación de LLM.
        Censura PII en prompt y completion, enlaza tenant_id y trace_id, y despacha a Langfuse.
        """
        scrubbed_prompt = scrub_pii_text(prompt) or ""
        scrubbed_completion = scrub_pii_text(completion) or ""
        raw_meta = dict(metadata or {})
        raw_meta["tenant_id"] = str(context.tenant_id)
        if context.user_id:
            raw_meta["user_id"] = str(context.user_id)
        raw_meta["cost_usd"] = f"{cost_usd:.6f}"
        scrubbed_metadata = scrub_telemetry_payload(raw_meta)

        merged_tags = {**context.tags, **(tags or {})}
        merged_tags["tenant_id"] = str(context.tenant_id)
        scrubbed_tags = {
            str(k): str(v)
            for k, v in scrub_telemetry_payload(dict(merged_tags)).items()
        }

        now_iso = datetime.now(UTC).isoformat()
        total_tokens = prompt_tokens + completion_tokens

        record = {
            "trace_id": context.trace_id,
            "span_id": context.span_id,
            "tenant_id": str(context.tenant_id),
            "user_id": str(context.user_id) if context.user_id else None,
            "model": model,
            "prompt": scrubbed_prompt,
            "completion": scrubbed_completion,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "tags": scrubbed_tags,
            "metadata": scrubbed_metadata,
            "created_at": now_iso,
        }
        self._recorded_generations.append(record)

        # Crear payload Langfuse v2 batch
        event_id = uuid.uuid4().hex
        gen_id = context.span_id or uuid.uuid4().hex[:16]

        batch = [
            {
                "id": f"evt-trc-{event_id[:12]}",
                "type": "trace-create",
                "timestamp": now_iso,
                "body": {
                    "id": context.trace_id,
                    "name": "oppyfy-chat-interaction",
                    "userId": str(context.user_id) if context.user_id else None,
                    "metadata": scrubbed_metadata,
                    "tags": [f"{k}:{v}" for k, v in scrubbed_tags.items()],
                },
            },
            {
                "id": f"evt-gen-{event_id[:12]}",
                "type": "generation-create",
                "timestamp": now_iso,
                "body": {
                    "id": gen_id,
                    "traceId": context.trace_id,
                    "name": f"generation-{model}",
                    "model": model,
                    "input": scrubbed_prompt,
                    "output": scrubbed_completion,
                    "usage": {
                        "input": prompt_tokens,
                        "output": completion_tokens,
                        "total": total_tokens,
                        "unit": "TOKENS",
                    },
                    "calculatedTotalCost": float(cost_usd),
                    "startTime": context.start_time.isoformat(),
                    "endTime": now_iso,
                    "metadata": scrubbed_metadata,
                },
            },
        ]

        await self._post_ingestion_event(batch)
        return context.trace_id

    async def trace_tool_call(
        self,
        context: TraceContext,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: dict[str, Any],
        latency_ms: int,
        error: str | None = None,
    ) -> str:
        """
        Registra la invocación de una herramienta operativa (tool call) con redacción PII.
        """
        scrubbed_input = scrub_telemetry_payload(tool_input)
        scrubbed_output = scrub_telemetry_payload(tool_output)

        span_id = uuid.uuid4().hex[:16]
        now_iso = datetime.now(UTC).isoformat()

        record = {
            "trace_id": context.trace_id,
            "span_id": span_id,
            "tenant_id": str(context.tenant_id),
            "tool_name": tool_name,
            "input": scrubbed_input,
            "output": scrubbed_output,
            "latency_ms": latency_ms,
            "error": scrub_pii_text(error) if error else None,
            "created_at": now_iso,
        }
        self._recorded_tool_calls.append(record)

        batch = [
            {
                "id": f"evt-span-{span_id}",
                "type": "span-create",
                "timestamp": now_iso,
                "body": {
                    "id": span_id,
                    "traceId": context.trace_id,
                    "name": f"tool:{tool_name}",
                    "input": scrubbed_input,
                    "output": scrubbed_output,
                    "statusMessage": scrub_pii_text(error) if error else "OK",
                    "level": "ERROR" if error else "DEFAULT",
                    "metadata": {
                        "tenant_id": str(context.tenant_id),
                        "latency_ms": latency_ms,
                    },
                },
            }
        ]

        await self._post_ingestion_event(batch)
        return span_id

    async def record_feedback(
        self,
        feedback: AIChatFeedback,
    ) -> bool:
        """
        Envía un score a Langfuse para asociar la evaluación humana al trace.
        Calcula un valor normalizado (1.0 para positivo, 0.0 para negativo).
        """
        score_val = 1.0 if feedback.feedback_type == "positive" else 0.0
        now_iso = datetime.now(UTC).isoformat()

        comment = scrub_pii_text(feedback.user_correction) if feedback.user_correction else (feedback.failure_category or "")

        record = {
            "feedback_id": str(feedback.id),
            "trace_id": feedback.trace_id,
            "tenant_id": str(feedback.tenant_id),
            "user_id": str(feedback.user_id) if feedback.user_id else None,
            "feedback_type": feedback.feedback_type,
            "failure_category": feedback.failure_category,
            "score_value": score_val,
            "rating": feedback.rating,
            "comment": comment,
            "created_at": now_iso,
        }
        self._recorded_feedbacks.append(record)

        batch = [
            {
                "id": f"evt-score-{uuid.uuid4().hex[:12]}",
                "type": "score-create",
                "timestamp": now_iso,
                "body": {
                    "traceId": feedback.trace_id,
                    "name": "user-feedback",
                    "value": score_val,
                    "comment": comment,
                    "metadata": {
                        "feedback_id": str(feedback.id),
                        "tenant_id": str(feedback.tenant_id),
                        "message_id": feedback.message_id,
                        "failure_category": feedback.failure_category,
                        "rating": feedback.rating,
                    },
                },
            }
        ]

        return await self._post_ingestion_event(batch)

    async def flush(self) -> None:
        """Fuerza la descarga de eventos pendientes."""
        # En implementación por HTTP directo o memoria no hay búfer diferido huérfano
        pass

    # Helper inspection methods para tests
    def get_recorded_generations(self) -> list[dict[str, Any]]:
        return list(self._recorded_generations)

    def get_recorded_tool_calls(self) -> list[dict[str, Any]]:
        return list(self._recorded_tool_calls)

    def get_recorded_feedbacks(self) -> list[dict[str, Any]]:
        return list(self._recorded_feedbacks)

    def clear(self) -> None:
        self._recorded_generations.clear()
        self._recorded_tool_calls.clear()
        self._recorded_feedbacks.clear()
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0


__all__ = ["LangfuseTracer"]
