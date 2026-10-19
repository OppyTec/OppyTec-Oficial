# ADR-017: Almacenamiento Multi-Tenant en Cloudflare R2, Conversión Dual a WebP, Deduplicación `SHA-256` y Cuota en MB por Plan

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_almacenamiento_imagenes_r2_y_cuotas_001.md` / `.agent/skills/r2_media_storage/SKILL.md`

---

## 1. Contexto

Permitir que los usuarios suban fotografías de productos, platos, recetas o respaldos de facturas en formatos crudos pesados (`PNG`/`JPEG` de `8 MB` desde cámaras móviles) con metadatos EXIF de geolocalización y sin aislamiento de rutas agota rápidamente el almacenamiento, ralentiza la carga en redes móviles y expone a vulnerabilidades de ejecución de archivos maliciosos o acceso cruzado entre clientes.

## 2. Decisión

Implementar el motor **`R2MediaStorageService` (`oppytec-backend/src/core/storage/`)** sobre Cloudflare R2 (API compatible con S3 y cero costo de egreso) bajo 5 reglas de ingeniería:

1. **Jerarquía de Llaves Físicamente Aislada por Entorno, Holding y Tenant:**
   - Toda llave en el bucket sigue obligatoriamente la estructura:
     `{env}/{holding_slug}/{tenant_slug}/{category}/{yyyy}/{mm}/{sha256_prefix}_{variant}.webp`
   - Ningún tenant puede construir ni firmar URLs fuera de su propio prefijo `{env}/{holding_slug}/{tenant_slug}/`.
2. **Validación Forense de *Magic Bytes* y Purga de EXIF:**
   - Se rechaza cualquier archivo cuya firma binaria real (*Magic Bytes* en los primeros 32 bytes) no coincida con un formato permitido (`image/jpeg`, `image/png`, `image/webp`, `application/pdf`), ignorando la extensión del nombre o el `Content-Type` declarado por el cliente.
   - Se eliminan el 100% de los metadatos EXIF/GPS antes de procesar la imagen.
3. **Pipeline de Optimización Dual a `.webp`:**
   - Toda imagen subida se convierte automáticamente en memoria a dos variantes ultraligeras en formato **WebP**:
     - `thumb.webp` (`300x300 px`, `~15–25 KB`) para listados y grillas móviles.
     - `display.webp` (`max 1200x1200 px`, `~60–110 KB`) para fichas de detalle y recetas.
4. **Deduplicación por Contenido (`SHA-256`) y Cuota de Almacenamiento por Plan (`max_storage_mb`):**
   - Si un mismo tenant sube dos veces la misma imagen (mismo hash `SHA-256`), se reutiliza el objeto en R2 sin duplicar espacio.
   - Antes de confirmar la subida, se verifica con bloqueo transaccional (`SELECT ... FOR UPDATE`) que `used_storage_bytes + new_bytes <= max_storage_mb * 1024 * 1024` según el plan del cliente.

## 3. Consecuencias

- **Positivas:**
  - Ahorro superior al `85%` en espacio de almacenamiento y carga instantánea en dispositivos móviles (*Mobile-First*).
  - Control comercial exacto de la cuota de almacenamiento (`MB`) contratada por cada restaurante o Holding.
- **Negativas / Trade-offs:**
  - Procesamiento de imagen en CPU durante la subida, acotado mediante límites estrictos de tamaño de entrada y resolución máxima.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca y Red Team:** `oppytec-backend/tests/architecture/test_media_storage_isolation_and_quotas.py` y `oppytec-backend/tests/security_redteam/test_06_malicious_file_upload_magic_bytes.py`.
- **Invariante Verificada:** Verifica que un ejecutable o script renombrado como `.jpg` o `.xlsx` sea bloqueado con HTTP `415`, que los metadatos EXIF sean eliminados, que las llaves R2 incluyan `{env}/{holding}/{tenant}/` y que se bloquee la subida al superar `max_storage_mb`.
