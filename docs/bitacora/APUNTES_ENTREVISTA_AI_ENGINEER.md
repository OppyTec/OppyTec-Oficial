---
title: "Apuntes Maestros para la Entrevista: AI Engineer"
tags:
  - entrevista
  - ai-engineer
  - segundo-cerebro
  - oppytec-v2
  - resumen-ejecutivo
updated: "2026-10-29"
---

# 🎯 Hoja de Ruta para la Entrevista — AI Engineer (Oficina de AI Transformation)

> **Misión:** Resumen de alto impacto para repasar antes de entrar a la reunión y tener como referencia visual en **Obsidian**.  
> **Conexiones Clave:** [[00-MAPA-SEGUNDO-CEREBRO|Mapa Maestro]] | [[../../GUIA_ARQUITECTURA_AGENTICA_OPPYTEC_V2|Guía de Arquitectura Agéntica]] | [[../../COMPARATIVA_LIDR_VS_OPPYTEC_V2|Comparativa LIDR vs OppyTec]]

---

## ⚡ 1. Discurso de Apertura (Los primeros 90 segundos)

* *"Soy un **AI Engineer** que actúa como puente real entre la ciencia de datos/IA y la ingeniería de software corporativa de nivel empresarial."*
* *"En mi proyecto **OppyTec v2.0**, diseñé e implementé un **Sistema Operativo Cognitivo** con un escuadrón multi-agente de **13 agentes especializados en un DAG de 5 etapas**."*
* *"Resolví los problemas reales de llevar agentes a producción:*
  1. **Concurrencia de código:** Bloqueos atómicos AST con `fcntl.flock` para evitar que agentes se pisen.
  2. **Consumo de tokens y alucinaciones:** Indexador **Graphify** que entrega contratos en menos de 150 tokens.
  3. **Resiliencia FinOps:** Enrutador dinámico multi-proveedor (`model_router.json`) con **fallback automático ante límites de cuota (HTTP 429)**.
  4. **Gobernanza Anti-Trampa:** Hashes **SHA-256** inmutables y agente Red Team con **poder de veto final**."*

---

## 🧠 2. Conceptos Clave que Debes Saber Definir Rápido

### A. JEV (Sistema 1)
* **¿Qué es?** Enrutador cognitivo determinista que evalúa prompts en $<15\text{ ms}$.
* **¿Qué hace?** Decide si la tarea va por carril rápido (**FAST_TRACK**) o requiere el pipeline completo (**DAG_PIPELINE**), asignando al agente líder con su modelo óptimo.

### B. Organigrama de 13 Agentes en DAG (Directed Acyclic Graph)
* **Etapa 1:** Arquitectura y Esquemas (`02-software-architect`, `03-database-engineer`).
* **Etapa 2:** Construcción Paralela (`04-backend-dev`, `05-frontend-dev`).
* **Etapa 3:** Capas Cruzadas (`06-oppyfy-ai`, `07-i18n-fx`, `08-observability`).
* **Etapa 4:** Calidad y Cierre (`09-qa-parity`, `10-security-redteam`, `11-git-merge`, `12-tech-writer`).
* **Etapa 5:** Certificación E2E Desacoplada (`13-browser-playwright`).

### C. Calidad 5D (Testing en 5 Dimensiones)
* El Agente 09 evalúa el código en:
  1. **Nivel:** Unitarias, Integración, Sistema E2E, Aceptación UAT.
  2. **Naturaleza:** Funcionales y No Funcionales (Latencia $P_{95} \le 120\text{ ms}$, 500 RPS).
  3. **Tipos:** Smoke (<3s), Regresión, Carga (Locust), Pentesting Red Team.
  4. **Conocimiento:** Caja Blanca (AST), Caja Gris (OpenAPI Schemathesis), Caja Negra (Fuzzing).
  5. **Ejecución:** Automatizadas (Quality Gates) y Manuales guiadas.
* **Superpoder:** Bucle autónomo de autoreparación (hasta 3 intentos si un test falla).

### D. Rendimiento: 500 RPS y $P_{95} \le 120\text{ ms}$
* **RPS:** *Requests Per Second* (Peticiones por Segundo).
* 500 RPS = **30.000 req/min** = **1.8 millones de consultas/hora**.
* $P_{95} \le 120\text{ ms}$ significa que el 95% de las consultas a base de datos y ventas responden en menos de 120 milisegundos, con **0 errores HTTP 500**.
* **Comando para Ejecutarlo en Vivo:**
  ```bash
  python scripts/harness.py benchmark-load
  ```
  *(Arroja ~2.500 RPS proyectados con $P_{95} \approx 22\text{ ms}$ y 0 errores, certificando el SLA en menos de 2 segundos).*

---

## 🛠️ 3. Preguntas Trampa y Cómo Responderlas

| Pregunta de la Entrevistadora | Tu Respuesta Clave |
| :--- | :--- |
| *"¿Por qué no usar simplemente LangChain o AutoGen?"* | *"Porque los frameworks en memoria resuelven pipelines de chat, pero no resuelven **ingeniería de software real**: no gestionan colisiones de archivos en Git, ni bloqueos de concurrencia atómica, ni impiden que los agentes relajen los tests unitarios para auto-aprobarse. Nosotros construimos un arnés de gobernanza con contratos formales (OpenSpec) y sellos SHA-256."* |
| *"¿Qué pasa si la API de Gemini o OpenAI se cae o da error 429?"* | *"Implementamos un **Enrutador Dinámico Multi-Proveedor** con Tiers Abstractos. Si Gemini Argon agota su cuota, el sistema degrada automáticamente a Claude 3.7 Sonnet o GPT-4o sin detener la ejecución y registra el evento en telemetría."* |
| *"¿Cómo garantizas la seguridad entre clientes corporativos?"* | *"Multi-Tenancy real por aislamiento de esquemas en PostgreSQL (`tenant_*`), RBAC estricto de 3 niveles (`modulo.submodulo.funcion`) y auditoría ofensiva de 11 vectores (prevención de IDOR, SQLi y manipulación de cabeceras)."* |

---

## 🗺️ 4. Cómo Mostrar Obsidian en la Entrevista (El Momento WOW)

1. Abre Obsidian y muestra este mapa de notas.
2. Presiona **`Ctrl + G`** para abrir la **Vista de Grafo**.
3. Diles:  
   *"Manejo la arquitectura de mis proyectos utilizando Obsidian como mi **Segundo Cerebro**. Aquí tengo mapeado cómo se conectan las decisiones de arquitectura (ADRs), los contratos de negocio, las bitácoras del escuadrón agéntico y los reportes de calidad. Esto me permite tener una trazabilidad cognitiva del 100% sobre cualquier sistema que construyo."*
