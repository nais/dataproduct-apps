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
    blobname = "topics_" + os.getenv("NAIS_CLUSTER_NAME")
    storage_client = storage.Client()
    storage_client.get_bucket('gs://dataproduct-apps-topics').delete_blob(blobname)
    storage_client.get_bucket('dataproduct-apps-topics').blob(blobname).upload_from_string(topics_as_json(topics))
    LOG.info("Wrote %d topics to %s", len(topics), blobname)

