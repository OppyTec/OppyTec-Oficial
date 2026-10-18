# Regla 17: Observabilidad 4-Pilares y Centro de Mando en `platform-admin`
- Referencia: `estrategia_observabilidad_monitoreo_y_analitica_001.md`.
- Instrumentación central desde Fase 1 con `OpenTelemetry` (`X-Trace-ID`), `Grafana LGTM`, `Sentry/GlitchTip` y `Umami`, filtro PII (`scrub_telemetry_payload`) y Centro de Observabilidad de 13 sub-vistas filtrable por `Environment`.
