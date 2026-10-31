"""
oppytec-backend/src/core/mcp_bridge/__init__.py
Módulo MCP Dynamic Bridge: Puente de conexión universal para servidores MCP
y generador de SDK para Code Mode.
"""
from __future__ import annotations

from src.core.mcp_bridge.manager import (
    MCPBridgeError,
    MCPBridgeManager,
    MCPServerConnectionError,
    MCPToolExecutionError,
)
from src.core.mcp_bridge.models import (
    MCPServerConfig,
    MCPToolDefinition,
    MCPToolParameter,
    TransportType,
)
from src.core.mcp_bridge.sdk_generator import DynamicSDKGenerator

__all__ = [
    "DynamicSDKGenerator",
    "MCPBridgeError",
    "MCPBridgeManager",
    "MCPServerConfig",
    "MCPServerConnectionError",
    "MCPToolDefinition",
    "MCPToolExecutionError",
    "MCPToolParameter",
    "TransportType",
]
