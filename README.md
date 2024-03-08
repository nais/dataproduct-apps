# dataproduct-apps

Update BQ with todays apps

## Architecture

dataproduct-apps runs as a Naisjob in all clusters, collecting deployed applications and publishing them to a topic on the nav-infrastructure-kafka cluster.
A separate instance runs as an Application in prod-gcp, consuming from the topic and updating BigQuery with received messages.

## Development

We use [`earthly`](https://earthly.dev) for building.
If you don't have earthly installed, you can use the wrapper [`earthlyw`](https://github.com/mortenlj/earthlyw) in the root of the repository.

Build docker image: `./earthlyw +docker`
Run prospector and pytest: `./earthlyw +tests`

## It's dangerous to go alone! Take this :crossed_swords:

Adding a new feild to the resulting data product in Metabase can be an adventure. Here are the steps to add a new field to the resulting data product:

* Add the new field in `model.py`, `persist.py` and corresponding logic in `collect.py` and tests in `tests/` directory
* Add the new field in BigQuery table `dataproduct_apps.dataproduct_apps_v2` in Google Cloud Console
  * Update the view query for `dataproduct_apps.dataproduct_apps_unique` to include the new field
* Trigger `Sync Database Schema` in Metabase to update the data product schema (needs admin access)
