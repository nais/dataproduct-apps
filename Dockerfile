ARG PYTHON_VERSION=3.9
ARG KUBECTL_VERSION=v1.19.0

FROM python:${PYTHON_VERSION} as build
ARG KUBECTL_VERSION

RUN mkdir -p /app/bin/ && \
    wget --directory-prefix=/app/bin/ https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl && \
    chmod a+x /app/bin/kubectl && \
    pip install poetry

WORKDIR /app

ENV POETRY_VIRTUALENVS_IN_PROJECT=true

COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-root --no-interaction

COPY .prospector.yaml /app/
COPY dataproduct_apps/ /app/dataproduct_apps/
COPY tests/ /app/tests/

RUN poetry run prospector && poetry run pytest
RUN poetry install --no-dev --no-interaction

FROM navikt/python:${PYTHON_VERSION}

COPY --from=build /app/bin/ /usr/local/bin/
COPY --from=build /app/.venv/ /app/.venv/
COPY --from=build /app/dataproduct_apps/ /app/dataproduct_apps/

CMD ["/app/.venv/bin/dataproduct-apps"]
