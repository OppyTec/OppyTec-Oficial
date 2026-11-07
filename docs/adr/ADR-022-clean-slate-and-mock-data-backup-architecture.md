# ADR-022: Arquitectura de Estado Virgen por Defecto (*Clean Slate*), Bóveda de Respaldo Mock Data en JSON y Desacoplamiento Reactivo Frontend/Backend

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-11-07
- **Estrategia de Referencia:** `AGENTS.md` / `.agent/rules/01-domain-driven-design-and-clean-architecture.md` / Consola `Lab & QA Sandbox` (`/admin/sandbox/mock-data`)

---

## 1. Contexto

Históricamente, durante la construcción incremental de las 13 fases de **OppyTec v2.0**, diversos servicios del Backend (`oppytec-backend/src/modules/*`) y múltiples vistas, hooks y clientes HTTP del Frontend (`oppytec-frontend/src/features/*` y `oppytec-frontend/src/shared/*`) mantuvieron arreglos de datos sintéticos pre-poblados (`MOCK_*`, `INITIAL_*_MOCK`, `FALLBACK_*`) y semillas de demostración (ej. Holding *"Grupo Gastronómico Andino"*, sucursal `gran-via`, usuarios demo, productos de catálogo, lotes FEFO, kardex, mermas, alertas, recetas, combos, órdenes de compra, facturas, eventos y logs FinOps).

Para que el sistema opere como una plataforma SaaS empresarial lista para producción desde el arranque inicial, la base de datos PostgreSQL (`oppytec_dev`) y todas las vistas de la aplicación deben iniciar en un estado **100% Virgen (*Clean Slate*)**, conservando únicamente la configuración **Génesis** indispensable del Plano de Control (`public`), mientras que la totalidad de los datos sintéticos de prueba debe preservarse de forma íntegra y estructurada en una **Bóveda JSON Canónica de Respaldo (`mock_data_backup.json`)** controlada exclusivamente por el Switch Maestro de Mock Data (`/admin/sandbox/mock-data`).

---

## 2. Decisión Arquitectónica

### 2.1. Bóveda Canónica de Respaldo Mock Data (`mock_data_backup.json`)

Toda la data sintética retirada del código fuente y de la base de datos activa se preserva sin pérdida de información en dos artefactos espejo sincronizados:
1. **Backend:** `oppytec-backend/fixtures/mock_data_backup.json`
2. **Frontend:** `oppytec-frontend/src/shared/mock/mock_data_backup.json`

#### Contrato de Esquema JSON (`MockDataBackupVault`):
```json
{
  "version": "2.0.0",
  "exported_at": "2026-11-07T00:00:00Z",
  "description": "Bóveda canónica de respaldo de Mock Data y Presets Gastronómicos de OppyTec v2.0",
  "datasets": {
    "holdings": [],
    "legal_entities": [],
    "tenants": [],
    "client_users": [],
    "catalog": [],
    "inventory": [],
    "fefo_batches": [],
    "kardex": [],
    "counts": [],
    "mermas": [],
    "alerts": [],
    "recipes": [],
    "combos": [],
    "option_groups": [],
    "procurement": [],
    "invoices": [],
    "events": [],
    "consumo": [],
    "activities": [],
    "projection": {},
    "oppyfy": {},
    "finops_logs": []
  },
  "gastronomic_presets": {
    "RESTAURANT_FINE_DINING": {},
    "HOTEL_BUFFET": {},
    "DARK_KITCHEN": {},
    "FAST_CASUAL_CHAIN": {}
  }
}
```
- Cuando el administrador global activa el modo `"demo"` o inyecta un preset desde `/admin/sandbox/mock-data`, `SandboxManagerService` (Backend) y `mockModeStorage.ts` (Frontend) restauran los datasets desde esta bóveda canónica.

---

### 2.2. Estado Base "Clean Slate" (100% Virgen por Defecto en PostgreSQL y Memoria Backend)

En estado por defecto (`Clean Slate`), tanto la base de datos PostgreSQL (`oppytec_dev`) como las estructuras en memoria de los servicios del Backend (`_SANDBOX_STATE`, `_TENANTS_MEMORY`, `_USERS_MEMORY`, `_PRODUCTS_MEMORY`, `_RECIPES_MEMORY`, `_ORDERS_MEMORY`, `_FINOPS_STATE`, etc.) contienen **EXCLUSIVAMENTE** la configuración Génesis definida en `oppytec-backend/src/core/bootstrap.py`:

| Entidad / Esquema | Estado en *Clean Slate* | Detalle Canónico Conservado |
|---|---|---|
| **SuperUser Génesis** (`public.global_users`) | **1 registro único** | `email`: `OppyTec.Admin@gmail.com` \| `username`: `oppytec.admin` \| `password`: `oppytec2026` (Argon2id vía `SecretStr`) \| `is_superuser_god`: `True` \| `role`: `superuser` |
| **Módulos Base** (`public.app_modules`) | **7 registros base** | `catalog`, `inventory`, `operations`, `recipes`, `procurement`, `analytics`, `oppyfy` |
| **Roles Globales** (`public.global_roles`) | **4 registros base** | `superuser` (rank 0), `admin` (rank 10), `supervisor` (rank 20), `developer` (rank 30) y permiso comodín `*.*.*` |
| **Planes Comerciales SaaS** (`public.system_plans`) | **3 registros base** | `basic`, `starter`, `enterprise` con precios multi-moneda `Decimal` (`CLP`, `USD`, `EUR`, `BRL`) |
| **Catálogo IA & FinOps** (`public.ai_model_configs` / `public.saas_ai_policy_config`) | **6 modelos + 1 política** | Configuración base de modelos LLM y política global FinOps |
| **Holdings, Razones Sociales y Sucursales** (`public.holdings`, `public.legal_entities`, `public.tenants`) | **0 registros (`[]`)** | Ningún holding, entidad legal ni esquema `tenant_*` pre-creado |
| **Usuarios de Clientes** (`tenant_*.users`) | **0 registros (`[]`)** | Cero usuarios de sucursal o tenant |
| **Datos Operativos y Transaccionales** | **0 registros (`[]`)** | Cero productos, stock, lotes FEFO, movimientos kardex, recuentos, mermas, alertas, recetas, combos, órdenes de compra, facturas, eventos, actividades o logs FinOps |

---

### 2.3. Contrato de Desacoplamiento Reactivo en Frontend (`oppytec-frontend`)

1. **Inicialización en Modo `"clean"` para Navegador Real y Compatibilidad con Vitest (`src/shared/mock/mockModeStorage.ts`):**
   - Se incorpora una clave de versión de migración (`MOCK_DATA_CLEAN_SLATE_MIGRATED_KEY = "oppytec_clean_slate_v2_initialized"`).
   - En un navegador interactivo real (fuera del runner automatizado `vitest`/`jsdom`), si la migración Clean Slate no se ha aplicado o si no existe preferencia explícita del usuario en `localStorage`, el sistema inicializa automáticamente `oppytec_mock_data_mode = "clean"`.
   - Se provee el selector funcional puro `selectByMockMode<T>(demoData: T, cleanData: T): T` que evalúa `isMockDataEnabled()` en tiempo real:
     * Si `mode === "demo"`, retorna `demoData` (cargado desde el respaldo).
     * Si `mode === "clean"`, retorna `cleanData` (colecciones vacías `[]` o métricas en `0`).

2. **Prohibición de Fallbacks Sintéticos en Modo `"clean"` (`src/shared/api/httpClient.ts` y `src/features/*`):**
   - Cuando `isMockDataEnabled() === false` (modo `"clean"`), queda **estrictamente prohibido** capturar errores de red o respuestas vacías del backend para sustituirlos silenciosamente por `MOCK_*`, `INITIAL_*_MOCK` o `FALLBACK_*`.
   - Todas las vistas de los módulos (`Dashboard`, `Catalog`, `Inventory`, `FEFO`, `Kardex`, `Counts`, `Mermas`, `Alerts`, `Recipes`, `Combos`, `OptionGroups`, `Procurement`, `Invoices`, `Events`, `Consumo`, `Activities`, `Projection`, `OppyFy`, `PlatformAdmin` / `Tenants` / `Holdings` / `Users` / `FinOps`) deben renderizar sus estados vacíos limpios (*Empty States* con i18n `es`/`en`) cuando las colecciones están vacías (`[]`).

---

## 3. Evaluación Obligatoria Gate JEV (`¿Lo puede hacer JEV (Sí/No)?`)

- **Pregunta:** *¿La conmutación entre estado Clean Slate y la hidratación/purga de la bóveda Mock Data debe ejecutarse mediante el motor heurístico/probabilístico JEV en tiempo de ejecución?*
- **Respuesta:** **NO en runtime de datos; SÍ únicamente en el enrutamiento de agentes (`route-task`).**
- **Justificación Arquitectónica:**
  1. La integridad de estado *Clean Slate* vs *Demo Mode* exige determinismo transaccional absoluto ($100\%$ predecible e idempotente): cuando el modo es `"clean"`, toda consulta sobre entidades de negocio no creadas debe retornar exactamente `0` registros (`[]`), sin inferencia ni aproximación heurística.
  2. La carga y purga de `mock_data_backup.json` se ejecuta mediante operaciones atómicas de base de datos (`DELETE` / `TRUNCATE` de tablas no-Génesis y `DROP SCHEMA IF EXISTS tenant_* CASCADE` en PostgreSQL) y selectores booleanos deterministas (`isMockDataEnabled()`).

---

## 4. Consecuencias y Verificación Determinista

- **Positivas:**
  - Al iniciar sesión con `OppyTec.Admin@gmail.com` (`oppytec2026`), el administrador encuentra la plataforma completamente limpia, sin sucursales ficticias ni productos hardcodeados, lista para dar de alta clientes reales o activar explícitamente el Sandbox de demostración cuando lo desee.
  - Ningún dato de prueba se pierde: el $100\%$ de los datasets y los 4 presets gastronómicos quedan resguardados en `mock_data_backup.json`.
  - Compatibilidad del $100\%$ con las suites unitarias y de integración existentes en `pytest` y `vitest`.
- **Verificación Determinista:**
  - Validación en PostgreSQL real (`oppytec_dev`) de que `public.holdings`, `public.legal_entities`, `public.tenants` tienen `0` filas y `public.global_users` tiene exclusivamente `1` fila (`OppyTec.Admin@gmail.com`).
  - Pruebas unitarias y de integración verificando que en modo `"clean"` todas las vistas y hooks retornan `[]` sin inyectar datos sintéticos.
