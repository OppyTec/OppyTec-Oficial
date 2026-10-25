# 📋 PLAN MAESTRO DE CONTROL Y EJECUCIÓN: GESTIÓN DE PRODUCTOS (`/gestion?tab=productos`)

> **Regla de Gobernanza:** Este documento es el tablero de control de ejecución estricto.  
> Cada paso debe ser **100% corroborado y aprobado** antes de pasar al siguiente.  
> **Solo cuando se finalicen todos los pasos**, este documento podrá ser eliminado, no antes.  
> **Fuente de Verdad (Solo Lectura):** `OppyTec-Legacy/OppyTec_Frontend/src/pages/Gestion/`  
> **Destino:** `oppytec-frontend/src/features/gestion/`

---

## 📊 Estado General del Proyecto

- [x] **Fase 1:** Arquitectura de Datos, Tipos y Hook de Estado Resiliente (`useGestion.ts`) — **COMPLETADA**
- [x] **Fase 2:** Toolbar Unificado, Filtros de Ámbito, Carrusel de Categorías y Paginador — **COMPLETADA**
- [x] **Fase 3:** Tabla Multidimensional de Productos (30+ Columnas) y Vista Móvil Adaptativa — **COMPLETADA**
- [x] **Fase 4:** Modales de Soporte de Tabla, Categorías, Catálogos y Transferencia — **COMPLETADA**
- [x] **Fase 5:** Modal Multicanal `ProductoWizardDialog` (Wizard Manual en 4 Pasos con Drafting) — **COMPLETADA**
- [x] **Fase 6:** Módulos de Ingesta Inteligente: `ExcelImportModal` (IA) y `FacturaImportModal` (IA OCR/DTE) — **AUDITADA Y COMPLETADA**
- [ ] **Fase 7:** Cobertura de Internacionalización (i18n 100% `es`/`en` y 0 Textos Hardcodeados)
- [ ] **Fase 8:** Montaje de Rutas, Suites de Pruebas Unitarias/Integración (Vitest), Compilación y Verificación E2E

---

## 🔍 Detalle y Criterios de Aceptación por Fase

---

### [x] FASE 1: Arquitectura de Datos, Modelos y Tipos — ✅ 100% COMPLETADA
- [x] **1.1** Crear `oppytec-frontend/src/features/gestion/types.ts` con todos los contratos de dominio:
  - `Producto`, `Categoria`, `Marca`, `TipoEnvase`, `BodegaConfig`, `PresentacionCompra`.
  - Definición tipada de las 30+ columnas (`ALL_COLUMNS`, `ColumnKey`, `COLUMN_WIDTHS`).
  - Tipos de presets de tabla (`TablePreset`, `SortOption`).
- [x] **1.2** Implementar el hook `useGestion.ts` en `oppytec-frontend/src/features/gestion/useGestion.ts`:
  - Conexión a la API con fallback a un mock inicial completo y representativo (0 pantallas en blanco).
  - Manejo de estados de carga, error y sincronización reactiva.
  - Métodos CRUD para productos, categorías, marcas y formatos de envase.
- [x] **1.3** Corroborar tipado estricto con `npx tsc --noEmit` y suite de pruebas unitarias (15/15 tests aprobados en `useGestion.test.ts`).

---

### [x] FASE 2: Toolbar Unificado, Filtros de Ámbito, Carrusel de Categorías y Paginación — ✅ 100% COMPLETADA
- [x] **2.1** Construir la cabecera `SectionHeader` con título "Gestión de Productos", subtítulo "Catálogo de productos e insumos", ícono `Package` y color ámbar `#eab308`.
- [x] **2.2** Implementar el Banner de Recuperación de Borrador (`Draft Recovery Banner`):
  - Detección reactiva en `localStorage` de borradores incompletos (`oppytec_producto_draft`).
  - Muestra nombre en borrador, paso (1-4), botón "Descartar" y botón "Recuperar Borrador".
- [x] **2.3** Construir el Toolbar unificado (Desktop y Mobile):
  - Selector de Área Operativa (`AreaSelector`).
  - Selector de Bodegas (`BodegaSelector`).
  - Menú desplegable *"Tabla"* con submenús para plantillas públicas, privadas y personalizar vista.
  - Menú desplegable *"Categorías"* con acceso a administrar categorías y toggle mostrar/ocultar.
  - Botón *"Catálogos"* (marcas y envases).
  - Menú *"Acciones"* con opción "Transferir Stock".
  - Botón primario `+ Producto` con guardia RBAC `<Can perform="catalog.products.create">`.
- [x] **2.4** Implementar la barra de búsqueda en tiempo real con debounce persistente.
- [x] **2.5** Implementar el carrusel de categorías (`CategoriaSeccion.tsx`):
  - Badges con `CategoryIcon` y color HEX personalizado.
  - Soporte de multi-selección con animación suave (`framer-motion`) y resplandor activo.
- [x] **2.6** Integrar el paginador `TablePagination` (10, 30, 50, 100 con elipsis y botones extremos).

---

### [x] FASE 3: Tabla Multidimensional de Productos y Vista Móvil Adaptativa — ✅ 100% COMPLETADA
- [x] **3.1** Implementar `CategoryTableWrapper.tsx` para sincronización de scroll horizontal entre categorías con middle-click pan.
- [x] **3.2** Implementar la tabla de productos con soporte para las 30+ columnas configurables:
  - **📦 Stock y Logística:** Bodega, Ubicación física, Stock Actual con barra cromática de nivel, Stock Mínimo, Contenido Total con indicador 💧 útil.
  - **💰 Costos de Compra:** Último costo unitario/embalaje neto y bruto, Penúltimo costo, Variación inflacionaria % (🔴 +X% o 🟢 -X%), Costo PPP neto y bruto, Costo histórico.
  - **🏷️ Ventas y Márgenes:** Precio de venta neto y bruto, Margen neto y bruto %, Valor de inventario neto y bruto.
  - **⏳ Rotación y Autonomía:** Días de cobertura, Índice de rotación mensual.
- [x] **3.3** Formateadores monetarios y porcentuales según configuración regional FX y moneda activa (`formatMoney`, `formatUnitCost`).
- [x] **3.4** Modos de visualización: Agrupado por Categoría (con acordeones colapsables y badges de conteo) y Lista Simple continua.
- [x] **3.5** Vista móvil adaptativa (Mobile-First):
  - Tarjetas colapsadas con información esencial y touch targets >= 44px (`ProductMobileCard.tsx`).
  - Acordeón expandible para ver desglose por bodega, costos y acciones rápidas.

---

### [x] FASE 4: Modales de Soporte de Tabla, Categorías, Catálogos y Transferencia — ✅ 100% COMPLETADA
- [x] **4.1** Implementar `TableConfigModal.tsx`:
  - Selector y reordenamiento de 30+ columnas visibles por sección.
  - Toggles para alternar columnas de valores Netos vs Brutos ("Todo Neto" / "Todo Bruto").
  - Guardado y selección de presets de tabla públicos (`SYSTEM_PRESETS`) y privados en `localStorage`.
- [x] **4.2** Implementar `AdministradorCategoriasDialog.tsx`:
  - CRUD completo de categorías con asignación de iconos y paleta de colores.
  - Pestaña de matriz interactiva de áreas operativas con checkboxes accesibles.
- [x] **4.3** Implementar `CatalogosManagerDialog.tsx`:
  - Gestión de Familias, Marcas y Catálogo de Formatos/Envases con búsqueda predictiva.
- [x] **4.4** Implementar `TransferDialog.tsx`:
  - Diálogo para registrar transferencias de stock entre bodegas con validación origen-destino y cálculo reactivo de existencias.

---

### [x] FASE 5: Modal Multicanal `ProductoWizardDialog` (Wizard Manual en 4 Pasos) — ✅ 100% COMPLETADA
- [x] **5.1** Cabecera multicanal con conmutador: Wizard Manual, Importar Excel IA, Factura IA.
- [x] **5.2** Paso 1 (Básico & Familia):
  - Nombre comercial, Marca (con selector y creación rápida al vuelo), SKU/Código de barras/PLU.
  - Categoría y Subcategoría, Áreas operativas asignadas, Tipo (Insumo / Venta / Mixto), Foto con carga y preview.
- [x] **5.3** Paso 2 (Envases & Packs):
  - Unidad base de medida (kg, L, un, g, mL), Envase primario con creación al vuelo.
  - Presentaciones de compra / Embalajes múltiples (Caja x6, Pack x12, etc.) con factores de conversión y subtítulo formateado.
- [x] **5.4** Paso 3 (Bodegas & Stock):
  - Distribución por bodega, asignación de ubicación física (Pasillo/Estante), Stock mínimo y máximo.
- [x] **5.5** Paso 4 (Precios & Costos):
  - Costos de adquisición netos y brutos, precio de venta.
  - Tarjetas reactivas de KPIs financieros calculadas al vuelo por `calculateFinancialKPIs`: Food Cost %, Margen Neto %, Margen Bruto % y Markup %.
- [x] **5.6** Banner superior de Nombre Autogenerado estándar ERP en vivo (`generateFullProductName`).
- [x] **5.7** Autoguardado reactivo continuo en `localStorage` (`oppytec_producto_draft`) con indicadores de estado de guardado.

---

### [x] FASE 6: Módulos de Ingesta Inteligente (Excel IA y Facturas IA) — ✅ 100% AUDITADA Y COMPLETADA
- [x] **6.1** Módulo Excel Import IA (`ExcelImportModal/`):
  - Drag & drop de archivos (.xlsx, .xls, .csv).
  - Sanitización estricta Anti-Formula Injection (CWE-1236).
  - Detección heurística e inteligente de columnas (`ExcelColumnMatcher`).
  - Pipeline de análisis en 5 etapas con barra de progreso.
  - `ExcelEntityMatcherBanner` para resolver marcas y categorías nuevas.
  - Rejilla de revisión interactiva (`ExcelImportReviewGrid`) previa a la confirmación.
  - Descarga de plantilla oficial (`ExcelTemplateDownloader`).
- [x] **6.2** Módulo Facturas IA (`FacturaImportModal/`):
  - Ingesta de Facturas Electrónicas (PDF o XML DTE).
  - Extracción de metadatos (RUT, Razón Social, Folio, Montos, IVA).
  - `FacturaSupplierBanner` con alta rápida de nuevos proveedores (`ProveedorDialog`).
  - Rejilla de extracción de líneas de factura (`FacturaReviewGrid`).
  - Mapeo de insumos hacia el Kardex existente o creación como nuevos.
  - Selector de unidad de medida (`UnidadMedidaCombobox`) y bodega receptora.
  - Borrador persistente de factura en proceso (`oppytec_factura_ia_draft`).

---

### [x] FASE 7: Internacionalización (i18n 100% `es`/`en`) — ✅ 100% CERTIFICADA
- [x] **7.1** Crear archivos de traducción completos en:
  - `oppytec-frontend/src/shared/i18n/locales/es/gestion.json` y `en/gestion.json` (140 claves c/u)
  - `locales/es/products.json` y `en/products.json` (83 claves c/u)
  - `locales/es/excel_import.json` y `en/excel_import.json` (121 claves c/u)
  - `locales/es/factura_import.json` y `en/factura_import.json` (66 claves c/u)
- [x] **7.2** Registrar los namespaces en `config.ts` e `i18next.d.ts` (19 namespaces registrados con tipado estricto).
- [x] **7.3** Verificar 0 strings hardcodeadas en toda la interfaz con fallbacks seguros contra pantallas en blanco.

---

### [ ] FASE 8: Montaje de Rutas, Pruebas Unitarias, Compilación y Verificación
- [x] **8.1** Montar en `oppytec-frontend/src/app/router.tsx` la ruta `/gestion` hacia `<GestionPage />`.
- [x] **8.2** Escribir suite exhaustiva de pruebas unitarias y de integración (`GestionPage.test.tsx`) con 100% passing (12/12 tests).
- [x] **8.3** Ejecutar `npx tsc --noEmit` y `npm test` verificando cero errores y regresiones (133/133 tests frontend, 235/235 tests backend, 0 errores TypeScript/Linter).
- [x] **8.4** Reconstruir imagen de Docker frontend (`docker compose build frontend && docker compose up -d frontend`) — Completado y en ejecución.
- [ ] **8.5** Ejecutar pruebas visuales automatizadas con Playwright (Agente 13) — *Pospuesto a solicitud del usuario para realizarse más adelante*.
- [x] **8.6** Sincronización del Grafo AST con Graphify (`python scripts/harness.py sync-graph`) — Sincronizado (83 nodos, 111 aristas).
