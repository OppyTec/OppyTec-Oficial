# Lecciones Destiladas de Trayectorias (`trajectory_lessons.md`)

> Este archivo almacena lecciones transversales destiladas mediante `/refine` tras superar los *Quality Gates*. Las lecciones específicas de cada especialidad viven en `.agent/subagents/<id>-<agente>/knowledge.md`.

1. **[L-001] Prohibición de Hashes Aleatorios en Alembic:** Nunca usar hashes hexadecimales ni `alembic merge heads`; usar siempre numeración correlativa `NNNN_<public|tenant>_<slug>.py` y `scripts/db_migration.py rebase`.
2. **[L-002] Aislamiento de Bóvedas OpenSpec para RAG:** Jamás incluir sentencias SQL ni rutas `.py`/`.tsx` en `specs/business-domain/` para proteger el RAG de clientes en `OppyFy`.
3. **[L-003] Cero `float` y Ordenamiento Canónico de Locks:** Usar siempre `Decimal` en dinero/stock y ordenar ascendentemente los IDs (`ORDER BY producto_id ASC, bodega_id ASC FOR UPDATE`) antes de bloquear múltiples filas a 500 RPS.
4. **[L-004] Protección de Nombres Propios en `i18n` Dinámico:** Traducir conceptos operativos (`"Helado de Chocolate"` -> `"Chocolate Ice Cream"`), pero mantener inmutables marcas y proveedores (`"Pollo King"`).
