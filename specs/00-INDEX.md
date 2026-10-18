# OppyTec — Documentación Maestra y Especificaciones del Sistema (`specs/00-INDEX.md`)

> **Versión del Sistema:** OppyTec v2.0  
> **Estado General:** Documentación Normativa Sincronizada con las 16 Estrategias Maestras (`.agent/estrategias/`)  
> **Ecosistema:** SaaS Multi-Tenant Global (`i18n` + Multi-Moneda FX) para Gestión Gastronómica, Hotelera y Comercial  
> **Fecha de Actualización:** Octubre 2026  

---

## 1. Propósito y Visión General

Este directorio (`specs/`) constituye la **fuente de verdad técnica y de producto** para el proyecto **OppyTec v2.0**, operando en sinergia directa con la capa de gobernanza agéntica (`.agent/`), el árbol de arquitectura (`propuesta_arquitectura_tree_001.md`) y el marco maestro (`MASTER-AGENTIC-ENGINEERING-FRAMEWORK.md`).

OppyTec es una plataforma SaaS Multi-Tenant diseñada bajo filosofía ***Mobile-First, Then Web*** para resolver con precisión matemática (`Decimal`) los desafíos de abastecimiento, control de stock en 3 capas de unidades, escandallos (fichas técnicas de recetas), mermas, puntos de venta (POS), buffet/eventos, compras, facturación con IA y analítica ejecutiva en restaurantes, bares, hoteles, cafeterías y cadenas multilocales estructuradas bajo **Holdings**.

---

## 2. Mapa de Especificaciones Canónicas y Bóvedas Bipartitas OpenSpec

### 2.1 Los 7 Documentos Fundacionales (`specs/00..06-*.md`)

| Archivo | Dimensión / Enfoque | Audiencia Principal | Estado | Enlace |
|---|---|---|---|---|
| **00-INDEX.md** | Índice maestro, arquitectura documental, vínculo con `.agent/` y glosario ubicuo | Todo el equipo / Los 12 Agentes | **Actualizado v2.0** | [00-INDEX.md](00-INDEX.md) |
| **01-PRD.md** | Requerimientos de producto, jerarquía de usuarios/roles, casos de uso, planes, créditos `OppyFy` y edge cases | Product Owners, Desarrolladores, Agentes | **Actualizado v2.0** | [01-PRD.md](01-PRD.md) |
| **02-TRD.md** | Stack técnico cerrado, los 5 entornos, Observabilidad 4-Pilares, R2, Backups 4-Capas, `JEV` y NFRs ($P_{95} \le 120\text{ ms}$) | Tech Leads, Backend/DevOps, Agentes | **Actualizado v2.0** | [02-TRD.md](02-TRD.md) |
| **03-USER-FLOWS.md** | Árbol de rutas, recorridos de usuario (las 22 vistas), selectores globales (`Idioma`, `Moneda`, `Tenant`, `Bodega`) y estados UI | Frontend, UX/UI, QA, Agentes | **Actualizado v2.0** | [03-USER-FLOWS.md](03-USER-FLOWS.md) |
| **04-DESIGN-SYSTEM.md** | Los 3 temas oficiales (`light`, `dark`, `ocean-blue`), tipografía `Outfit`, animaciones, 42 colores, 49 íconos y *Mobile-First* | Diseñadores, Frontend, Agente 05 | **Actualizado v2.0** | [04-DESIGN-SYSTEM.md](04-DESIGN-SYSTEM.md) |
| **05-DATABASE-SCHEMA.md** | Esquemas PostgreSQL (`public` vs `tenant_*`), RBAC Dual, `OppyFy`, `llm_request_logs`, `i18n`, `FX` y cuotas | Backend, DBAs, Seguridad, Agentes 03/04 | **Actualizado v2.0** | [05-DATABASE-SCHEMA.md](05-DATABASE-SCHEMA.md) |
| **06-IMPLEMENTATION-PLAN.md** | Secuencia cronológica de refactorización (Paso 0 + Fases 1 a 6), asignación de los 12 Agentes, Quality Gates y Atlas `Archify` | Ingenieros, Los 12 Agentes | **Actualizado v2.0** | [06-IMPLEMENTATION-PLAN.md](06-IMPLEMENTATION-PLAN.md) |

---

### 2.2 Las 2 Bóvedas Espejo de OpenSpec (`openspec.config.yaml`)
Siguiendo [`.agent/estrategias/estrategia_openspec_negocio_vs_codigo_001.md`](../.agent/estrategias/estrategia_openspec_negocio_vs_codigo_001.md), las especificaciones granulares por módulo se dividen estrictamente en dos bóvedas protegidas por `test_openspec_bipartition_and_sync.py`:
1. **🟢 Bóveda 1 (`specs/business-domain/*.business.spec.md`):** *"Cómo funciona el negocio y cómo usar OppyTec"*. 100% libre de SQL, rutas `.py`/`.tsx` o arquitectura interna. Alimenta la **Capa 3A del RAG de `OppyFy`** para clientes.
2. **🔵 Bóveda 2 (`specs/engineering-code/*.code.spec.md`):** *"Cómo funciona el código y la arquitectura de OppyTec"*. Espejo 1:1 con contratos DDL, endpoints FastAPI, códigos RBAC de 3 niveles (`<modulo>.<submodulo>.<funcion>`), evaluación obligatoria `jev_system1_evaluation` (`can_jev_handle_it: true | false`), locks canónicos y pruebas.

---

### 2.3 Las 16 Estrategias Maestras Normativas (`.agent/estrategias/`)
Todo desarrollo en `oppytec-backend/` y `oppytec-frontend/` está subordinado a las 16 estrategias ubicadas en `.agent/estrategias/`:
1. [`estrategia_migraciones_alembic_001.md`](../.agent/estrategias/estrategia_migraciones_alembic_001.md) — Migraciones correlativas `0001..NNNN` (`public` vs `tenant`) y Bootstrap Génesis (`oppytec.admin`).
2. [`estrategia_rbac_y_auditoria_001.md`](../.agent/estrategias/estrategia_rbac_y_auditoria_001.md) — RBAC Dual de 3 niveles, acceso transversal en el Holding, cupos con `soft-delete`, permisos JIT y auditoría forense.
3. [`estrategia_testing_calidad_y_seguridad_001.md`](../.agent/estrategias/estrategia_testing_calidad_y_seguridad_001.md) — Co-Creación 1:1 de tests, 5 dimensiones, Gates estratificados, Cero Hardcoding y 11 vectores Red Team (Kali + Caos).
4. [`estrategia_entornos_y_despliegue_001.md`](../.agent/estrategias/estrategia_entornos_y_despliegue_001.md) — Los 5 entornos (`local`, `preview`, `ci`, `staging`, `production`), invarianza `SHA-256` (`runtime-env.js`) y *Fail-Fast*.
5. [`estrategia_orquestacion_git_worktrees_y_smart_merge_001.md`](../.agent/estrategias/estrategia_orquestacion_git_worktrees_y_smart_merge_001.md) — Orquestación paralela con **Prime Agent (`rlm.spawn`)**, Git Worktrees, AST Claiming (`fcntl.flock`) y *Merge Train*.
6. [`estrategia_visualizacion_y_auditoria_archify_001.md`](../.agent/estrategias/estrategia_visualizacion_y_auditoria_archify_001.md) — Atlas Visual Interactivo HTML (`Archify` alimentado desde `Graphify` a costo 0 de tokens).
7. [`estrategia_openspec_negocio_vs_codigo_001.md`](../.agent/estrategias/estrategia_openspec_negocio_vs_codigo_001.md) — Bipartición de `specs/` (`business-domain/` vs `engineering-code/`).
8. [`estrategia_asistente_ai_oppyfy_rag_y_creditos_001.md`](../.agent/estrategias/estrategia_asistente_ai_oppyfy_rag_y_creditos_001.md) — Asistente **`OppyFy`** (marca configurable), RAG de 3 capas, RBAC propio editable por cliente, paquetes de créditos acumulables sin caducidad, medidor `% contexto` y FinOps `llm_request_logs`.
9. [`estrategia_motor_decisiones_jev_system1_001.md`](../.agent/estrategias/estrategia_motor_decisiones_jev_system1_001.md) — Motor global **JEV (Sistema 1)** con los 4 candados automáticos *"¿Lo puede hacer JEV (Sí/No)?"*.
10. [`estrategia_internacionalizacion_i18n_multilenguaje_001.md`](../.agent/estrategias/estrategia_internacionalizacion_i18n_multilenguaje_001.md) — `i18n` Full-Stack (`es` 🇪🇸 / `en` 🇺🇸 + futuros), banderas SVG, traducción dinámica de datos cliente (`"Pollo King"` inmutable) y patrón `Pi`.
11. [`estrategia_multimoneda_fx_precios_y_cobros_001.md`](../.agent/estrategias/estrategia_multimoneda_fx_precios_y_cobros_001.md) — Motor Multi-Moneda FX (Bancos Centrales BCCh + BCE), selector independiente del idioma, consola admin y gestión de precios.
12. [`estrategia_observabilidad_monitoreo_y_analitica_001.md`](../.agent/estrategias/estrategia_observabilidad_monitoreo_y_analitica_001.md) — Los 4 pilares (`OpenTelemetry`, `Grafana LGTM`, `Sentry/GlitchTip`, `Umami`) y Centro de Observabilidad de 13 sub-vistas con filtro por `Environment`.
13. [`estrategia_almacenamiento_imagenes_r2_y_cuotas_001.md`](../.agent/estrategias/estrategia_almacenamiento_imagenes_r2_y_cuotas_001.md) — Almacenamiento Cloudflare R2 aislado por Tenant/Entorno, compresión WebP en 2 capas y cuota de memoria MB por plan.
14. [`estrategia_respaldos_base_datos_y_recuperacion_001.md`](../.agent/estrategias/estrategia_respaldos_base_datos_y_recuperacion_001.md) — Respaldos en 4 Capas cifrados (`.sql.zst.age`) con restauración quirúrgica de un solo Tenant.
15. [`estrategia_escuadron_multiagente_prompts_y_autoreparacion_001.md`](../.agent/estrategias/estrategia_escuadron_multiagente_prompts_y_autoreparacion_001.md) — Escuadrón de **12 Agentes Especializados**, System Prompts y bucles de autoreparación autónoma en QA y Ciberseguridad.
16. [`estrategia_sistema_diseno_ux_ui_y_mobile_first_001.md`](../.agent/estrategias/estrategia_sistema_diseno_ux_ui_y_mobile_first_001.md) — Rescate exhaustivo del ADN visual de `OppyTec-Legacy` (3 temas, 42 colores, 49 íconos) y filosofía *Mobile-First*.

---

## 3. Principio de Inviolabilidad de `OppyTec-Legacy` y Paridad Matemática

1. **Inviolabilidad del código Legacy:** Ningún archivo dentro de `OppyTec-Legacy/OppyTec_Backend` ni de `OppyTec-Legacy/OppyTec_Frontend` puede ser modificado, eliminado o renombrado. Está protegido en modo solo lectura por `.agent/guardrails/jev_policies.yaml`.
2. **Consulta Eficiente mediante `LegacyGraph` (0 Tokens):** Para analizar dependencias o llamadas de `OppyTec-Legacy`, los agentes utilizan `.agent/skills/graphify/graph_navigator.py` sobre los grafos pre-calculados en `OppyTec-Legacy/grafos-legacy/`.
3. **Paridad Matemática Inalterable:** Las fórmulas gastronómicas y operativas (conversión de 3 capas de unidades, costo promedio ponderado PPP, Kardex, escandallos y mermas) deben arrojar resultados idénticos a `OppyTec-Legacy`, verificados por el bucle de autoreparación del **Agente 09 (QA Parity Engineer)**.

---

## 4. Gobernanza Agéntica Activa (`.agent/`)

- **22 Reglas Inmutables (`.agent/rules/00..21-*.md`):** Selladas con hash `SHA-256` en `.agent/evals/eval_hashes.sha256`.
- **12 Sub-Agentes Especializados (`.agent/subagents/01..12-*/`):** Cada uno con su propio `prompt.md`, `knowledge.md` evolutivo y `handovers/latest_handover.md`.
- **Evaluaciones Anti-Trampa (`.agent/evals/rubric_10_criteria.yaml`):** 10 criterios de solo lectura verificados por `scripts/harness.py`.

---

## 5. Glosario Ubicuo del Dominio OppyTec v2.0

- **SuperUser Génesis ("Dios"):** Primer administrador global del sistema OppyTec en el esquema `public` (inyectado desde variables de entorno `SUPERUSER_GENESIS_*`: `oppytec.admin@gmail.com` / `oppytec.admin`), con facultad para crear trabajadores globales de OppyTec (`superuser`, `admin`, `supervisor`, `developer` + roles custom), Holdings, Entidades Legales, Tenants, Planes y Módulos.
- **Holding:** Grupo empresarial matriz en `public.holdings` que agrupa una o más entidades legales y múltiples sucursales (`Tenants`). Los `Propietarios` están asociados a 1 Holding y pueden operar en 1 o varios Tenants de ese mismo Holding.
- **Entidad Legal:** Razón social con RUT/Tax ID en `public.legal_entities`, vinculada a 1 Holding y en relación estricta **`1:1` con 1 Tenant**.
- **Tenant (Sucursal / Inquilino):** Establecimiento individual (ej. *Restaurante Pacífico Centro* o *Hotel Pacífico*). Posee su propio esquema PostgreSQL aislado (`tenant_<slug>`) y su propia moneda contable base (`base_currency`).
- **RBAC Dual de 3 Niveles (`<modulo>.<submodulo>.<funcion>`):** Sistema de control de acceso con jerarquía numérica (`hierarchy_rank`) dividido en dos áreas: Trabajadores Globales de OppyTec (`public`, cupo ilimitado con `soft-delete`) y Trabajadores Clientes (`Holding`/`tenant_*`, sujetos al cupo `max_active_users` del plan donde el `soft-delete` libera el cupo al instante y revoca sesiones en Redis), más permisos temporales JIT y auditoría forense inmutable.
- **Bodega y Área Operativa:** Espacios de almacenamiento (ej. Bodega Principal, Cocina Caliente, Barra) y zonas de trabajo a las cuales se asignan insumos y personal.
- **Producto / Insumo y 3 Capas de Unidades:** Ítem del catálogo modelado en 3 capas exactas con `Decimal` (Presentación de Compra $\to$ Envase de Almacenamiento $\to$ Unidad Base de Receta/Consumo), agrupable por **Categoría**, **Familia de Productos** y **Etiquetas (`#tags`)**.
- **Escandallo / Receta:** Ficha técnica culinaria que combina insumos y sub-recetas con factor de merma para calcular dinámicamente el costo por porción y margen bruto.
- **Merma:** Pérdida de stock por vencimiento (FEFO), deterioro o error de preparación, sujeta a flujo de aprobación gerencial según umbral y registrada en el Kardex (`registro_stock`).
- **`OppyFy` (Marca Configurable de Asistente IA):** Copiloto e inteligencia operativa con **RAG en 3 Capas** (Capa 1 Conversacional con medidor de `% de contexto` anti-alucinación; Capa 2 de Funciones en Código Duro sobre el Tenant; Capa 3 Vectorial HNSW sobre `specs/business-domain/`, documentos privados y memoria del negocio), gobernado por un **Panel RBAC Exclusivo con Dominios y Sub-dominios 100% editables por cada cliente**, comercializado mediante **Paquetes de Créditos independientes del plan, acumulables (`1.000 + 10.000 = 11.000`) y sin caducidad**, y auditado estrictamente en `public.llm_request_logs`.
- **`JEV` (Modelo Sistema 1):** Motor global de decisiones rápidas y tipadas (`Boolean`, `Choice`, `Score` en 70–500 ms con confianza calibrada) evaluado obligatoriamente en todo módulo actual o futuro (*"¿Lo puede hacer JEV: Sí/No?"*).
- **`i18n` Dinámico con Protección de Nombres Propios y Patrón `Pi`:** Internacionalización completa (`es` Bandera de España SVG y `en` Bandera de EE.UU. SVG + idiomas futuros) que traduce tanto la interfaz estática (11 namespaces JSON) como los conceptos editables por el cliente (`"Cono Helado de Chocolate"` $\leftrightarrow$ `"Chocolate Ice Cream Cone"`), protegiendo como inmutables las marcas y proveedores (`"Pollo King"`) a costo casi cero mediante `public.i18n_translation_memory` y prompts minimalistas estilo `Pi`.
- **Motor Multi-Moneda FX:** Conversor alimentado por el **Banco Central de Chile (`BCCh`)** y el **Banco Central Europeo (`BCE`)** que permite cambiar la moneda de visualización (`CLP`, `USD`, `EUR`, `BRL`) de forma independiente al idioma seleccionado.
