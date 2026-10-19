# Regla 22: Tiempo Real con WebSockets (`Redis Pub/Sub`), Filtro RBAC y Prohibición de Polling
- Referencia: `.agent/estrategias/estrategia_tiempo_real_websockets_y_notificaciones_001.md`.
- **Cero Polling HTTP:** Prohibido usar `setInterval` o `refetchInterval` para consultar notificaciones, alertas, saldos de stock o estados de procesos asíncronos.
- **Túnel Único y Bus Redis:** Toda notificación y actualización en vivo viaja por `/api/v1/ws/realtime` respaldado por **Redis Pub/Sub + Redis Streams** (`rt:{env_ns}:{holding_id}:{tenant_id}`).
- **Seguridad y Reactividad:** Cada evento se filtra en el servidor según los permisos RBAC de 3 niveles (`required_permission`) antes de enviarse por el socket, e invalida automáticamente las `queryKeys` correspondientes en `TanStack React Query v5`.
