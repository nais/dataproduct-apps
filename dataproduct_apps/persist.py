import logging
import os

from google.cloud import bigquery
from google.cloud.bigquery import DatasetReference, TableReference

from dataproduct_apps import kafka


LOG = logging.getLogger(__name__)


def run():
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

    row_count = 0
    error_count = 0
    for records in kafka.receive():
        if not records:
            # No new messages for over a minute, we're done for this time
            break
        for topic_partition, messages in records:
            error_mapping = client.insert_rows_json(table, (m.value for m in messages))
            for row_id, errors in error_mapping:
                error_count += 1
                LOG.error("Errors in row %r:\n%s", row_id, "\n".join(errors))
            row_count += len(messages)
            LOG.info("Inserted %d records from %s", len(messages), topic_partition)

    LOG.info("inserted %d rows, %d errors", row_count, error_count)
