"""
oppytec-backend/tests/unit/core/test_mcp_bridge.py
Pruebas unitarias completas para el módulo MCP Dynamic Bridge (Fase 1 de Code Mode sobre MCP).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.core.mcp_bridge import (
    DynamicSDKGenerator,
    MCPBridgeManager,
    MCPToolDefinition,
    MCPToolExecutionError,
)


@pytest.fixture
def sample_tool_schema() -> dict[str, Any]:
    return {
        "name": "query",
        "description": "Ejecuta una consulta SQL en la base de datos de PostgreSQL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "Sentencia SQL SELECT a ejecutar",
                },
                "max_rows": {
                    "type": "integer",
                    "description": "Límite de filas devueltas",
                },
            },
            "required": ["sql"],
        },
    }


@pytest.fixture
def sample_postgres_tool(sample_tool_schema: dict[str, Any]) -> MCPToolDefinition:
    return MCPToolDefinition.from_mcp_schema(
        server_name="postgres",
        tool_data=sample_tool_schema,
    )


class TestMCPToolDefinition:
    def test_from_mcp_schema_parsing(self, sample_postgres_tool: MCPToolDefinition) -> None:
        assert sample_postgres_tool.server_name == "postgres"
        assert sample_postgres_tool.name == "query"
        assert sample_postgres_tool.qualified_name == "postgres.query"
        assert "SQL" in sample_postgres_tool.description
        assert "sql" in sample_postgres_tool.parameters
        assert sample_postgres_tool.required_parameters == ("sql",)

    def test_get_python_signature(self, sample_postgres_tool: MCPToolDefinition) -> None:
        sig = sample_postgres_tool.get_python_signature()
        assert "postgres_query(" in sig
        assert "sql: str" in sig
        assert "max_rows: int | None = None" in sig

    def test_to_capability_descriptor_token_minimal(
        self, sample_postgres_tool: MCPToolDefinition
    ) -> None:
        descriptor = sample_postgres_tool.to_capability_descriptor()
        assert descriptor["server"] == "postgres"
        assert descriptor["name"] == "query"
        assert descriptor["qualified_name"] == "postgres.query"
        assert "parameters" in descriptor
        assert descriptor["required"] == ["sql"]
        # Serialización compacta para verificación de volumen de tokens
        serialized = json.dumps(descriptor)
        # Menos de 500 caracteres (~125 tokens), cumpliendo < 150 tokens
        assert len(serialized) < 500


class TestMCPBridgeManager:
    def test_load_configuration_from_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / "mcp_test_config.json"
        config_payload = {
            "mcpServers": {
                "postgres": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/db"],
                    "env": {"DEBUG": "true"},
                },
                "r2_storage": {
                    "command": "node",
                    "args": ["server.js"],
                    "transport": "stdio",
                },
            }
        }
        config_file.write_text(json.dumps(config_payload), encoding="utf-8")

        manager = MCPBridgeManager(config_path=config_file)
        pg_server = manager.get_server("postgres")
        assert pg_server is not None
        assert pg_server.name == "postgres"
        assert pg_server.command == "npx"
        assert pg_server.env.get("DEBUG") == "true"

        r2_server = manager.get_server("r2_storage")
        assert r2_server is not None
        assert r2_server.transport == "stdio"

    def test_load_configuration_missing_file_safe_fallback(self, tmp_path: Path) -> None:
        missing_path = tmp_path / "does_not_exist.json"
        manager = MCPBridgeManager(config_path=missing_path, auto_load=True)
        assert len(manager.get_all_tools()) == 0

    def test_register_and_get_tool(self, sample_postgres_tool: MCPToolDefinition) -> None:
        manager = MCPBridgeManager(auto_load=False)
        manager.register_tool(sample_postgres_tool)

        found = manager.get_tool("postgres", "query")
        assert found is not None
        assert found.qualified_name == "postgres.query"

        not_found = manager.get_tool("postgres", "unknown")
        assert not_found is None

    def test_search_capabilities_exact_and_fuzzy(self) -> None:
        manager = MCPBridgeManager(auto_load=False)

        tool_sales = MCPToolDefinition(
            server_name="postgres",
            name="query_sales",
            qualified_name="postgres.query_sales",
            description="Consulta de ventas y pedidos completados del restaurante",
            parameters={"status": {"type": "string"}},
        )
        tool_kardex = MCPToolDefinition(
            server_name="inventory",
            name="get_kardex_movements",
            qualified_name="inventory.get_kardex_movements",
            description="Historial de movimientos de kardex y mermas por lote FEFO",
            parameters={"batch_id": {"type": "integer"}},
        )
        tool_recipes = MCPToolDefinition(
            server_name="catalog",
            name="calculate_recipe_food_cost",
            qualified_name="catalog.calculate_recipe_food_cost",
            description="Cálculo de costos teóricos y rendimiento de recetas",
            parameters={"recipe_id": {"type": "integer"}},
        )

        manager.register_tools([tool_sales, tool_kardex, tool_recipes])

        # 1. Búsqueda por ventas
        res_sales = manager.search_capabilities("ventas pedidos", limit=1)
        assert len(res_sales) == 1
        assert res_sales[0]["qualified_name"] == "postgres.query_sales"

        # 2. Búsqueda por mermas FEFO
        res_kardex = manager.search_capabilities("kardex mermas", limit=1)
        assert len(res_kardex) == 1
        assert res_kardex[0]["qualified_name"] == "inventory.get_kardex_movements"

        # 3. Búsqueda con query vacío devuelve hasta el límite
        res_all = manager.search_capabilities("", limit=2)
        assert len(res_all) == 2

    def test_call_tool_with_in_memory_handler(self) -> None:
        manager = MCPBridgeManager(auto_load=False)

        def mock_query_handler(sql: str, limit: int = 10) -> list[dict[str, Any]]:
            return [{"id": 1, "query_received": sql, "limit": limit}]

        tool = MCPToolDefinition(
            server_name="postgres",
            name="query",
            qualified_name="postgres.query",
            description="Mock query",
            parameters={"sql": {"type": "string"}, "limit": {"type": "integer"}},
            handler=mock_query_handler,
        )
        manager.register_tool(tool)

        result = manager.call_tool("postgres", "query", {"sql": "SELECT 1;", "limit": 5})
        assert result == [{"id": 1, "query_received": "SELECT 1;", "limit": 5}]

    def test_call_tool_not_found_raises_execution_error(self) -> None:
        manager = MCPBridgeManager(auto_load=False)
        with pytest.raises(MCPToolExecutionError) as exc_info:
            manager.call_tool("nonexistent", "tool", {})
        assert "no existe en el catálogo" in str(exc_info.value)


class TestDynamicSDKGenerator:
    def test_generate_python_signatures_stub(self, sample_postgres_tool: MCPToolDefinition) -> None:
        generator = DynamicSDKGenerator([sample_postgres_tool])
        stubs = generator.generate_python_signatures()

        assert "class PostgresNamespace:" in stubs
        assert "def query(self, sql: str, max_rows: int | None = None) -> object:" in stubs
        assert "class OppySDK:" in stubs
        assert "oppy: OppySDK" in stubs

    def test_build_sandbox_namespace_invocation(self, sample_postgres_tool: MCPToolDefinition) -> None:
        captured_calls: list[tuple[str, str, dict[str, Any]]] = []

        def mock_caller(server: str, tool: str, kwargs: dict[str, Any]) -> Any:
            captured_calls.append((server, tool, kwargs))
            return {"status": "success", "rows": 42}

        generator = DynamicSDKGenerator([sample_postgres_tool])
        namespace = generator.build_sandbox_namespace(mock_caller)

        assert "oppy" in namespace
        assert "postgres" in namespace

        # Invocación estilo oppy.postgres.query(sql="SELECT ...")
        res1 = namespace["oppy"].postgres.query(sql="SELECT * FROM items")
        assert res1 == {"status": "success", "rows": 42}

        # Invocación directa postgres.query("SELECT ...") posicional
        res2 = namespace["postgres"].query("SELECT 1;")
        assert res2 == {"status": "success", "rows": 42}

        assert len(captured_calls) == 2
        assert captured_calls[0] == ("postgres", "query", {"sql": "SELECT * FROM items"})
        assert captured_calls[1] == ("postgres", "query", {"sql": "SELECT 1;"})

    def test_access_unknown_tool_raises_attribute_error(self, sample_postgres_tool: MCPToolDefinition) -> None:
        generator = DynamicSDKGenerator([sample_postgres_tool])
        namespace = generator.build_sandbox_namespace(lambda _s, _t, _kw: None)

        with pytest.raises(AttributeError) as exc_info:
            _ = namespace["postgres"].non_existent_tool
        assert "no expone la herramienta 'non_existent_tool'" in str(exc_info.value)

        with pytest.raises(AttributeError) as exc_info2:
            _ = namespace["oppy"].non_existent_server
        assert "Servidor MCP 'non_existent_server' no registrado" in str(exc_info2.value)
