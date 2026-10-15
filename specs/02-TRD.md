# 02-TRD.md — Technical Requirements Document (TRD)

> **Documento:** Requerimientos Técnicos y Arquitectura de Sistemas  
> **Proyecto:** OppyTec SaaS  
> **Versión:** 2.0  
> **Fecha:** Octubre 2026  

---

## 1. Stack Tecnológico Cerrado

El ecosistema técnico de OppyTec se estructura bajo una arquitectura desacoplada y orientada a servicios (Backend API RESTful + Frontend SPA). Todas las dependencias principales están congeladas para garantizar estabilidad y rendimiento.

```mermaid
graph TB
    subgraph Frontend["Frontend Layer (SPA)"]
        React["React 19 + TypeScript"]
        Vite["Vite 6 (Bundler)"]
        Router["React Router v7"]
        TanStack["TanStack React Query v5"]
        UI["Tailwind CSS + Radix UI + shadcn/ui"]
    end

    subgraph Backend["Backend Layer (REST API)"]
        FastAPI["FastAPI (Python 3.12 Asíncrono)"]
        SQLA["SQLAlchemy 2.0 (Async) + Alembic"]
        Pydantic["Pydantic v2 (Esquemas y Validación)"]
        Uvicorn["Uvicorn / Gunicorn ASGI"]
    end

    subgraph Data["Persistence & Cache"]
        Postgres[("PostgreSQL 16 (Multi-Tenant Schemas + pgvector)")]
        Redis[("Redis 7 (aioredis: Cache, Sessions, PubSub)")]
    end

    subgraph StorageAI["Storage & External Providers"]
        R2["Cloudflare R2 / AWS S3 (Media)"]
        Gemini["Google Gemini API (LLM / RAG)"]
        OAuth["Google OAuth 2.0"]
    end

    Frontend -->|HTTPS / WSS| Backend
    Backend --> SQLA
    SQLA --> Postgres
    Backend --> Redis
    Backend --> R2
    Backend --> Gemini
    Frontend --> OAuth
```

### 1.1 Backend Core
- **Lenguaje de Programación:** Python 3.12 (asíncrono, con tipado estricto mediante anotaciones de tipo completas).
- **Framework Web:** FastAPI (ASGI, validación nativa con Pydantic v2, OpenAPI/Swagger automático).
- **ORM / Capa de Datos:** SQLAlchemy 2.0 Async (`AsyncSession`) con driver `asyncpg`.
- **Gestión de Migraciones:** Alembic configurado con soporte multi-esquema (itera sobre todos los esquemas de inquilinos).
- **Criptografía y Hashing:** Passlib con algoritmo Argon2 / Bcrypt para contraseñas; PyJWT para tokens de sesión.
- **Gestión de Paquetes:** `uv` como gestor de paquetes de alto rendimiento (o pip / virtualenv con `pyproject.toml`).

### 1.2 Frontend Core
- **Framework / Librería Base:** React 19 con soporte para Server State reactivo.
- **Lenguaje:** TypeScript 5.x configurado en modo estricto (`noImplicitAny: true`, `strictNullChecks: true`).
- **Empaquetador y Servidor de Desarrollo:** Vite 6.
- **Enrutamiento:** React Router DOM v7 con rutas protegidas (`PrivateRoute`) y layout persistente.
- **Manejo de Estado del Servidor & Caché:** TanStack React Query v5 + Axios configurado con interceptores para JWT.
- **Manejo de Formularios:** React Hook Form + validación de esquemas con Zod.
- **Estilos y Componentes:** Tailwind CSS, Radix UI (primitivas accesibles), Lucide React (iconografía) y Framer Motion (micro-animaciones).
- **Feedback & Visualización:** Sonner (toasts flotantes), Recharts (gráficos estadísticos) y `html5-qrcode` (escáner con cámara).

### 1.3 Capa de Persistencia y Caché
- **Base de Datos Principal:** PostgreSQL 16 con extensión `pgvector` activada para búsqueda semántica vectorial.
  - **Aislamiento Multi-Tenant:** Esquemas independientes de PostgreSQL (un esquema por inquilino, p.ej. `tenant_restaurante_pacifico`, más un esquema `public` para entidades globales).
- **Caché y Colas en Memoria:** Redis 7 (gestión de sesiones activas, tokens revocados, rate-limiting y cola de tareas ligeras).

---

## 2. Servicios y APIs de Terceros

| Servicio | Proveedor | Propósito | Alternativa / Fallback |
|---|---|---|---|
| **Almacenamiento de Archivos (Object Storage)** | Cloudflare R2 / AWS S3 | Imágenes de productos, avatares de usuarios y comprobantes/facturas digitalizadas en formato PDF/JPG. | Almacenamiento local en disco montado en `/uploads` (modo desarrollo). |
| **Modelos de Lenguaje (LLM) & RAG** | Google Gemini (Gemini 1.5 Pro / Flash) | Procesamiento de consultas en lenguaje natural para Oppy Bot, generación de resúmenes de inventario y extracción estructurada de comprobantes. | OpenAI API (GPT-4o mini) mediante adaptador polimórfico. |
| **Autenticación Federada** | Google OAuth 2.0 | Inicio de sesión rápido para usuarios corporativos y administradores. | Autenticación nativa local (Email + Argon2 password). |
| **Envío Transaccional de Correos** | Resend API / SMTP Seguro | Verificación de correos, invitaciones de equipo y reseteo de contraseñas. | Servidor SMTP estándar con TLS. |
| **Monitoreo de Errores** | Sentry SDK (Python & React) | Detección en tiempo real de excepciones no controladas y métricas de rendimiento APM. | Logs estructurados JSON en consola estándar (`stdout`). |

---

## 3. Requisitos No Funcionales (NFRs)

### 3.1 Rendimiento y Latencia
- **Consultas Operativas (Lectura/Escritura de Stock):** Tiempo de respuesta $P_{95} \le 120\text{ ms}$ en condiciones de carga nominal.
- **Generación de Reportes Complejos:** $P_{95} \le 800\text{ ms}$ apoyado en vistas materializadas o agregaciones indexadas.
- **Tiempo de Carga Inicial del Frontend (First Contentful Paint - FCP):** $\le 1.2\text{ s}$ gracias a code-splitting dinámico de rutas en Vite.

### 3.2 Concurrencia y Escalabilidad
- Capacidad para soportar un mínimo de **500 solicitudes por segundo (RPS)** concurrentes por nodo backend.
- Conexiones a Base de Datos optimizadas mediante pooling asíncrono con `asyncpg` (`pool_size=40`, `max_overflow=20` por instancia).

### 3.3 Rate Limiting y Protección contra Abuso
- **Endpoints de Autenticación (`/auth/login`, `/auth/refresh`):** Máximo 5 intentos por minuto por dirección IP (algoritmo Sliding Window en Redis) para mitigar ataques de fuerza bruta.
- **Endpoints Transaccionales Operativos:** 120 peticiones por minuto por token de usuario autenticado.
- **Consultas a Modelos de IA (`/ai/chat`):** Máximo 20 prompts por minuto por tenant para controlar costos de consumo de API.

### 3.4 Seguridad y Protección de Datos
- **Aislamiento Multi-Tenant Estricto:** Ejecución imperativa del comando `SET LOCAL search_path = :tenant_schema, public` al abrir cada sesión de base de datos antes de despachar la transacción.
- **Inspección Binaria de Archivos (Magic Bytes):** Todo archivo subido (PDF, PNG, JPEG) se valida mediante inspección de cabecera binaria con `python-magic` para evitar extensiones apócrifas y ataques de subida de ejecutables.
- **Políticas HTTP Seguras:** Cabeceras HSTS activadas, cookies con flags `HttpOnly`, `SameSite=Lax` y `Secure`, y validación exhaustiva de orígenes CORS.

---

## 4. Reglas de Entorno y Despliegue

### 4.1 Entornos de Ejecución
1. **Development (`development`):** Ejecución local asistida por Docker Compose (`docker-compose.yml`), base de datos PostgreSQL local o Neon dev, y servidor Vite con Hot Module Replacement (HMR).
2. **Staging / Testing (`test`):** Entorno efímero para ejecución de suite de pruebas automatizadas (`pytest` con base de datos en memoria/aislada).
3. **Production (`production`):** Contenedores Docker optimizados multi-stage, servidos tras un Reverse Proxy con terminación TLS (Cloudflare / Nginx / Railway), con almacenamiento en Cloudflare R2 y base de datos gestionada de alta disponibilidad.

### 4.2 Matriz de Variables de Entorno Requeridas

```bash
# Core Environment
ENVIRONMENT=production # [development | test | production]
SECRET_KEY=super_secret_cryptographic_key_min_32_bytes
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database & Cache
DATABASE_URL=postgresql+asyncpg://user:password@pg-host:5432/oppytec_db
REDIS_URL=redis://:password@redis-host:6379/0

# Storage (R2 / S3)
STORAGE_PROVIDER=r2 # [local | s3 | r2]
R2_ACCOUNT_ID=cloudflare_account_id
R2_ACCESS_KEY_ID=r2_access_key
R2_SECRET_ACCESS_KEY=r2_secret_key
R2_BUCKET_NAME=oppytec-media
R2_PUBLIC_URL=https://media.oppytec.com

# External APIs
GOOGLE_CLIENT_ID=google_oauth_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=google_oauth_secret
GEMINI_API_KEY=AIzaSy...
RESEND_API_KEY=re_...
SENTRY_DSN=https://...
```

### 4.3 Directrices de Contenedores Docker
- **Backend:** Imagen base `python:3.12-slim`, usuario no privilegiado (`non-root user: appuser`), compilación de dependencias en etapa `builder` para mantener la imagen final por debajo de 200 MB.
- **Frontend:** Etapa de compilación con `node:20-alpine` ejecutando `pnpm build`, y etapa de entrega sirviendo estáticos mediante Nginx con compresión Gzip/Brotli o integración directa en el hosting de borde.
