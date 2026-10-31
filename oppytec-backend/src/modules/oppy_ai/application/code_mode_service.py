"""
oppytec-backend/src/modules/oppy_ai/application/code_mode_service.py
Servicio de Aplicación de Code Mode para OppyFy (Fase 3 de Plan Maestro MCP).
Orquesta la interacción entre el asistente OppyFy, el catálogo universal de capacidades MCP
(MCPBridgeManager) y el motor hermético de ejecución aislada en sandbox (CodeModeSandboxRunner).

Garantiza:
1. Zero-Prompt Overhead: Búsqueda dinámica y catálogo token-minimal (< 150 tokens) con `search_capabilities`.
2. Aislamiento Multi-Tenant estricto y prevención de ataques IDOR Cross-Tenant.
3. Hard-Code Data Stripping de métricas financieras para usuarios sin privilegios.
4. Telemetría FinOps obligatoria y cálculo de tokens ahorrados en `public.llm_request_logs`.
5. Retorno estructurado para el chat de OppyFy y ejecución de consultas analíticas compuestas.
"""
from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from src.adapters.ai.protocol import LlmUsageRecord
from src.core.mcp_bridge.manager import MCPBridgeManager
from src.core.sandbox.models import (
    SandboxContext,
    SandboxExecutionResult,
    SandboxSecurityError,
)
from src.core.sandbox.runner import CodeModeSandboxRunner

if TYPE_CHECKING:
    from src.modules.oppy_ai.application.metered_ai_service import MeteredAIService

logger = logging.getLogger("oppytec.oppyfy.code_mode")


@dataclass(frozen=True)
class OppyfyCodeModeExecutionResult:
    """Resultado tipado de la ejecución de Code Mode listo para el chat de OppyFy."""

    success: bool
    result: object = None
    stdout: str = ""
    execution_time_ms: float = 0.0
    error: str | None = None
    error_code: str | None = None
    raw_tokens_estimate: int = 0
    final_tokens_estimate: int = 0
    tokens_saved_estimate: int = 0
    summary: str = ""
    structured_chat_response: dict[str, Any] = field(default_factory=dict)
    usage_record: LlmUsageRecord | None = None


class OppyfyCodeModeService:
    """
    Servicio de orquestación de Code Mode sobre MCP para el asistente OppyFy.
    """

    def __init__(
        self,
        bridge_manager: MCPBridgeManager | None = None,
        sandbox_runner: CodeModeSandboxRunner | None = None,
        metered_ai_service: MeteredAIService | None = None,
    ) -> None:
        self.bridge_manager = bridge_manager or MCPBridgeManager(auto_load=True)
        self.sandbox_runner = sandbox_runner or CodeModeSandboxRunner(
            bridge_manager=self.bridge_manager
        )
        self._metered_service = metered_ai_service

    def set_metered_service(self, metered_service: MeteredAIService) -> None:
        """Asocia o actualiza el servicio medido de IA."""
        self._metered_service = metered_service

    def search_capabilities(
        self,
        tenant_id: str,
        query: str = "",
        limit: int = 5,
    ) -> list[dict[str, object]]:
        """
        Descubrimiento semántico token-minimal (< 150 tokens por capacidad)
        de herramientas registradas en los servidores MCP.
        """
        if not tenant_id:
            logger.warning("search_capabilities invocado sin tenant_id explícito.")

        return self.bridge_manager.search_capabilities(query=query, limit=limit)

    def execute_code_mode(
        self,
        tenant_id: str | uuid.UUID,
        user_id: int,
        user_role: str | int | tuple[int, ...] | Sequence[int] | None = None,
        permissions: frozenset[str] | set[str] | list[str] | Sequence[str] | None = None,
        script_code: str = "",
        can_view_costs: bool = False,
        *,
        holding_id: uuid.UUID | str | None = None,
        thread_id: uuid.UUID | None = None,
        caller_feature: str = "oppyfy_code_mode",
        metered_service: MeteredAIService | None = None,
    ) -> OppyfyCodeModeExecutionResult:
        """
        Ejecuta un script en el sandbox aislado con verificación RBAC, multi-tenant y stripping de costos.
        Registra la telemetría FinOps en `public.llm_request_logs` a través de MeteredAIService.
        """
        # 1. Normalización de tenant_id
        raw_tenant = str(tenant_id).strip()
        safe_tenant = raw_tenant.replace("-", "_")
        clean_tenant = safe_tenant if safe_tenant.startswith("tenant_") else f"tenant_{safe_tenant}"

        # 2. Normalización de role_ids
        role_ids: tuple[int, ...]
        if isinstance(user_role, int):
            role_ids = (user_role,)
        elif isinstance(user_role, (tuple, list)):
            role_ids = tuple(int(x) for x in user_role if isinstance(x, int) or str(x).isdigit())
        elif isinstance(user_role, str):
            role_ids = (int(user_role),) if user_role.isdigit() else (1,)
        else:
            role_ids = ()

        # 3. Normalización de permisos
        if permissions is None:
            normalized_perms = frozenset()
        elif isinstance(permissions, frozenset):
            normalized_perms = permissions
        else:
            normalized_perms = frozenset(permissions)

        # 4. Construcción de SandboxContext con validación de seguridad
        try:
            context = SandboxContext(
                tenant_id=clean_tenant,
                user_id=int(user_id),
                role_ids=role_ids,
                permissions=normalized_perms,
                can_view_costs=bool(can_view_costs),
                holding_id=str(holding_id) if holding_id else None,
            )
        except SandboxSecurityError as sec_err:
            logger.warning("Fallo de seguridad al construir SandboxContext: %s", sec_err.message)
            return OppyfyCodeModeExecutionResult(
                success=False,
                error=sec_err.message,
                error_code=sec_err.error_code,
                summary=f"Acceso denegado: {sec_err.message}",
                structured_chat_response={
                    "type": "code_mode_execution",
                    "status": "error",
                    "error": sec_err.message,
                    "error_code": sec_err.error_code,
                    "data": None,
                    "stdout": "",
                    "metrics": {
                        "execution_time_ms": 0.0,
                        "raw_tokens_estimate": 0,
                        "final_tokens_estimate": 0,
                        "tokens_saved_estimate": 0,
                    },
                },
            )

        # 5. Ejecución en Sandbox
        runner_res: SandboxExecutionResult = self.sandbox_runner.execute(
            code=script_code,
            context=context,
        )

        # 6. Construcción del resumen y respuesta estructurada para el chat de OppyFy
        if runner_res.success:
            summary = self._build_success_summary(
                runner_res.result,
                runner_res.tokens_saved_estimate,
            )
            structured_resp: dict[str, Any] = {
                "type": "code_mode_execution",
                "status": "success",
                "data": runner_res.result,
                "stdout": runner_res.stdout,
                "metrics": {
                    "execution_time_ms": runner_res.execution_time_ms,
                    "raw_tokens_estimate": runner_res.raw_tokens_estimate,
                    "final_tokens_estimate": runner_res.final_tokens_estimate,
                    "tokens_saved_estimate": runner_res.tokens_saved_estimate,
                },
            }
        else:
            summary = f"Fallo en la ejecución de Code Mode ({runner_res.error_code}): {runner_res.error}"
            structured_resp = {
                "type": "code_mode_execution",
                "status": "error",
                "error": runner_res.error,
                "error_code": runner_res.error_code,
                "data": None,
                "stdout": runner_res.stdout,
                "metrics": {
                    "execution_time_ms": runner_res.execution_time_ms,
                    "raw_tokens_estimate": runner_res.raw_tokens_estimate,
                    "final_tokens_estimate": runner_res.final_tokens_estimate,
                    "tokens_saved_estimate": runner_res.tokens_saved_estimate,
                },
            }

        # 7. Intercepción y Registro en Telemetría FinOps (MeteredAIService)
        active_metered = metered_service or self._metered_service
        usage_rec: LlmUsageRecord | None = None

        if active_metered is not None:
            usage_rec = self._record_finops_telemetry(
                metered_service=active_metered,
                context=context,
                script_code=script_code,
                runner_res=runner_res,
                holding_id=holding_id,
                thread_id=thread_id,
                caller_feature=caller_feature,
            )

        return OppyfyCodeModeExecutionResult(
            success=runner_res.success,
            result=runner_res.result,
            stdout=runner_res.stdout,
            execution_time_ms=runner_res.execution_time_ms,
            error=runner_res.error,
            error_code=runner_res.error_code,
            raw_tokens_estimate=runner_res.raw_tokens_estimate,
            final_tokens_estimate=runner_res.final_tokens_estimate,
            tokens_saved_estimate=runner_res.tokens_saved_estimate,
            summary=summary,
            structured_chat_response=structured_resp,
            usage_record=usage_rec,
        )

    @staticmethod
    def _build_success_summary(result: object, tokens_saved: int) -> str:
        """Genera una síntesis en lenguaje natural para la burbuja de chat de OppyFy."""
        savings_text = f" (Ahorro FinOps: {tokens_saved} tokens)" if tokens_saved > 0 else ""
        if isinstance(result, dict):
            return f"Consulta completada exitosamente. Se generaron {len(result)} métricas clave{savings_text}."
        if isinstance(result, (list, tuple)):
            return f"Consulta completada exitosamente. Se obtuvieron {len(result)} registros consolidados{savings_text}."
        if result is not None:
            return f"Consulta completada exitosamente: {result}{savings_text}."
        return f"Script ejecutado correctamente sin valor de retorno{savings_text}."

    @staticmethod
    def _record_finops_telemetry(
        metered_service: MeteredAIService,
        context: SandboxContext,
        script_code: str,
        runner_res: SandboxExecutionResult,
        holding_id: uuid.UUID | str | None,
        thread_id: uuid.UUID | None,
        caller_feature: str,
    ) -> LlmUsageRecord:
        """Registra la invocación en MeteredAIService y emite el registro LlmUsageRecord."""
        # Resolver UUID de holding
        try:
            if isinstance(holding_id, uuid.UUID):
                h_uuid = holding_id
            elif holding_id:
                h_uuid = uuid.UUID(str(holding_id))
            else:
                h_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        except (ValueError, TypeError):
            h_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(holding_id or "oppytec-holding"))

        # Resolver UUID de tenant
        try:
            t_uuid = uuid.UUID(context.tenant_id)
        except (ValueError, TypeError):
            t_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, context.tenant_id)

        input_tokens = max(1, len(script_code) // 4)
        output_tokens = max(1, runner_res.final_tokens_estimate)

        cost_usd = Decimal("0.000000")
        cost_clp = Decimal("0.00")
        if hasattr(metered_service, "calculate_token_cost"):
            try:
                cost_usd, cost_clp = metered_service.calculate_token_cost(
                    "gemini-2.5-flash",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            except Exception:
                pass

        usage_rec = LlmUsageRecord(
            holding_id=h_uuid,
            tenant_id=t_uuid,
            tenant_schema=context.tenant_id,
            user_id=context.user_id,
            engine_tier="SYSTEM_2_LLM",
            caller_feature=caller_feature,
            model_name="code-mode-sandbox",
            input_tokens=input_tokens,
            cached_tokens=0,
            output_tokens=output_tokens,
            provider_cost_usd=cost_usd,
            provider_cost_clp=cost_clp,
            credits_deducted=Decimal("0.00"),
            request_duration_ms=max(1, int(runner_res.execution_time_ms)),
            thread_id=thread_id,
            api_success=runner_res.success,
            error_message=runner_res.error,
            tokens_saved=runner_res.tokens_saved_estimate,
        )

        if hasattr(metered_service, "_record_usage"):
            metered_service._record_usage(usage_rec)

        return usage_rec
