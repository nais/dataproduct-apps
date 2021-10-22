FROM python:3.9-slim as build

RUN apt-get -y update && \
    apt-get -y install wget && \
    mkdir -p /app/bin/ && \
    wget --directory-prefix=/app/bin/ https://dl.k8s.io/release/v1.19.0/bin/linux/amd64/kubectl && \
    chmod a+x /app/bin/kubectl && \
    pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock /app/
RUN poetry config virtualenvs.in-project true && poetry install --no-root --no-interaction

COPY dataproduct_apps /app/dataproduct_apps/
COPY tests /app/tests/
COPY .prospector.yaml /app/

RUN poetry run prospector && poetry run pytest
RUN poetry install --no-dev --no-interaction

FROM navikt/python:3.9

COPY --from=build /app/bin /usr/local/bin/
COPY --from=build /app/.venv /app/.venv/
COPY --from=build /app/dataproduct_apps /app/dataproduct_apps/

CMD ["/app/.venv/bin/dataproduct-apps"]
