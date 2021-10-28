import logging
import os

from google.cloud import bigquery
from google.cloud.bigquery import DatasetReference, TableReference

from dataproduct_apps import kafka


LOG = logging.getLogger(__name__)


def run_forever():
    client = bigquery.Client()
    dataset_ref = DatasetReference(os.getenv("GCP_TEAM_PROJECT_ID"), "dataproduct_apps")
    table_ref = TableReference(dataset_ref, "dataproduct_apps")

    schema = [
        bigquery.SchemaField(name="collection_time", field_type="DATETIME"),
        bigquery.SchemaField(name="cluster", field_type="STRING"),
        bigquery.SchemaField(name="name", field_type="STRING"),
        bigquery.SchemaField(name="team", field_type="STRING"),
        bigquery.SchemaField(name="namespace", field_type="STRING"),
        bigquery.SchemaField(name="image", field_type="STRING"),
        bigquery.SchemaField(name="ingresses", field_type="STRING", mode="repeated"),
    ]
    table = client.create_table(bigquery.Table(table_ref, schema=schema), exists_ok=True)

    rows = []

    for app in kafka.receive():
        LOG.info("app: %s", app)
        rows.append(app)

    errors = client.insert_rows_json(table, rows)
    for error in errors:
        LOG.error(error)

    LOG.info("inserted %d rows, %d errors", len(rows), len(errors))
