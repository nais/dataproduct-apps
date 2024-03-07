import logging
import os

from google.cloud import bigquery
from google.cloud.bigquery import DatasetReference, TableReference

from dataproduct_apps import kafka

LOG = logging.getLogger(__name__)


def run():
    client, table = _init_bq()
    return _persist_records(client, table)


def debug_messages(values):
    for i, value in enumerate(values):
        LOG.debug("Row: %05d, Message: %r", i, value)


def _persist_records(client, table):
    row_count = 0
    error_count = 0
    for records in kafka.receive():
        for topic_partition, messages in records.items():
            filtered_records = apply_filters(messages)
            if len(filtered_records) == 0:
                break
            debug_messages(filtered_records)
            errors = client.insert_rows_json(table, filtered_records)
            for error in errors:
                row_id = error["index"]
                row_errors = error["errors"]
                error_count += 1
                LOG.fatal("Errors in row %r:\n%s", row_id, "\n".join(
                    _format_bq_error(e) for e in row_errors))
            if error_count > 0:
                LOG.info(
                    "Inserted at least %d records in total before error.", row_count)
                return row_count, error_count
            row_count += len(messages)
            LOG.info("Inserted %d records from %s",
                     len(messages), topic_partition)
    LOG.info("Inserted %d rows", row_count)
    return row_count, error_count


def apply_filters(messages):
    filtered_records = []
    for message in messages:
        value = message.value

        # Remove messages with "uses_tokenx" flag
        if "uses_tokenx" in value:
            continue

        # Remove invalid outbound_hosts (None values)
        outbound_hosts = [h for h in value["outbound_hosts"] if h is not None]
        value["outbound_hosts"] = outbound_hosts

        filtered_records.append(value)
    return filtered_records


def _format_bq_error(error):
    if "location" in error:
        return "{reason}: {message} @ {location}".format(**error)
    else:
        return "{reason}: {message}".format(**error)


def _init_bq():
    client = bigquery.Client()
    dataset_ref = DatasetReference(
        os.getenv("GCP_TEAM_PROJECT_ID"), "dataproduct_apps")
    table_ref = TableReference(dataset_ref, "dataproduct_apps_v2")
    schema = [
        bigquery.SchemaField(name="collection_time", field_type="DATETIME"),
        bigquery.SchemaField(name="cluster", field_type="STRING"),
        bigquery.SchemaField(name="name", field_type="STRING"),
        bigquery.SchemaField(name="team", field_type="STRING"),
        bigquery.SchemaField(
            name="action_url", field_type="STRING", mode="nullable"),
        bigquery.SchemaField(name="namespace", field_type="STRING"),
        bigquery.SchemaField(name="image", field_type="STRING"),
        bigquery.SchemaField(
            name="ingresses", field_type="STRING", mode="repeated"),
        bigquery.SchemaField(name="uses_token_x",
                             field_type="BOOL", mode="nullable"),
        bigquery.SchemaField(name="uses_auto_instrument",
                             field_type="BOOL", mode="nullable"),
        bigquery.SchemaField(name="uses_loki_logs",
                             field_type="BOOL", mode="nullable"),
        bigquery.SchemaField(name="inbound_apps",
                             field_type="STRING", mode="repeated"),
        bigquery.SchemaField(name="outbound_apps",
                             field_type="STRING", mode="repeated"),
        bigquery.SchemaField(name="outbound_hosts",
                             field_type="STRING", mode="repeated"),
        bigquery.SchemaField(name="read_topics",
                             field_type="STRING", mode="repeated"),
        bigquery.SchemaField(name="write_topics",
                             field_type="STRING", mode="repeated"),
        bigquery.SchemaField(
            name="databases", field_type="STRING", mode="nullable"),
        bigquery.SchemaField(name="dbs", field_type="STRING", mode="repeated"),

    ]
    table = client.create_table(bigquery.Table(
        table_ref, schema=schema), exists_ok=True)
    return client, table
