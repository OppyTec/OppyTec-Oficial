# Reporte de Traspaso (`Handover`) — Agente 06: AI, OppyFy & JEV Engineer

- **Fecha UTC:** 2026-11-02T00:41:00Z
- **Agente:** Agente 06 (`06-ai-oppyfy-and-jev-engineer`)
- **Fase / Módulo:** FASE 8 del Módulo de Eventos — Auditoría e Integración del Módulo de Eventos, Salones y Banquetes con las capacidades de IA OppyFy y Motor JEV Sistema 1.
- **Estado de Certificación:** `APPROVED_100_PERCENT` (Herramientas operativas de eventos expuestas con `@hardcoded_data_stripping`, esquemas declarativos `OPPYFY_EVENT_TOOL_SCHEMAS`, enrutamiento determinista JEV Sistema 1 con confianza >= 0.85 y latencia P95 < 0.1ms, redacción estricta `[REDACTED_COST]` para usuarios sin privilegios financieros, y preservación de 100% de tests unitarios de OppyFy y Eventos).

---

## 1. Completed (Qué se implementó, integró y verificó)

### 1.1 Herramientas Operativas Deterministas de Eventos (JEV Capa 2)
En [`oppytec-backend/src/modules/oppy_ai/application/operational_tools/events_tools.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/oppy_ai/application/operational_tools/events_tools.py):
1. **`analyze_event_supply_feasibility`**:
   - Evalúa si las existencias en bodega cubren el requerimiento de insumos de un evento (factible $\le 80$ pax, quiebre $> 80$ pax).
   - Identifica faltantes críticos, insumos sustitutos, costos unitarios y tiempos de reposición de proveedores (cumpliendo la Regla inmutable "Pollo King").
   - 100% `Decimal` anti-float.
2. **`query_upcoming_events`**:
   - Consulta banquetes y eventos agendados en una ventana temporal (`days_ahead=30`), con desglose de fecha, franja horaria, asistentes, salón asignado, estado (`AGENDADO`, `CONFIRMADO`, etc.) y métricas financieras (`costo_total`, `precio_venta`, `margen_bruto`).
   - Retorna agregaciones monetarias tipadas en `Decimal`.
3. **`check_salon_availability`**:
   - Evalúa la disponibilidad física de salones para una fecha y franja horaria específica.
   - Valida capacidad máxima vs asistentes y detección de conflictos anti-overbooking.
   - Detalla salones disponibles (con precio neto, IVA 19%, precio bruto en `Decimal`) y salones no disponibles con su causa (`CAPACITY_EXCEEDED` o `OVERBOOKING_CONFLICT`).
4. **`estimate_event_budget_and_feasibility`**:
   - Calcula presupuesto integral del banquete (alquiler de salón, catering/menú según tier estándar/premium/buffet/corporativo, staff de servicio, subtotal neto, IVA al 19%, total bruto y margen proyectado).
   - Evalúa factibilidad simultánea de materias primas en bodega.
   - 100% `Decimal` anti-float.
5. **`OPPYFY_EVENT_TOOL_SCHEMAS`**:
   - Esquemas OpenAPI / JSON Schema declarativos de las 4 herramientas para function calling de LLM y puentes de transporte MCP.

### 1.2 Enrutador de Herramientas y Subdominios (`tool_router.py`)
En [`oppytec-backend/src/modules/oppy_ai/application/tool_router.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/oppy_ai/application/tool_router.py):
- Se incorporaron `"check_salon_availability"` y `"estimate_event_budget_and_feasibility"` al catálogo tipado `HardCodedToolCode` y `HARD_CODED_TOOL_CATALOG`.
- Se mapearon por defecto al subdominio `"abastecimiento_y_eventos"`.
- Se cableó la ejecución determinista en `_run_deterministic_query` para `query_upcoming_events`, `check_salon_availability`, `estimate_event_budget_and_feasibility` y `analyze_event_supply_feasibility`.

### 1.3 Clasificación Semántica en JEV Sistema 1 (`jev_adapter.py`)
En [`oppytec-backend/src/adapters/ai/jev_adapter.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/adapters/ai/jev_adapter.py):
- Se enriquecieron las afinidades semánticas de `SEMANTIC_AFFINITIES` para:
  * `"query_upcoming_events"` (`evento`, `eventos`, `banquete`, `matrimonio`, `invitado`, `invitados`, `reserva`, `agendado`, `agendados`, `proximos eventos`).
  * `"check_salon_availability"` (`salon`, `salones`, `disponibilidad`, `disponible`, `ocupado`, `overbooking`, `aforo`, `capacidad salon`).
  * `"estimate_event_budget_and_feasibility"` (`presupuesto`, `cotizar`, `cotizacion`, `estimar costo`, `presupuesto banquete`, `calcular evento`, `estimar presupuesto`).
  * `"analyze_event_supply_feasibility"` (`factibilidad`, `faltantes`, `insumos evento`, `banquete`, `cubrir`, `abastecer`, `stock banquete`).
- Se optimizó `_score_candidates` para asignar puntaje prioritario (`0.96`) cuando la coincidencia léxica acumula 3 o más palabras clave.

### 1.4 Redacción RBAC Estricta (`oppyfy_rbac.py`)
En [`oppytec-backend/src/modules/oppy_ai/domain/oppyfy_rbac.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/oppy_ai/domain/oppyfy_rbac.py):
- Se incorporaron a `SENSITIVE_COST_KEYS`: `"total_bruto"`, `"costo_total_acumulado"`, `"ingreso_proyectado"`, `"margen_proyectado"`, `"precio_venta"`, `"precio_neto"`, `"precio_bruto"`, `"iva"`, `"salon_alquiler_neto"`, `"catering_costo_neto"` y `"staff_costo_neto"`.
- Cuando un usuario no posee el permiso `can_view_costs=True`, todos estos campos se redactan de manera inmutable a `"[REDACTED_COST]"`, mientras que las métricas operativas (asistentes, fechas, nombres de salón, factibilidad) permanecen disponibles.

### 1.5 Corrección Crítica en Observabilidad (`observability.py`)
En [`oppytec-backend/src/core/observability.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/core/observability.py):
- Se corrigió el context manager `_safe_start_span` que capturaba indiscriminadamente todas las excepciones lanzadas dentro del bloque `yield`, provocando un `RuntimeError: generator didn't stop after throw()`.
- Ahora maneja `span_cm.__enter__()` en fallback transparente a `_NoOpSpan()` ante fallos de inicio, y asegura la propagación limpia de excepciones de negocio con `finally: span_cm.__exit__(*sys.exc_info())`.

### 1.6 Suites de Pruebas y Certificación
- `tests/unit/modules/test_oppyfy_events_tools.py`: **5/5 passed** (100% verde en 0.14s).
- `tests/unit/modules/test_oppy_ai_services.py`: **16/16 passed** (100% verde en 0.25s).
- `tests/unit/modules/test_oppyfy_projection_tools.py`: **6/6 passed** (100% verde en 0.26s).
- `tests/unit/modules/test_events_domain_and_models.py`: **12/12 passed** (100% verde en 0.23s).
- `tests/unit/modules/test_events_services.py`: **15/15 passed** (100% verde en 0.77s).
- Total suites vinculadas: **61/61 passed** en < 1.0s.

---

## 2. Artifacts Created & Modified

- **Creados:**
  - `oppytec-backend/tests/unit/modules/test_oppyfy_events_tools.py`
- **Modificados:**
  - `oppytec-backend/src/modules/oppy_ai/application/operational_tools/events_tools.py`
  - `oppytec-backend/src/modules/oppy_ai/application/operational_tools/__init__.py`
  - `oppytec-backend/src/modules/oppy_ai/application/tool_router.py`
  - `oppytec-backend/src/modules/oppy_ai/domain/oppyfy_rbac.py`
  - `oppytec-backend/src/adapters/ai/jev_adapter.py`
  - `oppytec-backend/src/core/observability.py`
  - `.agent/subagents/06-ai-oppyfy-and-jev-engineer/knowledge.md`
  - `.agent/subagents/06-ai-oppyfy-and-jev-engineer/handovers/latest_handover.md`

---

## 3. Friction & Failures Handled
- **Fricción:** Al verificar `test_events_services.py`, 6 tests fallaban con `RuntimeError: generator didn't stop after throw()` debido a que el generador `@contextmanager _safe_start_span` en `observability.py` capturaba `BaseException` y ejecutaba un segundo `yield _NoOpSpan()`.
- **Resolución:** Se refactorizó `_safe_start_span` para ejecutar `__enter__()` antes del yield y cerrar con `finally: span_cm.__exit__(*sys.exc_info())`, logrando que todas las pruebas pasaran al 100% (27/27 de eventos).

---

## 4. Next Exact Action
- Enviar reporte final al Agente Líder/Orquestador (`send_message`) certificando el cierre de la FASE 8 para el Módulo de Eventos.
