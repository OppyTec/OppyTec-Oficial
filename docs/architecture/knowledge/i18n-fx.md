# Conocimiento de Dominio: Internacionalización (i18n `es`/`en`) & Multi-Moneda FX con Precisión `Decimal` (`recipes`)

## 1. Arquitectura i18n en `oppytec-frontend`
- **Configuración:** `src/shared/i18n/config.ts` y tipado estricto en `src/shared/i18n/i18next.d.ts`.
- **Namespaces JSON:** `src/shared/i18n/locales/es/recipes.json` y `src/shared/i18n/locales/en/recipes.json` mantienen paridad exacta 1:1 en todas las rutas de hojas e interpolaciones `{{...}}`.
- **Estructura del Namespace `recipes`:**
  - `header`: Títulos y subtítulos de `SectionHeader` para Recetas (`#f59e0b`) y Combos (`#ec4899`).
  - `tabs`: Navegación unificada de 3 pestañas (`productos`, `recetas`, `combos`) en `GestionTabNav.tsx`.
  - `toolbar`: Buscadores, selectores de categorías y filtros de tipo (`all`, `dynamic`, `static`, `subrecipes`) en `RecetasToolbar.tsx` y `CombosToolbar.tsx`.
  - `badges`: Indicadores visuales (`Dinámica`, `Fija`, `Sub-receta`, `Disponible`, `Sin stock`, semáforos de margen).
  - `table.recipes` y `table.combos`: Cabeceras, resúmenes de estructura ($N$ insumos fijos + $M$ grupos dinámicos), tooltips y acciones rápidas.
  - `mobile_card`: Etiquetas compactas y botones táctiles $\ge 44\text{px}$ para `RecetaMobileCard.tsx` y `ComboMobileCard.tsx`.
  - `views`: Confirmaciones, alertas y estados de carga en `RecetasView.tsx`, `CombosView.tsx` y `GestionPage.tsx`.
  - `modals.recipe`, `modals.combo`, `modals.option_group`, `modals.recipe_detail`: Textos de formularios en 3 pasos, paneles de escandallo en vivo, selectores de biblioteca y ficha técnica imprimible.
  - `allergens`: Nombres bilingües y descripciones sanitarias de los 14 alérgenos normados (`AllergenBadge.tsx`).

## 2. Motor Multi-Moneda FX Determinista (0 Floats Contables)
- **Aritmética de Punto Fijo ($10^8$ `BigInt`):**
  - Implementada en `src/shared/currency/currencyEngine.ts` (`parseScaledDecimal`, `formatScaledDecimal`, `convertAmountExact`, `formatCurrencyAmount`).
  - Soporta 5 divisas: `CLP` (0 decimales), `USD` (2 decimales), `EUR` (2 decimales), `BRL` (2 decimales) y `UF` (4 decimales).
- **Integración en Componentes de Recetas y Combos:**
  - `useCurrencyFormatter()` expone `convertAndFormat(amount, fromCurrency)` conectado reactivamente al `CurrencyProvider` global, con fallback determinista a `CLP` cuando se renderiza fuera del provider.
  - `formatMoney(value, currency, fromCurrency)` en `src/shared/lib/utils.ts` delega directamente en `convertAmountExact` y `formatCurrencyAmount`.
  - `calculateIngredientTotalCost(cantidad, mermaPct, costoUnitario)` en `RecetaDialog.tsx` opera exclusivamente con `BigInt` escalado ($10^8$) para evitar derivas IEEE 754 (ej. `0.1 + 0.2`).
