# Regla 08: Seguridad Ofensiva (Red Team), Cero Hardcoding y Prevención de Deadlocks
- Referencia: `estrategia_testing_calidad_y_seguridad_001.md`.
- Cero credenciales, URLs o puertos hardcodeados; uso obligatorio de `SecretStr` en `src/core/config.py`.
- Ordenamiento canónico de locks (`ORDER BY producto_id ASC, bodega_id ASC FOR UPDATE`) + retry en `SQLSTATE 40P01`.
- Resiliencia ante caída de Redis (Fallback a PostgreSQL en Auth y Circuit Breaker en caché).
