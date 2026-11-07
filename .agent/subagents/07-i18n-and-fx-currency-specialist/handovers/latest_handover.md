# Reporte de Traspaso (`Handover`) — Agente 07: Especialista en i18n y Multi-Moneda FX

- **Fecha UTC:** 2026-11-07T01:13:00Z
- **Agente:** `07-i18n-and-fx-currency-specialist`
- **Fase / Hito:** ADR-022 / Etapa 3 — Certificación de Paridad 1:1 `i18n` (`es`/`en`), Bóveda de Respaldo JSON (`mock_data_backup.json`), Clean Slate (`$0`), Invariante `"Pollo King"` y Multi-Moneda FX (`Decimal`).
- **Estado de Certificación:** `ADR_022_STAGE_3_I18N_AND_FX_CERTIFIED` (45/45 tests passing en suites `SandboxI18nAndFx.test.tsx`, `i18n.test.tsx` y `currency.test.tsx`; 29/29 tests passing en `oppytec-backend/tests/architecture/`; 17/17 tests passing en backend i18n/FX; 100% paridad 1:1 en los 11 namespaces core y 26 archivos JSON totales).

---

## 1. Resumen Ejecutivo y Tareas Completadas (`Completed`)

1. **Gobernanza Pre-ejecución Obligatoria (`Graphify`)**:
   - Ejecutado `python3 scripts/harness.py nav "i18n"` (11 nodos y aristas mapeadas: `core:i18n_engine`, `frontend:shared_i18n`, `frontend:language_flag_selector`, `suite:frontend_sandbox_i18n_vitest`).
   - Ejecutado `python3 scripts/harness.py nav "fx"` (8 nodos y aristas mapeadas: `core:fx_currency`, `frontend:shared_fx_currency`, `frontend:currency_selector`, `suite:frontend_currency_test`).
   - Reservados atómicamente los nodos AST en `claims_registry.json` mediante `python3 scripts/harness.py claim-ast`.

2. **Auditoría y Paridad 1:1 Estricta de los 11 Namespaces `i18n` (`es`/`en`) y Bóveda JSON (`ADR-022`)**:
   - Verificada programáticamente la paridad 1:1 exacta (`diff_es = set()`, `diff_en = set()`) en los 11 namespaces núcleo (`common`, `auth`, `navigation`, `catalog`, `inventory`, `recipes`, `operations`, `analytics`, `oppyfy`, `platform_admin`, `holding_hub`) y en la totalidad de los 26 archivos JSON en `oppytec-frontend/src/shared/i18n/locales/es/*.json` y `en/*.json` (1.183 claves hoja en `platform_admin.json`).
   - Certificadas las claves de la Bóveda de Respaldo Maestro JSON (`mock_data_backup.json`) y Clean Slate en `platform_admin.json` (`backup_vault_title`, `backup_vault_desc`, `btn_download_backup`, `btn_purge_clean_slate`, `btn_restore_backup`, `purge_clean_slate_success`, `restore_backup_success`).
   - Añadidas las claves faltantes de traducción dinámica para el preset `preset-finops-isolation` (`finops_isolation_title`, `finops_isolation_subtitle`, `finops_isolation_desc`, `finops_isolation_badge`) en `es/platform_admin.json`, `en/platform_admin.json` y `MockDataSandboxView.tsx`, garantizando `0` strings duros al conmutar `es <-> en`.

3. **Invariante Inmutable `"Pollo King"` (`is_proper_noun_protected`)**:
   - Verificado que `"Pollo King"`, `"OppyTec"` y `"JEV"` permanecen blindados en `IMMUTABLE_PROPER_NOUNS` (frontend) y `is_proper_noun_protected` (backend `i18n_engine.py`), impidiendo traducciones espurias como `"Chicken King"`.

4. **Precisión `Decimal` y Formateo Multi-Moneda FX en Clean Slate (`$0`)**:
   - Certificado el formateo monetario exacto sin coma flotante IEEE-754 mediante `formatMoney` en modo Clean Slate (`$0` en CLP, `US$0.00` en USD, `€0,00` en EUR) y en los presets gastronómicos (`$3.850.000`, `$8.940.000`, `$4.120.000`).

5. **Suite de Pruebas Ejecutada**:
   - Frontend: `pnpm --dir oppytec-frontend test src/features/platform-admin/sandbox/__tests__/SandboxI18nAndFx.test.tsx src/shared/i18n src/shared/currency` -> **3 suites, 45/45 tests passing** (incluyendo 3 nuevos tests dedicados a ADR-022 en `SandboxI18nAndFx.test.tsx`).
   - Backend Arquitectura: `oppytec-backend/.venv/bin/pytest oppytec-backend/tests/architecture/` -> **29/29 tests passing**.
   - Backend Unit i18n/FX: `oppytec-backend/.venv/bin/pytest oppytec-backend/tests/unit/test_i18n_fx_and_realtime.py oppytec-backend/tests/unit/test_holding_hub_i18n_fx.py` -> **17/17 tests passing**.

---

## 2. Fricciones y Fallos (`Friction & Failures`)

- Detectado que el preset `preset-finops-isolation` en `MockDataSandboxView.tsx` no resolvía dinámicamente sus textos vía `translateKey` al cambiar a inglés (`en`). Corregido inmediatamente añadiendo las 4 claves simétricas en `es/platform_admin.json` y `en/platform_admin.json` y enlazándolas en `dynamicPresets`.

---

## 3. Próxima Acción Exacta (`Next Exact Action`)

- Proceder con el cierre de la Etapa 3 y paso a la Etapa 4 del pipeline DAG (Agentes 09, 10, 11 y 12) para validación QA, auditoría Red Team y sincronización final del grafo AST (`sync-graph`).
