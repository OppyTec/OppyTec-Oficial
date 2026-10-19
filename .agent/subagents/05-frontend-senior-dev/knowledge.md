# Base de Conocimiento Evolutiva — Agente 05: Programador Senior Frontend, ADN Visual Legacy y Mobile-First

> Lecciones aprendidas específicas de `05-frontend-senior-dev` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Fase 1 — Invarianza de Artefacto SHA-256 (`runtime-env.js`)]:** El bundle de Vite 6 se compila una única vez de forma agnóstica al entorno; `/docker-entrypoint.sh` genera `/usr/share/nginx/html/runtime-env.js` (`window.__OPPYTEC_RUNTIME_ENV__`) al arrancar el contenedor, y `src/shared/config/env.ts` lo valida con `Zod` en modo *Fail-Fast* (bloqueando `localhost`/`127.0.0.1` o esquemas `http://`/`ws://` en `staging` y `production`).
- **[Fase 1 — ADN Visual Legacy (3 Temas + 42 Colores + CLS=0)]:** `src/index.css` y `tailwind.config.ts` preservan simultáneamente selectores de clase (`.dark`, `.ocean-blue`) y atributos (`[data-theme="light" | "dark" | "ocean-blue"]`), los 42 `PRESET_COLORS`, las animaciones `.animate-blink-*` y `.animate-perimeter-glow`, la regla `.touch-target` (`>= 44x44px`) y el blindaje de especificidad `0,1,0,2` (`html > body[data-scroll-locked]`) para `CLS = 0` en modales Radix UI.
- **[Fase 1 — Telemetría Frontend Sin Fuga PII]:** `otel.ts` inyecta `X-Trace-ID` y W3C `traceparent`; `sentry.ts` ejecuta `scrubFrontendPii` recursivo (`sendDefaultPii: false`); y `umami.ts` opera sin cookies únicamente cuando `VITE_UMAMI_ENABLED === "true"` en `staging`/`production`, limpiando tokens de las rutas con `sanitizeAnalyticsPath`.
