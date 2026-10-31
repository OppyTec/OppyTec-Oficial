"""
oppytec-backend/src/core/mcp_bridge/sdk_generator.py
Generador dinámico de SDK tipado y proxies de ejecución en memoria para el runtime del sandbox.
Convierte introspecciones MCP en namespaces Python seguros que pueden invocarse directamente.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence

from src.core.mcp_bridge.models import MCPToolDefinition


class _ToolProxy:
    """Wrapper de llamada dinámico para una herramienta MCP específica."""

    def __init__(
        self,
        server_name: str,
        tool_def: MCPToolDefinition,
        caller_fn: Callable[[str, str, dict[str, object]], object],
    ) -> None:
        self._server_name = server_name
        self._tool_def = tool_def
        self._caller_fn = caller_fn
        self.__name__ = tool_def.name
        self.__doc__ = f"{tool_def.description}\nFirma: {tool_def.get_python_signature()}"

    def __call__(self, *args: object, **kwargs: object) -> object:
        param_names = list(self._tool_def.parameters.keys())
        merged_args: dict[str, object] = {}

        for idx, val in enumerate(args):
            if idx < len(param_names):
                merged_args[param_names[idx]] = val
            else:
                merged_args[f"arg_{idx}"] = val

        merged_args.update(kwargs)
        return self._caller_fn(self._server_name, self._tool_def.name, merged_args)

    def __repr__(self) -> str:
        return f"<MCPToolProxy {self._tool_def.qualified_name}>"


class _ServerProxy:
    """Proxy de servidor que expone sus herramientas como métodos invocables."""

    def __init__(
        self,
        server_name: str,
        tools: dict[str, MCPToolDefinition],
        caller_fn: Callable[[str, str, dict[str, object]], object],
    ) -> None:
        self._server_name = server_name
        self._tools = dict(tools)
        self._caller_fn = caller_fn
        self._proxies: dict[str, _ToolProxy] = {
            t_name: _ToolProxy(server_name, t_def, caller_fn)
            for t_name, t_def in tools.items()
        }

    def __getattr__(self, name: str) -> object:
        if name.startswith("_"):
            raise AttributeError(f"Private access to '{name}' is forbidden.")
        if name in self._proxies:
            return self._proxies[name]
        raise AttributeError(
            f"El servidor MCP '{self._server_name}' no expone la herramienta '{name}'. "
            f"Herramientas disponibles: {list(self._proxies.keys())}"
        )

    def __getitem__(self, name: str) -> object:
        return self.__getattr__(name)

    def __repr__(self) -> str:
        return f"<MCPServerProxy '{self._server_name}' tools={list(self._proxies.keys())}>"

    def list_tools(self) -> list[str]:
        """Retorna los nombres de herramientas registradas para este servidor."""
        return sorted(self._proxies.keys())


class _OppyRootProxy:
    """Namespace raíz unificado `oppy` dentro del sandbox (`oppy.<server>.<tool>()`)."""

    def __init__(
        self,
        server_proxies: dict[str, _ServerProxy],
        all_tools: dict[str, MCPToolDefinition],
        caller_fn: Callable[[str, str, dict[str, object]], object],
    ) -> None:
        self._servers = dict(server_proxies)
        self._all_tools = dict(all_tools)
        self._caller_fn = caller_fn
        self.tools = {
            q_name: _ToolProxy(t_def.server_name, t_def, caller_fn)
            for q_name, t_def in all_tools.items()
        }

    def __getattr__(self, name: str) -> object:
        if name.startswith("_"):
            raise AttributeError(f"Private access to '{name}' is forbidden.")
        if name in self._servers:
            return self._servers[name]
        raise AttributeError(
            f"Servidor MCP '{name}' no registrado en `oppy`. "
            f"Servidores disponibles: {list(self._servers.keys())}"
        )

    def __getitem__(self, name: str) -> object:
        return self.__getattr__(name)

    def __repr__(self) -> str:
        return f"<OppySandboxSDK servers={list(self._servers.keys())}>"


class DynamicSDKGenerator:
    """Generador dinámico de definiciones tipadas y proxies ejecutables para sandbox."""

    def __init__(self, tools: Sequence[MCPToolDefinition] | None = None) -> None:
        self._tools: list[MCPToolDefinition] = list(tools or [])

    def set_tools(self, tools: Sequence[MCPToolDefinition]) -> None:
        """Actualiza el conjunto de herramientas disponibles para generar el SDK."""
        self._tools = list(tools)

    def generate_python_signatures(self) -> str:
        """
        Genera stubs tipados Python (PEP 484) legibles por el LLM o IDE
        con las herramientas y firmas disponibles.
        """
        if not self._tools:
            return "# No MCP tools registered in SDK\n"

        lines: list[str] = [
            "# --- OppyTec Code Mode Dynamic SDK Type Stubs ---",
            "from typing import Any\n",
        ]

        by_server: dict[str, list[MCPToolDefinition]] = {}
        for tool in self._tools:
            by_server.setdefault(tool.server_name, []).append(tool)

        for server_name, server_tools in sorted(by_server.items()):
            class_name = f"{server_name.capitalize()}Namespace"
            lines.append(f"class {class_name}:")
            for tool in server_tools:
                sig = tool.get_python_signature()
                parts = sig.split("(", 1)
                func_name = tool.name
                params = parts[1] if len(parts) > 1 else ") -> object"
                method_params = f"self{params}" if params.startswith(")") else f"self, {params}"
                lines.append(f"    def {func_name}({method_params}:")
                doc = tool.description or f"Tool {tool.qualified_name}"
                lines.append(f'        """{doc}"""')
                lines.append("        ...\n")

        lines.append("class OppySDK:")
        for server_name in sorted(by_server.keys()):
            class_name = f"{server_name.capitalize()}Namespace"
            lines.append(f"    {server_name}: {class_name}")

        lines.append("\noppy: OppySDK")
        return "\n".join(lines)

    def build_sandbox_namespace(
        self,
        caller_fn: Callable[[str, str, dict[str, object]], object],
    ) -> dict[str, object]:
        """
        Construye el namespace inyectable en las variables globales del Sandbox.
        Permite invocar tanto `oppy.<server>.<tool>(...)` como `<server>.<tool>(...)`.
        """
        by_server: dict[str, dict[str, MCPToolDefinition]] = {}
        all_tools_by_qualified: dict[str, MCPToolDefinition] = {}

        for tool in self._tools:
            by_server.setdefault(tool.server_name, {})[tool.name] = tool
            all_tools_by_qualified[tool.qualified_name] = tool

        server_proxies: dict[str, _ServerProxy] = {}
        for server_name, tools_dict in by_server.items():
            server_proxies[server_name] = _ServerProxy(server_name, tools_dict, caller_fn)

        oppy_root = _OppyRootProxy(server_proxies, all_tools_by_qualified, caller_fn)

        namespace: dict[str, object] = {
            "oppy": oppy_root,
            "mcp": oppy_root,
        }
        for s_name, s_proxy in server_proxies.items():
            namespace[s_name] = s_proxy

        return namespace
