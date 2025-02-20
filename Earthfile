VERSION 0.8
FROM python:3.9
WORKDIR /app

ARG EARTHLY_GIT_PROJECT_NAME
ARG --global CACHE_BASE=ghcr.io/$EARTHLY_GIT_PROJECT_NAME

INSTALL_MISE:
    FUNCTION
    ENV MISE_DATA_DIR="/mise"
    ENV MISE_CONFIG_DIR="/mise"
    ENV MISE_CACHE_DIR="/mise/cache"
    ENV MISE_INSTALL_PATH="/usr/local/bin/mise"
    ENV PATH="/mise/shims:$PATH"

    COPY mise.toml .
    RUN curl https://mise.run | sh && \
        mise trust /app/mise.toml


build:
    DO +INSTALL_MISE
    RUN mise install poetry
    ENV POETRY_VIRTUALENVS_IN_PROJECT=true

    COPY pyproject.toml poetry.lock .
    RUN poetry install --no-root --no-interaction

    COPY --dir .prospector.yaml dataproduct_apps tests .
    RUN poetry install --no-interaction && \
        poetry run prospector && \
        poetry run pytest
    RUN poetry install --no-interaction

    SAVE ARTIFACT .venv
    SAVE ARTIFACT dataproduct_apps
    SAVE IMAGE --push ${CACHE_BASE}-build:cache

tests:
    LOCALLY
    RUN poetry install --no-interaction && \
        poetry run prospector && \
        poetry run pytest

integration-tests:
    DO github.com/earthly/lib+INSTALL_DIND
    DO +INSTALL_MISE
    RUN mise install poetry
    ENV POETRY_VIRTUALENVS_IN_PROJECT=true
    COPY --dir +build/.venv .
    COPY --dir +build/dataproduct_apps .
    COPY docker-compose.yml pyproject.toml poetry.lock .
    COPY --dir tests .
    WITH DOCKER --compose docker-compose.yml
        RUN sleep 30 && poetry run pytest --run-integration
    END

docker:
    # Ensure images are pushed to cache for these targets
    BUILD +build

    COPY --dir +build/.venv +build/dataproduct_apps .

    ENV PATH="/app/.venv/bin:$PATH"

    ARG EARTHLY_GIT_SHORT_HASH
    ARG IMAGE_TAG=$EARTHLY_GIT_SHORT_HASH
    ARG IMAGE=nais/dataproduct-apps
    SAVE IMAGE --push ${IMAGE}:${IMAGE_TAG} ${IMAGE}:latest
