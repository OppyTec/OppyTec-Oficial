# syntax=docker/dockerfile:1.7
# ==============================================================================
# OppyTec v2.0 Frontend — Immutable Multi-Stage Build (Build Once, Deploy Everywhere)
# Garantiza invarianza SHA-256 del bundle estático en /usr/share/nginx/html.
# La configuración por entorno se inyecta en runtime vía /docker-entrypoint.sh -> /runtime-env.js
# ==============================================================================

# ─── Stage 1: Builder (Node 22 Alpine + pnpm) ────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9.12.0 --activate

COPY package.json ./
RUN pnpm install --frozen-lockfile=false

COPY tsconfig.json vite.config.ts tailwind.config.ts postcss.config.js index.html ./
COPY src ./src

ENV NODE_ENV=production
RUN pnpm run build

# ─── Stage 2: Production Runtime (Nginx Unprivileged / Hardened) ─────────────
FROM nginx:1.27-alpine AS runtime

LABEL org.opencontainers.image.title="oppytec-frontend" \
      org.opencontainers.image.description="OppyTec v2.0 React 19 SPA Mobile-First (Immutable SHA-256 Bundle)" \
      org.opencontainers.image.vendor="OppyTec SaaS"

# Copiar artefacto compilado inmutable
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar configuración SPA + Reverse Proxy (/api/v1/ -> backend:8000)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar generador POSIX de /runtime-env.js
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh && \
    chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && chown nginx:nginx /var/run/nginx.pid

EXPOSE 80 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
