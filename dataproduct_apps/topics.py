import os
import logging

import json

from dataproduct_apps.k8s import init_k8s_client
from dataproduct_apps.crd import Topic

LOG = logging.getLogger(__name__)


def topics_as_json(topics):
    list_of_dicts = []
    for topic in topics:
        list_of_dicts.append(topic.as_dict())

    return json.dumps(list_of_dicts)


def collect_topics():
    init_k8s_client()
    return Topic.list(namespace=None)


def write_file_to_cloud_storage(topics):
    from google.cloud import storage
    bucket = 'dataproduct-apps-topics'
    blobname = "topics_" + os.getenv("NAIS_CLUSTER_NAME") + ".json"
    storage_client = storage.Client()
    if storage_client.get_bucket(bucket).blob(blobname).exists():
        storage_client.get_bucket(bucket).delete_blob(blobname)

    storage_client.get_bucket(bucket).blob(blobname).upload_from_string(topics_as_json(topics))
    LOG.info("Wrote %d topics to %s", len(topics), blobname)

