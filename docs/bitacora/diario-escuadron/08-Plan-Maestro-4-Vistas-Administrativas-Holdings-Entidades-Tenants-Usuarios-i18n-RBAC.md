---
title: "Bitácora Plan Maestro: Implementación de las 4 Vistas Administrativas (Holdings, Entidades Legales, Tenants y Usuarios Clientes), Paridad i18n 1:1, Protección Declarativa RBAC <Can> y Testing Interactivo"
phase: "Plan Maestro Admin (Pasos 3 y 4)"
date: "2026-10-23"
author_agent: "12-tech-writer-openspec-archify"
tags:
  - bitacora
  - plan-maestro
  - platform-admin
  - 4-vistas-administrativas
  - holdings
  - legal-entities
  - tenants
  - client-users
  - i18n-paridad
  - rbac-can
  - dynamic-admin-table
  - vitest
---

# 📓 Bitácora Plan Maestro: Implementación de las 4 Vistas Administrativas, Paridad i18n 1:1, Protección Declarativa RBAC `<Can>` y Suite de Tests Interactiva

> **Resumen en simple para personas:**  
> En esta entrega del Plan Maestro de **OppyTec v2.0**, el Escuadrón Multi-Agente llevó a la realidad operativa el corazón de la administración SaaS. Se implementaron en el frontend React 19 las **4 Vistas Administrativas Fundamentales**:
> 1. **Empresas Matrices (Holdings):** Visión global corporativa, planes SaaS y excepciones de capacidad por consorcio.
> 2. **Sociedades Tributarias (Entidades Legales):** Registro de razones sociales y RUTs chilenos validados bajo norma de módulo 11, con cardinalidad estricta 1:1 con cada restaurante.
> 3. **Aprovisionamiento de Restaurantes y Sucursales (Tenants):** Configuración de cada sucursal gastronómica con árbol interactivo de módulos SaaS, selector rápido de los 10 módulos del Plan Básico, moneda base y esquema físico aislado en PostgreSQL.
> 4. **Directorio de Usuarios Clientes:** Supervisión de personal operativo, validación estricta de cupos (`max_active_users`), botón de baja lógica ("Archivar") que libera de inmediato la vacante en el acto, y función de asistencia técnica ("Entrar como Local").
> 
> La solución se construyó sobre dos nuevos componentes reutilizables de alta ingeniería (`DynamicAdminTable` y `DynamicAdminForm`), alcanzó paridad total multilingüe en español e inglés sin cadenas hardcodeadas, se blindó contra manipulaciones visuales mediante permisos RBAC declarativos (`<Can perform="...">`) y se certificó con una suite completa de pruebas interactivas en Vitest (`36/36 passed`) y pruebas de backend (`83/83 unit passed` y `26/26 architecture passed`).

---

## 1. ¿Qué Hizo el Escuadrón en esta Entrega?

| Dimensión | Especialistas Involucrados | Qué se Construyó y Certificó (Explicado en Simple) |
|---|---|---|
| **Frontend UI/UX React 19** | Agente 05 (`frontend-senior-dev`) | Diseñó e implementó las 4 vistas en `AdminManagementViews.tsx` y los componentes genéricos `DynamicAdminTable` y `DynamicAdminForm`. Integró soporte reactivo para creación y edición en modales, filtros dinámicos en vivo, banderas de estado y semáforo `<QuotaProgressIndicator />`. |
| **Internacionalización i18n** | Agente 07 (`i18n-and-fx-currency-specialist`) | Erradicó el 100% de cadenas hardcodeadas en JSX. Creó las secciones espejo `holdings`, `legal_entities`, `tenants_view`, `client_users` y `table_common` en `locales/es/platform_admin.json` y `locales/en/platform_admin.json`. |
| **Ciberseguridad & Red Team** | Agente 10 (`cybersecurity-redteam-auditor`) | Blindó las vistas mediante RBAC declarativo de 3 niveles con `<Can perform="...">`. Los botones de alta, edición, baja, archivo y soporte quedan ocultos del DOM si el usuario carece del permiso correspondiente (`platform_admin.*`), previniendo elevación de privilegios o bypass visual. |
| **Backend API & Permisos** | Agente 04 (`backend-senior-dev`) | Conectó los endpoints REST de `/api/v1/tenancy/` con la validación de permisos globales, la revocación inmediata de sesiones en Redis ante soft-delete y la emisión de tokens scoped de soporte con auditoría forense inmutable. |
| **Testing & Calidad 5D** | Agente 09 (`qa-parity-and-test-engineer`) | Implementó `AdminManagementViews.test.tsx` cubriendo el ciclo de modales, alta de entidades, asignación de módulos, liberación inmediata de cupo por soft-delete y la verificación del veto visual RBAC (36 vitests pasando en total). |
| **Gobernanza Git & Merge Train** | Agente 11 (`git-worktree-merge-arbiter`) | Mantuvo el árbol de commits 100% lineal en `master`, libre de conflictos o locks residuales, y validó la invarianza SHA-256 de las reglas y rúbricas. |
| **Documentación & Segundo Cerebro** | Agente 12 (`tech-writer-openspec-archify`) | Actualizó las especificaciones bipartitas en `specs/business-domain/` y `specs/engineering-code/`, enriqueció el grafo de dependencias AST con Graphify (`graph.json`), actualizó el Segundo Cerebro y redactó esta bitácora oficial. |

---

## 2. Anatomía de las 4 Vistas Administrativas

### 🏢 A. Gestión de Empresas Matrices (`AdminHoldingsView`)
- Permite al SuperUser Global crear y gestionar holdings gastronómicos.
- Vincula cada holding a su plan comercial base (`plan_slug`).
- Configura cupos corporativos de usuarios, almacenamiento en megabytes y excepciones personalizadas de productos y proveedores para toda la cadena.
- **Permiso Exigido:** `platform_admin.holdings.manage`.

### 📑 B. Gestión de Sociedades Tributarias (`AdminLegalEntitiesView`)
- Administra las razones sociales legales asociadas a cada holding.
- Valida rigurosamente el RUT chileno mediante algoritmo de módulo 11, rechazando identificaciones inválidas o duplicadas.
- Establece la relación física estricta **1:1** con cada restaurante o sucursal (`UNIQUE(legal_entity_id)`), garantizando cumplimiento tributario y trazabilidad contable.
- **Permiso Exigido:** `platform_admin.legal_entities.manage`.

### 🏪 C. Aprovisionamiento de Restaurantes y Sucursales (`AdminTenantsView`)
- Crea y configura las sucursales operativas de cada holding.
- Aprovisiona el esquema físico aislado en PostgreSQL (`tenant_<slug>`).
- Presenta el **Árbol de Módulos SaaS (`SAAS_MODULE_TREE`)** con interruptores interactivos por módulo y sub-función.
- Incluye el botón de acción rápida *"Marcar 10 Módulos de Plan Básico"* (`PLAN_BASICO_10_MODULE_SLUGS`) para aprovisionar clientes del plan estándar con un solo clic.
- Permite fijar excepciones de cuotas paramétricas por sucursal (productos, proveedores, almacenamiento) y moneda operativa base (`CLP`, `USD`, `EUR`, `BRL`).
- **Permiso Exigido:** `platform_admin.tenants.provision`.

### 👥 D. Directorio de Usuarios Clientes (`AdminClientUsersView`)
- Centraliza la administración de usuarios y trabajadores de cada holding y local.
- Refleja el estado de vida del usuario con badges claros: `Activo` o `Liberado` (archivado).
- Modal de creación que valida en tiempo real si el local dispone de cupo según `max_active_users`.
- **Botón "Archivar" (Soft-Delete):** Permite dar de baja lógica al trabajador, revocando de inmediato sus tokens activos en Redis y liberando el asiento de usuario al instante para dar de alta a un nuevo colaborador.
- **Botón "Entrar" (Impersonación de Soporte Técnico):** Emite un token scoped temporal para que el equipo de soporte pueda ingresar a la interfaz del local y asistir directamente al cliente, dejando constancia inmutable en la bitácora de auditoría.
- **Permiso Exigido:** `platform_admin.client_users.manage` (y `platform_admin.tenants.provision` para impersonación).

---

## 3. Infraestructura de Componentes Reutilizables

Para asegurar consistencia visual y máxima velocidad en la construcción de pantallas futuras, se crearon dos componentes clave:

### 🧩 `DynamicAdminTable`
- Componente genérico tipado con soporte de ordenamiento por columnas, búsqueda en tiempo real insensible a mayúsculas/minúsculas y renderizado condicional de botones de acción.
- Incorpora soporte nativo para los permisos declarativos `createPermission`, `editPermission` y `deletePermission`, integrando `<Can perform="...">` directamente en el encabezado y las filas de la tabla.
- Integrado con el motor de traducción `translateKey("platform_admin", ...)` para títulos, botones de búsqueda, estados vacíos y badges.

### 📝 `DynamicAdminForm`
- Motor declarativo de renderizado de campos para modales de creación y edición.
- Soporta tipos de entrada: texto (`text`), números con validación de mínimos (`number`), selectores simples (`select`), interruptores booleanos (`checkbox`) y listas de selección múltiple (`multiselect`).
- Incluye selector identificable `${testId}-submit-btn` para pruebas deterministas en Vitest y Playwright.

---

## 4. Calidad, Seguridad y Verificación Determinista

La entrega fue sometida a la batería de Quality Gates obteniendo resultados impecables:

1. **Frontend Vitest Suite (`oppytec-frontend`):**
   - **`36 passed`** en 6 archivos de test.
   - `AdminManagementViews.test.tsx`: 5 pruebas interactivas certificando el flujo de creación de holdings, validación de RUT, asignación de módulos, soft-delete con liberación de cuota y veto visual RBAC ante roles no autorizados.
   - `App.test.tsx`: 13 pruebas validando el enrutador SPA y la navegación del panel administrativo.
2. **Backend Pytest Suite (`oppytec-backend`):**
   - **`83 passed`** en suite unitaria determinista.
   - `test_tenancy_admin_audit_and_redis_killswitch.py`: 3 pruebas certificando la exigencia de permisos canónicos de 3 niveles, revocación en Redis y registro de auditoría de impersonación.
   - `test_plan_basico_quotas_and_admin_provisioning.py`: 3 pruebas validando cuotas, overrides y aprovisionamiento SaaS.
3. **Architecture Gates:**
   - **`26 passed`** en `tests/architecture/`.
   - `test_openspec_bipartition_and_sync.py`: 100% passed (0% código/SQL prohibido en negocio y paridad 1:1).
   - `test_i18n_keys_parity_and_no_hardcoded_strings.py`: 100% passed (cero cadenas hardcodeadas y simetría es/en en `platform_admin.json`).
4. **Anti-Reward-Hacking Harness:**
   - `python scripts/harness.py verify-evals`: 100% integridad criptográfica SHA-256.

---

## 5. Conclusión

Con la llegada de estas 4 vistas administrativas, OppyTec v2.0 completa la infraestructura de gestión multi-tenant para empresas, sociedades, locales y usuarios. La arquitectura modular, el blindaje RBAC visual y la paridad idiomática completa aseguran una operación SaaS robusta, profesional y lista para escalar.
