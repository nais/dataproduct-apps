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
