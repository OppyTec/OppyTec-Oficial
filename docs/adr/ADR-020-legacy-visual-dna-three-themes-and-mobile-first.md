# ADR-020: Preservación del ADN Visual de `OppyTec-Legacy` (3 Temas `light`/`dark`/`ocean-blue`, 42 Colores, 49 Íconos) y Arquitectura *Mobile-First*

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_sistema_diseno_ux_ui_y_mobile_first_001.md` / `specs/04-DESIGN-SYSTEM.md`

---

## 1. Contexto

En las refactorizaciones impulsadas por IA es frecuente que los agentes reemplacen la identidad visual original de un producto por plantillas genéricas en blanco y negro o diseñen tablas anchas de escritorio que resultan inutilizables cuando un cocinero, bodeguero o administrador opera desde su teléfono móvil en terreno.

## 2. Decisión

Blindar por contrato el **ADN Visual de `OppyTec-Legacy`** enriqueciéndolo con una arquitectura **100% *Mobile-First* (`360px -> 768px -> 1280px`)**:

1. **Preservación Inmutable de los 3 Temas Canónicos (`ThemeProvider`):**
   - `light`: Tema claro corporativo de alto contraste para oficinas y cocinas iluminadas.
   - `dark`: Tema oscuro profundo (`#0f172a` / `#1e293b`) para operación nocturna y barras.
   - `ocean-blue`: Tema insignia marino de OppyTec (`--bg-ocean-deep`, acentos cian/turquesa y superficies *glassmorphism*).
2. **Catálogo Completo de 42 Tokens de Color y 49 Íconos Semánticos (`IconRegistry.tsx`):**
   - Ningún componente React puede usar colores hexadecimales quemados (`#...`) fuera de `design-tokens.css` y `tailwind.config.ts`.
   - Se preservan los 49 íconos semánticos (`lucide-react`) y las micro-interacciones (`hover-lift`, `glass-panel`, `pulse-badge`) de `OppyTec-Legacy`.
3. **Ley de Diseño *Mobile-First* y `<ResponsiveDataView />`:**
   - Toda vista se construye primero para pantallas móviles de `360px` de ancho con áreas táctiles mínimas de `44x44 px` (WCAG AAA) y barra de navegación inferior (`<MobileBottomNav />`).
   - Se prohíben las tablas HTML desbordadas en móvil: el componente `<ResponsiveDataView />` renderiza automáticamente tarjetas táctiles accionables en pantallas `< 768px` (`md`) y tablas densas ordenables en escritorio `>= 768px`.

## 3. Consecuencias

- **Positivas:**
  - Continuidad visual total para los usuarios actuales de `OppyTec-Legacy`, sumada a una ergonomía móvil superior en bodegas, cocinas y salones.
  - Cambio instantáneo entre los 3 temas (`light`, `dark`, `ocean-blue`) sin recargar la página.
- **Negativas / Trade-offs:**
  - Prohibido introducir tablas crudas `<table>` en vistas de negocio sin envolverlas en `<ResponsiveDataView />`.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca:** `oppytec-backend/tests/architecture/test_ui_design_tokens_and_mobile_first.py`.
- **Invariante Verificada:** Verifica la existencia de los 3 temas (`light`, `dark`, `ocean-blue`) en `design-tokens.css`, los 49 íconos en `IconRegistry.tsx`, la ausencia de colores hexadecimales hardcodeados en `src/features/` y el cumplimiento de breakpoints *Mobile-First*.
