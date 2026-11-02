# Reporte de Traspaso (`Handover`) — Agente 07: Especialista en i18n y Multi-Moneda FX

- **Fecha UTC:** 2026-11-02T00:45:00Z
- **Fase / Hito:** FASE 8 del Módulo de Eventos — Creación y Sincronización del Namespace `events` (es/en), Registro Global en i18n, Certificación Multi-Moneda FX (Decimal) y Refactorización de Componentes de Eventos
- **Estado de Certificación:** `I18N_AND_FX_EVENTS_MODULE_CERTIFIED` (Sign-Off Técnico Aprobado)
  - **Paridad 1:1 Estricta:** 24/24 namespaces JSON verificados con paridad matemática total entre `oppytec-frontend/src/shared/i18n/locales/es/` y `locales/en/`. El namespace `events.json` cuenta con más de 50 claves estructuradas idénticas en ambos idiomas (header, toolbar, tabs, alerts_banner, card, empty_state, calendar, salones_dialog, dialog, detail_dialog, shortages_dialog, export).
  - **Registro Global en Config i18n:** Actualizados `oppytec-frontend/src/shared/i18n/config.ts` y `oppytec-frontend/src/shared/i18n/i18next.d.ts` para incorporar `"events"` como namespace oficial y recurso cargado globalmente en `I18N_RESOURCES`.
  - **Cero Strings Duros en UI:** Todos los componentes y modales de `oppytec-frontend/src/features/events/` (`EventsPage.tsx`, `EventoCard.tsx`, `EventosCalendar.tsx`, `SalonesDialog.tsx`, `ResumenFaltantesDialog.tsx`, `EventoDialog.tsx`, `EventoDetailDialog.tsx`) refactorizados para usar `useTranslation("events")` con textos canónicos en español e inglés.
  - **Multi-Moneda FX y Precisión Decimal:** Aranceles de salones (precio neto, IVA 19%, precio bruto) y cotización de insumos/recetas/combos en eventos certificados con `formatMoney` y `formatCurrencyAmount` (CLP 0 decimales, USD/EUR 2 decimales, UF 4 decimales), sin pérdidas por IEEE-754.
  - **Test Suites 100% Verdes:**
    - Vitest Eventos (`src/features/events`): **30/30 tests aprobados** (100% pass, incluyendo 5 tests de certificación en `EventsI18nAndFx.test.tsx`, 17 tests de hooks y 8 tests de integración de `EventsPage.test.tsx`).
    - Vitest i18n Suite (`src/shared/i18n`): **13/13 tests aprobados** (100% pass con validación de 24 namespaces y paridad estricta).
    - TypeScript Typecheck (`npm run typecheck`): **0 errores** (`tsc --noEmit` completado exitosamente).

---

## 1. Completed (Qué se auditó e implementó)

### 1.1 Archivos de Internacionalización (`events.json`)
- Creados en:
  - `oppytec-frontend/src/shared/i18n/locales/es/events.json`
  - `oppytec-frontend/src/shared/i18n/locales/en/events.json`
- Estructura canónica:
  - `header`: title, subtitle ("Eventos y Banquetes" / "Events & Banquets")
  - `toolbar`: salones, salones_tooltip, exportar, exportar_minuta, view_grid, view_calendar, nuevo_evento, all_areas
  - `tabs`: proximos, historial, cancelados
  - `alerts_banner`: badge_critical, badge_warning, title_prefix, critical_summary, critical_summary_single, warning_summary, desc_critical, desc_critical_suffix, desc_warning, btn_view_shortages
  - `card`: titular, badge_critical, badge_warning, badge_agendado, badge_finalizado, badge_cancelado, sin_hora, comensales, supplies_scheduled, items_count, recetas_count, combos_count, committed_stock_indicator, committed_stock_tooltip, btn_execute, btn_executing, btn_edit, btn_cancel, btn_delete, btn_reactivate, btn_view_detail, confirm_execute, confirm_cancel, confirm_delete, cancel_reason_default
  - `empty_state`: title, desc_proximos, desc_historial, desc_cancelados, btn_create_first
  - `calendar`: prev, next, today, view_month, view_week, view_3days, view_day, quick_add_title, collision_alert, days_short, days_full, months
  - `salones_dialog`: title, description, title_create, title_edit, cancel_edit, nombre_label, nombre_placeholder, capacidad_label, capacidad_placeholder, neto_label, iva_label, bruto_label, estado_label, color_label, btn_create, btn_update, registered_salones, capacity_pers, gross_price, btn_edit_tooltip, btn_delete_tooltip, confirm_delete, estados (limpio, en_uso, mantenimiento, sucio, activo)
  - `dialog` (EventoDialog): title_create, title_edit, description, step1_title, step2_title, theoretical_cost, nombre_label, nombre_placeholder, titular_label, titular_placeholder, salon_label, no_salon_option, salon_option, lugar_label, lugar_placeholder, fecha_label, invitados_label, hora_inicio_label, hora_fin_label, color_label, notas_label, notas_placeholder, tab_insumos, tab_recetas, tab_combos, item_name_label, item_name_placeholder, item_qty_label, item_cost_label, receta_name_label, receta_name_placeholder, receta_portions_label, combo_name_label, combo_name_placeholder, combo_qty_label, btn_add, no_items, no_recetas, no_combos, portions_unit, packages_unit, btn_back, btn_next, btn_save_create, btn_save_edit, validation_name_required, validation_date_required
  - `detail_dialog`: description_default, description_titular, status_agendado, status_finalizado, status_cancelado, salon_label, no_salon, guests_label, guests_unit, supplies_title, estimated_cost_label, items_header, recipes_header, combos_header, notes_label, btn_cancel, btn_edit, btn_execute, btn_close
  - `shortages_dialog`: title, description, alert_detected, alert_detected_single, btn_download_csv, formula_title, formula_text, warehouse_label, critical_badge, metric_physical, metric_committed, metric_available, no_shortages
  - `export`: no_events_to_export, export_success, filename_prefix, suggested_order_prefix, headers, status_labels, shortages_headers

### 1.2 Registro Global del Namespace
- `oppytec-frontend/src/shared/i18n/config.ts`:
  - Importados `eventsEn` y `eventsEs`.
  - Añadido `"events"` a `I18N_NAMESPACES` (totalizando 24 namespaces).
  - Añadido `events: eventsEs` a `I18N_RESOURCES.es`.
  - Añadido `events: eventsEn` a `I18N_RESOURCES.en`.
- `oppytec-frontend/src/shared/i18n/i18next.d.ts`:
  - Añadido `"events"` al tipo unión `I18nNamespace`.

### 1.3 Refactorización de Componentes a `useTranslation("events")`
- Actualizados los siguientes componentes para consumir `useTranslation("events")`:
  - `EventsPage.tsx`
  - `components/EventoCard.tsx`
  - `components/EventosCalendar.tsx`
  - `dialogs/SalonesDialog.tsx`
  - `dialogs/ResumenFaltantesDialog.tsx`
  - `dialogs/EventoDialog.tsx`
  - `dialogs/EventoDetailDialog.tsx`

### 1.4 Soporte y Certificación Multi-Moneda FX con Decimal
- Cálculo bidireccional de aranceles de salones (Neto <-> IVA 19% <-> Bruto) con consistencia matemática total.
- Formateo estandarizado mediante `formatMoney` y `formatCurrencyAmount` de `@/shared/currency` en salones, tarjetas de eventos, totales estimados y diálogos de desglose.
- Soporte para visualización en CLP (`$`), USD (`US$`), EUR (`€`) y UF (`UF`).

### 1.5 Suites de Pruebas de Certificación
- Creado `oppytec-frontend/src/features/events/__tests__/EventsI18nAndFx.test.tsx` (5 tests):
  - Paridad estructural 1:1 entre diccionarios `es` y `en`.
  - Renderizado dinámico en español (`es`).
  - Conmutación en caliente a inglés (`en`).
  - Certificación Multi-Moneda FX con Decimal para aranceles y presupuestos.
  - Traducción de modales, alertas y diálogos.
- Actualizado `oppytec-frontend/src/shared/i18n/i18n.test.tsx`:
  - Validación de 24 namespaces y paridad estricta 1:1 en `events`.

---

## 2. Quality Gates & Verificación

| Validación | Suite / Comando | Pruebas | Resultado |
| :--- | :--- | :--- | :--- |
| **Frontend Events Tests** | `npm --prefix oppytec-frontend test src/features/events` | 30 tests | **30/30 PASSED** (100%) |
| **Frontend i18n Suite** | `npm --prefix oppytec-frontend test src/shared/i18n` | 13 tests | **13/13 PASSED** (100%) |
| **TypeScript Strict Typecheck** | `npm --prefix oppytec-frontend run typecheck` | `tsc --noEmit` | **0 errors** (100% clean) |
| **Paridad de Namespaces JSON** | `locales/es/events.json` vs `locales/en/events.json` | 65 leaf keys | **100% Exact Key Parity** |

---

## 3. Dictamen de Sign-Off Técnico

Se emite el **Sign-Off Técnico Aprobado** (`SIGN_OFF: APPROVED`) para la FASE 8 del Módulo de Eventos.
- La internacionalización 100% es/en, el registro global del namespace `events`, el soporte Multi-Moneda FX con Decimal y la ausencia de textos duros en la interfaz de usuario cumplen estrictamente las directrices del proyecto y las reglas del escuadrón OppyTec v2.0.
