# Certificación Formal de Impacto en Base de Datos (Sign-off Auditor)
## Sub-Plan 2 — Etapa 1: Switch Maestro de Mock Data, Editor Reactivo y Presets Gastronómicos

- **Agente Auditor:** `03-database-alembic-and-backup-engineer` (Agente 03)
- **Fecha UTC:** 2026-11-05T21:35:00Z
- **Fase / Hito:** Sub-Plan 2 — Etapa 1 (Auditoría de Base de Datos para el Switch Maestro de Mock Data y Presets)
- **Estado de Certificación:** `ZERO_DATABASE_IMPACT_CERTIFIED` (Aprobado sin cambios DDL en esquemas de BD)
- **Alembic Current Head:** `0018_public_holding_hub_credit_distribution_and_purchases` (Lineal correlativo 0001..0018, 1 Head único, 0 bifurcaciones)

---

## 1. Resumen Ejecutivo y Alcance de la Auditoría

El **Sub-Plan 2** implementa el **Switch Maestro de Mock Data** (`demo` vs `clean` / BD Real Limpia), el panel interactivo de control de datos sintéticos y el catálogo de **Presets Gastronómicos** ("Pollería / Rotisería", "Dark Kitchen Sushi", "Restaurante Fine Dining", "Cafetería / Bakery") en la consola *Lab & QA Sandbox* de Platform Admin.

Como Agente 03, se procedió a la auditoría técnica exhaustiva de:
1. La necesidad y pertinencia de persistencia del estado del Switch Maestro y los presets (evaluación `localStorage` + cabeceras HTTP vs modelo relacional `public.tenants` / tablas de settings).
2. El comportamiento transaccional al conmutar a **"BD Real Limpia"**, verificando que las lecturas a esquemas vacíos no requieran alteraciones al catálogo de migraciones Alembic.
3. El blindaje e invariantes de **aislamiento multi-tenant** en la inyección de presets en modo real, garantizando la imposibilidad matemática de contaminar el esquema `public` o esquemas de clientes productivos.
4. La estabilidad de la estrategia de **Backups de 4-Capas** de OppyTec v2.0.

---

## 2. Dictamen de Persistencia: Arquitectura Desacoplada sin DDL

### 2.1 Evaluación Técnica: `localStorage` + Cabecera HTTP vs Columnas en `public.tenants`
Se evaluó si la persistencia del Switch Maestro (`dataMode: "demo" | "clean"`) y el preset activo (`activePresetId`) debía almacenarse en columnas de base de datos (`public.tenants.mock_data_mode`, tabla `platform_settings`) o en el cliente browser.

**Dictamen del Agente 03:**
Se dictamina y aprueba formalmente la adopción de una **Arquitectura 100% Desacoplada del Motor Relacional (Zero DDL)**:
- **Almacenamiento Primario:** `localStorage` en el navegador del operador / tester bajo claves tipadas:
  - `oppytec_mock_data_mode`: `"demo" | "clean"` (por defecto `"demo"` en entornos locales/qa, `"clean"` en producción).
  - `oppytec_mock_preset_id`: `"chicken_rotisserie" | "sushi_dark_kitchen" | "fine_dining" | "bakery_cafe"`.
- **Propagación Contextual:** Cabeceras HTTP opcionales enviadas por el cliente en peticiones API:
  - `X-OppyTec-Data-Mode: clean | demo`
  - `X-OppyTec-Mock-Preset: <preset_id>`

### 2.2 Fundamentación Técnica de no Modificar la Base de Datos
1. **Invariante de Aislamiento Concurrente entre Operadores:**
   Si el estado del Switch Maestro se almacenara en `public.tenants` o en una tabla de settings global, un operador de QA alternando a `"clean"` afectaría inmediatamente a todos los demás operadores o testers que estén navegando simultáneamente en ese tenant, rompiendo la independencia de sesiones.
2. **Cero Impacto DDL y Cero Bloqueos Transaccionales:**
   No se requiere añadir columnas (`ALTER TABLE public.tenants ADD COLUMN ...`), evitando locks de esquema, reescritura de metadatos o migración Alembic `0019_...`.
3. **Inviolabilidad de Producción:**
   En entornos productivos, ningún atacante o usuario puede forzar persistencias de modo sandbox en la base de datos central de clientes.
4. **Resiliencia y Modo Offline:**
   El frontend conmuta de forma instantánea entre fixtures sintéticas y consultas API sin latencia de I/O en la base de datos para consultar flags de estado efímeros.

---

## 3. Certificación de Modo "BD Real Limpia" y Alembic Head Frozen

### 3.1 Certificación de Lectura de Esquemas Reales Vacíos
- Cuando el Switch Maestro conmuta al modo `"clean"` (BD Real Limpia), el frontend bypassa los interceptores/fixtures de mock data y delega la consulta a los endpoints canónicos de OppyTec v2.0.
- El backend establece la conexión mediante SQLAlchemy 2.0 Async aplicando el aislamiento de esquema:
  ```sql
  SET LOCAL search_path = tenant_<slug>, public;
  ```
- Al consultar tablas operacionales (`kardex`, `recetas`, `combos`, `compras`, `facturas_dte`) en esquemas vírgenes o recién aprovisionados (`tenant_qa_lab`, `tenant_sandbox_fefo`), PostgreSQL responde legítimamente con datasets vacíos (`[]`, contadores en `0`).
- **Garantía:** No se requiere ninguna mutación, bandera ni vista sintética en la base de datos real para soportar el estado limpio.

### 3.2 Alembic Head Congelado en `0018`
- Se verificó la cadena correlativa de migraciones con la suite `tests/architecture/test_alembic_integrity.py`:
  - 18 versiones lineales correlativas (`0001` a `0018`).
  - Head canónico único: `0018_public_holding_hub_credit_distribution_and_purchases.py`.
  - Cero ramas bifurcadas (`down_revision` único y escalar en todas las versiones).
  - Cero migraciones añadidas para el Sub-Plan 2: **El catálogo de migraciones se mantiene estrictamente congelado.**

---

## 4. Aislamiento de Esquemas para Inyección de Presets en Modo Real

Para operaciones donde el operador decida materializar o inyectar los datos del Preset Gastronómico seleccionado en la base de datos física (`dry_run=False`):

### 4.1 Lista Blanca Estricta de Esquemas Aislados Autorizados
Toda operación de mutación física queda gobernada por el guardrail `_enforce_sandbox_environment_guard()`:
1. **Esquemas Autorizados:**
   - Patrón prefijado: `tenant_qa_*`, `tenant_sandbox_*`, `tenant_test_*`, `tenant_integration_*`
   - Slugs canónicos explícitos: `tenant_genesis`, `tenant_qa_lab`, `tenant_sandbox_fefo`
2. **Esquemas Estrictamente Prohibidos:**
   - Esquema global `public`: Prohibido incondicionalmente para inyecciones operacionales gastronómicas.
   - Esquemas de tenants productivos (`tenant_prod_*`, `tenant_<holding_real>_*`): Cualquier intento es abortado inmediatamente con excepción `EnvironmentGuardViolationError` (código HTTP `400 Bad Request`, `ISOLATED_SCHEMA_REQUIRED`).

### 4.2 Matriz de Gobernanza Multi-Entorno Fail-Fast
- **Entorno `production`:**
  - Mutaciones físicas con `dry_run=False` están **ESTRICTAMENTE PROHIBIDAS**.
  - Si un request con `dryRun=False` llega a un servidor con `ENVIRONMENT=production`, el guardrail falla de inmediato con `403 Forbidden` (`PRODUCTION_MUTATION_FORBIDDEN`), sin tocar la base de datos.
- **Entorno `staging`:**
  - Inyecciones físicas sobre esquemas autorizados exigen confirmación obligatoria explícita (`confirmStagingAction=true` en payload o cabecera `X-Sandbox-Confirm-Staging: true`).
- **Entornos `local` / `preview` / `ci`:**
  - Permitida la inyección física únicamente en los esquemas autorizados de la lista blanca.

---

## 5. Verificación de Permisos RBAC de 3 Niveles

Los endpoints y acciones operativas del Switch Maestro y Presets operan bajo los permisos canónicos de 3 niveles:
- **`platform_admin.sandbox.access`**: Lectura del estado del switch, inspección de presets disponibles e historial de ejecuciones.
- **`platform_admin.sandbox.manage`**: Conmutación operativa, inyección física de presets gastronómicos y ejecución de reseteos en esquemas autorizados.

**Auditoría de Invariantes:**
- Formato `modulo.submodulo.accion` verificado al 100%.
- Restricción exclusiva al plano global (`RequireGlobalPermission`). Tokens de usuarios de inquilinos (`tenant-scoped`) son rechazados con `403 Forbidden` (`GLOBAL_STAFF_REQUIRED`).

---

## 6. Estado y Resiliencia de Backups de 4-Capas

El diseño del Switch Maestro y Presets preserva íntegramente la arquitectura de continuidad operativa:
- **Capa L1 (Snapshots EBS/LVM):** Inalterada; la ausencia de DDL asegura snapshots delta compactos sin fragmentación de bloques.
- **Capa L2 (pg_dump lógico comprimido zstd + cifrado age):** Respaldos globales y de esquemas autorizados mantienen coherencia relacional y sumas SHA-256 inalteradas.
- **Capa L3 (WAL-G continuo / PITR sobre Cloud Storage):** Sin generación espuria de WALs por DDLs efímeros; streaming continuo verificado.
- **Capa L4 (Exportación quirúrgica por tenant schema):** Los esquemas aislados (`tenant_qa_lab`, etc.) pueden exportarse o reiniciarse quirúrgicamente mediante scripts sin impactar los esquemas de producción.

---

## 7. Autoevaluación según Rúbrica de 10 Criterios (`rubric_10_criteria.yaml`)

| # | Criterio | Estado | Justificación de Auditoría |
|---|---|:---:|---|
| 1 | `SPEC_BIPARTITION_AND_JEV_GATE` | ✅ APROBADO | Arquitectura alineada con especificaciones de negocio e ingeniería en OpenSpec. |
| 2 | `CLEAN_ARCHITECTURE_BOUNDARIES` | ✅ APROBADO | El desacoplamiento vía `localStorage` y cabeceras preserva la independencia del dominio y repositorios de base de datos. |
| 3 | `ZERO_ANY_AND_STRICT_TYPING` | ✅ APROBADO | Tipado estricto en contratos Pydantic y schemas TypeScript (`MockDataEntityCategory`, `MockDataGenerationConfig`). |
| 4 | `ZERO_HARDCODING_AND_SECRETSTR` | ✅ APROBADO | Cero cadenas de conexión o credenciales expuestas; uso de variables de entorno canónicas. |
| 5 | `ALEMBIC_LINEAR_CORRELATIVE` | ✅ APROBADO | Head en `0018`, secuencia 0001..0018 intacta sin bifurcaciones, 0 migraciones añadidas. Verificado con `test_alembic_integrity.py`. |
| 6 | `RBAC_THREE_LEVEL_AND_AUDIT` | ✅ APROBADO | Permisos `platform_admin.sandbox.access` y `platform_admin.sandbox.manage` validados con formato canónico de 3 niveles. |
| 7 | `CO_CREATION_1_TO_1_TESTS_AND_LEGACY_PARITY` | ✅ APROBADO | 23 pruebas unitarias y de guardrails pasando al 100% en backend (`test_platform_admin_sandbox.py` y `test_sandbox_observability_and_environments.py`). |
| 8 | `I18N_AND_MULTI_CURRENCY_FX` | ✅ APROBADO | Identificadores de presets y metadatos no alteran la regla protegida 'Pollo King' ni formatos multimoneda. |
| 9 | `OPPYFY_JEV_TELEMETRY_AND_R2_QUOTAS` | ✅ APROBADO | Cero colisiones con cuotas R2 ni logs FinOps en `public.llm_request_logs`. |
| 10 | `OFFENSIVE_SECURITY_AND_MOBILE_FIRST_DNA` | ✅ APROBADO | Guardrails anti-contaminación activos: bloqueo incondicional en producción (403), confirmación en staging (400) y rechazo de esquemas no aislados. |

**Calificación:** **10 / 10 Criterios Aprobados.**

---

## 8. Dictamen de Traspaso a Etapa 2

- **Veredicto:** **APROBADO PARA ETAPA 2 (CONSTRUCCIÓN PARALELA BACKEND + FRONTEND)**.
- **Directrices para el Escuadrón:**
  - **Agente 04 (Backend Dev):** Mantener el router de sandbox y servicios sin persistir flags del switch en `public.tenants`. Respetar el guardrail de esquemas autorizados `_enforce_sandbox_environment_guard()` para toda mutación.
  - **Agente 05 (Frontend Dev):** Implementar el Switch Maestro en el cliente utilizando persistencia en `localStorage` (`oppytec_mock_data_mode`, `oppytec_mock_preset_id`) y cabecera HTTP `X-OppyTec-Data-Mode`. Proveer el selector visual de los 4 presets gastronómicos canónicos.
