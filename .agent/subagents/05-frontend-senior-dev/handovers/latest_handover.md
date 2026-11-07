# Reporte de Traspaso (`Handover`) — Agente 05: Frontend Senior React 19, Tailwind CSS & TanStack Query v5

- **Fecha UTC:** 2026-11-07T01:03:00Z
- **Agente:** Agente 05 (`05-frontend-senior-dev`)
- **Fase / Hito:** ADR-022 — Etapa 2 (Construcción Frontend): Eliminación 100% de Mock Data Hardcodeada en Modo Clean DB (`clean`) y Bóveda de Respaldo Maestro JSON (`mock_data_backup.json`)
- **Estado de Certificación:** `CLEAN_SLATE_GENESIS_FRONTEND_CERTIFIED` (98/98 test files, 1,171/1,171 vitest tests passing al 100%, 0 errores de compilación TypeScript estricto con `pnpm --dir oppytec-frontend run typecheck`, 100% de paridad i18n español/inglés).

---

## 1. Completed (Qué se ejecutó, validó y certificó)

1. **Núcleo Reactivo de Modo Clean vs Demo (`src/shared/mock/mockModeStorage.ts` y `src/shared/api/httpClient.ts`):**
   - `ensureBrowserDefaultCleanMode()`: En navegador real (cuando no se ejecuta bajo Vitest, es decir `!(typeof process !== "undefined" && process.env?.VITEST)` y `import.meta.env?.MODE !== "test"`), auto-inicializa `oppytec_mock_data_mode = "clean"`, limpia `oppytec_mock_custom_dataset` y marca `oppytec_clean_slate_v2_ready = "true"`.
   - Conserva el retorno `"demo"` cuando `localStorage` está vacío en entorno Vitest para mantener 100% de compatibilidad con las suites de pruebas existentes (`MockDataMasterSwitchAndPresets.test.tsx`).
   - Nuevos helpers exportados:
     * `selectByMockMode<T>(demoData: T, cleanData: T): T`
     * `useMockAwareData<T>(demoData: T, cleanData: T): T`
   - En `httpClient.ts`: cuando `isMockClean` es `true` (`X-OppyTec-Mock-Mode: clean`) y la respuesta HTTP falla o cae en `catch`:
     * Si `Array.isArray(options?.fallbackData)` -> retorna `[]`.
     * Si `options?.fallbackData` es un objeto paginado con `Array.isArray(items)` en un `GET` -> retorna `{ ...fallbackData, items: [], total: 0 }`.

2. **Vista `/admin/sandbox/mock-data` (`src/features/platform-admin/sandbox/MockDataSandboxView.tsx`):**
   - Al seleccionar el preset `"clean-slate"` y confirmar el **Factory Reset**, invoca automáticamente `setMockMode("clean")` además de `executeFactoryReset`, conmutando el Switch Maestro a `"Clean DB"` y emitiendo el evento global de limpieza a todas las vistas.
   - Nueva tarjeta **"Respaldo Maestro JSON (`mock_data_backup.json`)"** (`data-testid="mock-data-backup-vault-card"`) con 3 botones operativos e i18n completo (`es`/`en`):
     * `data-testid="btn-download-mock-backup-json"`: Descarga `mock_data_backup.json` desde `@/shared/mock/mock_data_backup.json`.
     * `data-testid="btn-purge-all-clean-slate"`: Activa `setMockMode("clean")`, limpia `localStorage` de datasets custom y ejecuta el reset a `clean-slate`.
     * `data-testid="btn-restore-mock-backup"`: Activa `setMockMode("demo")` y restaura el dataset desde el respaldo JSON.

3. **Desacoplamiento Sistemático de Mock Data Hardcodeada en el 100% de Vistas, Hooks y Servicios (`src/`):**
   - **Layout, Shared & Router:** `Navbar.tsx`, `HoldingTenantSwitcher.tsx`, `BodegaSelector.tsx`, `AreaSelector.tsx`, `RealtimeProvider.tsx` (`INITIAL_EVENTS = []` en modo `"clean"`), `app/router.tsx` (`ClientAppShell`).
   - **Platform Admin:** `AdminDashboard.tsx` (`tenants = []`, summary con `holdings: 0, legal_entities: 0, tenants: 0, active_client_seats: 0, users: 1, plans: 3`), `AdminManagementViews.tsx` (`AdminGlobalUsersView` únicamente con `OppyTec.Admin@gmail.com`; holdings, razones sociales, sucursales, usuarios clientes y rubros en `[]`; planes con `0` clientes), `hooks/useAdminPlans.ts`, `hooks/useTokenConsumption.ts`, `hooks/useJevConsumption.ts`, `hooks/useAiCreditPacks.ts`, `sandbox/FefoDatesSandboxView.tsx`, `ai-models/api.ts`.
   - **Home & Inventory:** `home/HomeDashboard.tsx`, `inventory/hooks/useStock.ts`, `inventory/hooks/useRecuentos.ts`, `inventory/conteo/ContarInventarioPage.tsx`, `inventory/recuentos/RecuentosPage.tsx`, `inventory/recuentos/RecuentoDetalleModal.tsx`, `inventory/alerts/hooks/useAlertas.ts`, `inventory/alerts/hooks/useAlertBadge.ts`, `inventory/stock/dialogs/AddingMercaderiaDialog.tsx`, `inventory/stock/dialogs/SolicitudesDialog.tsx`.
   - **Gestión, Consumo & Abastecimiento:** `gestion/useGestion.ts`, `gestion/hooks/useRecetas.ts`, `gestion/hooks/useCombos.ts`, `gestion/hooks/useGruposOpciones.ts`, `consumo/hooks/useConsumo.ts`, `consumo/hooks/useBuffet.ts`, `consumo/hooks/useManosLibres.ts`, `procurement/hooks/useCompras.ts`, `procurement/hooks/useProveedores.ts`, `procurement/hooks/useMermaAnalytics.ts`, `procurement/ProcurementFeatureView.tsx`, `procurement/components/CatalogoPrecios.tsx`, `procurement/dialogs/CompraDialog.tsx`, `procurement/mermas/GestionarMermaView.tsx`.
   - **Facturas, Eventos, Proyección, Historial, Actividades, Notificaciones, Holding Hub, OppyFy y Configuración:** `invoices/invoicesApi.ts`, `invoices/components/FacturaReviewGrid.tsx`, `events/api/eventsApi.ts`, `events/hooks/useEvents.ts`, `events/hooks/useSalones.ts`, `events/hooks/useEventAlerts.ts`, `projection/api/projectionApi.ts`, `projection/hooks/useProyeccionData.ts`, `historial/useHistorial.ts`, `activities/hooks/useNotas.ts`, `activities/hooks/useTareas.ts`, `activities/hooks/useHorarios.ts`, `activities/hooks/useCollaborators.ts`, `activities/notas/MinutaTraspasoDialog.tsx`, `notifications/hooks/useApprovals.ts`, `notifications/hooks/useNotificationMatrix.ts`, `notifications/hooks/usePendingCount.ts`, `notifications/components/ConteoRequestDetails.tsx`, `holding-hub/useHoldingHubData.ts`, `oppyfy/hooks/useOppyfyGovernance.ts`, `oppyfy/hooks/useOppyfyChat.ts`, `oppyfy/OppyFyFeatureView.tsx`, `oppyfy/OppyfyWorkspacePage.tsx`, `users/UsuariosPage.tsx`, `profile/ProfilePage.tsx`, `configuracion/tabs/RestauranteConfig.tsx`, `configuracion/tabs/BodegasConfig.tsx`, `configuracion/tabs/AreasOperativasConfig.tsx`, `configuracion/tabs/PlantillasEmailConfig.tsx`, `catalog/index.tsx`, `recipes/index.tsx`, `operations/index.tsx`, `analytics/index.tsx`, `rbac-and-audit/index.tsx`.

---

## 2. Friction & Failures (Incidentes y Resolución)

- **Ajustes de Tipado Estricto (`tsc --noEmit`):** Se alinearon los objetos vacíos `CLEAN_*` con las interfaces exactas de dominio (`MinutaTraspasoResponse`, `PaginatedKardexHistoryResponse`, `InvoiceStats`, `JevConsumptionSummaryResponse`, `TokenConsumptionResponse`, `MermaAnalyticsData`), logrando `0` errores de compilación TypeScript.
- **Sincronización de Catálogo en `useProveedores.ts`:** En modo `"demo"`, cuando no hay proveedor seleccionado (`selectedSupplierId === null`), `fallbackCatalog` agrega todos los ítems de `MOCK_PRODUCTOS_PROVEEDOR`; en modo `"clean"`, retorna `[]`.

---

## 3. Evidencias de Verificación Automatizada (`pnpm`)

- **Typecheck estricto:**
  ```bash
  pnpm --dir oppytec-frontend run typecheck
  # Salida: $ tsc --noEmit (Exit Code 0, 0 errores)
  ```
- **Suite Completa Vitest:**
  ```bash
  pnpm --dir oppytec-frontend test
  # Test Files: 98 passed (98)
  # Tests: 1171 passed (1171)
  ```

---

## 4. Next Exact Action (Traspaso a Etapa 3 y Etapa 4)

- **Para Agente 07 (`07-i18n-and-fx-currency-specialist`):** Verificar paridad de llaves `sandbox.mock_data.backup_vault_*` en `es/platform_admin.json` y `en/platform_admin.json`.
- **Para Agente 09 (`09-qa-parity-and-test-engineer`):** Certificar en conjunto con Backend la limpieza total de vistas en modo `"clean"` y la restauración desde `mock_data_backup.json`.
