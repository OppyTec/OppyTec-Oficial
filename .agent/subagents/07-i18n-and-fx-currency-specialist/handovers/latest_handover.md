# Reporte de Traspaso (`Handover`) — Agente 07: Especialista en i18n y Multi-Moneda FX

- **Fecha UTC:** 2026-10-26T23:05:00Z
- **Fase / Hito:** Fase 7.1 y 7.2 — Internacionalización 100% `es`/`en`, Regla Inmutable "Pollo King" y Multi-Moneda FX con Precisión `Decimal` — [`PLAN_MAESTRO_OPPYFY_AI.md`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/PLAN_MAESTRO_OPPYFY_AI.md)
- **Estado de Certificación:** `I18N_AND_FX_OPPYFY_AI_CERTIFIED`
  - Vitest OppyFy Feature Suites (`OppyfyI18nAndFx.test.tsx`, `OppyfyGovernance.test.tsx`, `OppyfyView.test.tsx`, `useOppyfyHooks.test.ts`): **51/51 tests aprobados** (100% pass en 3.16s).
  - Vitest Shared i18n Suite (`i18n.test.tsx`): **10/10 tests aprobados** (100% pass en 1.36s).
  - Vitest Shared Currency Suite (`currency.test.tsx`): **4/4 tests aprobados** (100% pass en 1.31s).
  - Paridad 1:1 Estricta: 159/159 claves simétricas en `oppyfy.json` (`es`/`en`) y 526/526 claves en `platform_admin.json`.
  - Invariante "Pollo King": Preservación inmutable verificada (jamás traducido a "Chicken King" ni modificado sintácticamente).
  - Multi-Moneda FX: Formateo exacto en CLP ($) sin decimales, USD (US$) con 2 decimales, UF con 4 decimales, punto fijo 10^8 (`parseScaledDecimal`), cero floats contables.

## 1. Completed (Qué se implementó)

### 1.1 Tarea 7.1 — Auditoría y Paridad 1:1 `es`/`en` y Regla Inmutable Pollo King
- **Sincronización 1:1 de catálogos i18n:**
  - [`oppytec-frontend/src/shared/i18n/locales/es/oppyfy.json`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/src/shared/i18n/locales/es/oppyfy.json) y [`oppytec-frontend/src/shared/i18n/locales/en/oppyfy.json`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/src/shared/i18n/locales/en/oppyfy.json):
    - Cobertura integral de secciones: `common`, `chat`, `canvas`, `governance`, `domains`, `grants`, `wallets`, `edit_wallet_modal`, `buy_pack_modal`, `audit`.
    - Eliminación de cadenas hardcodeadas en modales de gobernanza: `status_enabled`, `status_disabled`, `success_message`, `final_price_label`, `processing`, `close_aria`, `error_invalid_ceiling`, `error_save`, `current_consumption`, `saving`.
    - Verificación de {{placeholders}} idénticos sin claves huérfanas.
- **Regla Inmutable "Pollo King":**
  - Validación de presencia de "Pollo King" en `IMMUTABLE_PROPER_NOUNS`.
  - Validación de `resolveDynamicFieldI18n` garantizando que registros comerciales como "Pollo King" jamás devuelvan traducciones forzadas ("Chicken King", "Rey del Pollo").
  - Preservación en sugerencias rápidas (`chat.suggestion_fefo`), síntesis de canvas (`rollover_modal.default_summary`) y paquetes de créditos IA ("Pack Enterprise Pollo King").

### 1.2 Tarea 7.2 — Multi-Moneda FX con Precisión `Decimal`
- **Integración de formateo seguro en UI:**
  - [`BuyCreditPackModal.tsx`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/src/features/oppyfy/components/governance/BuyCreditPackModal.tsx): Adopción de `formatCurrencyAmount` de `@/shared/currency/useCurrencyFormatter` para montos en CLP (`$15.000 CLP`) y USD (`US$15.00`), garantizando formateo contable exacto sin deriva IEEE-754.
  - [`EditWorkerWalletModal.tsx`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/src/features/oppyfy/components/governance/EditWorkerWalletModal.tsx): Mensajes de validación y límites en formato i18n reactivo.
  - [`OppyfyWorkerWalletsManager.tsx`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/src/features/oppyfy/components/governance/OppyfyWorkerWalletsManager.tsx): Estados Habilitado/Enabled e Inhabilitado/Disabled internacionalizados.
- **Suite de Pruebas Automatizadas:**
  - Nueva suite [`OppyfyI18nAndFx.test.tsx`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/src/features/oppyfy/__tests__/OppyfyI18nAndFx.test.tsx) con 15 pruebas unitarias exhaustivas que certifican paridad, inmutabilidad, fixed-point math, circuito de anomalía FX y componentes visuales.

## 2. Quality Gates & Verificación

| Validación | Comando | Resultado |
| :--- | :--- | :--- |
| **Vitest OppyFy i18n & FX Suite** | `pnpm vitest run src/features/oppyfy/__tests__/OppyfyI18nAndFx.test.tsx` | **15/15 tests aprobados** (100% pass) |
| **Vitest All OppyFy Suites** | `pnpm vitest run src/features/oppyfy/__tests__/` | **51/51 tests aprobados** (100% pass) |
| **Vitest Shared i18n Suite** | `pnpm vitest run src/shared/i18n/i18n.test.tsx` | **10/10 tests aprobados** (100% pass) |
| **Vitest Shared Currency FX Suite** | `pnpm vitest run src/shared/currency/currency.test.tsx` | **4/4 tests aprobados** (100% pass) |

## 3. Friction & Failures
- **Ubicación de clave `default_summary`:** Se detectó inicialmente una discrepancia en la ruta del JSON (`rollover_modal.default_summary` en lugar de `canvas.default_summary`). Fue corregida en la prueba para apuntar a la ruta canónica.

## 4. Next Exact Action
- Enviar reporte final al agente coordinador (ID: `d0212433-cb68-4d01-aea7-ef017fe152b9`) para habilitar la Fase 8 (Observabilidad y Telemetría OTEL / Prometheus / Loki) o fases subsecuentes del Plan Maestro OppyFy AI.
