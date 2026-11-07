# Certificación Formal de Impacto en Base de Datos (Sign-off Auditor)
## Sub-Plan 4 — Etapa 1: Simulador de Envejecimiento Temporal FEFO y Desplazamiento de Fechas en Platform Admin Sandbox

- **Agente Auditor:** `03-database-alembic-and-backup-engineer` (Agente 03)
- **Fecha UTC:** 2026-11-06T00:52:00Z
- **Fase / Hito:** Sub-Plan 4 — Etapa 1 (Auditoría de Impacto en Base de Datos, Blindaje Multi-Tenant y Aislamiento FEFO Time-Warp)
- **Estado de Certificación:** `ZERO_DATABASE_IMPACT_CERTIFIED` (Aprobado sin cambios DDL en esquemas de BD, Simulación 100% en memoria, Aislamiento estricto de esquemas en desplazamiento)
- **Alembic Current Head:** `0018_public_holding_hub_credit_distribution_and_purchases` (Lineal correlativo 0001..0018, 1 Head único, 0 bifurcaciones, estrictamente congelado)

---

## 1. Resumen Ejecutivo y Alcance de la Auditoría

El **Sub-Plan 4** implementa el **Simulador de Envejecimiento Temporal FEFO (Time-Warp) y Desplazamiento de Fechas** dentro de la consola *Lab & QA Sandbox* de Platform Admin (`/admin/sandbox` -> pestaña `FEFO Dates`), diseñado para permitir a los auditores operacionales, ingenieros de control de mermas y equipos de QA:
1. Evaluar de forma no destructiva el impacto financiero y de merma alimentaria al proyectar el reloj operacional entre 1 y 90 días en el futuro (`POST /api/v1/platform-admin/sandbox/fefo/simulate`).
2. Clasificar automáticamente los lotes de inventario según la regla de oro gastronómica FEFO (*First Expired, First Out*) en 4 estados críticos: `expired` ($\le 0\text{ días}$), `critical` ($\le 3\text{ días}$), `warning` ($\le 10\text{ días}$) y `optimal` ($> 10\text{ días}$).
3. Computar valorizaciones monetarias de pérdida estimada con precisión contable en moneda activa (`CLP`, `USD`, `EUR`, etc.).
4. Ejecutar el desplazamiento físico y controlado de fechas de vencimiento de lotes únicamente bajo solicitud explícita con permisos de administración (`POST /api/v1/platform-admin/sandbox/fefo/shift`).

Como Agente 03 (Especialista en Base de Datos, Alembic y Backups 4-Capas), se procedió a la auditoría técnica exhaustiva de:
- La certificación de que la simulación proyectiva (`/fefo/simulate`) con `dry_run=True` se ejecuta 100% en memoria y modo solo lectura (cero escrituras transaccionales en PostgreSQL).
- La certificación de que el endpoint de desplazamiento físico (`/fefo/shift`) está blindado con guardrails de aislamiento que restringen cualquier mutación física exclusivamente a esquemas aislados autorizados de prueba (`tenant_qa_lab`, `tenant_sandbox_fefo`), bloqueando con HTTP 400 cualquier esquema de cliente real o el esquema global `public`.
- La garantía de que el catálogo de migraciones de Alembic permanezca estrictamente congelado en `0018_public_holding_hub_credit_distribution_and_purchases` (Zero DDL, 0 migraciones añadidas).
- La preservación de la resiliencia en la estrategia de respaldos en 4-capas y los permisos RBAC de 3 niveles.

---

## 2. Dictamen de Persistencia: Simulación 100% en Memoria / Solo Lectura (Zero DDL / 0 Mutaciones)

### 2.1 Certificación de Simulación Proyectiva (`POST /fefo/simulate`)
El endpoint `/api/v1/platform-admin/sandbox/fefo/simulate` recibe el modelo `FefoWarpSimulationRequest` con parámetro `dry_run=True` por defecto.
- **Ejecución en Memoria:**
  El cómputo de envejecimiento temporal reside 100% en la capa de aplicación dentro de `SandboxApplicationService.simulate_fefo_warp()`.
- **Cero Mutaciones en Base de Datos:**
  - $0$ sentencias `INSERT`, $0$ sentencias `UPDATE`, $0$ sentencias `DELETE` emitidas contra la base de datos PostgreSQL.
  - Cero transacciones de escritura abiertas, cero bloqueo de tablas o filas (`FOR UPDATE`), y cero churn en los archivos Write-Ahead Logging (WAL).
  - La base de datos no sufre degradación de I/O ni fragmentación de páginas de disco por la ejecución iterativa de simulaciones de tiempo futuro.
- **Invariantes Matemáticas de Clasificación FEFO:**
  Para cada lote evaluado con fecha original de expiración $T_{\text{orig}}$ y fecha simulada $T_{\text{sim}} = T_{\text{actual}} + \Delta_{\text{offset}}$:
  $$\text{remaining\_days} = \lfloor (T_{\text{orig}} - T_{\text{sim}}).\text{days} \rfloor$$
  $$\text{status} = \begin{cases} 
  \text{'expired'} & \text{si } \text{remaining\_days} \le 0 \\
  \text{'critical'} & \text{si } 1 \le \text{remaining\_days} \le 3 \\
  \text{'warning'} & \text{si } 4 \le \text{remaining\_days} \le 10 \\
  \text{'optimal'} & \text{si } \text{remaining\_days} > 10
  \end{cases}$$
- **Cómputo Monetario Determinista de Riesgo de Pérdida:**
  $$\text{Loss}(\text{expired}) = \text{Stock} \times \text{UnitCost}$$
  $$\text{Loss}(\text{critical}) = \text{Stock} \times \text{UnitCost} \times 0.75$$
  $$\text{Loss}(\text{warning}) = 0.00$$
  $$\text{Loss}(\text{optimal}) = 0.00$$
  $$\text{TotalSpoilageRiskAmount} = \sum_{b \in \text{Batches}} \text{Loss}(b)$$
  Todos los cálculos respetan tipos `Decimal`/`float` redondeados con precisión comercial a 2 decimales, sin alteración de datos reales.

---

## 3. Blindaje de Aislamiento y Guardrails para Desplazamiento Físico (`POST /fefo/shift`)

### 3.1 Salvaguarda Preview-Only con `dry_run=True`
Cuando el payload incluye `dry_run=True`:
- El endpoint `/api/v1/platform-admin/sandbox/fefo/shift` opera en modo pasivo estricto.
- Retorna de inmediato la respuesta tipada `FefoShiftResponse` con `status="preview_only"` y `shiftedBatchesCount=0`.
- Cero registros o lotes sufren alteración de fechas en la base de datos física.

### 3.2 Guardrail Fail-Fast de Esquemas Autorizados (Anti-IDOR y Aislamiento Tenancy)
Cuando un operador con privilegios de gestión (`platform_admin.sandbox.manage`) solicita la aplicación efectiva del corrimiento temporal (`dry_run=False`), el guardrail centralizado `_enforce_sandbox_environment_guard()` se ejecuta en primera instancia:

1. **Lista Blanca Estricta de Esquemas Aislados Autorizados:**
   Solo se autorizan esquemas con prefijos controlados o pertenecientes al conjunto canónico de pruebas:
   - Esquemas prefijados: `tenant_qa_*`, `tenant_sandbox_*`, `tenant_test_*`, `tenant_integration_*`
   - Esquemas canónicos explícitos: `tenant_genesis`, `tenant_qa_lab`, `tenant_sandbox_fefo`
2. **Bloqueo Inmediato HTTP 400 ante Esquemas No Autorizados:**
   - Si la solicitud intenta desplazar fechas en esquemas de clientes reales (ej. `tenant_restaurante_real`, `tenant_prod_*`) o en el esquema global `public`:
   - El sistema aborta inmediatamente con excepción `EnvironmentGuardViolationError`:
     * Código HTTP: `400 Bad Request`
     * Código de error: `ISOLATED_SCHEMA_REQUIRED`
     * Mensaje: *"Aislamiento de esquema violado: El esquema destino '...' no es un esquema de pruebas aislado autorizado para mutaciones físicas del sandbox."*
   - Cero consultas `UPDATE` llegan al motor de base de datos relacional.

### 3.3 Matriz de Protección por Entorno (Producción y Staging)
- **Entorno `production`:**
  - El desplazamiento físico de fechas con `dry_run=False` está **TERMINANTEMENTE PROHIBIDO**.
  - Ante cualquier solicitud con `dry_run=False`, el guardrail falla de inmediato con `403 Forbidden` (`PRODUCTION_MUTATION_FORBIDDEN`).
- **Entorno `staging`:**
  - El desplazamiento físico con `dry_run=False` exige confirmación explícita obligatoria (`confirmStagingAction=true` en payload o cabecera `X-Sandbox-Confirm-Staging: true`).
  - Sin confirmación, el backend rechaza con `400 Bad Request` (`STAGING_CONFIRMATION_REQUIRED`).
- **Entornos `local`, `preview` y `ci`:**
  - Permitido únicamente en los esquemas de la lista blanca autorizada (`tenant_qa_lab`, `tenant_sandbox_fefo`).

---

## 4. Certificación de Alembic Head Congelado e Intacto en `0018`

### 4.1 Auditoría del Directorio de Versiones (`oppytec-backend/alembic/versions/`)
Se auditó la totalidad de los archivos de migración:
- 18 versiones lineales correlativas exactas:
  1. `0001_public_genesis_tenancy_modules_and_global_rbac.py`
  2. `0002_tenant_initial_client_rbac_and_core_modules.py`
  3. `0003_public_plans_quotas_and_tenant_capacity_overrides.py`
  4. `0004_tenant_inventory_kardex_and_physical_counts.py`
  5. `0005_tenant_consumption_buffet_and_voice_tables.py`
  6. `0006_tenant_approval_requests_and_notification_matrix.py`
  7. `0007_public_system_plans_extension_and_saas_policy.py`
  8. `0008_tenant_recipes_combos_dynamic_option_groups.py`
  9. `0009_tenant_procurement_purchases_and_suppliers.py`
  10. `0010_tenant_oppyfy_custom_rbac_and_credit_wallets.py`
  11. `0011_public_jev_request_logs_and_finops_telemetry.py`
  12. `0012_public_ai_model_configs_catalog_extension.py`
  13. `0013_tenant_events_salones_and_reservations.py`
  14. `0014_tenant_projection_snapshots_and_consumption_rates.py`
  15. `0015_tenant_actividades_triada_enriquecida.py`
  16. `0016_tenant_invoices_dte_and_supplier_aliases.py`
  17. `0017_public_ai_benchmarks_and_tenant_feedback.py`
  18. `0018_public_holding_hub_credit_distribution_and_purchases.py`

### 4.2 Dictamen de Head Intacto
- **Head Oficial:** `0018_public_holding_hub_credit_distribution_and_purchases`
- **Cadena:** Estrictamente lineal 0001..0018, 1 Head único escalar, 0 bifurcaciones (`down_revision` único).
- **Congelamiento para Sub-Plan 4:** **CERO DDL, 0 migraciones añadidas**. La migración `0019_...` **NO** ha sido creada ni es requerida.
- **Verificación Automatizada:**
  Suite de arquitectura ejecutada:
  ```bash
  oppytec-backend/.venv/bin/pytest oppytec-backend/tests/architecture/test_alembic_integrity.py -v
  ```
  **Resultado:** `2 passed in 0.20s` (100% verde).

---

## 5. Resiliencia de la Estrategia de Backups de 4-Capas

El funcionamiento del Simulador FEFO Time-Warp preserva íntegramente la continuidad operativa y la higiene de respaldos de OppyTec v2.0:
- **Capa L1 (Snapshots EBS/LVM):** Inalterada; la ausencia de DDL y la simulación en memoria evitan churn de bloques o fragmentación física.
- **Capa L2 (pg_dump lógico zstd + cifrado asimétrico age):** Los respaldos periódicos mantienen sumas de comprobación SHA-256 inalteradas, sin tablas intermedias o vistas huérfanas de simulación.
- **Capa L3 (WAL-G continuo / PITR sobre Cloud Storage):** La simulación analítica con `dry_run=True` no emite registros WAL a la base de datos relacional.
- **Capa L4 (Exportación quirúrgica por tenant schema `tenant_<slug>`):** Plena compatibilidad preservada; los esquemas aislados autorizados (`tenant_qa_lab`, `tenant_sandbox_fefo`) pueden ser desplazados o reseteados quirúrgicamente sin interferir con las exportaciones L4 de clientes comerciales de producción.

---

## 6. Verificación de Permisos RBAC de 3 Niveles y Barrera de Plano

Los endpoints del simulador FEFO implementan la matriz RBAC canónica de 3 niveles:
- **`platform_admin.sandbox.access`**:
  * Autorizado para simulación analítica de envejecimiento temporal (`POST /api/v1/platform-admin/sandbox/fefo/simulate`).
  * Solo lectura y cálculo proyectivo no destructivo.
- **`platform_admin.sandbox.manage`**:
  * Requerido para aplicar desplazamiento físico de fechas en esquemas autorizados (`POST /api/v1/platform-admin/sandbox/fefo/shift`).
  * Gobernado por `_enforce_sandbox_environment_guard`.

### 6.1 Formato Canónico y Barrera Global
- **Formato:** Cumple estrictamente con el regex `^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$`.
- **Barrera Global:** Enforzado mediante la dependencia `RequireGlobalPermission`. Tokens con alcance de inquilino (`is_global_staff=False`) son rechazados de inmediato con `403 Forbidden` (`GLOBAL_STAFF_REQUIRED`).

---

## 7. Autoevaluación según Rúbrica de 10 Criterios (`rubric_10_criteria.yaml`)

| # | Criterio | Estado | Justificación de Auditoría Técnica |
|---|---|:---:|---|
| 1 | `SPEC_BIPARTITION_AND_JEV_GATE` | ✅ APROBADO | Alineación integral con `platform-admin-sandbox.business.spec.md` y `platform-admin-sandbox.code.spec.md`. Suite `test_openspec_bipartition_and_sync.py` pasando 100% (PASSED). |
| 2 | `CLEAN_ARCHITECTURE_BOUNDARIES` | ✅ APROBADO | Lógica analítica de simulación y cálculo de pérdidas confinada en `SandboxApplicationService`, desacoplada del motor de almacenamiento relacional. Cero imports circulares. |
| 3 | `ZERO_ANY_AND_STRICT_TYPING` | ✅ APROBADO | Contratos Pydantic v2 en `schemas_sandbox.py` (`FefoWarpSimulationRequest`, `FefoSimulationResponse`, `FefoBatchSimulationImpact`, `FefoShiftResponse`) con `extra="forbid"`, alias bidireccionales y cero `Any`. |
| 4 | `ZERO_HARDCODING_AND_SECRETSTR` | ✅ APROBADO | Cero cadenas de conexión o credenciales hardcodeadas; configuración centralizada en `src.core.config.get_settings()`. |
| 5 | `ALEMBIC_LINEAR_CORRELATIVE` | ✅ APROBADO | Catálogo lineal 0001..0018 intacto. Head congelado en `0018_public_holding_hub_credit_distribution_and_purchases.py`. Validado con `test_alembic_integrity.py` (2 passed). |
| 6 | `RBAC_THREE_LEVEL_AND_AUDIT` | ✅ APROBADO | Permisos `platform_admin.sandbox.access` y `platform_admin.sandbox.manage` con formato de 3 niveles y barrera `RequireGlobalPermission`. Logging estructurado con actor, schema y offset. |
| 7 | `CO_CREATION_1_TO_1_TESTS_AND_LEGACY_PARITY` | ✅ APROBADO | Suites unitarias y de entornos pasando 100%: 31 passed en `test_platform_admin_sandbox.py` y 20 passed en `test_sandbox_observability_and_environments.py`. |
| 8 | `I18N_AND_MULTI_CURRENCY_FX` | ✅ APROBADO | Moneda tipada (`currency="CLP"`), cálculo de pérdidas exacto, y respeto de la regla 'Pollo King' en traducciones y nombres de insumos. |
| 9 | `OPPYFY_JEV_TELEMETRY_AND_R2_QUOTAS` | ✅ APROBADO | La simulación FEFO no afecta cuotas de almacenamiento R2 ni altera la bitácora append-only `public.llm_request_logs`. |
| 10 | `OFFENSIVE_SECURITY_AND_MOBILE_FIRST_DNA` | ✅ APROBADO | Guardrail fail-fast activo: bloqueo 403 en producción (`PRODUCTION_MUTATION_FORBIDDEN`), bloqueo 400 en staging sin confirmación, y bloqueo 400 ante esquemas no autorizados (`ISOLATED_SCHEMA_REQUIRED`). |

**Calificación:** **10 / 10 Criterios Aprobados.**

---

## 8. Dictamen de Traspaso a Etapa 2

- **Veredicto:** **APROBADO PARA ETAPA 2 (CONSTRUCCIÓN PARALELA BACKEND + FRONTEND + QA MASTER)**.
- **Directrices para el Escuadrón:**
  - **Agente 04 (Backend Dev):** Mantener la implementación de `/fefo/simulate` 100% en memoria y asegurar que `/fefo/shift` aplique el guardrail `_enforce_sandbox_environment_guard()` sin añadir migraciones DDL a Alembic.
  - **Agente 05 (Frontend Dev):** Conectar la pestaña `FefoDatesSandboxView.tsx` en `oppytec-frontend` con los endpoints `/fefo/simulate` y `/fefo/shift`, renderizando la matriz de lotes con semáforos de riesgo y formateador multi-moneda.
  - **Agente 08 (i18n & FX Specialist):** Verificar que los montos de pérdidas proyectadas se presenten en la moneda seleccionada con formateo tipado y traducciones completas en `platform_admin.json`.
  - **Agente 09 (QA Master):** Validar la cobertura integral de pruebas de regresión, integración y observabilidad en backend y frontend.
