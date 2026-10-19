# ADR-014: Internacionalización (`i18n`) Full-Stack Estática y Dinámica con Protección de Nombres Propios (`"Pollo King"`) y Minimalismo `Pi`

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_internacionalizacion_i18n_multilenguaje_001.md` / `.agent/skills/i18n_manager/SKILL.md`

---

## 1. Contexto

En un ERP SaaS internacional para gastronomía y hotelería, traducir únicamente las etiquetas estáticas de la interfaz (botones y menús) deja la mitad de la pantalla en el idioma original porque los nombres de insumos (`"Helado de Chocolate"`), cargos (`"Jefe de Cocina"`) y categorías son ingresados dinámicamente por los usuarios. Sin embargo, traducir ciegamente todos los datos del cliente mediante un traductor automático corrompe las marcas comerciales y razones sociales de proveedores (convirtiendo erróneamente `"Pollo King"` en `"Chicken King"`).

## 2. Decisión

Implementar un motor de **Internacionalización (`i18n`) Full-Stack de Doble Capa (Estática + Dinámica)** con **Selector Visual de Bandera SVG (`🇪🇸 ES` / `🇺🇸 EN`)**, **Protección de Nombres Propios** y el patrón de **Minimalismo de Contexto `Pi`**:

1. **Capa 1 — `i18n` Estática (11 Namespaces JSON con Paridad 1:1 `es`/`en`):**
   - Prohibición absoluta de strings quemados en componentes React o mensajes de error FastAPI.
   - Los 11 namespaces canónicos (`common`, `auth`, `dashboard`, `catalog`, `inventory`, `waste`, `recipes`, `procurement`, `operations`, `oppyfy`, `admin`) mantienen paridad exacta de claves verificada en el *Fast Gate*.
2. **Capa 2 — `i18n` Dinámica de Datos del Cliente con Memoria Global (`public.i18n_translation_memory`):**
   - Los conceptos descriptivos creados por el cliente (productos genéricos, categorías, unidades de medida, nombres de roles/cargos) almacenan sus traducciones en columnas JSONB (`nombre_i18n: {"es": "Helado de Chocolate", "en": "Chocolate Ice Cream"}`).
   - Antes de traducir un término nuevo, se consulta la tabla global `public.i18n_translation_memory` indexada por hash normalizado; si ya existe, se reutiliza en `0 ms` y con `0 tokens`.
3. **Escudo de Inmutabilidad de Nombres Propios y Marcas (`"Pollo King"`):**
   - Los nombres de proveedores, razones sociales, marcas registradas, SKUs y nombres de sucursales están marcados como **inmutables** (`proper_noun_guard.py` asistido por `JEV Boolean`). Jamás se traducen (`"Pollo King"` permanece siempre como `"Pollo King"` en cualquier idioma).
4. **Patrón de Minimalismo `Pi` (`i18n_manager.py` CLI):**
   - Para evitar que los agentes de IA carguen archivos JSON de miles de líneas en su ventana de contexto al agregar una clave, operan exclusivamente mediante la CLI atómica `python3 .agent/skills/i18n_manager/scripts/i18n_manager.py upsert --ns <namespace> --key <clave> --es "..." --en "..."`.

## 3. Consecuencias

- **Positivas:**
  - Experiencia 100% bilingüe (`🇪🇸 ES` / `🇺🇸 EN`) tanto en interfaz como en catálogos operativos sin distorsionar marcas ni nombres de proveedores.
  - Ahorro masivo de tokens de contexto para los agentes al manipular traducciones por CLI atómica.
- **Negativas / Trade-offs:**
  - Todo modelo con texto descriptivo traducible debe incluir su columna `*_i18n` JSONB y pasar por el `DynamicTranslatorService`.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca:** `oppytec-backend/tests/architecture/test_i18n_keys_parity_and_no_hardcoded_strings.py`.
- **Invariante Verificada:** Verifica que las claves de los 11 archivos JSON en `locales/es/` y `locales/en/` sean conjuntos matemáticamente idénticos, que no existan strings literales sin `t()` en la UI ni `HTTPException(detail="...")` con texto quemado en Backend, y que `proper_noun_guard` preserve intacto `"Pollo King"`.
