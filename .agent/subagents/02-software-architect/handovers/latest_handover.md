# Reporte de Traspaso (`Handover`) — Agente 02: Arquitecto de Software DDD & Clean Architecture

- **Fecha UTC:** 2026-11-01T20:30:00+00:00
- **Módulo:** Módulo de Eventos, Salones, Banquetes y Consumo de Inventario (`/eventos`)
- **Fase:** Fase 1 — Arquitectura de Dominio DDD, Entidades, Value Objects, Contratos y Modelado SQLAlchemy `TenantBase`

---

## 1. Completed (Qué se realizó)

1. **Estructura Modular DDD Canónica (`oppytec-backend/src/modules/events/`):**
   - `__init__.py`: Paquete raíz del módulo.
   - `domain/__init__.py`: Exportación canónica de todas las entidades, value objects, excepciones y contratos.
   - `domain/exceptions.py`: Jerarquía completa de excepciones RFC 7807 (`EventsDomainError`, `EventNotFoundError`, `SalonNotFoundError`, `EventOverbookingError`, `SalonCapacityExceededError`, `EventAlreadyExecutedError`, `EventAlreadyCancelledError`, `InvalidEventTimeSlotError`, `InvalidMoneyAmountError`, `EventStatusTransitionError`, `EventItemNotFoundError`) con claves de i18n (`events:errors.*`).
   - `domain/value_objects.py`:
     - `EventStatus`: Enum tipado con parser flexible case-insensitive (`AGENDADO`, `CONFIRMADO`, `EN_CURSO`, `EJECUTADO`, `CANCELADO`).
     - `SalonState`: Enum higiénico y operativo (`limpio`, `en_uso`, `mantenimiento`, `sucio`).
     - `EventTimeSlot`: Value object inmutable con validación `hora_fin > hora_inicio` y cálculo determinista de solapamiento (`overlaps()`).
     - `SalonCapacity`: Capacidad no negativa con método `assert_can_accommodate(attendees)`.
     - `MoneyAmount`: Value object inmutable con `Decimal(14, 2)`, redondeo `ROUND_HALF_UP`, métodos de IVA (`with_vat`, `without_vat`) y prohibición de montos negativos.
     - `ItemQuantity`: Cantidad de insumo positiva con 4 decimales (`Decimal(12, 4)`).
   - `domain/entities.py`:
     - Entidades de dominio desacopladas: `Salon`, `EventoItem`, `EventoReceta`, `EventoCombo`, `EventoTrabajador`, `EventoConsumoKardex`.
     - Agregado Raíz `Evento`: Control de ciclo de vida (`confirmar()`, `iniciar()`, `ejecutar()`, `cancelar()`), validación anti-overbooking (`verificar_solapamiento()`, `assert_no_colision()`), validación de aforo (`validar_capacidad()`), y gestión de líneas de insumos, recetas, combos y trabajadores con acumulación idempotente.
   - `domain/repositories.py`: Interfaces de repositorio `EventRepositoryProtocol` y `SalonRepositoryProtocol`.

2. **Modelos de Persistencia SQLAlchemy 2.0 (`infrastructure/models.py`):**
   - Herencia estricta de `TenantBase` para residir en esquemas aislados por cliente `tenant_*`.
   - Implementación de mixins `AuditTimestampsMixin`, `SoftDeleteMixin` y `TranslatableI18nMixin` según corresponda.
   - Modelado de tablas:
     - `salones`: id UUID PK, nombre, capacidad_personas, precio_neto, iva_porcentaje, precio_bruto, notas, estado, color, areas_operativas_ids (JSONDictType).
     - `salon_areas_operativas`: tabla asociativa Many-to-Many entre `salones` y `areas_operativas`.
     - `eventos`: id UUID PK, nombre (con synonym `nombre_evento`), titular, tipo_evento, salon_id (FK salones.id), lugar, fecha, hora_inicio, hora_fin, cantidad_personas (con synonyms `cantidad_invitados` y `asistentes_confirmados`), estado, color, ejecutado, cancelado, ejecutado_at, cancelado_at, motivo_cancelacion, encargado_id, created_by_user_id, valor_publico (con synonym `presupuesto_acordado`), notas, nota_personal, nota_equipo, nota_visible. Soporte en constructor para inicialización con datetimes `fecha_inicio`/`fecha_fin`.
     - `evento_items`: id UUID PK, evento_id (FK eventos.id CASCADE), producto_id (FK productos.id), bodega_id (FK bodegas.id), cantidad, costo_unitario_estimado, notas.
     - `evento_recetas`: id UUID PK, evento_id (FK eventos.id CASCADE), receta_id (FK recetas.id), bodega_id (FK bodegas.id nullable), porciones, notas.
     - `evento_combos`: id UUID PK, evento_id (FK eventos.id CASCADE), combo_id (FK combos.id), bodega_id (FK bodegas.id nullable), cantidad, notas.
     - `evento_trabajadores`: id UUID PK, evento_id (FK eventos.id CASCADE), usuario_id, rol_evento, horas_asignadas.
     - `evento_consumos_kardex`: id UUID PK, evento_id (FK eventos.id CASCADE), kardex_movement_id (FK registro_stock.id), producto_id, bodega_id, cantidad_consumida, costo_unitario_ppp, origen_tipo, origen_id.
   - Refactorización de `src/modules/operations/infrastructure/models.py` para re-exportar `Salon` y `Evento` desde `src.modules.events.infrastructure.models`, eliminando la duplicidad de tablas en `TenantBase.metadata`.

3. **Testing y Calidad 1:1 Co-Creation:**
   - Creada suite `oppytec-backend/tests/unit/modules/test_events_domain_and_models.py` con 12 tests unitarios (100% pasando en 0.23s).
   - Validada retrocompatibilidad con `test_operations_services.py` (5 tests pasando).
   - Validada la suite completa de arquitectura `tests/architecture/` (29 tests pasando).
   - Sincronizado el grafo de arquitectura con `python scripts/harness.py sync-graph`.

---

## 2. Friction & Failures (Fricciones y Desafíos Resueltos)

- **Conflicto de Metadatos SQLAlchemy:** `src/modules/operations/infrastructure/models.py` tenía clases placeholder `Salon` y `Evento` asociadas a `__tablename__ = "salones"` y `"eventos"`. Se resolvió reexportando limpiamente los modelos canónicos de `events` en `operations` y dotando a `Evento` de synonyms y virtual properties (`fecha_inicio`, `fecha_fin`, `nombre_evento`), logrando compatibilidad perfecta sin duplicidad en el catálogo de SQLAlchemy.
- **Tipos de Foreign Keys en PostgreSQL:** Se identificó que las tablas existentes `productos`, `bodegas`, `recetas`, `combos`, `areas_operativas` y `registro_stock` emplean IDs enteros/BigInteger, mientras que los eventos y salones utilizan UUID v4. Los modelos enlazan los tipos correspondientes sin discordancias DDL.

---

## 3. Next Exact Action (Siguiente Acción Exacta)

- **Para el Agente 03 / Agente 04:**
  - Coordinar la aplicación de la migración correlativa Alembic para las tablas de inquilino `tenant_*`.
  - Desarrollar la Fase 2: Implementación de repositorios SQLAlchemy, servicios de aplicación y endpoints FastAPI en `src/modules/events/presentation/router.py`.
