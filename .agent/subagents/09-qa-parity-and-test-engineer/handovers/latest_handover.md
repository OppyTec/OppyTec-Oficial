# Reporte de Traspaso (`Handover`) — Agente 09: QA, Parity & Test Engineer

- **Fecha UTC:** 2026-10-31T22:45:00Z
- **Agente:** Agente 09 (`09-qa-parity-and-test-engineer`)
- **Fase / Hito:** Fase 4 del Plan Maestro "Code Mode sobre MCP" (`.agent/Planes-Maestros/PLAN_MAESTRO_CODE_MODE_MCP.md`): "Certificación de Calidad 5D y Auditoría Red Team del Sandbox de Code Mode".
- **Estado de Certificación:** `CODE_MODE_STAGE4_QUALITY_AND_REDTEAM_CERTIFIED` (100% verde: 89/89 tests ofensivos Red Team, 44/44 tests unitarios de Code Mode y 29/29 tests de arquitectura aprobados; cero fugas multi-tenant, zero bypass a Hard-Code Data Stripping, Watchdog DoS estricto y telemetría FinOps verificada).

---

## 1. Completed (Qué se ejecutó y validó)

1. **Creación de la Suite Ofensiva Red Team en `oppytec-backend/tests/security_redteam/test_17_code_mode_sandbox_security.py`:**
   - **Vector 1: Intento de escape de sandbox mediante introspección dunder:**
     - 11 payloads de introspección dunder (`().__class__.__bases__[0].__subclasses__()`, `''.__class__.__mro__`, `(lambda: None).__globals__`, `__code__`, `__dict__`, etc.) bloqueados en seco por el validador AST con `SANDBOX_SECURITY_VIOLATION`.
     - 11 llamadas a built-ins reflexivos peligrosos (`globals()`, `locals()`, `vars()`, `eval()`, `exec()`, `open()`, `breakpoint()`, etc.) bloqueadas deterministamente.
     - Pruebas de integración contra `OppyfyCodeModeService` verificando respuestas estructuradas sin filtración de datos y con registro forense.
   - **Vector 2: Intento de evasión e inyección de módulos del SO:**
     - 17 payloads de importación directa y de terceros (`os`, `sys`, `subprocess`, `shutil`, `socket`, `posix`, `ctypes`, `requests`, `httpx`, `pickle`, `importlib`, etc.) rechazados antes de ejecución.
     - Intercepción hermética tanto en nivel sintáctico AST como en el built-in protegido `_safe_import`.
     - Verificación de ejecución autorizada de módulos seguros (`math`, `json`, `datetime`, `decimal.Decimal`).
   - **Vector 3: Ataque DoS por bucle infinito y disparo de timeout (watchdog):**
     - Bucle infinito `while True: pass` cortado por el watchdog (timeout configurado) arrojando `SANDBOX_TIMEOUT_EXCEEDED` en < 0.3s.
     - Bucle de alta frecuencia interceptado por el limitador de 1.000.000 instrucciones de `sys.settrace`.
     - Captura adecuada de `stdout` previo al corte forzado.
   - **Vector 4: Bomba AST (scripts con más de 2000 nodos AST para agotar memoria):**
     - Expresiones con más de 2500 nodos AST y scripts con más de 2100 sentencias rechazados con `SANDBOX_SECURITY_VIOLATION` antes de compilar.
     - Scripts analíticos legítimos (< 2000 nodos) ejecutados exitosamente.
   - **Vector 5: Intento de IDOR Cross-Tenant (`tenant_competitor` inyectado):**
     - Sentencias SQL con inyección de esquemas ajenos (`tenant_competitor.finanzas`) detectadas por regex y abortadas con `CROSS_TENANT_ACCESS_VIOLATION`.
     - Inyección en argumentos de herramientas MCP (`tenant_id`, almacenamiento de archivos en Cloudflare R2 con menciones inter-inquilino) bloqueadas.
     - Autorización legítima confirmada cuando el script referencia explícitamente el `tenant_id` activo propio.
   - **Vector 6: Evasión de Hard-Code Data Stripping:**
     - Redacción física recursiva a `"[REDACTED_COST]"` en lectura directa de columnas financieras (`costo_unitario`, `costo_total`, `margen_bruto`, `precio_compra`, `food_cost_amount`).
     - Evasión por renombramiento de claves / asignación de variables frustrada: el valor subyacente sigue redactado.
     - Operaciones aritméticas sobre costos redactados explotan con `TypeError`, garantizando confidencialidad.
     - Doble barrera de stripping: a la entrada de datos MCP y a la salida final sintetizada.
     - Administradores financieros con `can_view_costs=True` reciben los valores numéricos intactos.
   - **Vector 7: Invocación de herramientas MCP con permisos RBAC no concedidos:**
     - Invocaciones a herramientas de DML (`postgres.execute_dml`) y facturación (`sii_billing.emit_invoice`) rechazadas con `RBAC_PERMISSION_DENIED` si faltan `base_datos.modificar` o `facturacion.emitir`.
     - Verificación de jerarquía RBAC de 3 niveles con comodines (`inventario.*`).
     - Rol Superuser God autorizado para invocar cualquier herramienta MCP.
   - **Vector 8: Búsqueda de capacidades con consultas maliciosas (SQLi / Prompt Injection):**
     - 7 payloads SQLi (`' OR '1'='1' --`, `'; DROP TABLE...`, etc.) procesados herméticamente en memoria con scoring de similitud sin tocar motores SQL.
     - 6 payloads de Prompt Injection / XSS / SSTI manejados sin efectos colaterales.
     - Garantía estricta de descriptores token-minimal (< 150 tokens / < 600 bytes JSON).
   - **Vector 9: Telemetría de tokens en `llm_request_logs` con medición de `tokens_saved`:**
     - Reducción analítica masiva en memoria: 3 filas a 1 resumen reduce el volumen en > 75%, registrando `tokens_saved_estimate > 0`.
     - Verificación de emisión de `LlmUsageRecord` en `InMemoryTelemetrySink` con metadatos de linaje (`holding_id`, `tenant_id`, `user_id`, `caller_feature='oppyfy_code_mode'`, `engine_tier='SYSTEM_2_LLM'`).
     - Intentos de ataque generan registro forense en bitácora con `api_success=False` y mensaje de error.
   - **Vector 10: Integridad referencial de esquemas y retornos inmutables:**
     - Estructuras `@dataclass(frozen=True)` (`SandboxContext`, `SandboxExecutionResult`, `OppyfyCodeModeExecutionResult`) inmutables contra manipulación maliciosa.
     - Validación estricta de formato `tenant_[a-z0-9_]+` rechazando inyecciones SQL y caracteres no alfanuméricos.
     - Idempotencia del filtro `strip_sensitive_cost_data`.
     - Control estricto de referencias en el SDK tipado (`AttributeError` ante herramientas no registradas).

2. **Resultados de Ejecución de Suites:**
   - `pytest oppytec-backend/tests/security_redteam/test_17_code_mode_sandbox_security.py`: **89/89 pasados (100%) en 0.77s**.
   - `pytest oppytec-backend/tests/unit/core/test_mcp_bridge.py oppytec-backend/tests/unit/core/test_sandbox_runner.py oppytec-backend/tests/unit/modules/test_oppyfy_code_mode.py`: **44/44 pasados (100%) en 0.33s**.
   - `pytest oppytec-backend/tests/architecture/`: **29/29 pasados (100%) en 1.37s**.
   - Total acumulado: **162 tests ejecutados y aprobados con 0 fallos**.

3. **Sincronización del Grafo de Arquitectura Graphify:**
   - Comando: `python scripts/harness.py sync-graph`
   - Resultado: 97 nodos y 116 aristas sincronizados exitosamente en `docs/architecture/graphify/graph.json` y `visualizer.html`.

---

## 2. Friction & Failures (Qué cuidar)

- **Intercepción de __import__ en Tiempo de Compilación AST vs Runtime:** `__import__` está listado en `FORBIDDEN_BUILTIN_NAMES`. Cualquier script que intente usar la función sintáctica `__import__('...')` es interceptado de raíz por el `ast.walk` en `_validate_ast` arrojando `SANDBOX_SECURITY_VIOLATION` antes de evaluar el runtime. La función `_safe_import` actúa como segunda línea de defensa para cargas internas o invocadas indirectamente.
- **Micro-segundos de Ejecución en Bucles de Alta Frecuencia:** El step tracer de `sys.settrace` con cuota de 1.000.000 instrucciones detiene bucles `while True: pass` en aproximadamente 120ms en CPUs modernas, abortando la ejecución antes de alcanzar el timeout de pared (wall-clock) de 300ms, lo cual representa una protección óptima contra DoS.

---

## 3. Next Exact Action (Siguiente paso exacto)

- Fase 4 completada y certificada al 100%.
- Proceder a la Fase 5: Gobernanza, OpenSpec Bipartito (`specs/engineering-code/mcp-code-mode-bridge.spec.md`, `specs/business-domain/oppyfy-operational-intelligence.business.spec.md`) y sincronización documental a cargo de `12-tech-writer-openspec-archify`.
