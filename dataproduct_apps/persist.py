import logging

from google.cloud import bigquery
from dataproduct_apps import kafka


LOG = logging.getLogger(__name__)


def run_forever():
    client = bigquery.Client()
    table_id = f"{client.project}.dataproduct_apps.dataproduct_apps"

    schema = [
        bigquery.SchemaField(name="collection_time", field_type="DATETIME"),
        bigquery.SchemaField(name="cluster", field_type="STRING"),
        bigquery.SchemaField(name="name", field_type="STRING"),
        bigquery.SchemaField(name="team", field_type="STRING"),
        bigquery.SchemaField(name="namespace", field_type="STRING"),
        bigquery.SchemaField(name="image", field_type="STRING"),
        bigquery.SchemaField(name="ingresses", field_type="STRING", mode="repeated"),
    ]
    table = client.create_table(bigquery.Table(table_id, schema=schema), exists_ok=True)

    rows = []

    for app in kafka.receive():
        LOG.info("app: %s", app)
        rows.append(app)

    client.insert_rows_json(table, rows)
