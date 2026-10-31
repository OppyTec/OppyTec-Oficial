"""
oppytec-backend/src/core/mcp_bridge/manager.py
MCPBridgeManager: Administrador del ciclo de vida, introspección reactiva y búsqueda de capacidades
sobre servidores MCP (stdio/SSE/in-memory).
Implementa:
- Carga reactiva de configuración desde `~/.gemini/config/mcp_config.json` o variables de entorno.
- Introspección automática de herramientas vía `tools/list` (JSON-RPC 2.0).
- Catálogo semántico token-minimal vía `search_capabilities(query, limit)`.
- Orquestación de llamadas directas a herramientas (`call_tool`).
- Generación de SDK tipado para inyección en el Sandbox de Code Mode.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import unicodedata
from collections.abc import Sequence
from pathlib import Path

from src.core.exceptions import OppyTecError
from src.core.mcp_bridge.models import MCPServerConfig, MCPToolDefinition
from src.core.mcp_bridge.sdk_generator import DynamicSDKGenerator


class MCPBridgeError(OppyTecError):
    """Excepción base para fallos en el puente de transporte y herramientas MCP."""

    default_status_code = 502
    default_error_code = "MCP_BRIDGE_ERROR"
    default_i18n_key = "common:errors.mcp_bridge_error"
    default_title = "MCP Bridge Error"


class MCPServerConnectionError(MCPBridgeError):
    """Fallo de conexión o transporte al comunicarse con un servidor MCP."""

    default_status_code = 503
    default_error_code = "MCP_SERVER_UNAVAILABLE"
    default_i18n_key = "common:errors.mcp_server_unavailable"
    default_title = "MCP Server Unavailable"


class MCPToolExecutionError(MCPBridgeError):
    """Error al invocar o recibir la ejecución de una herramienta MCP."""

    default_status_code = 500
    default_error_code = "MCP_TOOL_EXECUTION_FAILED"
    default_i18n_key = "common:errors.mcp_tool_execution_failed"
    default_title = "MCP Tool Execution Failed"


def _normalize_text(text: str) -> str:
    """Normaliza texto eliminando acentos y convirtiendo a minúsculas para búsqueda de tokens."""
    nfkd = unicodedata.normalize("NFKD", text)
    cleaned = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return cleaned.lower().strip()


class MCPBridgeManager:
    """Administrador centralizado de servidores MCP y catálogo unificado de capacidades."""

    def __init__(
        self,
        config_path: Path | str | None = None,
        auto_load: bool = True,
    ) -> None:
        self._config_path: Path | None = self._resolve_config_path(config_path)
        self._servers: dict[str, MCPServerConfig] = {}
        self._tools: dict[str, MCPToolDefinition] = {}
        self._sdk_generator = DynamicSDKGenerator()

        if auto_load:
            self.load_configuration()

    @staticmethod
    def _resolve_config_path(explicit_path: Path | str | None) -> Path | None:
        if explicit_path:
            return Path(explicit_path).expanduser().resolve()

        env_path = os.environ.get("OPPYTEC_MCP_CONFIG_PATH")
        if env_path:
            return Path(env_path).expanduser().resolve()

        default_gemini = Path.home() / ".gemini" / "config" / "mcp_config.json"
        if default_gemini.exists():
            return default_gemini.resolve()

        return None

    @property
    def config_path(self) -> Path | None:
        return self._config_path

    def load_configuration(self, explicit_path: Path | str | None = None) -> dict[str, MCPServerConfig]:
        """Carga y parsea la configuración de servidores MCP desde el archivo JSON."""
        resolved = (
            Path(explicit_path).expanduser().resolve()
            if explicit_path is not None
            else self._config_path
        )
        if not resolved or not resolved.exists():
            return self._servers

        try:
            raw_text = resolved.read_text(encoding="utf-8")
            data = json.loads(raw_text)
            servers_data = data.get("mcpServers", {})
            for s_name, s_meta in servers_data.items():
                if isinstance(s_meta, dict):
                    server_cfg = MCPServerConfig(
                        name=s_name,
                        command=s_meta.get("command", "npx"),
                        args=list(s_meta.get("args", [])),
                        env=dict(s_meta.get("env", {})),
                        transport=s_meta.get("transport", "stdio"),
                        url=s_meta.get("url"),
                        enabled=s_meta.get("enabled", True),
                        description=s_meta.get("description", f"MCP server '{s_name}'"),
                    )
                    self.register_server(server_cfg)
        except Exception as exc:
            # Fallback seguro para no tumbar el arranque si el config está corrupto
            raise MCPBridgeError(
                f"Error al cargar configuración MCP desde '{resolved}': {exc}",
                i18n_key="common:errors.mcp_config_invalid",
            ) from exc

        return self._servers

    def register_server(self, config: MCPServerConfig) -> None:
        """Registra un servidor MCP programáticamente."""
        self._servers[config.name] = config

    def get_server(self, server_name: str) -> MCPServerConfig | None:
        """Obtiene la configuración de un servidor registrado."""
        return self._servers.get(server_name)

    def register_tool(self, tool: MCPToolDefinition) -> None:
        """Registra una herramienta introspeccionada o simulada en memoria."""
        self._tools[tool.qualified_name] = tool
        self._sdk_generator.set_tools(list(self._tools.values()))

    def register_tools(self, tools: Sequence[MCPToolDefinition]) -> None:
        """Registra múltiples herramientas en lote."""
        for t in tools:
            self._tools[t.qualified_name] = t
        self._sdk_generator.set_tools(list(self._tools.values()))

    def get_tool(self, server_name: str, tool_name: str) -> MCPToolDefinition | None:
        """Busca una herramienta por servidor y nombre."""
        qualified = f"{server_name}.{tool_name}"
        return self._tools.get(qualified)

    def get_all_tools(self) -> list[MCPToolDefinition]:
        """Retorna todas las herramientas registradas en el puente."""
        return list(self._tools.values())

    def introspect_server_tools(
        self,
        server_name: str,
        timeout_seconds: float = 5.0,
    ) -> list[MCPToolDefinition]:
        """
        Ejecuta introspección reactiva sobre el servidor MCP mediante `tools/list`.
        Para transporte `stdio`, interactúa mediante JSON-RPC 2.0.
        Para servidores en memoria, utiliza las herramientas previamente registradas.
        """
        server = self._servers.get(server_name)
        if not server:
            raise MCPServerConnectionError(
                f"Servidor MCP '{server_name}' no registrado.",
                i18n_key="common:errors.mcp_server_not_found",
            )

        if not server.enabled:
            return []

        # Si el servidor es en memoria o ya cuenta con herramientas mock registradas
        if server.transport == "in_memory":
            return [t for t in self._tools.values() if t.server_name == server_name]

        # Transporte stdio con JSON-RPC 2.0
        rpc_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }
        cmd = [server.command, *server.args]
        env = {**os.environ, **server.env}

        try:
            proc = subprocess.Popen(  # noqa: S603
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            req_str = json.dumps(rpc_request) + "\n"
            stdout_data, stderr_data = proc.communicate(input=req_str, timeout=timeout_seconds)

            if proc.returncode != 0 and not stdout_data:
                raise MCPServerConnectionError(
                    f"Fallo al ejecutar servidor MCP '{server_name}' (exit code {proc.returncode}): {stderr_data.strip()}",
                    i18n_key="common:errors.mcp_server_crash",
                )

            # Extrae la línea JSON válida de stdout
            discovered_tools: list[MCPToolDefinition] = []
            for line in stdout_data.splitlines():
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    resp = json.loads(line)
                    if resp.get("id") == 1 and "result" in resp:
                        tools_list = resp["result"].get("tools", [])
                        for t_raw in tools_list:
                            t_def = MCPToolDefinition.from_mcp_schema(
                                server_name=server_name,
                                tool_data=t_raw,
                            )
                            self.register_tool(t_def)
                            discovered_tools.append(t_def)
                        break
                except json.JSONDecodeError:
                    continue

            return discovered_tools

        except subprocess.TimeoutExpired as exc:
            proc.kill()
            raise MCPServerConnectionError(
                f"Timeout de introspección excedido ({timeout_seconds}s) para servidor MCP '{server_name}'.",
                i18n_key="common:errors.mcp_server_timeout",
            ) from exc
        except FileNotFoundError as exc:
            raise MCPServerConnectionError(
                f"Comando '{server.command}' no encontrado para servidor MCP '{server_name}'.",
                i18n_key="common:errors.mcp_server_command_not_found",
            ) from exc
        except Exception as exc:
            if isinstance(exc, MCPBridgeError):
                raise
            raise MCPServerConnectionError(
                f"Error inesperado al conectar con servidor MCP '{server_name}': {exc}",
                i18n_key="common:errors.mcp_server_unavailable",
            ) from exc

    def introspect_all(self, timeout_seconds: float = 5.0) -> dict[str, list[MCPToolDefinition]]:
        """Introspecciona todos los servidores MCP habilitados registrados."""
        results: dict[str, list[MCPToolDefinition]] = {}
        for s_name in self._servers:
            try:
                results[s_name] = self.introspect_server_tools(s_name, timeout_seconds=timeout_seconds)
            except MCPBridgeError:
                results[s_name] = []
        return results

    def search_capabilities(self, query: str, limit: int = 5) -> list[dict[str, object]]:
        """
        Búsqueda de capacidades token-minimal (< 150 tokens) sobre el catálogo de herramientas.
        Puntúa concordancias en nombre, descripción, servidor y parámetros.
        """
        norm_query = _normalize_text(query)
        if not norm_query:
            # Si no hay query, retorna las primeras 'limit' herramientas
            all_list = list(self._tools.values())[:limit]
            return [t.to_capability_descriptor() for t in all_list]

        query_tokens = [tok for tok in re.split(r"\W+", norm_query) if len(tok) >= 2]
        scored_tools: list[tuple[float, MCPToolDefinition]] = []

        for tool in self._tools.values():
            score = 0.0
            norm_name = _normalize_text(tool.name)
            norm_desc = _normalize_text(tool.description)
            norm_server = _normalize_text(tool.server_name)
            norm_params = _normalize_text(" ".join(tool.parameters.keys()))

            # 1. Coincidencia exacta o contenida
            if norm_query == norm_name or norm_query == tool.qualified_name.lower():
                score += 50.0
            elif norm_query in norm_name:
                score += 25.0
            elif norm_query in norm_desc:
                score += 15.0

            # 2. Coincidencia por tokens individuales
            for tok in query_tokens:
                if tok == norm_name:
                    score += 20.0
                elif tok in norm_name:
                    score += 10.0
                if tok in norm_server:
                    score += 8.0
                if tok in norm_desc:
                    score += 4.0
                if tok in norm_params:
                    score += 3.0

            if score > 0:
                scored_tools.append((score, tool))

        # Ordenar descendentemente por puntuación
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        return [t.to_capability_descriptor() for _, t in scored_tools[:limit]]

    def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, object],
        timeout_seconds: float = 10.0,
    ) -> object:
        """
        Invoca sincrónicamente una herramienta MCP con sus argumentos.
        Soporta delegación a handler en memoria o invocación JSON-RPC vía stdio.
        """
        tool = self.get_tool(server_name, tool_name)
        if not tool:
            raise MCPToolExecutionError(
                f"Herramienta '{server_name}.{tool_name}' no existe en el catálogo MCP.",
                i18n_key="common:errors.mcp_tool_not_found",
            )

        # 1. Si existe un handler en memoria (testing / adapter)
        if tool.handler is not None:
            try:
                return tool.handler(**arguments)
            except Exception as exc:
                raise MCPToolExecutionError(
                    f"Fallo en ejecución de herramienta '{tool.qualified_name}': {exc}",
                    i18n_key="common:errors.mcp_tool_execution_failed",
                ) from exc

        # 2. Si no hay handler, consultar servidor stdio
        server = self.get_server(server_name)
        if not server:
            raise MCPServerConnectionError(
                f"Servidor '{server_name}' no disponible para ejecutar '{tool_name}'.",
                i18n_key="common:errors.mcp_server_not_found",
            )

        rpc_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        cmd = [server.command, *server.args]
        env = {**os.environ, **server.env}

        try:
            proc = subprocess.Popen(  # noqa: S603
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            req_str = json.dumps(rpc_request) + "\n"
            stdout_data, stderr_data = proc.communicate(input=req_str, timeout=timeout_seconds)

            if proc.returncode != 0 and not stdout_data:
                raise MCPToolExecutionError(
                    f"Servidor MCP '{server_name}' falló al ejecutar '{tool_name}': {stderr_data.strip()}",
                    i18n_key="common:errors.mcp_tool_execution_failed",
                )

            for line in stdout_data.splitlines():
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    resp = json.loads(line)
                    if resp.get("id") == 2:
                        if "error" in resp:
                            err_msg = resp["error"].get("message", "Error desconocido")
                            raise MCPToolExecutionError(
                                f"Error devuelto por servidor MCP '{server_name}': {err_msg}",
                                i18n_key="common:errors.mcp_tool_execution_failed",
                            )
                        result = resp.get("result", {})
                        # MCP standard tools/call devuelve {"content": [{"type": "text", "text": "..."}]}
                        if isinstance(result, dict) and "content" in result:
                            contents = result["content"]
                            if isinstance(contents, list) and len(contents) > 0:
                                first = contents[0]
                                if isinstance(first, dict) and first.get("type") == "text":
                                    raw_text = first.get("text", "")
                                    try:
                                        return json.loads(raw_text)
                                    except json.JSONDecodeError:
                                        return raw_text
                        return result
                except json.JSONDecodeError:
                    continue

            return None

        except subprocess.TimeoutExpired as exc:
            proc.kill()
            raise MCPToolExecutionError(
                f"Timeout de ejecución excedido ({timeout_seconds}s) para herramienta '{tool.qualified_name}'.",
                i18n_key="common:errors.mcp_tool_timeout",
            ) from exc
        except Exception as exc:
            if isinstance(exc, MCPBridgeError):
                raise
            raise MCPToolExecutionError(
                f"Error al ejecutar herramienta '{tool.qualified_name}': {exc}",
                i18n_key="common:errors.mcp_tool_execution_failed",
            ) from exc

    def get_sdk_generator(self) -> DynamicSDKGenerator:
        """Retorna el generador dinámico de SDK sincronizado con las herramientas actuales."""
        self._sdk_generator.set_tools(list(self._tools.values()))
        return self._sdk_generator
