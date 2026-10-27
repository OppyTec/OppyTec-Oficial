# Reporte de Traspaso (`Handover`) — Agente 02: Arquitecto de Software DDD & Clean Architecture

- **Fecha UTC:** 2026-10-26T20:50:00+00:00
- **Fase:** FASE 1 de `PLAN_MAESTRO_OPPYFY_AI.md`: Arquitectura DDD, Primitivas de Dominio Puro, Billetera de Créditos y Semáforo de Contexto Anti-Alucinación para OppyFy

## 1. Completed (Qué se realizó)

1. **Diseño y Formalización de `context_meter.py` (`src/modules/oppy_ai/domain/context_meter.py`):**
   - Límite de seguridad canónico: `MAX_SAFE_THREAD_TOKENS = 8192` (con alias `DEFAULT_MAX_SAFE_THREAD_TOKENS` retrocompatible).
   - Semáforo de salud de contexto en `Decimal`:
     * 🟢 **Verde** (`<= 65.00%`): `OPTIMAL_GREEN`, sin alerta ni bloqueo.
     * 🟡 **Ámbar** (`65.01% - 85.00%`): `WARNING_AMBER`, con alerta preventiva `preventive_alert=True` configurable desde `> 80.00%`.
     * 🔴 **Rojo** (`> 85.00%`): `CRITICAL_RED`, con `requires_auto_compaction=True` y bloqueo estricto anti-alucinación `is_anti_hallucination_blocked=True` para prevenir el *Context Rot*.
   - Compactación y rollover al 5.00%:
     * `calculate_safe_rollover_token_budget`: calcula el 5% seguro del límite (`int(8192 * 0.05) = 410 tokens`).
     * `compact_thread_for_fresh_handover`: genera un `ThreadCompactionSummary` inicializado al `5.00%` de contexto con resumen sintetizado verificado.

2. **Diseño y Formalización de `credit_wallet.py` (`src/modules/oppy_ai/domain/credit_wallet.py`):**
   - Regla de acumulación sin caducidad: `balance nuevo = balance actual + créditos de paquetes comprados` (`1000 + 10000 = 11000.00`).
   - Deducción atómica con `Decimal` (cero `float`).
   - `WorkerQuotaPolicy`: políticas de cuota configurables por el Propietario (`max_daily_credits`, `max_per_query_credits`, `assigned_credit_ceiling`).
   - Comprobación granular de cupos: `check_worker_quota_policy` y `deduct_worker_credits` verificando interruptor `is_oppyfy_enabled`, saldo disponible, cupo diario, cupo por consulta y techo total asignado.

3. **Primitiva de Dominio `ai_credit_packs.py` (`src/modules/oppy_ai/domain/ai_credit_packs.py`):**
   - Entidad inmutable `AiCreditPack` para paquetes de créditos IA independientes configurados en Admin.
   - Paridad comercial con planes base: soporte para `plan_tier_discounts` (ej. `plan_basico`: 0%, `plan_pro`: 10%, `plan_enterprise`: 20%).
   - Cálculo de bonificaciones (`total_credits = credit_amount + bonus_credits`), costo unitario por crédito en USD (`cost_per_credit_usd`) y en CLP (`cost_per_credit_clp`).
   - Invariante inmutable: paquetes nunca expiran (`expires_in_days = None` obligatorio).

4. **Diseño y Formalización de `oppyfy_rbac.py` (`src/modules/oppy_ai/domain/oppyfy_rbac.py`):**
   - Entidades de dominios y subdominios editables por el cliente (`EditableOppyfyDomainSpec`, `EditableOppyfySubdomainSpec`).
   - Capacidades de dominio: `OppyfyCapability` (`QUERY_AI`, `VIEW_FINANCIAL_COSTS`, `EXECUTE_OPERATIONAL_TOOLS`, `EXPORT_CANVAS_ARTIFACTS`).
   - Concesiones de permisos con triple caducidad automática:
     1. `expires_at`: vencimiento por fecha/hora UTC (`GRANT_EXPIRED_BY_TIMESTAMP`).
     2. `max_prompts`: vencimiento por límite de consultas utilizadas (`GRANT_EXPIRED_BY_MAX_PROMPTS`).
     3. `temp_credit_ceiling`: vencimiento por techo de créditos consumidos (`GRANT_EXPIRED_BY_CREDIT_CEILING`).
   - Primitiva de consumo puro `consume_grant_quota`.
   - Redacción física en código duro `redact_cost_fields`: reemplaza campos financieros con `"[REDACTED_COST]"` cuando `can_view_costs=False`.

5. **Pureza de Dominio 100% (Clean Architecture):**
   - Cero dependencias a frameworks web (FastAPI) ni ORM (SQLAlchemy) en `src/modules/oppy_ai/domain/`.
   - Uso exclusivo de `dataclasses`, `Decimal` y tipado estándar.

6. **Suite Exhaustiva de Pruebas Unitarias de Dominio (`tests/unit/modules/test_oppy_ai_domain.py`):**
   - 20 pruebas unitarias específicas que cubren todos los casos de borde, semáforos, umbrales, cuotas, descuentos por plan base y expiraciones temporales.
   - **Resultado:** 20/20 passed al 100% (y 28/28 sumando los tests de servicios de OppyFy).
   - Suite completa de backend: 244 passed en 7.87s.

## 2. Friction & Failures (Qué salió mal / Qué cuidar)

- En la prueba de políticas de cuota (`test_worker_quota_policies_and_ceilings`), se detectó inicialmente una superposición de condiciones donde el gasto propuesto excedía tanto la cuota por query como el techo acumulado; se aislaron los casos de prueba para verificar individualmente cada código de rechazo (`EXCEEDS_PER_QUERY_QUOTA`, `EXCEEDS_DAILY_QUOTA`, `WORKER_CREDIT_CEILING_EXCEEDED`).
- En la función `redact_cost_fields`, se cuidó la indentación de `redacted_list.append(clean_item)` dentro del loop de ítems de lista para evitar duplicidad de elementos redactados.

## 3. Next Exact Action (Siguiente paso exacto)

- Traspasar la ejecución al Agente 03 (`03-database-alembic-and-backup-engineer`) para generar la migración lineal correlativa Alembic `0010_tenant_oppyfy_custom_rbac_and_credit_wallets.py` con los esquemas `tenant_*.oppyfy_*` y tablas públicas de soporte vectorial (`public.spec_chunks` y `public.llm_request_logs`).
