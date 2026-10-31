"""
oppytec-backend/tests/unit/core/test_sandbox_runner.py
Pruebas unitarias completas para el motor de Sandbox Aislado (Fase 2 de Code Mode sobre MCP).
Verifica:
1. Aislamiento de OS, red y AST anti-escape (imports prohibidos, builtins, dunder attributes).
2. Watchdog de timeout estricto.
3. Inyección inmutable de contexto Multi-Tenant y bloqueo Anti-IDOR Cross-Tenant.
4. Cumplimiento de permisos RBAC de 3 niveles (<modulo>.<submodulo>.<funcion>).
5. Hard-Code Data Stripping de costos y márgenes sensibles.
6. Telemetría FinOps de reducción y ahorro de tokens.
"""
from __future__ import annotations

import pytest

from src.core.mcp_bridge import MCPBridgeManager, MCPToolDefinition
from src.core.sandbox import (
    CodeModeSandboxRunner,
    SandboxContext,
    SandboxSecurityError,
)


@pytest.fixture
def test_tenant_context() -> SandboxContext:
    return SandboxContext(
        tenant_id="tenant_sushi_club",
        user_id=42,
        role_ids=(3,),
        hierarchy_rank=2,
        permissions=frozenset({"inventario.stock.consultar", "ventas.reportes.ver"}),
        can_view_costs=False,
    )


@pytest.fixture
def financial_admin_context() -> SandboxContext:
    return SandboxContext(
        tenant_id="tenant_sushi_club",
        user_id=1,
        role_ids=(1,),
        hierarchy_rank=0,
        permissions=frozenset({"*", "finanzas.costos.ver"}),
        can_view_costs=True,
    )


@pytest.fixture
def mock_bridge_manager() -> MCPBridgeManager:
    manager = MCPBridgeManager(auto_load=False)

    def mock_postgres_query(*_args: object, **_kwargs: object) -> list[dict[str, object]]:
        return [
            {
                "id": 101,
                "producto": "Salmón Fresco",
                "stock_actual": 15,
                "costo_unitario": 8500,
                "costo_total": 127500,
                "margen_bruto": 0.42,
                "status": "AVAILABLE",
            },
            {
                "id": 102,
                "producto": "Arroz Sushi",
                "stock_actual": 50,
                "costo_unitario": 1200,
                "costo_total": 60000,
                "margen_bruto": 0.65,
                "status": "AVAILABLE",
            },
            {
                "id": 103,
                "producto": "Alga Nori",
                "stock_actual": 0,
                "costo_unitario": 300,
                "costo_total": 0,
                "margen_bruto": 0.50,
                "status": "DEPLETED",
            },
        ]

    tool_pg = MCPToolDefinition(
        server_name="postgres",
        name="query",
        qualified_name="postgres.query",
        description="Consulta SQL protegida",
        parameters={"sql": {"type": "string"}, "tenant_id": {"type": "string"}},
        handler=mock_postgres_query,
        required_permission="inventario.stock.consultar",
    )
    manager.register_tool(tool_pg)
    return manager


class TestSandboxContext:
    def test_tenant_id_normalization(self) -> None:
        ctx1 = SandboxContext(tenant_id="la_trattoria", user_id=1)
        assert ctx1.tenant_id == "tenant_la_trattoria"

        ctx2 = SandboxContext(tenant_id="tenant_el_asador", user_id=2)
        assert ctx2.tenant_id == "tenant_el_asador"

    def test_invalid_tenant_id_format_raises(self) -> None:
        with pytest.raises(SandboxSecurityError) as exc_info:
            SandboxContext(tenant_id="illegal/tenant*name", user_id=1)
        assert "Esquema de tenant inválido" in str(exc_info.value)

    def test_has_permission_exact_and_wildcard(self) -> None:
        ctx = SandboxContext(
            tenant_id="tenant_bistro",
            user_id=10,
            permissions=frozenset({"inventario.stock.consultar", "cocina.*"}),
        )
        assert ctx.has_permission("inventario.stock.consultar") is True
        assert ctx.has_permission("cocina.recetas.crear") is True
        assert ctx.has_permission("finanzas.costos.ver") is False

    def test_superuser_god_has_all_permissions(self) -> None:
        ctx = SandboxContext(
            tenant_id="tenant_bistro",
            user_id=1,
            is_superuser_god=True,
        )
        assert ctx.has_permission("any.random.permission") is True


class TestCodeModeSandboxRunnerBasic:
    def test_execute_pure_python_logic(self, test_tenant_context: SandboxContext) -> None:
        runner = CodeModeSandboxRunner()
        script = """
numbers = [1, 2, 3, 4, 5]
squared = [n * n for n in numbers]
result = {"sum": sum(squared), "count": len(squared)}
"""
        res = runner.execute(script, test_tenant_context)
        assert res.success is True
        assert res.result == {"sum": 55, "count": 5}
        assert res.execution_time_ms >= 0.0

    def test_execute_with_return_statement(self, test_tenant_context: SandboxContext) -> None:
        runner = CodeModeSandboxRunner()
        script = """
x = 10
y = 20
return {"total": x + y, "tenant": tenant_id}
"""
        res = runner.execute(script, test_tenant_context)
        assert res.success is True
        assert res.result == {"total": 30, "tenant": "tenant_sushi_club"}

    def test_execute_with_stdout_capture(self, test_tenant_context: SandboxContext) -> None:
        runner = CodeModeSandboxRunner()
        script = """
print("Iniciando análisis...")
print("Procesando lote FEFO")
result = "OK"
"""
        res = runner.execute(script, test_tenant_context)
        assert res.success is True
        assert "Iniciando análisis..." in res.stdout
        assert "Procesando lote FEFO" in res.stdout
        assert res.result == "OK"


class TestCodeModeSandboxSecurity:
    def test_disallow_host_os_import(self, test_tenant_context: SandboxContext) -> None:
        runner = CodeModeSandboxRunner()
        script = """
import os
result = os.listdir(".")
"""
        res = runner.execute(script, test_tenant_context)
        assert res.success is False
        assert res.error_code == "SANDBOX_SECURITY_VIOLATION"
        assert "Importación no autorizada del módulo 'os'" in str(res.error)

    def test_disallow_subprocess_import(self, test_tenant_context: SandboxContext) -> None:
        runner = CodeModeSandboxRunner()
        script = """
from subprocess import check_output
result = check_output(["ls", "-la"])
"""
        res = runner.execute(script, test_tenant_context)
        assert res.success is False
        assert res.error_code == "SANDBOX_SECURITY_VIOLATION"
        assert "Importación no autorizada" in str(res.error)

    def test_allow_safe_imports(self, test_tenant_context: SandboxContext) -> None:
        runner = CodeModeSandboxRunner()
        script = """
import math
import json
import datetime
from decimal import Decimal

pi_val = math.pi
now = datetime.datetime.now()
dec = Decimal("10.5")
result = {"floor_pi": math.floor(pi_val), "dec": str(dec)}
"""
        res = runner.execute(script, test_tenant_context)
        assert res.success is True
        assert res.result == {"floor_pi": 3, "dec": "10.5"}

    def test_disallow_forbidden_builtins_eval_exec_open(
        self, test_tenant_context: SandboxContext
    ) -> None:
        runner = CodeModeSandboxRunner()

        for forbidden in ["eval('1+1')", "exec('x=1')", "open('/etc/passwd')"]:
            res = runner.execute(forbidden, test_tenant_context)
            assert res.success is False
            assert res.error_code == "SANDBOX_SECURITY_VIOLATION"

    def test_disallow_dunder_attribute_traversal(
        self, test_tenant_context: SandboxContext
    ) -> None:
        runner = CodeModeSandboxRunner()
        script = """
subclasses = ().__class__.__bases__[0].__subclasses__()
result = len(subclasses)
"""
        res = runner.execute(script, test_tenant_context)
        assert res.success is False
        assert res.error_code == "SANDBOX_SECURITY_VIOLATION"
        assert "Acceso prohibido al atributo privado o dunder" in str(res.error)

    def test_ast_bomb_node_limit_protection(self, test_tenant_context: SandboxContext) -> None:
        runner = CodeModeSandboxRunner(max_ast_nodes=50)
        # Generar código largo que supera 50 nodos
        script = " + ".join([f"({i} * {i})" for i in range(100)])
        res = runner.execute(f"result = {script}", test_tenant_context)
        assert res.success is False
        assert res.error_code == "SANDBOX_SECURITY_VIOLATION"
        assert "límite máximo de nodos AST" in str(res.error)


class TestCodeModeTimeoutWatchdog:
    def test_infinite_loop_timeout_protection(self, test_tenant_context: SandboxContext) -> None:
        runner = CodeModeSandboxRunner(timeout_seconds=0.4)
        script = """
while True:
    pass
"""
        res = runner.execute(script, test_tenant_context)
        assert res.success is False
        assert res.error_code == "SANDBOX_TIMEOUT_EXCEEDED"
        assert "Timeout de ejecución excedido" in str(res.error)


class TestCodeModeMultiTenantAndRBAC:
    def test_cross_tenant_query_detection_and_block(
        self,
        test_tenant_context: SandboxContext,
        mock_bridge_manager: MCPBridgeManager,
    ) -> None:
        runner = CodeModeSandboxRunner(bridge_manager=mock_bridge_manager)
        # El usuario pertenece a 'tenant_sushi_club' pero intenta consultar 'tenant_other_hacker'
        script = """
rows = oppy.postgres.query(sql="SELECT * FROM tenant_other_hacker.users;")
result = len(rows)
"""
        res = runner.execute(script, test_tenant_context)
        assert res.success is False
        assert res.error_code == "CROSS_TENANT_ACCESS_VIOLATION"
        assert "Cross-tenant access violation" in str(res.error)
        assert "tenant_other_hacker" in str(res.error)

    def test_same_tenant_query_allowed(
        self,
        test_tenant_context: SandboxContext,
        mock_bridge_manager: MCPBridgeManager,
    ) -> None:
        runner = CodeModeSandboxRunner(bridge_manager=mock_bridge_manager)
        script = """
rows = oppy.postgres.query(sql="SELECT * FROM tenant_sushi_club.inventory WHERE status = 'AVAILABLE';")
result = {"count": len(rows)}
"""
        res = runner.execute(script, test_tenant_context)
        assert res.success is True
        assert res.result == {"count": 3}

    def test_missing_rbac_permission_blocks_tool(
        self,
        mock_bridge_manager: MCPBridgeManager,
    ) -> None:
        runner = CodeModeSandboxRunner(bridge_manager=mock_bridge_manager)
        # Contexto sin permiso 'inventario.stock.consultar'
        restricted_context = SandboxContext(
            tenant_id="tenant_sushi_club",
            user_id=99,
            permissions=frozenset({"ventas.pedidos.ver"}),
        )
        script = """
rows = oppy.postgres.query(sql="SELECT * FROM tenant_sushi_club.inventory;")
result = len(rows)
"""
        res = runner.execute(script, restricted_context)
        assert res.success is False
        assert res.error_code == "RBAC_PERMISSION_DENIED"
        assert "inventario.stock.consultar" in str(res.error)


class TestHardCodeDataStrippingAndFinOps:
    def test_stripping_when_can_view_costs_is_false(
        self,
        test_tenant_context: SandboxContext,
        mock_bridge_manager: MCPBridgeManager,
    ) -> None:
        runner = CodeModeSandboxRunner(bridge_manager=mock_bridge_manager)
        # El script itera sobre los ítems de inventario
        script = """
rows = oppy.postgres.query(sql="SELECT * FROM tenant_sushi_club.inventory;")
# Intentar leer datos devueltos
first_item = rows[0]
return {
    "producto": first_item["producto"],
    "costo_unitario": first_item["costo_unitario"],
    "costo_total": first_item["costo_total"],
    "margen_bruto": first_item["margen_bruto"],
}
"""
        res = runner.execute(script, test_tenant_context)
        assert res.success is True
        assert res.result["producto"] == "Salmón Fresco"
        # Todos los costos y márgenes han sido interceptados y redactados
        assert res.result["costo_unitario"] == "[REDACTED_COST]"
        assert res.result["costo_total"] == "[REDACTED_COST]"
        assert res.result["margen_bruto"] == "[REDACTED_COST]"

    def test_costs_preserved_when_can_view_costs_is_true(
        self,
        financial_admin_context: SandboxContext,
        mock_bridge_manager: MCPBridgeManager,
    ) -> None:
        runner = CodeModeSandboxRunner(bridge_manager=mock_bridge_manager)
        script = """
rows = oppy.postgres.query(sql="SELECT * FROM tenant_sushi_club.inventory;")
first_item = rows[0]
return {
    "producto": first_item["producto"],
    "costo_unitario": first_item["costo_unitario"],
    "costo_total": first_item["costo_total"],
    "margen_bruto": first_item["margen_bruto"],
}
"""
        res = runner.execute(script, financial_admin_context)
        assert res.success is True
        assert res.result["producto"] == "Salmón Fresco"
        # Con permisos financieros, los valores reales son accesibles
        assert res.result["costo_unitario"] == 8500
        assert res.result["costo_total"] == 127500
        assert res.result["margen_bruto"] == 0.42

    def test_finops_token_savings_estimation(
        self,
        financial_admin_context: SandboxContext,
        mock_bridge_manager: MCPBridgeManager,
    ) -> None:
        runner = CodeModeSandboxRunner(bridge_manager=mock_bridge_manager)
        # El script realiza una agregación en memoria reduciendo 3 registros a 1 solo número
        script = """
rows = oppy.postgres.query(sql="SELECT * FROM tenant_sushi_club.inventory;")
available_count = sum(1 for item in rows if item["status"] == "AVAILABLE")
return {"total_available": available_count}
"""
        res = runner.execute(script, financial_admin_context)
        assert res.success is True
        assert res.result == {"total_available": 2}
        # Verifica métricas FinOps calculadas
        assert res.raw_tokens_estimate > 0
        assert res.final_tokens_estimate > 0
        assert res.tokens_saved_estimate >= 0
        assert res.raw_tokens_estimate > res.final_tokens_estimate
