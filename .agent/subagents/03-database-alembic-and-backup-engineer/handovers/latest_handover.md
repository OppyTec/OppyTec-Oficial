# Reporte de Traspaso (`Handover`) — Agente 03: Especialista en Base de Datos, Alembic y Backups 4-Capas

- **Fecha UTC:** 2026-11-05T14:55:00Z
- **Fase / Hito:** ETAPA 1 del Holding Hub Enterprise de OppyTec V2.0 — Migración correlativa lineal Alembic 0018 ([`0018_public_holding_hub_credit_distribution_and_purchases.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/alembic/versions/0018_public_holding_hub_credit_distribution_and_purchases.py)) y Modelos SQLAlchemy 2.0 en [`oppytec-backend/src/modules/tenancy/infrastructure/models.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/tenancy/infrastructure/models.py) en esquema `public`.
- **Estado de Certificación:** `HOLDING_HUB_DATABASE_0018_CERTIFIED` (Alembic 0001..0018 estrictamente lineal correlativa sin bifurcaciones ni gaps, reversibilidad LIFO idempotente, 5/5 tests de migración y modelos 100% verde, 43/43 tests de tenancy/holding hub 100% verde, regla Pollo King `translatable = False`, tipos `Numeric`/`Decimal` sin floats, sincronización Graphify completa).

---

## 1. Completed (Qué se ejecutó y validó)

1. **Consulta Previa a Graphify:**
   - Ejecutado `python scripts/harness.py nav "Holding"` validando las aristas activas de tenancy y dependencias del Holding Hub.

2. **Migración Correlativa Lineal Alembic 0018:**
   - Archivo: [`oppytec-backend/alembic/versions/0018_public_holding_hub_credit_distribution_and_purchases.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/alembic/versions/0018_public_holding_hub_credit_distribution_and_purchases.py)
   - `revision = "0018_public_holding_hub_credit_distribution_and_purchases"`
   - `down_revision = "0017_public_ai_benchmarks_and_tenant_feedback"`
   - `migration_scope = "public"`
   - **`upgrade()`:**
     * `public.holdings`: Agregada columna `credit_distribution_mode` (String(20), server_default="shared", nullable=False).
     * `public.holding_credit_distributions`: Tabla para distribución de cuotas mensuales de IA por tenant con `holding_id` (FK a `public.holdings.id` ON DELETE CASCADE), `tenant_id` (FK a `public.tenants.id` ON DELETE CASCADE), `monthly_ai_credits` (Integer default 2000), `created_at`, `updated_at`, y `UniqueConstraint("holding_id", "tenant_id", name="uq_holding_tenant_credit_distribution")`.
     * `public.holding_credit_purchases`: Tabla para compras de bolsas de créditos de IA con `holding_id` (FK a `public.holdings.id` ON DELETE CASCADE), `credits_amount` (Integer), `price_clp` (Numeric(14, 2)), `price_usd` (Numeric(14, 4)), `status` (String(32), default="COMPLETED"), `purchased_by_user_id` (FK a `public.global_users.id` ON DELETE SET NULL), y `created_at`.
   - **`downgrade()`:**
     * Reversibilidad simétrica LIFO e idempotente:
       1. `op.drop_table("holding_credit_purchases", schema="public")`
       2. `op.drop_table("holding_credit_distributions", schema="public")`
       3. `op.drop_column("holdings", "credit_distribution_mode", schema="public")`

3. **Modelos ORM SQLAlchemy 2.0:**
   - Actualizado [`oppytec-backend/src/modules/tenancy/infrastructure/models.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/tenancy/infrastructure/models.py):
     * `Holding`: incorporada `credit_distribution_mode: Mapped[str] = mapped_column(String(20), default="shared", nullable=False)`.
     * `HoldingCreditDistribution`: hereda de `(PublicBase, AuditTimestampsMixin)`, regla Pollo King (`translatable: ClassVar[bool] = False`), mapeado a `public.holding_credit_distributions`.
     * `HoldingCreditPurchase`: hereda de `(PublicBase)`, regla Pollo King (`translatable: ClassVar[bool] = False`), montos `Decimal` (`Numeric(14, 2)` CLP y `Numeric(14, 4)` USD), mapeado a `public.holding_credit_purchases`.

4. **Tests Unitarios de Calidad y Reversibilidad:**
   - Archivo: [`oppytec-backend/tests/unit/test_migration_0018_holding_hub.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/tests/unit/test_migration_0018_holding_hub.py)
   - Valida:
     * Integridad declarativa de modelos `Holding`, `HoldingCreditDistribution` y `HoldingCreditPurchase`.
     * Metadatos de migración 0018, secuencia lineal y `migration_scope = "public"`.
     * Ejecución idempotente de `upgrade()` y reversibilidad simétrica LIFO de `downgrade()`.
   - 5/5 tests pasados en 0.26s. Cero advertencias ni regresiones.

5. **Verificación de Cadena de Migraciones y Graphify:**
   - Ejecutado `uv --directory oppytec-backend run python scripts/db_migration.py verify`: cadena correlativa 0001..0018 OK.
   - Ejecutado `python scripts/harness.py sync-graph`: grafo sincronizado (123 nodos, 20 migraciones).

---

## 2. Friction & Failures
- Ninguna falla crítica. Tipado estricto `mypy --strict` validado en todos los archivos con supresión de `explicit-any` en metadatos de SQLAlchemy.
