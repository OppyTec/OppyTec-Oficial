"""
oppytec-backend/src/core/sandbox/runner.py
CodeModeSandboxRunner: Motor de ejecución segura y aislada en memoria para scripts de Code Mode.
Implementa:
1. Aislamiento estricto de OS y Red (AST validator + builtins restringidos).
2. Watchdog de tiempo de ejecución (timeout de 3.0s configurable).
3. Inyección inmutable del contexto Multi-Tenant (`tenant_*`) y verificación anti-IDOR Cross-Tenant.
4. Verificación de permisos RBAC de 3 niveles (`<modulo>.<submodulo>.<funcion>`).
5. 'Hard-Code Data Stripping': Redacción física de columnas y campos de costo/márgenes si no tiene permisos.
6. Estimación de reducción de tokens (FinOps telemetría).
"""
from __future__ import annotations

import ast
import contextlib
import datetime
import decimal
import io
import json
import math
import re
import sys
import threading
import time
import types
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal

from src.core.exceptions import CrossTenantAccessError
from src.core.mcp_bridge.manager import MCPBridgeManager
from src.core.sandbox.models import (
    SandboxContext,
    SandboxExecutionError,
    SandboxExecutionResult,
    SandboxSecurityError,
    SandboxTimeoutError,
)

FORBIDDEN_IMPORT_MODULES = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "socket",
        "shutil",
        "urllib",
        "requests",
        "httpx",
        "aiohttp",
        "posix",
        "nt",
        "threading",
        "multiprocessing",
        "ctypes",
        "pickle",
        "shelve",
        "importlib",
        "builtins",
        "site",
        "inspect",
        "pty",
        "fcntl",
    }
)

ALLOWED_IMPORT_MODULES = frozenset({"math", "json", "datetime", "decimal"})

FORBIDDEN_ATTRIBUTES = frozenset(
    {
        "__subclasses__",
        "__globals__",
        "__code__",
        "__class__",
        "__builtins__",
        "__import__",
        "__dict__",
        "__bases__",
        "__mro__",
        "__qualname__",
        "gi_frame",
        "f_globals",
        "f_locals",
        "f_builtins",
        "cr_frame",
    }
)

FORBIDDEN_BUILTIN_NAMES = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "open",
        "input",
        "breakpoint",
        "help",
        "exit",
        "quit",
        "__import__",
        "globals",
        "locals",
        "vars",
    }
)

SENSITIVE_COST_KEYS = frozenset(
    {
        "costo_unitario",
        "costo_neto",
        "costo_total",
        "costo_receta",
        "costo_total_merma",
        "costo_teorico_clp",
        "costo_real_clp",
        "precio_compra",
        "last_purchase_price",
        "historical_avg_price",
        "total_neto",
        "total_bruto_clp",
        "subtotal_neto",
        "iva_clp",
        "total_draft_neto_clp",
        "total_draft_bruto_clp",
        "total_estimated_reorder_cost",
        "total_at_risk_cost",
        "total_shortage_cost_neto",
        "margen",
        "margen_bruto",
        "unit_cost",
        "total_cost",
        "purchase_price",
        "profit_margin",
        "food_cost_amount",
        "ventas_totales_clp",
        "ticket_promedio_clp",
        "gasto_total",
        "total_monetario",
        "monto_total",
    }
)

REDACTED_COST_MARKER = "[REDACTED_COST]"
CROSS_TENANT_REGEX = re.compile(r"\b(tenant_[a-z0-9_]+)\b", re.IGNORECASE)


def strip_sensitive_cost_data(val: object) -> object:
    """
    Filtro recursivo de Hard-Code Data Stripping.
    Redacta en código duro todos los campos financieros/costos cuando el usuario carece de permiso.
    """
    if isinstance(val, Mapping):
        clean_dict: dict[str, object] = {}
        for k, v in val.items():
            k_lower = str(k).lower()
            is_sensitive = k_lower in SENSITIVE_COST_KEYS or any(
                token in k_lower
                for token in (
                    "costo",
                    "cost",
                    "margen",
                    "margin",
                    "precio",
                    "price",
                    "gasto",
                    "monetario",
                    "monto",
                    "tarifa",
                    "fee",
                    "presupuesto",
                )
            )
            if is_sensitive:
                clean_dict[k] = REDACTED_COST_MARKER
            else:
                clean_dict[k] = strip_sensitive_cost_data(v)
        return clean_dict

    if isinstance(val, (list, tuple)):
        return [strip_sensitive_cost_data(item) for item in val]

    return val


def _safe_import(
    name: str,
    globals_: Mapping[str, object] | None = None,
    locals_: Mapping[str, object] | None = None,
    fromlist: Sequence[str] = (),
    level: int = 0,
) -> object:
    """Función de importación acotada para el sandbox que bloquea módulos del SO."""
    top_level = name.split(".")[0]
    if top_level not in ALLOWED_IMPORT_MODULES:
        raise SandboxSecurityError(
            f"Importación prohibida en sandbox: '{name}'. Solo se permiten: {sorted(ALLOWED_IMPORT_MODULES)}",
            i18n_key="sandbox:errors.import_prohibited",
        )
    return __import__(name, globals_, locals_, fromlist, level)


class CodeModeSandboxRunner:
    """
    Ejecutor hermético para código generado por LLM con orquestación Code Mode sobre MCP.
    """

    def __init__(
        self,
        bridge_manager: MCPBridgeManager | None = None,
        timeout_seconds: float = 3.0,
        max_memory_mb: int = 64,
        max_ast_nodes: int = 2000,
    ) -> None:
        self.bridge_manager = bridge_manager or MCPBridgeManager(auto_load=False)
        self.timeout_seconds = timeout_seconds
        self.max_memory_mb = max_memory_mb
        self.max_ast_nodes = max_ast_nodes

    def _validate_ast(self, tree: ast.AST) -> None:
        """
        Valida que el AST del script no contenga nodos prohibidos
        ni supere la cuota de instrucciones/nodos.
        """
        for node_count, node in enumerate(ast.walk(tree), start=1):
            if node_count > self.max_ast_nodes:
                raise SandboxSecurityError(
                    f"Script supera el límite máximo de nodos AST ({self.max_ast_nodes}).",
                    i18n_key="sandbox:errors.ast_bomb_detected",
                )

            # 1. Prohibir importaciones no autorizadas
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod_name = alias.name.split(".")[0]
                    if mod_name not in ALLOWED_IMPORT_MODULES:
                        raise SandboxSecurityError(
                            f"Importación no autorizada del módulo '{alias.name}'.",
                            i18n_key="sandbox:errors.import_prohibited",
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mod_name = node.module.split(".")[0]
                    if mod_name not in ALLOWED_IMPORT_MODULES:
                        raise SandboxSecurityError(
                            f"Importación no autorizada de '{node.module}'.",
                            i18n_key="sandbox:errors.import_prohibited",
                        )

            # 2. Prohibir acceso a atributos mágicos/privados
            elif isinstance(node, ast.Attribute):
                attr = node.attr
                if attr.startswith("__") or attr in FORBIDDEN_ATTRIBUTES:
                    raise SandboxSecurityError(
                        f"Acceso prohibido al atributo privado o dunder '{attr}'.",
                        i18n_key="sandbox:errors.attribute_access_prohibited",
                    )

            # 3. Prohibir invocación directa de built-ins peligrosos
            elif isinstance(node, ast.Name):
                name = node.id
                if name in FORBIDDEN_BUILTIN_NAMES:
                    raise SandboxSecurityError(
                        f"Uso de función nativa prohibida '{name}'.",
                        i18n_key="sandbox:errors.builtin_prohibited",
                    )

    def _create_sandboxed_caller(
        self,
        context: SandboxContext,
        raw_tokens_tracker: list[int],
    ) -> Callable[[str, str, dict[str, object]], object]:
        """
        Crea el middleware de intercepción de llamadas a herramientas MCP.
        Aplica RBAC 3-niveles, bloqueo Anti-IDOR Cross-Tenant y Hard-Code Data Stripping.
        """

        def _caller(server_name: str, tool_name: str, arguments: dict[str, object]) -> object:
            tool_def = self.bridge_manager.get_tool(server_name, tool_name)
            if not tool_def:
                raise SandboxExecutionError(
                    f"Herramienta '{server_name}.{tool_name}' no existe en el catálogo MCP.",
                    i18n_key="sandbox:errors.tool_not_found",
                )

            # 1. Guardia de RBAC 3-niveles
            if tool_def.required_permission:
                context.check_permission_or_raise(tool_def.required_permission)

            # 2. Guardia Anti-IDOR Cross-Tenant
            # Escanea argumentos de tipo string buscando menciones de otros tenants
            for arg_v in arguments.values():
                if isinstance(arg_v, str):
                    for match in CROSS_TENANT_REGEX.finditer(arg_v):
                        found_tenant = match.group(1).lower()
                        if found_tenant != context.tenant_id.lower():
                            raise CrossTenantAccessError(
                                f"Cross-tenant access violation: El script intentó consultar '{found_tenant}', "
                                f"pero el contexto activo pertenece a '{context.tenant_id}'.",
                                i18n_key="tenancy:errors.cross_tenant_forbidden",
                            )

            # Forzar o inyectar el tenant_id activo si la herramienta lo admite
            args_with_tenant = dict(arguments)
            if "tenant_id" in tool_def.parameters:
                args_with_tenant["tenant_id"] = context.tenant_id

            # 3. Invocar herramienta en el puente MCP
            raw_output = self.bridge_manager.call_tool(server_name, tool_name, args_with_tenant)

            # 4. Rastrear tokens crudos para cálculo de ahorro FinOps
            try:
                serialized = json.dumps(raw_output, default=str)
                raw_tokens_tracker[0] += max(1, len(serialized) // 4)
            except (TypeError, ValueError):
                pass

            # 5. Hard-Code Data Stripping en la entrada de datos al script
            has_financial_access = context.can_view_costs or context.has_permission("finanzas.costos.ver")
            if not has_financial_access:
                return strip_sensitive_cost_data(raw_output)

            return raw_output

        return _caller

    def _prepare_safe_builtins(self) -> dict[str, object]:
        """Construye un diccionario de built-ins desinfectado para el runtime."""
        safe_builtins: dict[str, object] = {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "filter": filter,
            "float": float,
            "int": int,
            "isinstance": isinstance,
            "len": len,
            "list": list,
            "map": map,
            "max": max,
            "min": min,
            "print": print,
            "range": range,
            "round": round,
            "set": set,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "zip": zip,
            "math": math,
            "datetime": datetime,
            "json": json,
            "Decimal": Decimal,
            "decimal": decimal,
            "__import__": _safe_import,
        }
        return safe_builtins

    def execute(
        self,
        code: str,
        context: SandboxContext,
    ) -> SandboxExecutionResult:
        """
        Ejecuta un script en el sandbox aislado con protección de timeout y control de excepciones.
        """
        start_time = time.perf_counter()
        raw_tokens_tracker: list[int] = [0]

        # 1. Parsear y validar sintaxis y seguridad AST
        try:
            tree = ast.parse(code)
            self._validate_ast(tree)
        except SyntaxError as syn_err:
            return SandboxExecutionResult(
                success=False,
                error=f"Error de sintaxis en script: {syn_err}",
                error_code="SYNTAX_ERROR",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        except SandboxSecurityError as sec_err:
            return SandboxExecutionResult(
                success=False,
                error=sec_err.message,
                error_code=sec_err.error_code,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 2. Construir SDK tipado y namespace de ejecución
        caller_fn = self._create_sandboxed_caller(context, raw_tokens_tracker)
        sdk_generator = self.bridge_manager.get_sdk_generator()
        sandbox_namespace = sdk_generator.build_sandbox_namespace(caller_fn)

        safe_builtins = self._prepare_safe_builtins()

        execution_globals: dict[str, object] = {
            "__builtins__": safe_builtins,
            "tenant_id": context.tenant_id,
            "user_id": context.user_id,
            "math": math,
            "datetime": datetime,
            "json": json,
            "Decimal": Decimal,
            **sandbox_namespace,
            **context.extra_env,
        }

        # 3. Preparar transformación para soportar tanto `return`, `result = ...`, o expresión final
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(tree))

        stdout_buffer = io.StringIO()
        result_holder: list[object] = [None]
        error_holder: list[Exception | None] = [None]

        def _worker() -> None:
            max_steps = 1_000_000
            step_count = 0

            def _step_tracer(_frame: types.FrameType, _event: str, _arg: object) -> object:
                nonlocal step_count
                step_count += 1
                if step_count > max_steps:
                    raise SandboxTimeoutError(
                        f"Timeout de ejecución excedido: Límite de {max_steps} instrucciones superado."
                    )
                return _step_tracer

            sys.settrace(_step_tracer)  # type: ignore[arg-type]
            with contextlib.redirect_stdout(stdout_buffer):
                try:
                    local_scope: dict[str, object] = {}
                    if has_return:
                        # Envolver el script en una función para capturar el retorno directo
                        indented = "\n".join("    " + line for line in code.splitlines())
                        wrapped_code = f"def __sandbox_main__():\n{indented}\n__result__ = __sandbox_main__()"
                        compiled = compile(wrapped_code, "<sandbox>", "exec")
                        exec(compiled, execution_globals, local_scope)  # noqa: S102
                        result_holder[0] = local_scope.get("__result__")
                    else:
                        # Si no hay return, evaluar o extraer 'result'
                        compiled = compile(code, "<sandbox>", "exec")
                        exec(compiled, execution_globals, local_scope)  # noqa: S102
                        if "result" in local_scope:
                            result_holder[0] = local_scope["result"]
                        else:
                            # Si termina en expresión aislada
                            if tree.body and isinstance(tree.body[-1], ast.Expr):
                                expr_code = compile(
                                    ast.Expression(tree.body[-1].value),
                                    "<sandbox_expr>",
                                    "eval",
                                )
                                result_holder[0] = eval(expr_code, execution_globals, local_scope)  # noqa: S307
                except Exception as exc:
                    error_holder[0] = exc
                finally:
                    sys.settrace(None)

        # 4. Ejecutar con Watchdog en hilo daemon
        worker_thread = threading.Thread(target=_worker, daemon=True)
        worker_thread.start()
        worker_thread.join(timeout=self.timeout_seconds)

        if worker_thread.is_alive():
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return SandboxExecutionResult(
                success=False,
                stdout=stdout_buffer.getvalue(),
                execution_time_ms=elapsed_ms,
                error=f"Timeout de ejecución excedido ({self.timeout_seconds}s).",
                error_code="SANDBOX_TIMEOUT_EXCEEDED",
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        stdout_output = stdout_buffer.getvalue()

        # 5. Manejar posibles excepciones durante el script
        if error_holder[0] is not None:
            exc = error_holder[0]
            err_code = getattr(exc, "error_code", "SCRIPT_EXECUTION_ERROR")
            err_msg = str(getattr(exc, "message", str(exc)))
            return SandboxExecutionResult(
                success=False,
                stdout=stdout_output,
                execution_time_ms=elapsed_ms,
                error=err_msg,
                error_code=err_code,
            )

        final_res = result_holder[0]

        # 6. Hard-Code Data Stripping en el resultado final sintetizado
        has_financial_access = context.can_view_costs or context.has_permission("finanzas.costos.ver")
        if not has_financial_access:
            final_res = strip_sensitive_cost_data(final_res)

        # 7. Métricas FinOps de tokens ahorrados
        try:
            final_tokens = max(1, len(json.dumps(final_res, default=str)) // 4)
        except Exception:
            final_tokens = 5

        raw_tokens = raw_tokens_tracker[0]
        tokens_saved = max(0, raw_tokens - final_tokens)

        return SandboxExecutionResult(
            success=True,
            result=final_res,
            stdout=stdout_output,
            execution_time_ms=elapsed_ms,
            raw_tokens_estimate=raw_tokens,
            final_tokens_estimate=final_tokens,
            tokens_saved_estimate=tokens_saved,
        )
