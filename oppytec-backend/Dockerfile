# syntax=docker/dockerfile:1
# ==============================================================================
# OppyTec SaaS v2.0 — Backend Multi-Stage Dockerfile (Python 3.12 Slim, Non-Root)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Builder (Deterministic installation with uv / pip)
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml ./

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN uv pip install --no-cache -r pyproject.toml

# ------------------------------------------------------------------------------
# Stage 2: Runtime (Hardened Non-Root Image)
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_PORT=8000

RUN groupadd --gid 10001 oppytec && \
    useradd --uid 10001 --gid oppytec --shell /sbin/nologin --create-home oppytec && \
    apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=oppytec:oppytec src ./src

USER oppytec

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD ["sh", "-c", "curl -fsS http://127.0.0.1:${APP_PORT}/api/v1/health || exit 1"]

CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${APP_PORT} --no-server-header"]
