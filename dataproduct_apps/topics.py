import json
import logging
import os

from dataproduct_apps.crd import Topic
from dataproduct_apps.k8s import init_k8s_client
from dataproduct_apps.model import TopicAccessApp, AppRef

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
    bucket = 'dataproduct-apps-topics2'
    blobname = "topics_" + os.getenv("NAIS_CLUSTER_NAME") + ".json"
    storage_client = storage.Client()
    if storage_client.get_bucket(bucket).blob(blobname).exists():
        storage_client.get_bucket(bucket).delete_blob(blobname)

    storage_client.get_bucket(bucket).blob(blobname).upload_from_string(topics_as_json(topics))
    LOG.info("Wrote %d topics to %s", len(topics), blobname)


def parse_topics(topics: list[Topic]) -> list[TopicAccessApp]:
    list_of_topic_accesses = []
    for topic in topics:
        if topic.metadata.name.startswith("kafkarator-canary"):
            continue
        for acl in topic.spec.acl:
            team = topic.metadata.namespace
            if topic.metadata.labels:
                team = topic.metadata.labels.get("team", team)
            list_of_topic_accesses.append(TopicAccessApp(pool=topic.spec.pool,
                                                         team=team,
                                                         namespace=topic.metadata.namespace,
                                                         topic=topic.metadata.name,
                                                         access=acl.access,
                                                         app=AppRef(namespace=acl.team, name=acl.application)))
    return list_of_topic_accesses
