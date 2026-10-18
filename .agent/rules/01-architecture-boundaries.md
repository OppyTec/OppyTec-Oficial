# Regla 01: Fronteras de Clean Architecture y Aislamiento Multi-Tenant
- Separación estricta en 4 capas por módulo: `domain/` <- `application/` <- `infrastructure/` y `presentation/`.
- `domain/` jamás importa objetos de `fastapi`, `sqlalchemy`, `pydantic_settings` ni adaptadores externos.
- Esquema `public` (`PublicBase`) separado de los esquemas por sucursal `tenant_<slug>` (`TenantBase`).
