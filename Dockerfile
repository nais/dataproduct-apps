FROM python:3.9 AS builder
WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-root --no-interaction

COPY dataproduct_apps ./dataproduct_apps
RUN poetry install --no-interaction

FROM python:3.9-slim AS final
WORKDIR /app

COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/dataproduct_apps ./dataproduct_apps

ENV PATH="/app/.venv/bin:$PATH"
