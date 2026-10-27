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
- **[Dominio Recetas, Combos Dinámicos & Prevención DAG Cíclico]:**
  - Los Value Objects inmutables (`ServingYield`, `IngredientQuantity`, `DynamicCostSummary`, `OptionSelectionRule`) deben garantizar precisión estricta `Decimal` y 0 floats, usando `type(val).__name__ == "float"` para salvaguardar el escaneo AST.
  - La integridad polimórfica XOR (`RecetaIngrediente`, `GrupoOpcionesItem`, `ComboItem`) debe asegurar que el ítem referencie estrictamente a un producto O a una receta/sub-receta (`(target_a is not None) ^ (target_b is not None)`), lanzando `PolymorphicReferenceError`.
  - La recursión infinita en escandallos gastronómicos se mitiga con el algoritmo DAG `check_recipe_cycles(recipe_id, tree)` y `would_create_cycle`, evaluando con DFS en $O(V+E)$ rutas y conjuntos activos, detectando auto-recursión directa (A->A) y ciclos indirectos profundos con traza explícita.
- **[Dominio Procurement, Compras DDD & Recálculo PPP Inmutable]:**
  - El identificador tributario `RutTaxId` combina verificación Módulo 11 chileno canónico (`sum(digit * factor) % 11`, `11 - remainder` con mapeo `11->0`, `10->K`) con soporte para Tax ID internacional (`^[A-Za-z0-9.\-_]{3,64}$`), exponiendo propiedades `clean`, `formatted`, `body`, `dv`.
  - El recálculo de Costo Promedio Ponderado (PPP) tras recepción de mercadería `calculate_reception_ppp` implementa la fórmula inmutable `((Stock_actual * PPP_ant) + (Cant_recibida * Precio_compra)) / (Stock_actual + Cant_recibida)`. Evita la división por cero cuando `total_qty == 0` retornando el costo previo y rechaza terminantemente cantidades negativas o precios negativos.
  - La máquina de estados `PurchaseStatus` (`BORRADOR`, `SOLICITADA`, `EN_CAMINO`, `RECIBIDA_PARCIAL`, `RECIBIDA_TOTAL`, `CANCELADA`) garantiza que las transiciones sean unidireccionales y que estados terminales no puedan reabrirse ni cancelarse.
  - La regla "Pollo King" (`translatable: ClassVar[bool] = False` y `assert_proper_noun_immutable`) protege la integridad de nombres comerciales frente a pipelines i18n o reescrituras no supervisadas.
- **[Dominio OppyFy AI — Context Health Meter, RBAC Exclusivo y FinOps Wallet]:**
  - El medidor de salud `ContextMeter` calcula con precisión `Decimal` sobre `MAX_SAFE_THREAD_TOKENS = 8192`. El semáforo (`OPTIMAL_GREEN <= 65%`, `WARNING_AMBER 66-85%`, `CRITICAL_RED > 85%`) activa `is_anti_hallucination_blocked = True` al superar el 85%, bloqueando mensajes crudos y forzando compactación/resumen estructurado al `5.00%` con presupuesto seguro de tokens (`calculate_safe_rollover_token_budget`).
  - La economía de créditos en `credit_wallet.py` y `ai_credit_packs.py` garantiza que los paquetes de créditos IA nunca caducan (`expires_in_days = None` obligatorio), se acumulan directamente (`balance nuevo = balance actual + créditos comprados`) y hacen juego con los planes base aplicando descuentos comerciales por nivel (`plan_tier_discounts`). Las deducciones son atómicas con `Decimal` y respetan cupos por trabajador y políticas de cuota (`assigned_credit_ceiling`, `max_daily_credits`, `max_per_query_credits`).
  - El RBAC propio de OppyFy en `oppyfy_rbac.py` soporta dominios/subdominios editables por el tenant, capacidades explícitas (`OppyfyCapability`) y triple control de caducidad automática (`expires_at`, `max_prompts`, `temp_credit_ceiling`). Además, ejecuta redacción física estricta en código duro (`redact_cost_fields`) con `"[REDACTED_COST]"` cuando `can_view_costs == False`, blindando al LLM de filtraciones de margen o costo.




