VERSION 0.8
FROM python:3.9
WORKDIR /app

ARG KUBECTL_VERSION=v1.29.7
ARG EARTHLY_GIT_PROJECT_NAME
ARG CACHE_BASE=ghcr.io/$EARTHLY_GIT_PROJECT_NAME

FROM busybox

kubectl:
    RUN wget https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl && \
        chmod a+x kubectl
    SAVE ARTIFACT kubectl
    SAVE IMAGE --push ${CACHE_BASE}-kubectl:cache


build:
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
    SAVE IMAGE --push ${CACHE_BASE}-build:cache

tests:
    LOCALLY
    RUN poetry install --no-interaction && \
        poetry run prospector && \
        poetry run pytest

docker:
    # Ensure images are pushed to cache for these targets
    BUILD +kubectl
    BUILD +build

    COPY --dir +build/.venv +build/dataproduct_apps .
    COPY +kubectl/kubectl /usr/local/bin/

    ENV PATH="/bin:/usr/bin:/usr/local/bin:/app/.venv/bin"

    ARG EARTHLY_GIT_SHORT_HASH
    ARG IMAGE_TAG=$EARTHLY_GIT_SHORT_HASH
    ARG IMAGE=nais/dataproduct-apps
    SAVE IMAGE --push ${IMAGE}:${IMAGE_TAG} ${IMAGE}:latest
