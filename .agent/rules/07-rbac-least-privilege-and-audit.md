# Regla 07: RBAC Dual de 3 Niveles, Cupos por Plan con Soft-Delete y Auditoría Forense
- Referencia: `estrategia_rbac_y_auditoria_001.md`.
- Todo permiso sigue `<modulo>.<submodulo>.<funcion>` y evalúa: `M_Plan ∩ ((P_Rol ∪ P_Temp) \ P_Deny)`.
- Acceso transversal de trabajadores entre Tenants del mismo Holding con una sola cuenta.
- El `soft-delete` (`is_deleted = True`) libera inmediatamente el cupo `max_active_users` del plan y revoca sesiones en Redis.
- Registro forense inmutable con `authorization_lineage` en cada mutación.
