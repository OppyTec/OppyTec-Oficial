# ADR-001: Monolito Modular con Clean Architecture y DDD Estricto

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `propuesta_arquitectura_tree_001.md` / `.agent/rules/03-clean-architecture-and-ddd.md`

---

## 1. Contexto

En `OppyTec-Legacy`, la lógica de negocio matemática (conversión de unidades de 3 capas, costo promedio ponderado, deducción recursiva de recetas y validaciones de permisos) se encontraba acoplada directamente dentro de los routers de FastAPI y modelos ORM de SQLAlchemy. Esto dificultaba las pruebas unitarias aisladas en memoria, generaba dependencias circulares entre módulos y aumentaba el riesgo de regresiones al evolucionar el sistema.

## 2. Decisión

Adoptar una arquitectura de **Monolito Modular con Clean Architecture y Domain-Driven Design (DDD)** estructurada en **10 módulos de negocio desacoplados** bajo `oppytec-backend/src/modules/` (`identity`, `tenancy`, `audit`, `catalog`, `inventory`, `waste`, `recipes`, `procurement`, `operations`, `analytics`, `oppy_ai`).

Cada módulo se divide estrictamente en 4 anillos concéntricos con dirección de dependencia hacia adentro (`Presentation -> Infrastructure -> Application -> Domain`):

1. **`domain/` (Núcleo Puro):** Entidades, Value Objects, invariantes matemáticas (`Decimal`), excepciones de dominio y puertos (interfaces `Protocol`). **Prohibido importar FastAPI, SQLAlchemy, Redis o librerías de I/O.**
2. **`application/` (Casos de Uso):** Orquestación de comandos/queries, evaluación de reglas transversales, integración con `UnitOfWork` y emisión de eventos de dominio.
3. **`infrastructure/` (Adaptadores):** Modelos ORM de SQLAlchemy 2.0 (`PublicBase` / `TenantBase`), repositorios concretos y clientes externos.
4. **`presentation/` (Entrega HTTP/WS):** Routers FastAPI, esquemas Pydantic v2 de entrada/salida y dependencias de guardia RBAC.

## 3. Consecuencias

- **Positivas:**
  - El 100% de las invariantes financieras y de inventario en `domain/` se ejecutan en `< 5 ms` mediante tests unitarios y basados en propiedades (`Hypothesis`) sin requerir base de datos ni contenedores.
  - Aislamiento estricto entre dominios: la comunicación entre módulos se realiza mediante contratos explícitos de aplicación o eventos de dominio.
- **Negativas / Trade-offs:**
  - Mayor cantidad de archivos por módulo debido al mapeo explícito entre entidades de dominio, modelos ORM y esquemas Pydantic.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca:** `oppytec-backend/tests/architecture/test_clean_architecture.py` e `import-linter` en `pyproject.toml`.
- **Invariante Verificada:** Inspección AST automática que falla el *Fast Gate* (`< 15s`) si cualquier archivo dentro de `src/modules/*/domain/` importa `fastapi`, `sqlalchemy`, `redis`, `httpx` o cualquier módulo de `infrastructure/` o `presentation/`.
