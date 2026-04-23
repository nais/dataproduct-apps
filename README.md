# Dataproduct apps

Collects metadata about all deployed Nais applications across every Kubernetes cluster and persists it into Google BigQuery, where it is surfaced as a data product in Metabase.

## Architecture

The pipeline consists of three NaisJobs sharing the same Docker image, differentiated by the `command` field in each manifest.

```
  [Every cluster]                              [prod-gcp only]
  ┌─────────────────────┐                     ┌──────────────────────┐
  │  collect (04:13)    │──► Kafka topic ──►  │  persist (04:43)     │
  │  Kubernetes API     │  nais.dataproduct-  │  → BigQuery          │
  │  → App/Topic/SQL    │      apps           │  nais-prod-b6f2.     │
  └─────────────────────┘                     │  dataproduct_apps    │
                                              └──────────────────────┘
  [prod-gcp only]
  ┌─────────────────────┐
  │  topics (03:45)     │──► Kafka topic (compacted)
  │  Kubernetes API     │  nais.dataproduct-apps-topics
  │  → Topic CRDs       │
  └─────────────────────┘
```

| Job                        | Clusters                                           |
|----------------------------|----------------------------------------------------|
| `dataproduct-apps-collect` | All (`dev-gcp`, `prod-gcp`, `dev-fss`, `prod-fss`) |
| `dataproduct-apps-persist` | `prod-gcp` only                                    |
| `dataproduct-apps-topics`  | `prod-gcp` only                                    |

Both Kafka topics live on the `nav-infrastructure` pool.
The `dataproduct-apps` topic uses delete cleanup with 1-week retention; `dataproduct-apps-topics` is compacted with 6-hour retention.

## FSS vs GCP

The collector runs in every cluster but behaves differently depending on whether it is running in a GCP cluster (`dev-gcp`, `prod-gcp`) or an FSS/on-prem cluster (`dev-fss`, `prod-fss`).
FSS clusters only publish to Kafka — they never write to BigQuery directly.

### Summary table

|                      | GCP clusters                      | FSS clusters                   |
|----------------------|-----------------------------------|--------------------------------|
| GCP credentials      | Workload Identity (automatic)     | Service account secret mounted |
| SQL instances        | Collected                         | Skipped                        |
| Topic cluster lookup | Own cluster                       | Rewrites `-fss` → `-gcp`       |
| BigQuery writes      | Yes (`persist` job in `prod-gcp`) | No                             |

## Development

Run linter and tests:

```sh
mise run lint
mise run test
```

Run integration tests (requires Docker):

```sh
docker compose up -d
mise run integration-test
```

Alternatively, run directly with `uv`:

```sh
uv run ruff check . && uv run ruff format --check .
uv run pytest
uv run pytest --run-integration  # after docker compose up -d
```

For local development against a real cluster, start a `kubectl proxy` on `localhost:8001` — the k8s client will pick it up automatically when not running inside a cluster.

## New fields in Metabase

Adding a new field to the resulting data product in Metabase can be an adventure.
Here are the steps to add a new field to the resulting data product:

* Add the new field in `model.py`, `persist.py` and corresponding logic in `collect.py` and tests in `tests/` directory
* Add the new field in BigQuery table `nais-prod-b6f2.dataproduct_apps.apps` in Google Cloud Console
  * Update the view query for `nais-prod-b6f2.dataproduct_apps.unique` to include the new field
* Trigger `Sync Database Schema` in Metabase to update the data product schema (needs admin access)
