FROM python:3.13-slim AS builder
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY dataproduct_apps ./dataproduct_apps
RUN uv sync --frozen --no-dev

FROM python:3.13-slim AS final
WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/dataproduct_apps ./dataproduct_apps

ENV PATH="/app/.venv/bin:$PATH"
