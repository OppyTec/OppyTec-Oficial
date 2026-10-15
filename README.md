# OppyTec v2.0 — Plataforma SaaS de Gestión Gastronómica y Comercial

> **Monorepo Oficial de OppyTec**  
> Arquitectura Multi-Tenant desacoplada para gestión de inventarios, recetas (escandallos), mermas, compras y analítica en tiempo real para restaurantes, hoteles y cadenas multilocales (Holdings).

---

## 🏛️ Estructura del Proyecto

```plaintext
.
├── specs/                               # Fuente de verdad: especificaciones técnicas y de producto v2.0
│   ├── 00-INDEX.md                      # Índice maestro y glosario
│   ├── 01-PRD.md                        # Product Requirements Document
│   ├── 02-TRD.md                        # Technical Requirements Document
│   ├── 03-USER-FLOWS.md                 # Flujos de usuario y rutas
│   ├── 04-DESIGN-SYSTEM.md              # Sistema de diseño y tokens
│   ├── 05-DATABASE-SCHEMA.md            # Esquemas PostgreSQL (public vs tenant_*)
│   └── 06-IMPLEMENTATION-PLAN.md        # Plan de refactorización por fases
├── oppytec-backend/                     # API RESTful (Python 3.12, FastAPI, SQLAlchemy 2 Async, Alembic)
├── oppytec-frontend/                    # SPA (React 19, TypeScript, Vite, Tailwind CSS, TanStack Query)
├── MASTER-AGENTIC-ENGINEERING-FRAMEWORK.md # Marco normativo para agentes de IA y quality gates
└── .gitignore                           # Exclusión de dependencias, entornos y legacy local
```

---

## 🛠️ Stack Tecnológico

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (Async con `asyncpg`), Pydantic v2, Alembic, Redis 7.
- **Frontend:** React 19, TypeScript 5.x, Vite 6, Tailwind CSS, Radix UI, TanStack React Query v5.
- **Base de Datos:** PostgreSQL 16 con aislamiento Multi-Tenant por esquemas dinámicos y extensión `pgvector`.
- **Gobernanza Agéntica:** OpenSpec (Spec-Driven Development), Jev (Guardrails Sistema 1), Linters estrictos (`ruff`, `mypy`, `eslint`, `tsc`).

---

## 📋 Plan de Desarrollo

El desarrollo se ejecuta siguiendo el orden estricto de [specs/06-IMPLEMENTATION-PLAN.md](specs/06-IMPLEMENTATION-PLAN.md):
1. **Fase 1:** Setup, Andamiaje y Contenedores Docker
2. **Fase 2:** Base de Datos, Esquemas y Fixtures
3. **Fase 3:** Servicios Core y Clean Architecture
4. **Fase 4:** Endpoints API y Validaciones HTTP
5. **Fase 5:** UI, Estado Asíncrono y Componentes React
6. **Fase 6:** Pruebas Integrales, Seguridad y Auditoría
