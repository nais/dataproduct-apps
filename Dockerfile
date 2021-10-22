FROM python:3.9-slim as build

RUN pip install poetry
WORKDIR /app
COPY pyproject.toml poetry.lock /app/
RUN poetry config virtualenvs.in-project true && poetry install --no-root --no-interaction

COPY dataproduct-apps /app/dataproduct-apps/
COPY tests /app/tests/
COPY .prospector.yaml /app/

RUN poetry run prospector && poetry run pytest
RUN poetry install --no-dev --no-interaction

FROM navikt/python:3.9

COPY --from=build /app/.venv /app/.venv/
COPY --from=build /app/dataproduct-apps /app/dataproduct-apps/

USER apprunner

CMD ["python", "/app/dataproduct-apps/main.py"]
