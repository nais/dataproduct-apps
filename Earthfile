VERSION 0.8
FROM python:3.9
WORKDIR /app

ARG EARTHLY_GIT_PROJECT_NAME
ARG --global CACHE_BASE=ghcr.io/$EARTHLY_GIT_PROJECT_NAME

build:
    RUN pip install poetry
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
    FROM +build
    DO github.com/earthly/lib+INSTALL_DIND
    COPY ./docker-compose.yml ./
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
