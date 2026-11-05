# Reporte de Traspaso (`Handover`) — Agente 07: Especialista en i18n y Multi-Moneda FX

- **Fecha UTC:** 2026-11-05T15:55:00Z
- **Agente:** `07-i18n-and-fx-currency-specialist`
- **Fase / Hito:** Etapa 3 — Holding Hub Enterprise (Auditoría Integral i18n, Multi-Moneda FX Institucional y Regla "Pollo King").
- **Estado de Certificación:** `HOLDING_HUB_STAGE_3_I18N_AND_FX_CERTIFIED` (13/13 tests passing en frontend Vitest, 7/7 tests passing en backend Pytest, 100% simetría en claves `holding_hub.json`, 0 textos crudos/hardcoded en JSX, 0 floats en cálculo cambiario).

---

## 1. Resumen Ejecutivo y Tareas Completadas

1. **Consulta Previa a Graphify**:
   - Ejecutado `python scripts/harness.py nav "holding_hub"` validando la cadena de dependencias de migración (`0018_public_holding_hub`), modelos, router y componentes frontend.

2. **Auditoría y Paridad 100% de Catálogos i18n**:
   - `oppytec-frontend/src/shared/i18n/locales/es/holding_hub.json`: 174 claves completas organizadas modularmente (`navbar`, `sidebar`, `kpis`, `filters`, `branches_table`, `detail_modal`, `briefing`, `plans`, `credits`, `command_palette`, `alerts`).
   - `oppytec-frontend/src/shared/i18n/locales/en/holding_hub.json`: 174 claves espejo en inglés profesional gastronómico/enterprise con 100% de paridad y simetría exacta comprobada programáticamente.
   - Sincronización en `config.ts`, `i18next.d.ts` e `i18n.test.tsx` (registrando y testeando 26 namespaces oficiales).

3. **Erradicación Total de Textos Hardcodeados (0 JSX Raw Strings)**:
   - Auditados y refactorizados todos los componentes del Holding Hub:
     * `HoldingNavbar.tsx`: fallback de roles, badges y notificaciones dinámicas parametrizadas con `t()`.
     * `HoldingSidebar.tsx`: títulos contextuales, cuotas y badges internacionalizados.
     * `HoldingCentralSection.tsx`: labels de modales, RUTs, estados compartidos/asignados, KPIs financieros y de inventario.
     * `HoldingPlansSection.tsx`: matriz de planes (Starter, Growth, Enterprise), badges ("HOY", "Fin de ciclo"), botones y estados de transición.
     * `HoldingCreditsSection.tsx`: sliders de asignación, advertencias de sobrecupo (over-allocation warning), estados de compra y checkout.
     * `TenantCommandPalette.tsx`: atajos de teclado, conteo de locales y placeholders.
     * `HoldingAiBriefingCard.tsx`: etiquetas de accesibilidad `aria-label`, prefijos contextuales de párrafos, estados de autonomía y burn rate.
     * `HoldingHubLayout.tsx`: delegación de refrescos y sincronización de estado.

4. **Auditoría Multi-Moneda FX (CLP, USD, EUR, BRL)**:
   - Integración de `useCurrencyFormatter()` con `convertAndFormat(amount, "CLP", currency)` para garantizar que el cambio reactivo del `CurrencySelector` traduzca y convierta instantáneamente montos consolidados de ventas e inventario, paquetes de créditos IA y planes de suscripción mensual/anual.
   - Tasas de cambio institucionales respaldadas por Banco Central de Chile (BCCh) y Banco Central Europeo (BCE Frankfurter).
   - Uso estricto de aritmética sin pérdida de precisión: tipos `Decimal` en backend y `BigInt` escalado a $10^8$ en frontend.
   - Protección contra anomalías cambiarias (`anomaly_guard.py`) asegurando cuarentena automática ante fluctuaciones > 8%.

5. **Regla de Oro "Pollo King" (Invarianza de Nombres Propios)**:
   - Verificado que los nombres de holdings (ej. "Holding Gastronómico Pollo King"), razones sociales ("Pollo King SpA"), marcas protegidas ("Pollo King", "Savory", "Cevichería Central"), RUTs y nombres de esquemas PostgreSQL (`pollo_king_providencia`, `pollo_king_vina`, etc.) tengan `translatable = False` y se mantengan 100% inmutables entre idiomas.

6. **Cobertura de Pruebas**:
   - `oppytec-frontend/src/features/holding-hub/HoldingHub.test.tsx`: 13 pruebas unitarias y de integración pasando (incluye tests específicos de paridad i18n, reactividad FX multi-moneda y regla Pollo King).
   - `oppytec-frontend/src/shared/i18n/i18n.test.tsx`: 13 pruebas pasando con soporte de 26 namespaces.
   - `oppytec-backend/tests/unit/test_holding_hub_i18n_fx.py`: 7 pruebas exhaustivas pasando en Pytest.

---

## 2. Friction & Resoluciones Técnicas

- **Diferencia entre formateo estático y conversión FX**: `formatCurrencyAmount(val, cur)` solo añade el símbolo monetario sin convertir la magnitud numérica. Se actualizó el consumo a `convertAndFormat(val, "CLP", cur)` provisto por `useCurrencyFormatter()`, logrando conversiones exactas y reactivas en toda la interfaz corporativa.
- **Conteo de namespaces i18n**: Al incorporar `holding_hub` (y preexistente `invoices`), la prueba `i18n.test.tsx` fallaba por esperar exactamente 24 namespaces. Se actualizó a 26 y se agregó aserción explícita de `holding_hub`.
- **Enums de Acción en Anomaly Guard**: En las aserciones del backend se alinearon los estados con los literales exactos `AUTO_UPDATED` y `FX_ANOMALY_QUARANTINED` definidos en `anomaly_guard.py`.

---

## 3. Próximo Paso (Traspaso)

Entregar formalmente el informe de la Etapa 3 al agente orquestador (`01-orchestrator-pm`) y habilitar el avance a las etapas subsiguientes (Observabilidad de Métricas Holding Hub, QA Parity e Integración E2E).
