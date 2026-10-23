---
title: "Bitácora Plan Maestro: Panel Administrador Global, Plan Básico (10 Módulos) y Cuotas Paramétricas con Semáforo"
phase: "Plan Maestro Admin"
date: "2026-10-22"
author_agent: "12-tech-writer-openspec-archify"
tags:
  - bitacora
  - plan-maestro
  - platform-admin
  - plan-basico-10-modulos
  - cuotas-parametricas
  - semaforo-cuotas
  - soft-delete-release
  - impersonation-soporte
---

# 📓 Bitácora Plan Maestro: Cómo el Escuadrón Implementó y Certificó el Panel Administrador, el Plan Básico de 10 Módulos y las Cuotas Paramétricas con Semáforo

> **Resumen en simple para personas:**  
> En esta etapa de evolución de **OppyTec v2.0**, el Escuadrón Multi-Agente implementó la infraestructura comercial y administrativa completa del sistema SaaS. Se construyó el **Shell del Panel de Administración Global (`platform-admin`)**, el catálogo del **Plan Básico ("Núcleo Base de Control de Inventario")** compuesto exactamente por 10 módulos y funciones esenciales, y el motor de **6 Cuotas Paramétricas de Capacidad** (`usuarios`, `productos`, `proveedores`, `recetas`, `combos`, `almacenamiento en MB`). Además, se incorporó la **jerarquía de excepciones (overrides)** por Empresa o Sucursal, la regla de **liberación inmediata de cupo al archivar (Soft-Delete)**, el componente visual del **Semáforo de Salud de Cuotas** (Verde <80%, Amarillo 80–94%, Rojo 95–99%, Agotado 100%) y la herramienta de soporte técnico de **Impersonación ("Entrar como Local")** con trazabilidad forense. Toda la solución fue auditada y respaldada por la migración Alembic `0003`, suites unitarias deterministas (`100% pass`) y sincronización en las 2 bóvedas de OpenSpec.

---

## 1. ¿Qué Hizo el Escuadrón en la Implementación del Plan Maestro?

| Dimensión | Especialistas Involucrados | Qué se Construyó y Auditó (Explicado en Simple) |
|---|---|---|
| **Arquitectura & Tenancy** | Agente 02 & Agente 04 | Diseñaron la extensión del modelo relacional en `public.system_plans`, `public.holdings` y `public.tenants` incorporando las 6 cuotas numéricas, la resolución determinista de precedencia de límites y el filtro de permisos RBAC de 2 niveles (`<modulo>.<submodulo>`). |
| **Persistencia & Alembic** | Agente 03 | Creó la migración correlativa lineal `0003_public_plans_quotas_and_tenant_capacity_overrides.py` agregando columnas de capacidad y overrides sin quebrar datos históricos ni requerir `merge_heads`. |
| **Backend API & Seguridad** | Agente 04 & Agente 10 | Desarrollaron y aseguraron los endpoints REST de `/api/v1/tenancy/` para el aprovisionamiento de planes, holdings, entidades legales (RUTs), sucursales, usuarios clientes, resumen de cuotas (`/quotas/summary`) e impersonación de soporte con tokens scoped (`/admin/impersonate`). |
| **Frontend UI/UX React 19** | Agente 05 & Agente 07 | Construyeron el Shell administrativo (`AdminLayout`, `AdminSidebar`, `AdminDashboard`), las vistas CRUD de gestión (`AdminManagementViews.tsx`: Planes, Holdings, Entidades Legales, Sucursales y Usuarios Clientes), el componente interactivo `<QuotaProgressIndicator />` y el botón de selección de los 10 módulos del Plan Básico. |
| **Testing & Verificación** | Agente 09 | Diseñó la suite unitaria e integradora `oppytec-backend/tests/unit/test_plan_basico_quotas_and_admin_provisioning.py` (3 pruebas exhaustivas pasando al 100%) y expandió la suite de pruebas del frontend en `App.test.tsx` (31 tests pasando al 100%). |
| **Documentación & OpenSpec** | Agente 12 | Sincronizó las 2 bóvedas de OpenSpec (`specs/business-domain/` y `specs/engineering-code/`) para reflejar los 10 módulos del Plan Básico, las 6 cuotas y el semáforo, actualizó la memoria colectiva y redactó esta bitácora oficial. |

---

## 2. Anatomía de la Solución Implementada

### 📦 A. El Plan Básico ("Núcleo Base de Control de Inventario")
El Plan Básico fue concebido para dotar a restaurantes y bares del control riguroso de sus materias primas y pérdidas sin abrumar con configuraciones complejas. A través de la función `compute_effective_permissions` con soporte de prefijos de submódulo (`extract_permission_submodule_prefix`), el plan habilita de manera estricta y segura exactamente **10 módulos y funciones**:
1. **Inicio (`inicio`):** Tablero adaptativo con métricas operativas y atajos rápidos.
2. **Registro de Consumo (`operations.consumption_log`):** Pantalla táctil de consumo directo de insumos (ej. cocina o barra) descontando automáticamente de bodega sin necesidad de un POS completo.
3. **Registro de Stock (`inventory.stock`):** Ingreso ágil de inventario y recepciones directas de compras.
4. **Gestión de Productos (`catalog.products`):** Catálogo de ingredientes y artículos con factores de conversión en 3 capas de unidades (Compra, Almacenamiento, Consumo).
5. **Gestión de Mermas (`inventory.mermas`):** Registro de desperdicios, roturas y vencimientos con justificación obligatoria.
6. **Recuento Unificado (`inventory.counts`):** Conteo físico de inventario periódico con ajuste de varianzas e historial consolidado.
7. **Notificaciones (`notifications`):** Avisos y novedades de operación entre turnos.
8. **Alertas Preventivas (`alerts`):** Semáforo de stock mínimo, anomalías de consumo y vencimientos FEFO próximos.
9. **Historial de Movimientos (`audit.history`):** Libro mayor Kardex inmutable que audita cada gramo y unidad movilizada.
10. **Usuarios y Roles (`identity.users`):** Administración de personal operativo y asignación de perfiles según jerarquía.

*Aislamiento comercial:* Los módulos avanzados como recetas complejas/escandallos (`recipes.escandallos`), combos comerciales (`recipes.combos`), buffet inteligente (`operations.buffet`) y punto de venta (`operations.pos`) quedan automáticamente bloqueados para usuarios en Plan Básico.

---

### 🚦 B. Las 6 Cuotas Paramétricas y el Semáforo de Capacidad
Cada plan en OppyTec v2.0 parametriza cuantitativamente su capacidad a través de 6 recursos:
1. `users` (asientos de usuarios activos).
2. `products` (máximo de productos e insumos dados de alta en catálogo).
3. `suppliers` (máximo de proveedores comerciales registrados).
4. `recipes` (máximo de recetas activas; 0 en Plan Básico).
5. `combos` (máximo de combos comerciales activos; 0 en Plan Básico).
6. `storage_mb` (megabytes de almacenamiento para imágenes y adjuntos en Cloudflare R2).

#### Regla de Precedencia de Excepciones (Overrides)
Para dotar de máxima agilidad al equipo comercial y atender casos especiales, cualquier recurso puede tener una excepción configurada:
$$\text{Límite Efectivo} = \text{Tenant Override} \;\gg\; \text{Holding Override} \;\gg\; \text{Plan Base}$$

#### Liberación Inmediata por Soft-Delete
Cuando un usuario es desvinculado o un producto es discontinuado, se aplica baja lógica (`is_deleted = True`):
- Los elementos en soft-delete **dejan de contar como activos en el acto**.
- El cupo queda disponible de inmediato para dar de alta al nuevo trabajador o artículo.
- Los registros pasados de auditoría, recepciones y consumos jamás se pierden ni se corrompen.

#### Semáforo de Salud Visual (`<QuotaProgressIndicator />`)
El indicador visual categoriza el estado del recurso según el porcentaje de ocupación:
- 🟢 **NORMAL (< 80%):** Capacidad suficiente y saludable.
- 🟡 **WARNING (80% a 94%):** Estado preventivo, recomendando revisión o limpieza de obsoletos.
- 🔴 **CRITICAL (95% a 99%):** Alerta crítica con efecto pulsante (`animate-pulse`), anticipando la saturación.
- ⛔ **OVER_QUOTA (100% o límite 0):** Capacidad colmada o no incluida en el plan; bloquea nuevos registros con error `HTTP 409 QuotaExceededError`.

---

### 🖥️ C. Shell del Panel Administrador Global (`platform-admin`)
El panel de control para el SuperUser Global y personal de OppyTec cuenta con:
1. **`AdminLayout` & `AdminSidebar`:** Navegación por acordeones temáticos con el ADN Visual Legacy (`ocean-blue`, `dark`, `light`), selector de entorno y acceso al Centro de Observabilidad.
2. **`AdminPlansView`:** CRUD de planes comerciales con configuración directa de las 6 cuotas paramétricas y precios multi-moneda (`CLP`, `USD`, `EUR`, `BRL`) en `Decimal`.
3. **`AdminHoldingsView`:** Alta y administración de Holdings con overrides corporativos de capacidad.
4. **`AdminLegalEntitiesView`:** Registro de Razones Sociales con RUT validado bajo módulo 11.
5. **`AdminTenantsView`:** Aprovisionamiento de locales gastronómicos con relación estricta `1:1` con su Razón Social, creación automática del esquema PostgreSQL `tenant_<slug>`, árbol interactivo de módulos SaaS con botón rápido *"Marcar 10 Módulos de Plan Básico"* y asignación de excepciones de capacidad.
6. **`AdminClientUsersView`:** Gestión de personal cliente, validación de cupos `max_active_users`, botón de baja lógica con liberación inmediata de cupo y acción de **Impersonación ("Entrar como Local")** que genera un token seguro scoped para asistir al cliente directamente en su interfaz.

---

## 3. Verificación Determinista y Quality Gates

La implementación fue auditada exhaustivamente con los siguientes resultados verificados:
- **Backend Quality Gate:**
  - `uv run pytest tests/unit/test_plan_basico_quotas_and_admin_provisioning.py`: **`3 passed`** en 0.36 segundos.
  - Suite de arquitectura Alembic (`test_alembic_integrity.py`): **`2 passed`** certificando la correlatividad de la migración `0003`.
  - Suite completa de Backend Unit Tests (`pytest tests/unit`): **`68 passed`**.
  - Linters de Backend: `ruff check .` 0 errores, `mypy --strict src tests` **0 errores en 234 archivos fuente**.
- **Frontend Quality Gate:**
  - `vitest run --run`: **`31 passed`** (5 suites) validando el router SPA, la navegación del panel administrativo y el semáforo `<QuotaProgressIndicator />`.
  - Typecheck de Frontend: `tsc --noEmit` **0 errores de tipado**.
- **OpenSpec Architecture Gate:**
  - `test_openspec_bipartition_and_sync.py`: **`1 passed`** certificando la paridad 1:1 de las bóvedas y `0%` código/SQL prohibido en `specs/business-domain/`.

---

## 4. Conclusión

Con la implementación de este Plan Maestro, OppyTec v2.0 cuenta ahora con un motor de aprovisionamiento SaaS robusto, flexible y seguro. Las empresas y restaurantes pueden operar bajo esquemas comerciales claros y transparentes, con alertas preventivas que impiden sorpresas operativas y un panel administrativo de nivel corporativo.
