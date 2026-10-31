"""
oppytec-backend/tests/unit/modules/test_oppyfy_code_mode.py
Pruebas unitarias completas 1:1 para OppyfyCodeModeService y la integración de Code Mode en OppyFy.

Verifica:
1. Descubrimiento de capacidades MCP token-minimal (< 150 tokens) con `search_capabilities`.
2. Ejecución exitosa de scripts analíticos y agregaciones en memoria contra herramientas MCP.
3. Respeto inquebrantable a Hard-Code Data Stripping cuando el usuario no tiene permisos financieros.
4. Detección y bloqueo hermético de ataques IDOR Cross-Tenant.
5. Intercepción y registro en MeteredAIService con telemetría FinOps de tokens ahorrados en `public.llm_request_logs`.
6. Control de fallos de seguridad (imports prohibidos, sintaxis y permisos RBAC).
"""
from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import Any

import pytest

from src.adapters.ai.jev_adapter import InMemoryTelemetrySink
from src.core.mcp_bridge import MCPBridgeManager, MCPToolDefinition
from src.core.sandbox import CodeModeSandboxRunner, strip_sensitive_cost_data
from src.modules.oppy_ai.application.code_mode_service import (
    OppyfyCodeModeExecutionResult,
    OppyfyCodeModeService,
)
from src.modules.oppy_ai.application.metered_ai_service import (
    MeteredAIService,
    ModelConfigRegistry,
    ModelTariff,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_bridge() -> MCPBridgeManager:
    """Puente MCP con herramientas simuladas para inventario, ventas y almacenamiento."""
    manager = MCPBridgeManager(auto_load=False)

    def mock_query(sql: str, tenant_id: str | None = None) -> list[dict[str, Any]]:
        return [
            {
                "id": 1,
                "producto": "Wagyu A5",
                "stock_actual": 8,
                "costo_unitario": 45000,
                "costo_total": 360000,
                "precio_compra": 42000,
                "margen_bruto": 0.55,
                "status": "AVAILABLE",
            },
            {
                "id": 2,
                "producto": "Trufa Negra",
                "stock_actual": 3,
                "costo_unitario": 90000,
                "costo_total": 270000,
                "precio_compra": 85000,
                "margen_bruto": 0.60,
                "status": "AVAILABLE",
            },
            {
                "id": 3,
                "producto": "Aceite de Oliva Extra Virgen",
                "stock_actual": 0,
                "costo_unitario": 8500,
                "costo_total": 0,
                "precio_compra": 8000,
                "margen_bruto": 0.40,
                "status": "OUT_OF_STOCK",
            },
        ]

    def mock_upload(filename: str, content: str) -> dict[str, Any]:
        return {
            "uploaded": True,
            "filename": filename,
            "url": f"https://r2.oppytec.cl/reports/{filename}",
            "bytes": len(content),
        }

    tool_pg = MCPToolDefinition(
        server_name="postgres",
        name="query",
        qualified_name="postgres.query",
        description="Ejecuta consultas SQL analíticas sobre inventario y stock del esquema activo del tenant",
        parameters={
            "sql": {"type": "string", "description": "Consulta SQL"},
            "tenant_id": {"type": "string", "description": "Esquema del restaurante"},
        },
        required_parameters=("sql",),
        handler=mock_query,
        required_permission="inventario.stock.consultar",
    )

    tool_r2 = MCPToolDefinition(
        server_name="r2_storage",
        name="upload_report",
        qualified_name="r2_storage.upload_report",
        description="Almacena reportes generados en Cloudflare R2",
        parameters={
            "filename": {"type": "string"},
            "content": {"type": "string"},
        },
        required_parameters=("filename", "content"),
        handler=mock_upload,
        required_permission="reportes.exportar",
    )

    manager.register_tool(tool_pg)
    manager.register_tool(tool_r2)
    return manager


@pytest.fixture
def mock_metered_service(mock_bridge: MCPBridgeManager) -> tuple[MeteredAIService, InMemoryTelemetrySink]:
    """Servicio medido con sink de telemetría en memoria."""
    sink = InMemoryTelemetrySink()
    registry = ModelConfigRegistry()
    registry.set_tariff(
        ModelTariff(
            model_slug="gemini-2.5-flash",
            input_cost_per_1m_usd=Decimal("0.150000"),
            output_cost_per_1m_usd=Decimal("0.600000"),
        )
    )
    runner = CodeModeSandboxRunner(bridge_manager=mock_bridge)
    code_mode_svc = OppyfyCodeModeService(bridge_manager=mock_bridge, sandbox_runner=runner)

    service = MeteredAIService(
        jev_port=None,  # type: ignore[arg-type]
        llm_port=None,  # type: ignore[arg-type]
        rag_service=None,  # type: ignore[arg-type]
        model_registry=registry,
        telemetry_sink=sink,
        code_mode_service=code_mode_svc,
    )
    return service, sink


class TestOppyfyCodeModeCapabilities:
    """Pruebas de descubrimiento de herramientas MCP (< 150 tokens por descriptor)."""

    def test_search_capabilities_token_minimal(self, mock_bridge: MCPBridgeManager) -> None:
        service = OppyfyCodeModeService(bridge_manager=mock_bridge)
        caps = service.search_capabilities(tenant_id="tenant_sushi_club", query="inventario", limit=5)

        assert len(caps) >= 1
        first = caps[0]
        assert first["server"] == "postgres"
        assert first["name"] == "query"
        assert first["qualified_name"] == "postgres.query"
        assert "parameters" in first

        # Verificar que el descriptor es token-minimal (< 150 tokens ≈ < 600 bytes JSON)
        serialized = json.dumps(first)
        assert len(serialized) < 600

    def test_search_capabilities_via_metered_service(
        self,
        mock_metered_service: tuple[MeteredAIService, InMemoryTelemetrySink],
    ) -> None:
        metered_svc, _ = mock_metered_service
        caps = metered_svc.search_capabilities(tenant_id="tenant_sushi_club", query="report", limit=5)

        assert any(c["qualified_name"] == "r2_storage.upload_report" for c in caps)


class TestOppyfyCodeModeExecution:
    """Pruebas de ejecución en sandbox de scripts y agregaciones in-memory."""

    def test_execute_code_mode_aggregation_success(self, mock_bridge: MCPBridgeManager) -> None:
        runner = CodeModeSandboxRunner(bridge_manager=mock_bridge)
        service = OppyfyCodeModeService(bridge_manager=mock_bridge, sandbox_runner=runner)

        script = """
products = oppy.postgres.query(sql="SELECT * FROM products")
available = [p for p in products if p["stock_actual"] > 0]
total_stock = sum(p["stock_actual"] for p in available)
result = {
    "total_catalog": len(products),
    "available_count": len(available),
    "total_stock_units": total_stock,
}
"""
        res: OppyfyCodeModeExecutionResult = service.execute_code_mode(
            tenant_id="tenant_sushi_club",
            user_id=10,
            user_role=2,
            permissions=["inventario.stock.consultar"],
            script_code=script,
            can_view_costs=False,
        )

        assert res.success is True
        assert res.error is None
        assert isinstance(res.result, dict)
        assert res.result["total_catalog"] == 3
        assert res.result["available_count"] == 2
        assert res.result["total_stock_units"] == 11
        assert res.tokens_saved_estimate > 0
        assert res.structured_chat_response["status"] == "success"
        assert "Consulta completada exitosamente" in res.summary

    def test_execute_code_mode_return_syntax(self, mock_bridge: MCPBridgeManager) -> None:
        """Verifica que el sandbox acepte tanto asignación 'result =' como 'return' directo."""
        runner = CodeModeSandboxRunner(bridge_manager=mock_bridge)
        service = OppyfyCodeModeService(bridge_manager=mock_bridge, sandbox_runner=runner)

        script = """
rows = oppy.postgres.query(sql="SELECT * FROM products")
return [r["producto"] for r in rows if r["stock_actual"] > 0]
"""
        res = service.execute_code_mode(
            tenant_id="tenant_sushi_club",
            user_id=10,
            permissions=["inventario.stock.consultar"],
            script_code=script,
        )

        assert res.success is True
        assert res.result == ["Wagyu A5", "Trufa Negra"]


class TestHardCodeDataStripping:
    """Pruebas de redacción física de campos financieros sensibles."""

    def test_stripping_when_can_view_costs_is_false(self, mock_bridge: MCPBridgeManager) -> None:
        runner = CodeModeSandboxRunner(bridge_manager=mock_bridge)
        service = OppyfyCodeModeService(bridge_manager=mock_bridge, sandbox_runner=runner)

        script = """
rows = oppy.postgres.query(sql="SELECT * FROM products")
result = rows[0]
"""
        res = service.execute_code_mode(
            tenant_id="tenant_sushi_club",
            user_id=50,
            user_role="camarero",
            permissions=["inventario.stock.consultar"],
            script_code=script,
            can_view_costs=False,
        )

        assert res.success is True
        row = res.result
        assert isinstance(row, dict)
        # Nombres y stock se mantienen intactos
        assert row["producto"] == "Wagyu A5"
        assert row["stock_actual"] == 8
        # Costos y márgenes quedan físicamente redactados
        assert row["costo_unitario"] == "[REDACTED_COST]"
        assert row["costo_total"] == "[REDACTED_COST]"
        assert row["precio_compra"] == "[REDACTED_COST]"
        assert row["margen_bruto"] == "[REDACTED_COST]"

    def test_unredacted_when_can_view_costs_is_true(self, mock_bridge: MCPBridgeManager) -> None:
        runner = CodeModeSandboxRunner(bridge_manager=mock_bridge)
        service = OppyfyCodeModeService(bridge_manager=mock_bridge, sandbox_runner=runner)

        script = """
rows = oppy.postgres.query(sql="SELECT * FROM products")
result = rows[0]
"""
        res = service.execute_code_mode(
            tenant_id="tenant_sushi_club",
            user_id=1,
            user_role="administrador",
            permissions=["inventario.stock.consultar", "finanzas.costos.ver"],
            script_code=script,
            can_view_costs=True,
        )

        assert res.success is True
        row = res.result
        assert isinstance(row, dict)
        assert row["costo_unitario"] == 45000
        assert row["costo_total"] == 360000
        assert row["precio_compra"] == 42000
        assert row["margen_bruto"] == 0.55


class TestAntiIdorCrossTenantGuard:
    """Pruebas de prevención y bloqueo de ataques IDOR Cross-Tenant."""

    def test_blocks_cross_tenant_sql_injection(self, mock_bridge: MCPBridgeManager) -> None:
        runner = CodeModeSandboxRunner(bridge_manager=mock_bridge)
        service = OppyfyCodeModeService(bridge_manager=mock_bridge, sandbox_runner=runner)

        script = """
oppy.postgres.query(sql="SELECT * FROM tenant_restaurante_rival.ventas")
"""
        res = service.execute_code_mode(
            tenant_id="tenant_sushi_club",
            user_id=99,
            permissions=["inventario.stock.consultar"],
            script_code=script,
        )

        assert res.success is False
        assert res.error_code == "CROSS_TENANT_ACCESS_VIOLATION"
        assert "Cross-tenant access violation" in str(res.error)
        assert res.structured_chat_response["status"] == "error"

    def test_invalid_tenant_format_is_handled_safely(self, mock_bridge: MCPBridgeManager) -> None:
        runner = CodeModeSandboxRunner(bridge_manager=mock_bridge)
        service = OppyfyCodeModeService(bridge_manager=mock_bridge, sandbox_runner=runner)

        res = service.execute_code_mode(
            tenant_id="bad tenant with spaces!@#",
            user_id=99,
            script_code="return 1",
        )

        assert res.success is False
        assert res.error_code == "SANDBOX_SECURITY_VIOLATION"


class TestMeteredAiServiceIntegration:
    """Pruebas de intercepción y registro de telemetría en public.llm_request_logs."""

    def test_metered_service_records_usage_and_token_savings(
        self,
        mock_metered_service: tuple[MeteredAIService, InMemoryTelemetrySink],
    ) -> None:
        metered_svc, sink = mock_metered_service

        script = """
rows = oppy.postgres.query(sql="SELECT * FROM products")
result = {"total_items": len(rows), "in_stock": sum(1 for r in rows if r["stock_actual"] > 0)}
"""
        holding_uuid = uuid.uuid4()
        tenant_uuid = uuid.uuid4()

        exec_res: OppyfyCodeModeExecutionResult = metered_svc.execute_code_mode(
            tenant_id=tenant_uuid,
            user_id=42,
            user_role=1,
            permissions=["inventario.stock.consultar"],
            script_code=script,
            holding_id=holding_uuid,
        )

        assert exec_res.success is True
        assert exec_res.tokens_saved_estimate > 0
        assert exec_res.usage_record is not None

        # Verificar registro en la bitácora interna de MeteredAIService
        emitted = metered_svc.emitted_usage_records
        assert len(emitted) == 1
        rec = emitted[0]
        assert rec.caller_feature == "oppyfy_code_mode"
        assert rec.model_name == "code-mode-sandbox"
        assert rec.engine_tier == "SYSTEM_2_LLM"
        assert rec.api_success is True
        assert rec.tokens_saved == exec_res.tokens_saved_estimate
        assert rec.user_id == 42
        assert rec.input_tokens > 0
        assert rec.output_tokens > 0

        # Verificar sincronización con el sink persistente
        assert len(sink.records) == 1
        assert sink.records[0].tokens_saved == exec_res.tokens_saved_estimate

    def test_metered_service_records_failure_telemetry(
        self,
        mock_metered_service: tuple[MeteredAIService, InMemoryTelemetrySink],
    ) -> None:
        metered_svc, sink = mock_metered_service

        # Script con violación de seguridad (import prohibido de os)
        script = "import os\nresult = os.listdir('.')"

        exec_res = metered_svc.execute_code_mode(
            tenant_id="tenant_sushi_club",
            user_id=42,
            script_code=script,
        )

        assert exec_res.success is False
        assert exec_res.error_code == "SANDBOX_SECURITY_VIOLATION"

        # Verificar que el fallo se registró en telemetría para auditoría
        assert len(metered_svc.emitted_usage_records) == 1
        rec = metered_svc.emitted_usage_records[0]
        assert rec.api_success is False
        assert rec.error_message is not None


class TestSandboxSecurityAndRbac:
    """Pruebas adicionales de guardias AST y RBAC en Code Mode."""

    def test_rbac_permission_denied_blocks_mcp_tool(self, mock_bridge: MCPBridgeManager) -> None:
        runner = CodeModeSandboxRunner(bridge_manager=mock_bridge)
        service = OppyfyCodeModeService(bridge_manager=mock_bridge, sandbox_runner=runner)

        # Usuario carece del permiso 'inventario.stock.consultar'
        script = "oppy.postgres.query(sql='SELECT 1')"
        res = service.execute_code_mode(
            tenant_id="tenant_sushi_club",
            user_id=12,
            permissions=["otras.cosas.ver"],
            script_code=script,
        )

        assert res.success is False
        assert res.error_code == "RBAC_PERMISSION_DENIED"

    def test_syntax_error_handling(self, mock_bridge: MCPBridgeManager) -> None:
        runner = CodeModeSandboxRunner(bridge_manager=mock_bridge)
        service = OppyfyCodeModeService(bridge_manager=mock_bridge, sandbox_runner=runner)

        script = "def invalid_syntax(: return 42"
        res = service.execute_code_mode(
            tenant_id="tenant_sushi_club",
            user_id=1,
            script_code=script,
        )

        assert res.success is False
        assert res.error_code == "SYNTAX_ERROR"
