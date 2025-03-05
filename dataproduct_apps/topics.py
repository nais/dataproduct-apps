import json
import logging
from typing import Iterable, Tuple, Optional

from dataproduct_apps import kafka
from dataproduct_apps.config import Settings
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


def write_file_to_cloud_storage(settings: Settings, topics):
    from google.cloud import storage
    bucket = 'dataproduct-apps-topics2'
    blobname = f"topics_{settings.nais_cluster_name}.json"
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


def generate_topic_updates(settings: Settings, topics: list[Topic]) -> Iterable[Tuple[str, Optional[Topic]]]:
    existing_topics = get_existing_topics(settings)
    prefix = f"{settings.nais_cluster_name}:".encode("utf-8")
    topics_to_delete = {k for k in existing_topics.keys() if k.startswith(prefix)}
    updates = deletes = 0
    for topic in topics:
        topic_key = topic.key(settings.nais_cluster_name)
        if topic_key in existing_topics:
            topics_to_delete.discard(topic_key)
            if topic == existing_topics[topic_key]:
                continue
        yield topic_key, topic
        updates += 1
    for key in topics_to_delete:
        yield key, None
        deletes += 1
    LOG.info("Generated %d updates and %d deletes", updates, deletes)


def get_existing_topics(settings: Settings) -> dict[str, Topic]:
    topics = {}
    for records in kafka.receive_from_compacted(settings, settings.topic_topic):
        for topic_partition, messages in records.items():
            for message in messages:
                topics[message.key] = Topic.from_dict(message.value) if message.value else None
    return {key: topic for key, topic in topics.items() if topic is not None}
