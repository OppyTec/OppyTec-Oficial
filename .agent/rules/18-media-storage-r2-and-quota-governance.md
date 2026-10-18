# Regla 18: Almacenamiento de Imágenes en Cloudflare R2, WebP Dual y Cuotas por Plan
- Referencia: `.agent/estrategias/estrategia_almacenamiento_imagenes_r2_y_cuotas_001.md`.
- Llave incolisionable `{env}/{holding_id}/{tenant_id}/{category}/{sha256_16}_{variant}.webp`, compresión a `thumb.webp` (256px) y `display.webp` (1024px), deduplicación SHA-256, borrado de huérfanos y control de cuota `max_storage_mb` por plan.
