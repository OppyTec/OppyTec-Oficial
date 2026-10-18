# Regla 16: Motor Multi-Moneda FX (Bancos Centrales), Selector Independiente y Precios
- Referencia: `.agent/estrategias/estrategia_multimoneda_fx_precios_y_cobros_001.md`.
- Sincronización con Banco Central de Chile (`BCCh`) y Banco Central Europeo (`BCE Frankfurter`) con `Decimal(18, 8)`, Circuit Breaker `> 8%`, consola de monitoreo/corrección manual e historial en `platform-admin`, y `<CurrencySelector />` independiente del idioma con insignia de moneda activa.
