# 02-TRD.md — Technical Requirements Document (TRD)

> **Documento:** Requerimientos Técnicos, Stack Cerrado, Resiliencia, Observabilidad y Arquitectura de 5 Entornos  
> **Proyecto:** OppyTec SaaS v2.0  
> **Estado:** Actualizado y Sincronizado con las 16 Estrategias Maestras (`.agent/estrategias/`)  
> **Fecha:** Octubre 2026  

---

## 1. Stack Tecnológico Cerrado y Arquitectura de Sistemas

El ecosistema técnico de OppyTec v2.0 se estructura bajo una arquitectura **Clean Architecture Modular** (Backend API RESTful + SSE) y **Feature-Driven Mobile-First** (Frontend SPA), con observabilidad transversal y gobernanza determinista.

```mermaid
graph TB
    subgraph Frontend["💻 Frontend Layer (React 19 SPA - Mobile-First)"]
        React["React 19 + TypeScript 5 Strict"]
        Vite["Vite 6 + /runtime-env.js (Invarianza SHA-256)"]
        I18nFX["react-i18next (11 JSONs + Banderas SVG) + Multi-Moneda FX"]
        UI["3 Temas (light / dark / ocean-blue) + Radix UI + Vaul + Framer Motion"]
    end

    subgraph Backend["⚙️ Backend Layer (Python 3.12 + FastAPI + Clean Architecture)"]
        FastAPI["FastAPI + Pydantic v2 (extra='forbid', SecretStr)"]
        SQLA["SQLAlchemy 2.0 Async (PublicBase vs TenantBase) + Alembic Correlativo"]
        JevEngine["JEV (Sistema 1: Boolean, Choice, Score 70-500ms)"]
        OppyFy["OppyFy (RAG 3-Capas + Tool-Router Código Duro + Patrón Pi)"]
    end

    subgraph Data["🗄️ Persistence, Cache & 4-Layer Backups"]
        Postgres[("PostgreSQL 16 / Neon (Esquemas public + tenant_* + pgvector HNSW)")]
        Redis[("Redis 7 (Sesiones, Kill-Switch Soft-Delete, Caché L1, Locks)")]
        BackupVault[("Respaldos 4-Capas: Neon PITR + R2 Cifrado (.sql.zst.age) + VPS + Local")]
    end

    subgraph ExternalAndObs["🌐 Storage, Bancos Centrales & Observabilidad 4-Pilares"]
        R2["Cloudflare R2 ({env}/{holding}/{tenant}/ thumb.webp + display.webp)"]
        FXBanks["APIs Oficiales: Banco Central de Chile (BCCh) + BCE (Frankfurter)"]
        Obs["OpenTelemetry + Grafana LGTM + Sentry/GlitchTip + Umami"]
    end

    Frontend -->|HTTPS / SSE + X-Trace-ID + Accept-Language| Backend
    Backend --> SQLA --> Postgres
    Backend --> Redis
    Backend --> JevEngine & OppyFy
    Postgres --> BackupVault
    Backend --> R2 & FXBanks & Obs
    Frontend --> Obs
```

### 1.1 Backend Core (`oppytec-backend/`)
- **Lenguaje y Tipado:** Python 3.12 asíncrono con `mypy --strict` (cero `Any`) y uso exclusivo de `decimal.Decimal` (`NUMERIC` en SQL) para dinero, costos, stock, conversiones de unidades y tasas FX (prohibido `float`).
- **Framework Web y Validación:** FastAPI (ASGI) + Pydantic v2 (`ConfigDict(extra="forbid", str_strip_whitespace=True)`) y `pydantic-settings` con `SecretStr` obligatorio para toda variable sensible.
- **ORM y Pooling Multi-Tenant:** SQLAlchemy 2.0 Async (`AsyncSession`) con `asyncpg`, soportando tanto `AsyncAdaptedQueuePool` (`pool_size=40, max_overflow=20`) como `NullPool` con `statement_cache_size=0` para entornos con PgBouncer / Neon Transaction Pooler.
- **Migraciones Correlativas Lineales (`0001..NNNN`):** Alembic gobernado por `scripts/db_migration.py` (`new`, `rebase`, `verify`, `impact`) con formato estricto `NNNN_<public|tenant>_<slug>.py`, un único Head (prohibido `alembic merge heads`) y `downgrade()` real obligatorio.
- **Criptografía, Motores Nativos en Rust y Archivos:** Argon2id / Bcrypt para contraseñas; PyJWT para tokens; **`orjson` (motor en Rust)** para serialización JSON de alta velocidad (`ORJSONResponse` en FastAPI); **`python-calamine` (motor en Rust)** para lectura ultrarrápida de planillas Excel en el Importador IA; `Pillow`/`libvips` para limpieza EXIF y conversión de imágenes a `.webp` en 2 capas (`thumb` 256px + `display` 1024px); `zstandard` (`zstd`) + `age` (`AES-256`) para respaldos cifrados.

### 1.2 Frontend Core (`oppytec-frontend/`)
- **Framework y Compilación Inmutable:** React 19 + TypeScript 5.x (`noImplicitAny: true`, `strictNullChecks: true`) + Vite 6 con inyección de configuración en runtime (`/runtime-env.js` generado por `docker-entrypoint.sh` y validado con `Zod`) para cumplir *Build Once, Deploy Everywhere* (`SHA-256` idéntico entre Staging y Producción).
- **Internacionalización (`i18n`) y Multi-Moneda (`FX`):** `react-i18next` tipado con 11 namespaces JSON por idioma (`es`, `en` y listo para `pt`, `fr`, `it`, `de`), `<LanguageFlagSelector />` con banderas SVG vectoriales y `<CurrencySelector />` independiente del idioma (`CLP`, `USD`, `EUR`, `BRL`) con insignia de tasa activa.
- **Sistema de Diseño (ADN Legacy + *Mobile-First*):** Fuente `'Outfit'`, los 3 temas oficiales (`light`, `dark`, `ocean-blue`), clases `.glass` / `.glass-card`, animaciones `.animate-blink-*` y `.animate-perimeter-glow`, 42 `PRESET_COLORS`, 49 íconos `lucide-react`, `framer-motion`, `useSwipeNavigation`, `vaul` (drawers móviles), `@radix-ui`, `driver.js` (`.oppy-driver-popover`), `@dnd-kit`, `recharts`, `katex`, `html5-qrcode`, `react-easy-crop` y `sonner`.
- **Higiene de Arquitectura:** Validado por `eslint`, `pnpm dlx knip` (cero código muerto) y `.dependency-cruiser.cjs`.

### 1.3 Capa Cognitiva Dual (`JEV Sistema 1` + `OppyFy Sistema 2` con Patrón `Pi`)
- **`JEV` (TypeSafe AI — Sistema 1):** Motor global de decisiones rápidas y tipadas (`Boolean`, `Choice`, `Score` en 70–500 ms con confianza calibrada `0.00..1.00`), evaluado obligatoriamente en todo módulo actual o futuro (*"¿Lo puede hacer JEV: Sí/No?"*).
- **`OppyFy` (Sistema 2 + Prompts Minimalistas estilo `Pi`):** Orquestador de modelos Gemini 4 Argon / Gemini 3.8 Flash con RAG en 3 Capas, Agente Enrutador de funciones en código duro y registro obligatorio de toda llamada en `public.llm_request_logs`.

---

## 2. Servicios Externos, Almacenamiento y Observabilidad

| Categoría | Proveedor / Herramienta | Propósito en OppyTec v2.0 | Estrategia de Fallback / Aislamiento |
|---|---|---|---|
| **Almacenamiento de Imágenes y Archivos** | Cloudflare R2 (`oppytec-media-staging` / `oppytec-media-prod`) | Imágenes de catálogo (`thumb.webp` + `display.webp` con CDN inmutable) y facturas/documentos privados (Presigned URLs de 5 min) bajo `{env}/{holding_id}/{tenant_id}/` con cuota `max_storage_mb` por plan. | Almacenamiento en disco local aislado por `ENV_NAMESPACE` en `local` y `ci`. |
| **Bóveda de Respaldos en 4 Capas** | 1. Neon PITR<br/>2. Cloudflare R2 (`oppytec-backups-vault`)<br/>3. VPS Secundario Cloud<br/>4. Servidor Local de Oficina | Respaldos globales (`public`) y quirúrgicos por cliente (`tenant_<slug>`) comprimidos con `zstd` y cifrados con `age` (`.sql.zst.age`). | Restauración de 1 solo Tenant desde cualquiera de las 4 capas sin afectar a los demás restaurantes. |
| **Tasas de Cambio Oficiales (FX)** | 1. **Banco Central de Chile** (`mindicador.cl/api`)<br/>2. **Banco Central Europeo** (`api.frankfurter.dev`)<br/>3. Respaldo BCB PTAX / OpenER | Alimentan gratuitamente el conversor Multi-Moneda (`CLP`, `USD`, `EUR`, `BRL`, `UF`) con triangulación `Decimal(18, 8)`. | Caché en Redis + Escudo Anti-Anomalías (`> 8%`) + Override Manual auditado por el SuperUser en `platform-admin`. |
| **Observabilidad 4-Pilares** | 1. **`OpenTelemetry`** (`X-Trace-ID`)<br/>2. **`Grafana LGTM`** (`grafana/otel-lgtm`)<br/>3. **`Sentry / GlitchTip`**<br/>4. **`Umami Analytics`** | Trazas distribuidas, métricas de latencia y pool DB, caza de errores de código y analítica de uso de módulos sin cookies, unificados en las 13 sub-vistas de `platform-admin`. | En `local` bajo `--profile observability` (0 MB extra por defecto); en `ci` con `InMemorySpanExporter` (cero tráfico externo). |
| **Correo Transaccional** | Resend API / SMTP con TLS | Confirmaciones, alertas e invitaciones. | En `local`, `preview`, `ci` y `staging` opera un **Sinkhole (`Mailpit` / `SAFE_OUTBOUND_EMAIL_DOMAINS`)** para evitar envíos accidentales a clientes reales. |

---

## 3. Requisitos No Funcionales (NFRs), Concurrencia y Resiliencia

### 3.1 Rendimiento, Concurrencia y Prevención de Deadlocks
- **Latencias Objetivo (medidas por OpenTelemetry + Grafana):**
  - Operaciones transaccionales de Stock, Ventas y RBAC: $P_{95} \le 120\text{ ms}$ bajo carga de **500 RPS**.
  - Reportes ejecutivos y agregaciones analíticas: $P_{95} \le 800\text{ ms}$.
  - Decisiones estructuradas con `JEV (Sistema 1)`: $70\text{ – }500\text{ ms}$.
- **Ordenamiento Canónico de Locks (`ORDER BY id ASC FOR UPDATE`):**
  - Toda transacción que bloquee múltiples insumos o registros (ej. venta de receta o recepción de compra) DEBE ordenar los IDs de forma estrictamente ascendente antes de emitir `FOR UPDATE` para hacer matemáticamente imposibles los deadlocks cruzados, además de contar con decorador de retry con jitter exponencial ante `SQLSTATE 40P01`.

### 3.2 Ingeniería del Caos y Degradación Elegante (Zero Single Point of Failure)
- **Caída o Latencia de Redis (`> 50ms`):**
  - En el **Kill-Switch de Autenticación / Soft-Delete**: hace **Fallback automático a PostgreSQL** (`SELECT is_deleted FROM ...`) sin arrojar `HTTP 500`, y solo si PostgreSQL también falla responde con `503 Service Unavailable` + `Retry-After`.
  - En **Rate Limiting y Caché**: degrada en modo *Fail-Open* a limitador en memoria local del worker emitiendo alerta crítica en Sentry/Grafana.
- **Higiene del Pool de Conexiones Multi-Tenant:**
  - Uso obligatorio de `SET LOCAL search_path` dentro de transacciones y ejecución de `RESET search_path;` en el evento `checkin`/`reset` del pool de SQLAlchemy, verificado ante cancelaciones asíncronas (`asyncio.CancelledError`).

---

## 4. Arquitectura de los 5 Entornos y Variables de Configuración (`SecretStr`)

OppyTec v2.0 opera sobre una cadena de **4 entornos permanentes + 1 entorno efímero** validada en el milisegundo `0` por `oppytec-backend/src/core/config.py`:

| Entorno (`ENVIRONMENT`) | Base de Datos y Redis | Reglas de Seguridad y Red | Quality Gate Asociado |
|---|---|---|---|
| **1. `local`** | Contenedores locales (`localhost` / red Docker); aborta si detecta hosts remotos. | Lee `.env` local; Sinkhole de correo (`Mailpit`); observabilidad bajo `--profile observability`. | **Fast Gate (`< 15s`)** |
| **2. `preview`** | Aislado por `ENV_NAMESPACE` (`wt_01`, `pr_142`) en DB y prefijo de Redis (`wt_01:`). | Permite ramas efímeras (ej. *Neon Branching*) para `Git Worktrees` y PRs; bloquea `prod`/`staging`. | **Fast Gate + Smoke** |
| **3. `ci`** | Contenedores efímeros con rollback por `SAVEPOINT` (`< 10ms` por test). | **100% aislado de internet público**; `OTEL_EXPORTER="memory"`, APIs externas mockeadas. | **Main Gate (`< 3m`)** |
| **4. `staging`** | Datos sintéticos o 100% anonimizados (`anonymize_for_staging.py`, cero PII real). | Espejo 1:1 de Producción; Sinkhole de correos activo; `/openapi.json` autenticado para `Schemathesis`. | **Deep Gate (`500 RPS`, `Schemathesis`, `Trivy`)** |
| **5. `production`** | Cluster PostgreSQL 16 HA en Neon + Redis 7 HA + Respaldos en 4 Capas. | **Zero-SSH** (con protocolo *Break-Glass* auditado); inyección exclusiva por **Cloud Secret Manager**; `/docs`, `/redoc` y `/openapi.json` apagados (`None`). | **Monitoreo 24/7 (OTel + Grafana + Sentry + Umami)** |

### 4.1 Plantilla de Variables de Entorno (`.env.example` — Cero Secretos Reales en Código)
```bash
# 1. Identidad del Entorno y Namespace Efímero (Git Worktrees / PRs)
ENVIRONMENT=local # [local | preview | ci | staging | production]
ENV_NAMESPACE=default

# 2. Criptografía y JWT (Validados como SecretStr con longitud >= 32 bytes y alta entropía)
SECRET_KEY=replace_with_32_byte_high_entropy_secret_key_from_env
JWT_ACCESS_SECRET_KEY=replace_with_32_byte_high_entropy_access_secret
JWT_REFRESH_SECRET_KEY=replace_with_32_byte_high_entropy_refresh_secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 3. Persistencia, Pooling y Caché
DATABASE_URL=postgresql+asyncpg://db_user:db_pass@localhost:5432/oppytec_dev
REDIS_URL=redis://localhost:6379/0
DB_POOL_CLASS=AsyncAdaptedQueuePool # [AsyncAdaptedQueuePool | NullPool]
DB_POOL_SIZE=40
DB_MAX_OVERFLOW=20
DB_STATEMENT_CACHE_SIZE=0

# 4. SuperUser Génesis (Leído exclusivamente desde entorno por bootstrap.py, jamás hardcodeado en src/)
SUPERUSER_GENESIS_EMAIL=oppytec.admin@gmail.com
SUPERUSER_GENESIS_USERNAME=oppytec.admin
SUPERUSER_GENESIS_PASSWORD=replace_in_local_env_only

# 5. Marca Configurable de IA, Proveedores LLM y JEV (Sistema 1)
AI_ASSISTANT_BRAND_NAME=OppyFy
GEMINI_API_KEY=replace_with_gemini_api_key
JEV_API_KEY=replace_with_jev_api_key

# 6. Almacenamiento Cloudflare R2 y Respaldos en 4 Capas (.sql.zst.age)
STORAGE_PROVIDER=local # [local | r2 | s3]
R2_ACCOUNT_ID=replace_with_r2_account_id
R2_ACCESS_KEY_ID=replace_with_r2_access_key
R2_SECRET_ACCESS_KEY=replace_with_r2_secret_key
R2_MEDIA_BUCKET_NAME=oppytec-media-staging
R2_PUBLIC_URL=https://media-staging.oppytec.com
BACKUP_R2_BUCKET_NAME=oppytec-backups-vault
BACKUP_ENCRYPTION_PUBLIC_KEY=age1replace_with_public_key
BACKUP_SECONDARY_VPS_ENABLED=false

# 7. Red, CORS, Correo y Observabilidad 4-Pilares
ALLOWED_ORIGINS=["http://localhost:5173"]
EMAIL_PROVIDER=mailpit # [console_mock | mailpit | resend | smtp]
SAFE_OUTBOUND_EMAIL_DOMAINS=["oppytec.com"]
OTEL_EXPORTER=none # [none | memory | otlp]
SENTRY_DSN=
UMAMI_ENABLED=false
UMAMI_WEBSITE_ID=
```
