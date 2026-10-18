# Regla 15: Internacionalización (`i18n`) Full-Stack, Datos Dinámicos y Patrón `Pi`
- Referencia: `estrategia_internacionalizacion_i18n_multilenguaje_001.md`.
- Cero textos quemados en código; 11 namespaces JSON por idioma en paridad 1:1 (`es` Bandera de España SVG y `en` Bandera de EE.UU. SVG + idiomas futuros).
- Traducción dinámica automática al crear/editar conceptos operativos del cliente (`*_i18n` JSONB + `public.i18n_translation_memory` + micro-prompt estilo `Pi` con `credits_deducted = 0`), bloqueando la traducción de nombres propios, marcas y proveedores (`"Pollo King"`).
