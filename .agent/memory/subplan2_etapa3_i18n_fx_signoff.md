# Certificación Formal de i18n y Multi-Moneda FX — Sub-Plan 2: Switch Maestro, Presets Gastronómicos & Factory Reset

**Fecha:** 2026-11-05  
**Agente Responsable:** Agente 07 (`07-i18n-and-fx-currency-specialist`)  
**Módulo:** Consola `Lab & QA Sandbox` (`platform-admin/sandbox/`)  
**Estado:** **APROBADO & CERTIFICADO (100% Cobertura)**

---

## 1. Alcance de la Auditoría y Cobertura 1:1

Se ejecutó una auditoría exhaustiva de internacionalización (i18n) en español (`es`) e inglés (`en`) sobre todos los artefactos del **Sub-Plan 2**:
- `oppytec-frontend/src/features/platform-admin/sandbox/MockDataSandboxView.tsx`
- `oppytec-frontend/src/features/platform-admin/sandbox/presets/`
  - `types.ts`
  - `fastFoodPolloKing.ts`
  - `carnesAngusCava.ts`
  - `hotelDesayunoBuffet.ts`
  - `cleanSlate.ts`
  - `index.ts`
- `oppytec-frontend/src/shared/i18n/locales/es/platform_admin.json`
- `oppytec-frontend/src/shared/i18n/locales/en/platform_admin.json`
- `oppytec-frontend/src/features/platform-admin/sandbox/__tests__/SandboxI18nAndFx.test.tsx`

### 1.1 Matriz de Paridad 1:1 de Presets Gastronómicos

| Preset ID | Clave i18n | Español (`es`) | Inglés (`en`) | Cumplimiento |
| :--- | :--- | :--- | :--- | :---: |
| `fast-food-pollo-king` | `title` | Fast Food & Pollo King | Fast Food & Pollo King | **100% Invariante** |
| | `subtitle` | Cadena de comida rápida, freidoras, combos express y alta rotación | Fast food chain, fryers, express combos, and high turnover | **100% Paridad** |
| | `description` | Cadena de comida rápida, freidoras, combos express y packaging. | Fast food chain, fryers, express combos and packaging. | **100% Paridad** |
| | `badge` | ALTA ROTACIÓN | HIGH ROTATION | **100% Paridad** |
| `carnes-angus-cava` | `title` | Carnes Angus & Cava | Angus Steaks & Wine Cellar | **100% Paridad** |
| | `subtitle` | Steakhouse premium, cortes dry-aged madurados y cava subterránea | Premium steakhouse, dry-aged matured cuts, and underground cellar | **100% Paridad** |
| | `description` | Steakhouse premium, cortes dry-aged y cava subterránea. | Premium steakhouse, dry-aged cuts and underground cellar. | **100% Paridad** |
| | `badge` | ALTA GAMA | PREMIUM | **100% Paridad** |
| `hotel-desayuno-buffet` | `title` | Hotel & Desayuno Buffet | Hotel & Breakfast Buffet | **100% Paridad** |
| | `subtitle` | Hospitality, estaciones buffet matutino, panadería artesanal y eventos | Hospitality, morning buffet stations, artisan bakery, and events | **100% Paridad** |
| | `description` | Hospitality, estaciones buffet matutino y panadería. | Hospitality, morning buffet stations and bakery. | **100% Paridad** |
| | `badge` | HOSPITALITY | HOSPITALITY | **100% Paridad** |
| `clean-slate` | `title` | Clean Slate (Base Virgen) | Clean Slate (Virgin DB) | **100% Paridad** |
| | `subtitle` | Base de datos 100% limpia para verificar Empty States auténticos y onboarding | 100% clean database to verify authentic Empty States and onboarding | **100% Paridad** |
| | `description` | Base de datos 100% limpia para verificar Empty States. | 100% clean database to verify Empty States. | **100% Paridad** |
| | `badge` | EMPTY STATE | EMPTY STATE | **100% Paridad** |

### 1.2 Modal Factory Reset, Master Switch y Métricas KPI

Se certificaron sin strings duros visibles:
- **Switch Maestro**:
  - `master_switch_title_demo`: "Cambiar a BD Limpia" / "Switch to Clean DB"
  - `master_switch_title_clean`: "Cambiar a Modo Demo" / "Switch to Demo Mode"
  - `master_switch_badge_demo`: "Modo Demo" / "Demo Mode"
  - `master_switch_badge_clean`: "Clean DB" / "Clean DB"
- **Modal Factory Reset**:
  - `factory_reset_title`: "Restablecer a Valores de Fábrica" / "Restore Factory Defaults"
  - `factory_reset_desc`: "Restaura el esquema y borra mutaciones locales." / "Restores schema and clears local mutations."
  - `factory_reset_confirm`: "¿Estás seguro de que deseas ejecutar el Factory Reset en el esquema {{schema}}?" / "Are you sure you want to execute Factory Reset on schema {{schema}}?"
  - `factory_reset_btn_confirm`: "Confirmar Factory Reset" / "Confirm Factory Reset"
  - `factory_reset_btn_cancel`: "Cancelar" / "Cancel"
  - `factory_reset_success`: "Factory Reset completado exitosamente" / "Factory Reset completed successfully"
  - `factory_reset_error`: "Error durante Factory Reset" / "Error during Factory Reset"
- **Métricas KPI**:
  - `kpi_skus`: "SKUs" / "SKUs"
  - `kpi_warehouses`: "Bodegas" / "Warehouses"
  - `kpi_fefo_batches`: "Lotes FEFO" / "FEFO Batches"
  - `kpi_recipes`: "Recetas" / "Recipes"
  - `kpi_critical`: "Críticos" / "Critical"
  - `kpi_stock_value`: "Valor Stock" / "Stock Value"
  - `schema_prefix`: "Esquema" / "Schema"

---

## 2. Invariante Estricta de Nombres Propios: Regla "Pollo King"

En estricta observancia de las reglas inmutables de OppyTec v2.0:
- **"Pollo King"** se encuentra protegido en el conjunto canónico `IMMUTABLE_PROPER_NOUNS`.
- Tanto en `es/platform_admin.json` como en `en/platform_admin.json`, el preset se titula exactamente `"Fast Food & Pollo King"`.
- Los datasets canónicos preservan nombres propios en todas sus entidades:
  - `defaultHoldingName`: `"Pollo King Chile Holding"`
  - `razonSocial`: `"Gastronomía Rápida Pollo King SpA"`
  - `nombre` sucursal: `"Pollo King Mall Plaza Vespucio"`
- Se verificó mediante prueba unitaria que cualquier intento de traducción espuria (ej: "Chicken King") es bloqueado por el resolvedor dinámico y las aserciones de test.

---

## 3. Precisión Monetaria Decimal y Multi-Moneda FX

Todos los montos monetarios de los presets gastronómicos son procesados exclusivamente a través de `formatMoney` (`Decimal` / `bigint` escala fija $10^8$ sin pérdida por coma flotante IEEE-754):

| Preset Gastronómico | Volumen CLP | Formateo Canónico CLP | Formateo FX USD (Tasa BCCh $960) | Formateo FX EUR (Tasa BCE $1040) |
| :--- | :---: | :---: | :---: | :---: |
| **Fast Food & Pollo King** | 3.850.000 CLP | `$3.850.000` | `US$4,010.42` | `€3.701,92` |
| **Carnes Angus & Cava** | 8.940.000 CLP | `$8.940.000` | `US$9,312.50` | `€8.596,15` |
| **Hotel & Desayuno Buffet** | 4.120.000 CLP | `$4.120.000` | `US$4,291.67` | `€3.961,54` |
| **Clean Slate** | 0 CLP | `$0` | `US$0.00` | `€0,00` |

---

## 4. Resultados de Verificación de Tests Automatizados

Ejecución de suites Vitest de i18n y Platform Admin Sandbox:
- **Sandbox Tests:** `4 passed | 66 passed (66 tests)`
  - `MockDataMasterSwitchAndPresets.test.tsx`: 21/21 passed
  - `SandboxI18nAndFx.test.tsx`: 17/17 passed
  - `SandboxViews.test.tsx`: 14/14 passed
  - `SandboxApiAndTelemetry.test.ts`: 14/14 passed
- **Suite Global de i18n & FX (10 archivos de prueba):** `10 passed | 92 passed (92 tests)`
  - `src/shared/i18n/i18n.test.tsx` (PASS)
  - `src/shared/currency/currency.test.tsx` (PASS)
  - `src/features/platform-admin/sandbox/__tests__/SandboxI18nAndFx.test.tsx` (PASS)
  - `src/features/platform-admin/jev/__tests__/JevConsumptionI18nAndFx.test.tsx` (PASS)
  - `src/features/inventory/alerts/__tests__/AlertasI18nAndFX.test.tsx` (PASS)
  - `src/features/gestion/__tests__/RecipesI18nAndFx.test.tsx` (PASS)
  - `src/features/events/__tests__/EventsI18nAndFx.test.tsx` (PASS)
  - `src/features/projection/__tests__/projectionI18n.test.tsx` (PASS)
  - `src/features/procurement/__tests__/i18n_and_fx_procurement.test.ts` (PASS)
  - `src/features/oppyfy/__tests__/OppyfyI18nAndFx.test.tsx` (PASS)

---

## 5. Dictamen Formal

El Agente 07 (`07-i18n-and-fx-currency-specialist`) emite dictamen de **CONFORMIDAD PLENA**:
- Cero strings duros en vistas de sandbox y presets gastronómicos.
- Paridad 1:1 estricta entre namespaces inglés y español.
- Protección inviolable del nombre propio "Pollo King".
- Precisión decimal libre de fallos IEEE-754 en todos los cálculos monetarios.
