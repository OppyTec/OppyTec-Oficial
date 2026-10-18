# Regla 04: Guardrails de Ciberseguridad Zero-Trust
- Validación binaria de Magic Bytes en toda subida de archivos/imágenes y limpieza de metadatos EXIF/GPS.
- Ejecución obligatoria de `SET LOCAL search_path` validado con `validate_schema_identifier()` y `RESET search_path` al devolver la conexión al pool.
- Sanitización contra XSS, SQLi, SSTI, Formula Injection (`=CMD|...`) y prohibición de `var-in-href` sin validar protocolo `https://`.
