# ADR-002: Aislamiento Multi-Tenant Físico por Esquemas en PostgreSQL (`public` vs `tenant_<slug>`)

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_migraciones_alembic_001.md` / `specs/05-DATABASE-SCHEMA.md`

---

## 1. Contexto

OppyTec SaaS v2.0 atiende desde restaurantes independientes hasta Holdings empresariales multi-sucursal y multi-país. Almacenar los datos operativos de todos los clientes en las mismas tablas compartidas diferenciadas únicamente por una columna `tenant_id` introduce riesgo de fuga de datos inter-tenant (*Cross-Tenant Data Leakage*) ante cualquier omisión de un filtro `WHERE`, además de impedir restauraciones quirúrgicas de respaldo para un único restaurante.

## 2. Decisión

Implementar una arquitectura **Multi-Tenant con Aislamiento por Esquema en PostgreSQL 16** combinada con jerarquía corporativa en 3 niveles (`Holding -> LegalEntity -> Tenant`):

1. **Esquema Global (`public` — `PublicBase`):** Aloja el plano de control SaaS compartido: `holdings`, `legal_entities` (relación estricta `1:1` con `tenants`), `tenants`, catálogo de módulos, suscripciones, usuarios globales de OppyTec (`oppytec.admin`), memoria global de traducción (`i18n_translation_memory`), tasas de cambio (`fx_exchange_rates`) y bitácora forense (`llm_request_logs`).
2. **Esquema por Restaurante (`tenant_<slug>` — `TenantBase`):** Cada unidad operativa posee su propio esquema físico aislado en PostgreSQL (ej. `tenant_restaurante_central`) con sus propias tablas de bodega, recetas, mermas, órdenes de compra, turnos, buffet y eventos.
3. **Relación Legal Inmutable:** Toda unidad operativa (`Tenant`) está vinculada `1:1` a una Entidad Legal (`LegalEntity` con RUT/Tax ID, país y moneda base), la cual pertenece `N:1` a un `Holding`.

## 3. Consecuencias

- **Positivas:**
  - Defensa en profundidad contra fugas de datos entre clientes: un query sin filtro no puede leer tablas de otro `tenant_<slug>`.
  - Permite ejecutar restauraciones quirúrgicas de backups (`restore-tenant`) para un solo restaurante en segundos sin afectar al resto de la plataforma.
- **Negativas / Trade-offs:**
  - Las migraciones de esquema de cliente (`migration_scope = "tenant"`) deben iterar determinísticamente sobre todos los esquemas `tenant_*` registrados.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca y Seguridad:** `oppytec-backend/tests/architecture/test_alembic_integrity.py` y `oppytec-backend/tests/security_redteam/test_01_cross_tenant_schema_escape.py`.
- **Invariante Verificada:** Ningún modelo de `PublicBase` puede referenciar tablas de `TenantBase` mediante llaves foráneas cruzadas sin calificación explícita, y todo intento de inyección de `search_path` o acceso cruzado entre `tenant_a` y `tenant_b` es rechazado con HTTP `403`.
