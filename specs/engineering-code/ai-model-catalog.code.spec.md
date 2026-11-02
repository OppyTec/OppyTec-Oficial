---
spec_id: ENG-AI-MODEL-CATALOG
title: "Catálogo y Gestión de Modelos de Inteligencia Artificial y Motores JEV"
audience: engineering_internal
domain_module: oppy_ai
paired_spec: specs/business-domain/ai-model-catalog.business.spec.md
jev_system1_evaluation: "Sí (Jev.choice, umbral 0.80)"
last_verified_phase: "Fase Admin Catálogo AI v2.0"
---

# Catálogo y Gestión de Modelos de IA y Motores JEV — Especificación de Ingeniería

## 1. Contrato de Dominio DDD Puro (`src/modules/oppy_ai/domain/`)

### 1.1 Entidades y Value Objects Inmutables
La arquitectura de dominio desacoplada opera sin dependencias de frameworks web (FastAPI) ni ORM (SQLAlchemy), utilizando exclusivamente `dataclasses`, tipos estándar y precisión `Decimal`:

- **`AiEngineTier` (Enum):**
  - `SYSTEM_1_JEV`: Motores de clasificación e inferencia determinista ultrarrápidos (<100ms) desarrollados internamente.
  - `SYSTEM_2_LLM`: Modelos de lenguaje generativo de alta capacidad cognitiva para diálogo y razonamiento operativo.
  - `EMBEDDING`: Modelos de vectorización semántica de texto para memoria y RAG.

- **`AiModelTariffSpec` (Value Object):**
  - Estructura inmutable para el cálculo exacto de costos en USD:
    - `input_cost_per_1m_usd`: `Decimal` con precisión `Numeric(12, 6)`.
    - `cached_cost_per_1m_usd`: `Decimal` con precisión `Numeric(12, 6)` (por defecto `Decimal("0.000000")`).
    - `output_cost_per_1m_usd`: `Decimal` con precisión `Numeric(12, 6)`.
    - `embedding_cost_per_1m_usd`: `Decimal` con precisión `Numeric(12, 6)` (por defecto `Decimal("0.000000")`).
  - Invariante: Ningún valor de costo puede ser negativo (`value >= Decimal("0.000000")`). Cero uso de tipos de coma flotante (`float`).

- **`AiModelConfigEntity` (Entidad de Dominio):**
  - `model_slug`: `str` normalizado (slug alfanumérico en minúsculas, ej. `gemini-3.8-flash`, `jev-fast-classifier`).
  - `display_name`: `str` legible para interfaces humanas (ej. `Gemini 3.8 Flash`).
  - `provider`: `str` identificador del proveedor tecnológico (ej. `Google DeepMind`, `Anthropic`, `OpenAI`, `JEV Internal`).
  - `engine_tier`: `AiEngineTier`.
  - `tariffs`: `AiModelTariffSpec`.
  - `latency_p95_ms`: `int` (latencia esperada percentil 95 en milisegundos, ej. 50 para JEV, 800 para LLMs rápidos).
  - `min_confidence_score`: `Decimal | None` con precisión `Numeric(5, 4)` (umbral estadístico de Sistema 1, ej. `Decimal("0.8500")`).
  - `max_context_tokens`: `int` (cota superior de tokens de contexto, ej. 1.000.000).
  - `is_enabled`: `bool` (indicador de activación operativa).
  - `is_default`: `bool` (indicador de modelo principal para el tier correspondiente).
  - `is_fallback`: `bool` (indicador de modelo de contingencia ante caídas del principal).
  - `description`: `str` (documentación funcional del caso de uso recomendado).

### 1.2 Reglas de Dominio e Invariantes Arquitectónicas

1. **Invariante de Modelo Predeterminado Único por Tier:**
   - En cada `engine_tier` activo (`SYSTEM_1_JEV`, `SYSTEM_2_LLM`, `EMBEDDING`), debe existir exactamente un modelo con `is_default = True`.
   - Cuando se designa un nuevo modelo como `is_default = True` en un tier, el modelo que previamente ostentaba dicha condición se conmuta atómicamente a `is_default = False`.

2. **Invariante de Protección del Modelo Predeterminado:**
   - Queda estrictamente prohibido desactivar (`is_enabled = False`) o marcar para retiro al modelo configurado como `is_default = True`.
   - Para desactivar el modelo predeterminado, el administrador debe designar previamente otro modelo activo como predeterminado en la misma operación transaccional.

3. **Invariante de Modelo de Contingencia (*Fallback*):**
   - El modelo de contingencia (`is_fallback = True`) no puede ser idéntico al modelo predeterminado (`is_default = True`) dentro del mismo tier, a menos que solo exista un modelo registrado en dicho tier.
   - Todo modelo de contingencia debe mantener `is_enabled = True`.

4. **Invariante de Integridad Financiera y Soft Delete Obligatorio:**
   - Si un modelo cuenta con uno o más registros históricos de telemetría asociados en `public.llm_request_logs` o en `public.jev_request_logs`, **queda terminantemente prohibida su eliminación física (`DELETE FROM ai_model_configs`)**.
   - Cualquier solicitud de eliminación sobre un modelo con historial de invocaciones se transforma forzosamente en una **baja lógica** (`is_enabled = False`), preservando la integridad referencial y la consistencia matemática de los reportes históricos FinOps y costos liquidados.
   - La eliminación física (`Hard Delete`) se autoriza de forma estricta y exclusiva si y solo si el conteo de referencias en telemetría es idénticamente cero (`telemetry_count == 0`).

---

## 2. Contrato de Datos y Persistencia Relacional (`public.ai_model_configs`)

### 2.1 Esquema Físico en PostgreSQL
La tabla reside en el esquema global `public` y almacena las configuraciones maestras de los motores cognitivos:

```sql
-- Extensión y definición canónica de public.ai_model_configs
CREATE TABLE IF NOT EXISTS public.ai_model_configs (
    id SERIAL PRIMARY KEY,
    model_slug VARCHAR(64) UNIQUE NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    provider VARCHAR(64) NOT NULL,
    engine_tier VARCHAR(32) NOT NULL DEFAULT 'SYSTEM_2_LLM',
    input_cost_per_1m_usd NUMERIC(12, 6) NOT NULL DEFAULT 0.000000,
    cached_cost_per_1m_usd NUMERIC(12, 6) NOT NULL DEFAULT 0.000000,
    output_cost_per_1m_usd NUMERIC(12, 6) NOT NULL DEFAULT 0.000000,
    embedding_cost_per_1m_usd NUMERIC(12, 6) NOT NULL DEFAULT 0.000000,
    latency_p95_ms INTEGER NOT NULL DEFAULT 100,
    min_confidence_score NUMERIC(5, 4) NULL,
    max_context_tokens INTEGER NOT NULL DEFAULT 128000,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    is_fallback BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Índices de alto rendimiento para resolución de enrutamiento y estado
CREATE INDEX IF NOT EXISTS idx_ai_models_tier_default ON public.ai_model_configs (engine_tier, is_default);
CREATE INDEX IF NOT EXISTS idx_ai_models_provider ON public.ai_model_configs (provider);
CREATE INDEX IF NOT EXISTS idx_ai_models_enabled ON public.ai_model_configs (is_enabled);
```

### 2.2 Verificación de Referencias de Telemetría
La verificación de uso histórico para determinar el mecanismo de baja lógica o física consulta las bitácoras inmutables:
- Conteo en Sistema 2 y Embeddings: `SELECT COUNT(*) FROM public.llm_request_logs WHERE model_name = :model_slug`
- Conteo en Sistema 1: `SELECT COUNT(*) FROM public.jev_request_logs WHERE model_name = :model_slug`
- Si la suma acumulada de ambos recuentos es mayor a 0, la operación de borrado conmuta a `UPDATE public.ai_model_configs SET is_enabled = FALSE, updated_at = NOW() WHERE model_slug = :model_slug`.

---

## 3. Matriz RBAC de 3 Niveles y Seguridad de Acceso

La administración del catálogo se gobierna bajo la jerarquía de roles y permisos globales de OppyTec v2.0:

| Código de Permiso | Alcance y Audiencia | Operaciones Autorizadas |
| :--- | :--- | :--- |
| **`platform_admin.ai_models.read`** | **Acceso Abierto Staff Global:** Asignado a todos los colaboradores internos de OppyTec v2.0 autenticados (Soporte, Finanzas, Producto, Auditores y Desarrolladores). | `GET /api/v1/platform-admin/ai-models`<br/>`GET /api/v1/platform-admin/ai-models/{model_slug}` |
| **`platform_admin.ai_models.create`** | **Restringido Platform Admin:** Administradores globales de infraestructura y directores técnicos. | `POST /api/v1/platform-admin/ai-models` |
| **`platform_admin.ai_models.update`** | **Restringido Platform Admin:** Administradores globales de infraestructura y directores técnicos. | `PUT /api/v1/platform-admin/ai-models/{model_slug}`<br/>`PATCH /api/v1/platform-admin/ai-models/{model_slug}/set-default` |
| **`platform_admin.ai_models.delete`** | **Restringido Platform Admin:** Administradores globales de infraestructura y directores técnicos. | `DELETE /api/v1/platform-admin/ai-models/{model_slug}` |

- **Guardia de Autorización Backend:** `Depends(RequireGlobalPermission("platform_admin.ai_models.<accion>"))`.
- **Veto RBAC Frontend:** Componente reactivo `<Can permission="platform_admin.ai_models.create">` que oculta botones de acción destructiva o de mutación a usuarios sin privilegios administrativos.

---

## 4. Contrato de API REST RFC 7807 (`src/modules/oppy_ai/presentation/`)

### 4.1 Endpoints del Catálogo de Modelos

#### 1. `GET /api/v1/platform-admin/ai-models`
- **Permiso Requerido:** `platform_admin.ai_models.read`
- **Parámetros Query:**
  - `engine_tier` (`str`, opcional): Filtrar por nivel (`SYSTEM_1_JEV`, `SYSTEM_2_LLM`, `EMBEDDING`).
  - `is_enabled` (`bool`, opcional): Filtrar por estado de activación.
  - `provider` (`str`, opcional): Filtrar por nombre de proveedor.
- **Respuesta `200 OK`:** `list[AiModelCatalogResponse]`
```json
[
  {
    "model_slug": "gemini-3.8-flash",
    "display_name": "Gemini 3.8 Flash",
    "provider": "Google DeepMind",
    "engine_tier": "SYSTEM_2_LLM",
    "input_cost_per_1m_usd": "0.075000",
    "cached_cost_per_1m_usd": "0.018750",
    "output_cost_per_1m_usd": "0.300000",
    "embedding_cost_per_1m_usd": "0.000000",
    "latency_p95_ms": 750,
    "min_confidence_score": null,
    "max_context_tokens": 1000000,
    "is_enabled": true,
    "is_default": true,
    "is_fallback": false,
    "description": "Modelo insignia ultrarrápido y balanceado para el asistente operativo OppyFy."
  },
  {
    "model_slug": "jev-fast-classifier",
    "display_name": "Clasificador Rápido JEV",
    "provider": "JEV Internal",
    "engine_tier": "SYSTEM_1_JEV",
    "input_cost_per_1m_usd": "0.000000",
    "cached_cost_per_1m_usd": "0.000000",
    "output_cost_per_1m_usd": "0.000000",
    "embedding_cost_per_1m_usd": "0.000000",
    "latency_p95_ms": 45,
    "min_confidence_score": "0.8500",
    "max_context_tokens": 8192,
    "is_enabled": true,
    "is_default": true,
    "is_fallback": false,
    "description": "Motor de decisión binaria e intenciones operativas de Sistema 1 con micro-latencia."
  }
]
```

#### 2. `POST /api/v1/platform-admin/ai-models`
- **Permiso Requerido:** `platform_admin.ai_models.create`
- **Cuerpo de Solicitud (`AiModelCreateRequest`):**
```json
{
  "model_slug": "claude-3-7-sonnet",
  "display_name": "Claude 3.7 Sonnet",
  "provider": "Anthropic",
  "engine_tier": "SYSTEM_2_LLM",
  "input_cost_per_1m_usd": "3.000000",
  "cached_cost_per_1m_usd": "0.300000",
  "output_cost_per_1m_usd": "15.000000",
  "embedding_cost_per_1m_usd": "0.000000",
  "latency_p95_ms": 1200,
  "min_confidence_score": null,
  "max_context_tokens": 200000,
  "is_enabled": true,
  "is_default": false,
  "is_fallback": true,
  "description": "Modelo de razonamiento analítico de alta precisión para escandallos y proyección."
}
```
- **Respuesta `201 Created`:** Retorna el modelo creado `AiModelCatalogResponse`.
- **Errores:** `409 Conflict` si el `model_slug` ya existe o si se viola la regla de modelo predeterminado.

#### 3. `PUT /api/v1/platform-admin/ai-models/{model_slug}`
- **Permiso Requerido:** `platform_admin.ai_models.update`
- **Cuerpo de Solicitud (`AiModelUpdateRequest`):** Campos editables con validación estricta de tipos `Decimal` y `extra="forbid"`.
- **Respuesta `200 OK`:** Retorna la entidad actualizada. Inmediata sincronización en caliente con el registro en memoria `ModelConfigRegistry`.

#### 4. `DELETE /api/v1/platform-admin/ai-models/{model_slug}`
- **Permiso Requerido:** `platform_admin.ai_models.delete`
- **Comportamiento Arquitectónico Determinista:**
  1. Si `model.is_default == True`: Rechaza con `HTTP 409 Conflict` (tipo RFC 7807 `CANNOT_DELETE_DEFAULT_MODEL`, detail: "No se puede eliminar ni desactivar el modelo predeterminado. Designe otro modelo antes de proceder").
  2. Consulta la suma de referencias en `llm_request_logs` y `jev_request_logs`.
  3. Si `telemetry_references > 0`: Aplica **Soft Delete** (`UPDATE ai_model_configs SET is_enabled = FALSE`). Retorna `200 OK` con payload explicativo:
     ```json
     {
       "action": "SOFT_DELETED_ARCHIVED",
       "model_slug": "gemini-1.5-flash",
       "is_enabled": false,
       "historical_telemetry_logs_preserved": 45120,
       "message": "El modelo posee telemetría financiera histórica asociada. Ha sido desactivado lógicamente para proteger la trazabilidad de costos."
     }
     ```
  4. Si `telemetry_references == 0`: Ejecuta **Hard Delete** (`DELETE FROM ai_model_configs`). Retorna `204 No Content`.

---

## 5. Frontend UI/UX (`oppytec-frontend/src/features/platform-admin/ai-models/`)

- **Estructura de Componentes:**
  - `AiModelCatalogPage.tsx`: Vista principal montada en la ruta `/admin/ai-models` e indexada en el menú lateral de administración global.
  - `AiModelTable.tsx`: Tabla reactiva con tarjetas KPI superiores (Total de Modelos, Modelos JEV Activos, LLMs en Servicio, Costo Promedio por 1M de Tokens).
  - `AiModelUpsertModal.tsx`: Diálogo modal para alta y modificación de parámetros tarifarios, límites de tokens y latencias.
  - `AiModelDeleteDialog.tsx`: Diálogo interactivo que informa anticipadamente al usuario si la eliminación será física (0 llamadas) o una desactivación lógica de protección financiera.
- **Badges Visuales y Semáforos:**
  - Badge de Proveedor: Colores distintivos (Google: Azul, Anthropic: Naranja, OpenAI: Verde esmeralda, JEV: Violeta corporativo).
  - Badge de Nivel: `SYSTEM_1_JEV` (Micro-latencia / Costo Cero), `SYSTEM_2_LLM` (Razonamiento / Generación), `EMBEDDING` (Memoria Semántica).
  - Indicador de Rol: Estrella dorada para `is_default`, escudo de seguridad para `is_fallback`.
- **Internacionalización y Multi-Moneda:**
  - Archivos de traducción: `oppytec-frontend/src/shared/i18n/locales/{es,en}/platform_admin.json` bajo la clave `ai_models_catalog`. Cero textos sin traducir en la vista.

---

## 6. Observabilidad OpenTelemetry y Trazabilidad

- **Spans Semánticos:**
  - `platform_admin.ai_models.list`: Rastreo de consultas al catálogo con atributos `filter.engine_tier`, `models_count`.
  - `platform_admin.ai_models.create`: Registro de alta con atributos `model_slug`, `provider`, `engine_tier`, `input_cost_per_1m_usd`.
  - `platform_admin.ai_models.update`: Registro de mutación con atributos `model_slug`, `updated_fields`, `is_default`.
  - `platform_admin.ai_models.delete`: Registro del evento de baja con atributos `model_slug`, `resolution`: `soft_delete_archived` | `hard_deleted`, `telemetry_references_count`.
- **Garantía Zero-Float:** Todos los valores monetarios exportados en trazas o métricas se registran como `string` formateado o `Decimal`.

---

## 7. Evaluación JEV Sistema 1

jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **Sí**.
- **Primitiva:** `Jev.choice`
- **Umbral de confianza:** `0.80`
- **Aplicación Operativa:** Selección automática del modelo de contingencia (*Fallback Router*). Si la latencia observada de la llamada principal excede dos veces la cota `latency_p95_ms` o si el proveedor responde con un código transitorio HTTP 5xx, el micro-enrutador JEV selecciona en menos de 10 ms el modelo de respaldo habilitado para reintentar la solicitud sin impacto perceptible para el usuario del restaurante.

---

## 8. Plan de Pruebas Co-Creación 1:1

- **Pruebas Unitarias de Dominio:** `oppytec-backend/tests/unit/modules/test_ai_model_catalog_domain.py`
  - Validación de invariantes de modelo predeterminado único por tier.
  - Validación de impedimento de desactivación de modelo predeterminado.
  - Validación de regla de Soft Delete forzoso si `telemetry_references > 0`.
  - Verificación de tipos `Decimal` estrictos en tarifas y cero uso de `float`.
- **Pruebas de Servicios y Aplicación:** `oppytec-backend/tests/unit/modules/test_ai_model_catalog_service.py`
  - Sincronización en caliente entre base de datos y `ModelConfigRegistry`.
  - Conteo cruzado de telemetría en `llm_request_logs` y `jev_request_logs`.
- **Pruebas de API REST y Guardias RBAC:** `oppytec-backend/tests/unit/modules/test_ai_model_catalog_api.py`
  - Acceso autorizado para usuarios con `platform_admin.ai_models.read` en endpoints de lectura.
  - Restricción y rechazo `HTTP 403 Forbidden` en endpoints de mutación (`create`, `update`, `delete`) si el usuario solo posee permisos de lectura.
  - Respuestas RFC 7807 ante colisión de slugs o eliminación indebida de predeterminados.
- **Pruebas de Arquitectura y Bipartición:**
  - `oppytec-backend/tests/architecture/test_openspec_bipartition_and_sync.py` certifica la ausencia de código técnico en la especificación de negocio y el emparejamiento 1:1 con la presente especificación de ingeniería.
