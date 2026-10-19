# ADR-010: Atlas Visual Interactivo de Arquitectura con `Archify` Alimentado desde `Graphify` (Costo 0 de Tokens)

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_visualizacion_y_auditoria_archify_001.md` / `.agent/skills/archify/SKILL.md`

---

## 1. Contexto

Auditar visualmente una plataforma SaaS multi-tenant compleja leyendo decenas de archivos de código consume tiempo humano y, si se le pide a un LLM leer el repositorio completo para generar diagramas, desperdicia decenas de miles de tokens de contexto. Por otro lado, los diagramas estáticos tradicionales envejecen rápidamente y carecen de enlaces interactivos a las líneas reales de código y a sus pruebas.

## 2. Decisión

Establecer una sinergia en dos capas entre **`Graphify`** (para agentes de IA y scripts) y **`Archify` (`tt-a1i/archify`)** (para auditoría visual interactiva humana) en `docs/architecture/atlas/`:

1. **Separación de Responsabilidades por Nivel de Abstracción:**
   - **`Graphify` (`.agent/skills/graphify/graph_navigator.py`):** Extrae determinísticamente el grafo AST completo (`LegacyGraph` en modo solo lectura y `V2Graph` vivo) en milisegundos y con **0 tokens**, permitiendo consultar radio de impacto (*1-hop*) y líneas exactas de cada símbolo.
   - **`Archify` (`docs/architecture/atlas/01..05-*.archify.html`):** Construye **5 Mapas Interactivos HTML autocontenidos** respaldados por fuentes JSON tipadas (`sources/*.archify.json`) y recibos de validación (`sources/*.receipt.json`).
2. **Regla de Oro de Diseño Visual (*"Details in Cards, Not Excessive Edges"*):**
   - Cada mapa mantiene entre **8 y 20 nodos semánticos** agrupados por *Trust Boundaries* y capas arquitectónicas.
   - El detalle profundo (esquemas SQL, fórmulas matemáticas, códigos RBAC `<modulo>.<submodulo>.<funcion>`, invariantes y rutas de archivo `.py`/`.tsx` + tests asociados) se aloja en las **tarjetas de evidencia (`card`)** inspeccionables al hacer clic, junto con soporte para *Lenses*, *Upstream/Downstream Reach* y *Route Probe*.
3. **Los 5 Mapas Canónicos del Atlas:**
   - `01-tenancy-and-schemas.archify.html` (Fase 2)
   - `02-rbac-quotas-and-audit.archify.html` (Fase 3)
   - `03-clean-architecture-and-domain.archify.html` (Fases 3-4)
   - `04-critical-runtime-flows-and-resilience.archify.html` (Fases 4-6)
   - `05-environments-and-agentic-harness.archify.html` (Paso 0 y Fase 1)

## 3. Consecuencias

- **Positivas:**
  - Auditoría arquitectónica interactiva en cualquier navegador sin requerir servidor web activo.
  - Cero gasto de tokens durante el ciclo diario de codificación (*Fast Gate*), actualizando el Atlas únicamente al cierre de cada Fase o bajo demanda.
- **Negativas / Trade-offs:**
  - Prohibido editar los archivos `.archify.html` manualmente sin actualizar primero su fuente tipada `.archify.json` y su recibo `.receipt.json`.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca:** Validación de esquema JSON y recibo `SHA-256` en `docs/architecture/atlas/sources/*.receipt.json` y verificación de sincronización en `test_subagent_strategy_coverage.py`.
- **Invariante Verificada:** Todo archivo `.archify.html` cuenta con su fuente `.archify.json` válida, su `.receipt.json` con hash `SHA-256` coincidente y tarjetas vinculadas a rutas reales del árbol `propuesta_arquitectura_tree_001.md`.
