# Base de Conocimiento Evolutiva — Agente 02: Arquitecto de Software DDD & Clean Architecture

> Lecciones aprendidas específicas de `02-software-architect` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Auditoría Plan Maestro — Clean Architecture & Pureza de Dominio]:**
  - Todo archivo en `oppytec-backend/src/modules/*/domain/` debe mantenerse estrictamente desacoplado de infraestructura (sin `fastapi`, `sqlalchemy`, `redis`, `httpx`, `uvicorn`, etc.). Cualquier validación o cálculo debe operar con tipos nativos, `dataclasses` y `decimal.Decimal`.
  - La verificación AST `test_clean_architecture.py` garantiza mecánicamente la invariante.
- **[Auditoría Jerarquía Holding -> LegalEntity (1:1) -> Tenant]:**
  - La relación 1:1 estricta entre `LegalEntity` y `Tenant` debe asegurarse tanto en el esquema de PostgreSQL (`UNIQUE` constraint en `public.tenants.legal_entity_id`) como en el router HTTP (`validate_holding_legal_entity_tenant_cardinality`), rechazando intentos de reasignar una entidad legal existente o cruzar entidades entre Holdings.
- **[Plan Básico — Gating RBAC de 2 Niveles]:**
  - La ecuación de acceso efectivo debe soportar filtrado de submódulos (`<modulo>.<submodulo>`). En el Plan Básico, `operations.consumption_log` se autoriza sin abrir acceso a `operations.buffet` ni `operations.pos`.
- **[Cuotas Paramétricas de Capacidad & Liberación Soft-Delete]:**
  - Los 6 recursos del Plan (`users`, `products`, `suppliers`, `recipes`, `combos`, `storage_mb`) deben evaluarse con semáforos estandarizados: `NORMAL` (<80%), `WARNING` (80-94%), `CRITICAL` (95-99%) y `OVER_QUOTA` (>=100% o límite 0).
  - El borrado lógico (`Soft-Delete`, `is_deleted = True`) libera inmediatamente el cupo activo y desencadena la revocación en Redis vía `SessionKillSwitchService`.
- **[Dominio Inventario & Kardex DDD — Certificación Decimal y AST Anti-Float]:**
  - Para cumplir la regla inmutable de Cero Float en finanzas/dominio, incluso escribir `isinstance(val, float)` activa el scanner AST `test_zero_float_in_fx_and_domain_modules` porque detecta el símbolo `ast.Name(id='float')`. Se debe validar positivamente contra `(Decimal, int, str, StockQuantity)` y rechazar otros tipos en la rama `else` mediante `type(val).__name__`.
  - Las excepciones de dominio que representan errores de valor (`InvalidMovementTypeError`, `TransferSameWarehouseError`) deben heredar simultáneamente de `OppyTecError` y `ValueError` para preservar la retrocompatibilidad con aserciones clásicas y código existente sin perder los detalles RFC 7807.

