ARG PY_VERSION=3.9
ARG KUBECTL_VERSION=v1.19.13
ARG EARTHLY_GIT_PROJECT_NAME
ARG BASEIMAGE=ghcr.io/$EARTHLY_GIT_PROJECT_NAME

FROM busybox

kubectl:
    RUN wget https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl && \
        chmod a+x kubectl
    SAVE ARTIFACT kubectl
    SAVE IMAGE --push ${BASEIMAGE}-kubectl:cache


build:
    FROM python:${PY_VERSION}-slim

    WORKDIR /app

    RUN pip install poetry
    ENV POETRY_VIRTUALENVS_IN_PROJECT=true

    COPY pyproject.toml poetry.lock .
    RUN poetry install --no-root --no-interaction

    COPY --dir .prospector.yaml dataproduct_apps tests .
    RUN poetry install --no-interaction && \
        poetry run prospector && \
        poetry run pytest
    RUN poetry install --no-dev --no-interaction

    SAVE ARTIFACT .venv
    SAVE ARTIFACT dataproduct_apps
    SAVE IMAGE --push ${BASEIMAGE}-build:cache

tests:
    LOCALLY
    RUN poetry install --no-interaction && \
        poetry run prospector && \
        poetry run pytest

docker:
    FROM navikt/python:${PY_VERSION}
    ARG EARTHLY_GIT_SHORT_HASH
    ARG IMAGE_TAG=$EARTHLY_GIT_SHORT_HASH

    WORKDIR /app

    COPY --dir +build/.venv +build/dataproduct_apps .
    COPY +kubectl/kubectl /usr/local/bin/

    ENV PATH="/bin:/usr/bin:/usr/local/bin:/app/.venv/bin"

    SAVE IMAGE --push ${BASEIMAGE}:${IMAGE_TAG} ${BASEIMAGE}:latest
