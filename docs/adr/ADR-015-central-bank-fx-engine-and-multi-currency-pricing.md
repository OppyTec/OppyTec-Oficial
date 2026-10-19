# ADR-015: Motor Multi-Moneda FX Conectado a Bancos Centrales (BCCh + BCE) y Precios Multi-Divisa con `Decimal`

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_multimoneda_fx_precios_y_cobros_001.md` / `.agent/skills/fx_currency_manager/SKILL.md`

---

## 1. Contexto

Los Holdings gastronómicos y hoteleros operan con proveedores internacionales (facturas en `USD` o `EUR`), sucursales en distintos países (`CLP`, `BRL`, `USD`, `EUR`) y planes/paquetes de créditos comercializados en múltiples monedas. Acoplar la moneda al idioma de la interfaz o usar tipos de cambio estáticos manuales genera distorsiones contables.

## 2. Decisión

Implementar el **Motor Multi-Moneda FX (`oppytec-backend/src/core/fx/`)** totalmente independiente del selector de idioma (`i18n`), alimentado gratuitamente por fuentes oficiales de Bancos Centrales y protegido por un **Escudo Anti-Anomalías Cambiarias**:

1. **Fuentes Oficiales Gratuitas con Fallback Determinista:**
   - **Proveedor Primario LATAM/CLP (`bcch_provider.py`):** API oficial del **Banco Central de Chile (BCCh)** para series `USD/CLP`, `EUR/CLP`, `UF/CLP`.
   - **Proveedor Primario Global (`ecb_frankfurter_provider.py`):** API del **Banco Central Europeo (BCE vía Frankfurter)** para pares internacionales (`USD`, `EUR`, `BRL`, `MXN`, `GBP`).
   - **Triangulación Exacta con `Decimal` (`NUMERIC(18, 6)`):** Conversión cruzada mediante moneda pivote (`USD` o `EUR`) sin usar jamás `float`.
2. **Escudo Anti-Anomalías (`Circuit Breaker > 8%`):**
   - Si una tasa recibida desde una API externa varía más de un **`8.0%`** respecto al último cierre válido en `public.fx_exchange_rates`, el motor rechaza la actualización automática, conserva la última tasa verificada y emite una alerta crítica a `Observabilidad` para revisión en el Panel SuperAdmin.
3. **Inmutabilidad Histórica en Transacciones (`fx_rate_snapshot`):**
   - Toda factura de compra, movimiento de Kardex o cobro de suscripción/créditos congela en el registro transaccional la moneda original, el monto original y la tasa exacta (`fx_rate_snapshot`) vigente en ese segundo, garantizando que cambios futuros de divisa jamás alteren la contabilidad pasada.
4. **Selector Independiente en UI (`<CurrencySelector />` + `<MoneyBadge />`):**
   - El usuario puede usar la interfaz en Inglés (`🇺🇸 EN`) mientras visualiza montos en Pesos Chilenos (`CLP`) o Dólares (`USD`).

## 3. Consecuencias

- **Positivas:**
  - Consolidación financiera multi-país en tiempo real para el dueño del Holding sin costo de licencias de APIs cambiarias comerciales.
  - Auditoría contable inmutable por transacción histórica.
- **Negativas / Trade-offs:**
  - Todo componente visual que muestre importes monetarios debe utilizar obligatoriamente `<MoneyBadge amount={...} currency={...} />`.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca:** `oppytec-backend/tests/architecture/test_fx_currency_precision_and_governance.py`.
- **Invariante Verificada:** Verifica el uso exclusivo de `Decimal`, la activación del *Circuit Breaker* ante saltos mayores al `8%`, la triangulación exacta con redondeo `ROUND_HALF_UP` y la independencia entre `locale` y `currency`.
