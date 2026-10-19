# ADR-021: Motor de Tiempo Real con WebSockets (`/api/v1/ws/realtime`), Redis Pub/Sub + Streams, Filtrado RBAC y Prohibición de *HTTP Polling*

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_tiempo_real_websockets_y_notificaciones_001.md` / `.agent/skills/realtime_websockets/SKILL.md`

---

## 1. Contexto

En un restaurante u hotel donde múltiples usuarios operan simultáneamente (bodega recepcionando facturas, cocina descontando recetas, salón registrando consumo de buffet y el dueño supervisando el dashboard), usar `setInterval` o `refetchInterval` (*HTTP Polling*) multiplica artificialmente la carga sobre PostgreSQL y genera retrasos en alertas críticas de stock bajo o revocación de sesiones.

## 2. Decisión

Implementar una arquitectura de **Tiempo Real Basada en Eventos (`Zero HTTP Polling`)** mediante un multiplexor **WebSocket único por cliente (`/api/v1/ws/realtime`)** respaldado por **Redis 7 Pub/Sub + Redis Streams** y sincronizado automáticamente con **TanStack Query v5**:

1. **Aislamiento Multi-Tenant de Canales en Redis:**
   - Todo canal de publicación/suscripción respeta el namespace de entorno y tenant:
     `ws:{env}:tenant:{tenant_slug}:{topic}` y `ws:{env}:user:{user_id}` (para notificaciones directas y *Kill-Switch* instantáneo de sesión al hacer `soft-delete`).
2. **Filtrado RBAC en Vivo antes de Emitir Cada Frame (`RealtimeBroker`):**
   - Ningún evento WebSocket se transmite a ciegas a todos los conectados del tenant. Antes de despachar un mensaje por un socket abierto, el `ConnectionManager` verifica que el usuario posea el permiso de 3 niveles requerido por el evento (ej. `inventory.kardex.view` o `analytics.dashboard.view`).
3. **Recuperación de Eventos Perdidos con Redis Streams (`Last-Event-ID`) y Degradación Elegante:**
   - Ante micro-cortes de red móvil en cocina o bodega, el cliente reconecta con backoff exponencial + jitter enviando su último `event_id` para rehidratar los eventos ocurridos durante la desconexión desde el buffer acotado de Redis Streams (`MAXLEN ~ 1000`).
4. **Sincronización Reactiva con TanStack Query v5 (`useRealtimeSync.ts`):**
   - Cada sobre de evento (`RealtimeEnvelope`) incluye `invalidates_query_keys` (ej. `[["inventory", "stock"], ["operations", "buffet"]]`), disparando `queryClient.invalidateQueries()` de forma quirúrgica únicamente cuando cambia un dato real.
   - **Prohibición Absoluta de Polling:** Queda prohibido el uso de `setInterval(fetch...)` o `refetchInterval` en el Frontend.

## 3. Consecuencias

- **Positivas:**
  - Actualización sub-100ms de saldos de stock, alertas de mermas, estado de buffet y revocación inmediata de sesiones sin sobrecargar la base de datos con peticiones repetitivas.
  - Seguridad multi-tenant y RBAC idéntica a la de los endpoints REST.
- **Negativas / Trade-offs:**
  - Requiere mantener el heartbeat (`ping`/`pong` cada `25s`) y manejar el cierre inmediato con código `4001`/`4003` cuando Redis notifica la revocación de un token o usuario.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca y Red Team:** Escaneo AST en Frontend contra `refetchInterval` / `setInterval` con `fetch`, y pruebas de aislamiento WebSocket en `oppytec-backend/tests/security_redteam/test_10_redis_outage_circuit_breaker_and_ratelimit.py`.
- **Invariante Verificada:** Verifica que un usuario del `tenant_a` jamás reciba frames del `tenant_b`, que un trabajador sin permiso `analytics.finanzas.view` no reciba eventos financieros por WebSocket y que un `soft-delete` cierre el socket activo en `< 200ms`.
