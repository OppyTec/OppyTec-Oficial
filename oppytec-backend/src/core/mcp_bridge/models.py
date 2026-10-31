"""
oppytec-backend/src/core/mcp_bridge/models.py
Modelos y estructuras de datos tipadas para el puente universal MCP (Model Context Protocol).
Soporta transporte stdio, SSE y en memoria, e introspección reactiva de herramientas (Code Mode).
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

TransportType = Literal["stdio", "sse", "in_memory"]


class MCPServerConfig(BaseModel):  # type: ignore[explicit-any]
    """Configuración de conexión y transporte para un servidor MCP."""

    name: str = Field(..., description="Identificador único del servidor MCP (ej. 'postgres', 'cloudflare_r2')")
    command: str = Field(default="npx", description="Comando ejecutable para transporte stdio")
    args: list[str] = Field(default_factory=list, description="Argumentos de línea de comandos")
    env: dict[str, str] = Field(default_factory=dict, description="Variables de entorno específicas")
    transport: TransportType = Field(default="stdio", description="Protocolo de transporte MCP")
    url: str | None = Field(default=None, description="URL endpoint para transporte SSE o HTTP")
    enabled: bool = Field(default=True, description="Si el servidor está habilitado")
    description: str = Field(default="", description="Descripción legible del servicio provisto")

    model_config = {
        "extra": "ignore",
    }


@dataclass(frozen=True)
class MCPToolParameter:
    """Parámetro individual de una herramienta MCP introspeccionada."""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    default: object = None


@dataclass(frozen=True)
class MCPToolDefinition:  # type: ignore[explicit-any]
    """Definición introspeccionada de una herramienta MCP."""

    server_name: str
    name: str
    qualified_name: str
    description: str
    parameters: dict[str, object] = field(default_factory=dict)
    required_parameters: tuple[str, ...] = field(default_factory=tuple)
    handler: Callable[..., object] | None = None  # type: ignore[explicit-any]
    required_permission: str | None = None
    return_schema: dict[str, object] | None = None

    @classmethod
    def from_mcp_schema(  # type: ignore[explicit-any]
        cls,
        *,
        server_name: str,
        tool_data: dict[str, object],
        handler: Callable[..., object] | None = None,
        required_permission: str | None = None,
    ) -> MCPToolDefinition:
        """Crea una definición a partir del esquema JSON estándar devuelto por `tools/list`."""
        name = str(tool_data.get("name", "")).strip()
        description = str(tool_data.get("description", "")).strip()
        raw_input = tool_data.get("inputSchema", {})
        input_schema: dict[str, object] = raw_input if isinstance(raw_input, dict) else {}
        raw_props = input_schema.get("properties", {})
        properties: dict[str, object] = raw_props if isinstance(raw_props, dict) else {}
        raw_req = input_schema.get("required", [])
        required = tuple(str(x) for x in raw_req) if isinstance(raw_req, list) else ()
        qualified = f"{server_name}.{name}"

        return cls(
            server_name=server_name,
            name=name,
            qualified_name=qualified,
            description=description,
            parameters=dict(properties),
            required_parameters=required,
            handler=handler,
            required_permission=required_permission,
        )

    def get_python_signature(self) -> str:
        """Genera una firma tipada estilo Python para la herramienta."""
        type_mapping = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "list[object]",
            "object": "dict[str, object]",
        }
        arg_parts: list[str] = []
        for prop_name, prop_meta in self.parameters.items():
            raw_type = prop_meta.get("type", "string") if isinstance(prop_meta, dict) else "string"
            py_type = type_mapping.get(str(raw_type), "object")
            is_req = prop_name in self.required_parameters
            if is_req:
                arg_parts.append(f"{prop_name}: {py_type}")
            else:
                arg_parts.append(f"{prop_name}: {py_type} | None = None")

        args_str = ", ".join(arg_parts)
        safe_func_name = re.sub(r"[^a-zA-Z0-9_]", "_", self.qualified_name)
        return f"{safe_func_name}({args_str}) -> object"

    def to_capability_descriptor(self) -> dict[str, object]:
        """
        Produce un descriptor ultracompacto (< 150 tokens) para el catálogo
        de `search_capabilities()`, minimizando la saturación de contexto del LLM.
        """
        compact_params: dict[str, dict[str, object]] = {}
        for prop_name, prop_meta in self.parameters.items():
            if isinstance(prop_meta, dict):
                compact_params[prop_name] = {
                    "type": prop_meta.get("type", "string"),
                    "description": prop_meta.get("description", ""),
                    "required": prop_name in self.required_parameters,
                }
            else:
                compact_params[prop_name] = {
                    "type": "string",
                    "description": "",
                    "required": prop_name in self.required_parameters,
                }

        return {
            "server": self.server_name,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "description": self.description,
            "parameters": compact_params,
            "required": list(self.required_parameters),
            "signature": self.get_python_signature(),
        }
