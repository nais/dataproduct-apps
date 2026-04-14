# Dataproduct apps

Update BigQuery with todays Nais applications.

## Architecture

Dataproduct-apps runs as a Naisjob in all clusters, collecting deployed applications and publishing them to a topic on the nav-infrastructure-kafka cluster.
A separate instance runs as an Application in prod-gcp, consuming from the topic and updating BigQuery with received messages.

## Development

Run linter and tests locally: `poetry run prospector && poetry run pytest`
Run integration tests: `docker compose up -d && sleep 30 && poetry run pytest --run-integration`

## New fields in Metabase

Adding a new field to the resulting data product in Metabase can be an adventure.
Here are the steps to add a new field to the resulting data product:

* Add the new field in `model.py`, `persist.py` and corresponding logic in `collect.py` and tests in `tests/` directory
* Add the new field in BigQuery table `nais-prod-b6f2.dataproduct_apps.apps` in Google Cloud Console
  * Update the view query for `nais-prod-b6f2.dataproduct_apps.unique` to include the new field
* Trigger `Sync Database Schema` in Metabase to update the data product schema (needs admin access)
