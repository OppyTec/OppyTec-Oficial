# Regla 12: Bipartición de OpenSpec (`Negocio` vs `Código`) y Cuadriga de Sincronización
- Referencia: `estrategia_openspec_negocio_vs_codigo_001.md`.
- Bóveda 1 (`specs/business-domain/*.business.spec.md`): 0% SQL, 0% rutas `.py`/`.tsx`, segura para clientes y RAG de `OppyFy`.
- Bóveda 2 (`specs/engineering-code/*.code.spec.md`): espejo 1:1 con DDL, endpoints, códigos RBAC y evaluación `JEV`.
